
import asyncio

from concurrent.futures import ThreadPoolExecutor, as_completed

from langgraph.graph import StateGraph, END
from tavily import TavilyClient

from schemas.data_classes.langraph_state import LangGraphState
from services.qdrant_service import QdrantService
from services.openai_service import OpenAIService
from utils.config import settings
from utils.custom_logger import setup_logger

logger = setup_logger(__name__)


# Retrieval limits per source type
SOURCE_LIMITS = {
    "quran": 5,
    "hadith": 6,
    "tafseer": 3,
    "general_islamic_info": 10,
}


class LangGraphService:
    """
    Optimized 3-node LangGraph pipeline:
        classify_and_search → parallel_retrieve → generate_response
    """

    def __init__(
        self,
        qdrant_service,
        openai_service,
        classification_executor,
        retrival_executor
        ):

        self.qdrant_service = qdrant_service                         # Each QdrantClient can maintain its own HTTP connection pool.
        self.openai_service = openai_service
        self.classification_executor = classification_executor
        self.retrival_executor = retrival_executor
 
        # Tavily is optional — gracefully disabled if key is missing
        self.tavily_client = None
        if settings.TAVILY_API_KEY:

            try:
                self.tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
                logger.info("Tavily web search client initialized.")

            except Exception as e:
                logger.warning("Tavily client failed to initialize: %s. Web search disabled.", e)
                
        else:
            logger.warning("TAVILY_API_KEY not set — web search is disabled.")

        self.graph = self._create_graph()



    # ─────────────────────────────────────────────────────────
    # Node 1: Classify user query + web search (concurrent)
    # ─────────────────────────────────────────────────────────
    def _classify_and_search(self, state: LangGraphState) -> LangGraphState:
        """
        First node: Embeds the query once, then runs web search and
        LLM classification concurrently via ThreadPoolExecutor.
        """
        try:
            # Step 1: Embed query once — this vector is reused in classification cache + all retrievals
            logger.info("Embedding user query...")
            state.query_embedding = self.openai_service.embed_query(state.user_query)

            # Step 2: Run web search and LLM classification concurrently
            
            web_future = self.classification_executor.submit(self._run_web_search, state.user_query)
            classify_future = self.classification_executor.submit(self.openai_service.classify_query, state.user_query, state.query_embedding)

            # Collect web search results
            state.web_search_results = web_future.result()
            logger.info(f"Web search returned {len(state.web_search_results)} results")

            # Collect classification results
            classification_response = classify_future.result()

            if classification_response["status"] == "success":
                classification = classification_response["message"]
                state.required_sources = list(classification.required_sources)
                state.classification_reasoning = classification.reasoning
                logger.info(f"Classification: sources={state.required_sources}, reasoning={state.classification_reasoning}")
            else:
                logger.warning(f"Classification failed: {classification_response['message']}. Falling back to general.")
                state.required_sources = ["general_islamic_info"]

        except Exception as e:
            logger.error(f"Error in _classify_and_search: {e}")
            state.required_sources = ["general_islamic_info"]
            state.error_message = str(e)

        return state



    # ─────────────────────────────────────────────────────────
    # Node 2: Parallel retrieval from all required sources
    # ─────────────────────────────────────────────────────────
    def _parallel_retrieve(self, state: LangGraphState) -> LangGraphState:
        """
        Second node: Dispatches Qdrant searches for all required sources
        concurrently using the pre-computed query embedding.
        """
        if not state.query_embedding:
            logger.error("No query embedding available for retrieval")
            state.error_message = "Query embedding missing"
            return state

        required_sources = state.required_sources
        if not required_sources:
            logger.warning("No required sources identified, defaulting to general_islamic_info")
            required_sources = ["general_islamic_info"]

        logger.info(f"Starting parallel retrieval for sources: {required_sources}")

        future_to_source = {}
        for source in required_sources:
            collection_name = settings.COLLECTION_NAMES.get(source)
            if not collection_name:
                logger.warning(f"No collection configured for source: {source}")
                continue

            limit = SOURCE_LIMITS.get(source, 5)
            future = self.retrival_executor.submit(
                self.qdrant_service.search_by_vector,
                collection_name,
                state.query_embedding,
                limit,
            )
            future_to_source[future] = source

        # Collect results as they complete
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                documents = future.result()
                state.retrieved_documents[source] = documents
                logger.info(f"Retrieved {len(documents)} documents from '{source}'")
            except Exception as e:
                logger.error(f"Error retrieving from '{source}': {e}")
                state.retrieved_documents[source] = []

        return state



    # ─────────────────────────────────────────────────────────
    # Shared helper: Build context string from state
    # ─────────────────────────────────────────────────────────
    def _build_context(self, state: LangGraphState) -> str:
        """
        Compiles all retrieved documents + web search results
        into a single context string. Shared by both the sync
        graph node and the async streaming path.
        """
        context_sections = []

        # Add web search results
        if state.web_search_results:
            web_context = "\n--- WEB SEARCH RESULTS ---\n"
            for i, doc in enumerate(state.web_search_results):
                web_context += f"{i+1}.\nTitle: {doc['title']}\nContent: {doc['content']}\nURL: {doc['url']}\n\n"
            context_sections.append(web_context)

        # Add retrieved documents by source with explicit field extraction for Quranic Arabic text
        for source_type, documents in state.retrieved_documents.items():
            if documents:
                source_context = f"\n--- {source_type.upper()} SOURCES ---\n"
                for i, doc in enumerate(documents):
                    meta = doc.get("metadata", {})
                    if source_type.lower() == "quran":
                        arabic = meta.get("arabic", "")
                        surah = meta.get("surah", "")
                        ayah = meta.get("ayah_number", meta.get("reference", ""))
                        ref = meta.get("reference", f"{surah} {ayah}")
                        source_context += (
                            f"{i+1}.\n"
                            f"Surah: {surah} (Ayah {ayah})\n"
                            f"Arabic Ayah: {arabic}\n"
                            f"English Translation: {doc.get('content', '')}\n"
                            f"Reference: {ref}\n\n"
                        )
                    elif source_type.lower() == "hadith":
                        title = meta.get("title", meta.get("book_name", "Hadith"))
                        narrator = meta.get("narrator", "")
                        source_context += (
                            f"{i+1}.\n"
                            f"Hadith Source: {title}\n"
                            f"Narrator: {narrator}\n"
                            f"Hadith Text: {doc.get('content', '')}\n\n"
                        )
                    else:
                        source_context += f"{i+1}.\nContent: {doc.get('content', '')}\nMetadata: {meta}\n\n"
                context_sections.append(source_context)

        return "\n\n".join(context_sections)


    # ─────────────────────────────────────────────────────────
    # Node 3: Assemble context and generate final response
    # ─────────────────────────────────────────────────────────
    def _generate_response(self, state: LangGraphState) -> LangGraphState:
        """
        Third node: Compiles all retrieved documents + web search results 
        into a single context string and calls LLM for the final response.
        """
        try:
            if state.error_message and not state.retrieved_documents:
                state.final_response = f"I apologize, but I encountered an error: {state.error_message}"
                return state

            full_context = self._build_context(state)

            if not full_context.strip():
                state.final_response = "I could not find relevant information in the Islamic knowledge base for your query. Please try rephrasing your question or consult a qualified Islamic scholar."
                return state

            logger.info("Generating final response from LLM...")
            response = self.openai_service.generate_response(state.user_query, full_context)

            if response["status"] == "success":
                state.final_response = response["message"]
                logger.info("Response generated successfully")
            else:
                state.final_response = f"I apologize, but I encountered an error while generating the response: {response['message']}"
                logger.error(f"Response generation failed: {response['message']}")

        except Exception as e:
            logger.error(f"Error in _generate_response: {e}")
            state.final_response = f"I apologize, but I encountered an error: {str(e)}"

        return state



    # ─────────────────────────────────────────────────────────
    # Helper: Web search via Tavily
    # ─────────────────────────────────────────────────────────
    def _run_web_search(self, query: str) -> list:
        """Run Tavily web search. Returns list of dicts with content/url/title."""
        try:
            if not self.tavily_client:
                logger.warning("Tavily client not initialized, skipping web search")
                return []

            search_results = self.tavily_client.search(
                query=f"{query} in Islam.",
                search_depth="advanced",
                max_results=1,
                include_answer=True,
                include_raw_content=True,
                timeout=30,
            )

            web_documents = []
            for result in search_results.get("results", []):
                web_documents.append({
                    "content": result.get("content", ""),
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                })

            return web_documents

        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []



    # ─────────────────────────────────────────────────────────
    # Graph definition: 3 nodes, linear flow
    # ─────────────────────────────────────────────────────────
    def _create_graph(self):
        """
        Build the optimized 3-node LangGraph:
            classify_and_search → parallel_retrieve → generate_response → END
        """
        workflow = StateGraph(LangGraphState)

        workflow.add_node("classify_and_search", self._classify_and_search)
        workflow.add_node("parallel_retrieve", self._parallel_retrieve)
        workflow.add_node("generate_response", self._generate_response)

        workflow.set_entry_point("classify_and_search")
        workflow.add_edge("classify_and_search", "parallel_retrieve")
        workflow.add_edge("parallel_retrieve", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()



    # ─────────────────────────────────────────────────────────
    # Public API: process a user query end-to-end (synchronous)
    # ─────────────────────────────────────────────────────────
    def query(self, user_query: str) -> str:
        """
        Main entry point — processes a user query through the full pipeline.
        Returns the generated response string.
        """
        try:
            initial_state = LangGraphState(user_query=user_query)

            logger.info(f"Processing query: {user_query[:80]}...")
            final_state = self.graph.invoke(initial_state)

            return final_state["final_response"]

        except Exception as e:
            logger.error(f"Error in query pipeline: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"



    # ─────────────────────────────────────────────────────────
    # Public API: stream a user query (async generator)
    # ─────────────────────────────────────────────────────────
    async def query_stream(self, user_query: str):
        """
        Async generator that yields SSE event dicts.
        Phase 1: classify + retrieve (blocking I/O, yields status events)
        Phase 2: stream LLM tokens one-by-one (yields token events)
        Phase 3: yield done event with full response
        """
        try:
            logger.info(f"[STREAM] Processing query: {user_query[:80]}...")

            # Phase 1: Classification + Retrieval (non-streaming I/O work)
            yield {"status": "searching", "message": "Analyzing and retrieving from Islamic sources..."}

            initial_state = LangGraphState(user_query=user_query)

            # Run classify_and_search in a thread (it's synchronous / CPU-bound)
            state = await asyncio.to_thread(self._classify_and_search, initial_state)
            # Run parallel_retrieve in a thread
            state = await asyncio.to_thread(self._parallel_retrieve, state)

            # Check for errors after retrieval
            if state.error_message and not state.retrieved_documents:
                yield {"done": True, "full_response": f"I apologize, but I encountered an error: {state.error_message}"}
                return

            # Phase 2: Build context
            yield {"status": "generating", "message": "Composing response..."}

            full_context = self._build_context(state)

            if not full_context.strip():
                yield {"done": True, "full_response": "I could not find relevant information in the Islamic knowledge base for your query. Please try rephrasing your question or consult a qualified Islamic scholar."}
                return

            # Phase 3: Stream LLM response token-by-token
            logger.info("[STREAM] Starting LLM token streaming...")
            full_response = ""

            async for token in self.openai_service.generate_response_stream(user_query, full_context):
                full_response += token
                yield {"token": token, "done": False}

            logger.info("[STREAM] Response streamed successfully")
            yield {"done": True, "full_response": full_response}

        except Exception as e:
            logger.error(f"Error in query_stream: {e}")
            yield {"done": True, "full_response": f"I apologize, but I encountered an error: {str(e)}"}


