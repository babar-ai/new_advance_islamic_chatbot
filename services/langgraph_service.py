
import asyncio
import re
from typing import Optional, List, Dict, Any

from concurrent.futures import ThreadPoolExecutor, as_completed

from langgraph.graph import StateGraph, END
from tavily import TavilyClient

from schemas.data_classes.langraph_state import LangGraphState
from services.qdrant_service import QdrantService
from services.openai_service import OpenAIService
from utils.config import settings
from utils.custom_logger import setup_logger

from langsmith import traceable

from services import rerank_service


logger = setup_logger(__name__)


# How many candidates to fetch from Qdrant (3-4× the final limit gives the
# reranker enough choices without blowing up RAM or latency).
SOURCE_RETRIEVE_LIMITS = {
    "quran": 15,
    "hadith": 18,
    "tafseer": 15,
    "general_islamic_info": 20,
}

# Final number of documents kept per source AFTER reranking.
# When reranking is disabled these are used directly as retrieval limits.
SOURCE_FINAL_LIMITS = {
    "quran": 3,
    "hadith": 5,
    "tafseer": 2,
    "general_islamic_info": 6,
}


def _extract_source_url(meta: dict) -> Optional[str]:
    """Extracts authentic source URL directly from document metadata payload."""
    if not isinstance(meta, dict):
        return None
    for key in (
        "En_source_url",
        "source_url",
        "url",
        "link",
        "source_link",
        "Tafsir_Source",
    ):
        val = meta.get(key)
        if val and isinstance(val, str) and val.strip().startswith(("http://", "https://")):
            return val.strip()
    return None



def _remove_sources_section(text: str) -> str:
    """Strips out redundant '### 📚 Sources & References' section from the final response."""
    if not text:
        return text
    header_pattern = r"(?:^|\n)(?:#{1,4}\s*)?(?:📚\s*)?Sources\s*(?:&|and)\s*References\s*:?\s*(?:\r?\n|$)"
    match = re.search(header_pattern, text, re.IGNORECASE)
    if not match:
        return text

    before = text[:match.start()].rstrip()
    after = text[match.end():]

    disclaimer_match = re.search(
        r"(?:^|\n)(?:[*_>\s]*)(?:And\s+Allah\s+knows\s+best|وَاللَّ?هُ\s*أَعْلَمُ|Please\s+(?:always\s+)?consult\s+qualified\s+scholars)[\s\S]*$",
        after,
        re.IGNORECASE,
    )
    if disclaimer_match:
        return f"{before}\n\n{disclaimer_match.group(0).strip()}"
    return before


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

        # ── BM25 sparse encoder (fastembed) for hybrid search ─────────
        # Loaded once at startup and shared across all retrieval calls.
        # query_embed() is called per-request in _parallel_retrieve.

        self._bm25_model = None

        if settings.HYBRID_SEARCH_ENABLED:

            try:
                from fastembed.sparse.bm25 import Bm25
                self._bm25_model = Bm25(model_name="Qdrant/bm25", language="english")
                logger.info("BM25 sparse encoder (fastembed) loaded for hybrid search.")

            except ImportError:
                logger.warning(
                    "fastembed is not installed — hybrid search disabled. "
                    "Run: pip install fastembed"
                )

            except Exception as e:
                logger.warning("Failed to load BM25 model: %s — hybrid search disabled.", e)

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


                if hasattr(classification, "filters") and classification.filters:
                    filter_dict = classification.filters.model_dump(exclude_none=True)
                    setattr(state, "filters", filter_dict if filter_dict else None)
                else:
                    setattr(state, "filters", None)

                logger.info(f"Classification: sources={state.required_sources}, reasoning={state.classification_reasoning}, filters={getattr(state, 'filters', None)}")
            
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

        When settings.HYBRID_SEARCH_ENABLED=True, each collection search uses
        hybrid RRF fusion (dense semantic + BM25 sparse keyword vectors).
        The BM25 sparse vector for the user query is computed once here and
        reused for all collection searches in this node.

        Falls back to dense-only search if hybrid fails or is disabled.
        """
    
        if not state.query_embedding:
            logger.error("No query embedding available for retrieval")
            state.error_message = "Query embedding missing"
            return state
 
        required_sources = state.required_sources

        if not required_sources:
            logger.warning("No required sources identified, defaulting to general_islamic_info")
            required_sources = ["general_islamic_info"]

        filters = getattr(state, "filters", None)
        logger.info(f"Starting parallel retrieval for sources: {required_sources}, filters: {filters}")

        # ── Compute BM25 sparse vector for the query once (reused for all sources) ──
        sparse_indices: List[int] = []
        sparse_values: List[float] = []
        use_hybrid = settings.HYBRID_SEARCH_ENABLED and self._bm25_model is not None

        if use_hybrid:
            try:
                sparse_results = list(self._bm25_model.query_embed(state.user_query))
                if sparse_results:
                    sparse_emb = sparse_results[0]
                    sparse_indices = sparse_emb.indices.tolist()
                    sparse_values = sparse_emb.values.tolist()
                    logger.info(
                        "BM25 sparse vector computed for query (%d non-zero terms).",
                        len(sparse_indices),
                    )
                else:
                    logger.warning("BM25 returned empty sparse vector — falling back to dense-only.")
                    use_hybrid = False
            except Exception as e:
                logger.warning("BM25 query encoding failed: %s — falling back to dense-only.", e)
                use_hybrid = False

        future_to_source = {}

        for source in required_sources:
            collection_name = settings.COLLECTION_NAMES.get(source)

            if not collection_name:
                logger.warning(f"No collection configured for source: {source}")
                continue

            # Oversample when reranking is enabled; otherwise use final limits directly.
            if settings.RERANKER_ENABLED:
                limit = SOURCE_RETRIEVE_LIMITS.get(source, 15)
            else:
                limit = SOURCE_FINAL_LIMITS.get(source, 5)
            qdrant_filter = self.qdrant_service.build_qdrant_filter(collection_name, filters)

            if use_hybrid:
                # Hybrid search: dense + BM25 sparse via RRF
                future = self.retrival_executor.submit(
                    self.qdrant_service.hybrid_search_by_vector,
                    collection_name,
                    state.query_embedding,
                    sparse_indices,
                    sparse_values,
                    limit,
                    qdrant_filter,
                )
            else:
                # Dense-only fallback
                future = self.retrival_executor.submit(
                    self.qdrant_service.search_by_vector,
                    collection_name,
                    state.query_embedding,
                    limit,
                    qdrant_filter,
                )

            future_to_source[future] = (source, collection_name, qdrant_filter, limit, use_hybrid)

        # Collect results as they complete
        for future in as_completed(future_to_source):
            source, collection_name, qdrant_filter, limit, was_hybrid = future_to_source[future]

            try:
                documents = future.result()

                # If filtered search returned nothing, retry without metadata filters
                if not documents and qdrant_filter is not None:
                    logger.warning(
                        "Filtered search returned 0 docs for '%s'. Falling back to unfiltered search...",
                        source,
                    )
                    if was_hybrid:
                        documents = self.qdrant_service.hybrid_search_by_vector(
                            collection_name,
                            state.query_embedding,
                            sparse_indices,
                            sparse_values,
                            limit,
                            query_filter=None,
                        )
                    else:
                        documents = self.qdrant_service.search_by_vector(
                            collection_name,
                            state.query_embedding,
                            limit,
                            query_filter=None,
                        )

                state.retrieved_documents[source] = documents
                logger.info(f"Retrieved {len(documents)} documents from '{source}' (hybrid={was_hybrid})")

            except Exception as e:
                logger.error(f"Error retrieving from '{source}': {e}")
                state.retrieved_documents[source] = []

        return state




    # ─────────────────────────────────────────────────────────
    # Node 2.5: Rerank retrieved documents (optional)
    # ─────────────────────────────────────────────────────────
    def _rerank_documents(self, state: LangGraphState) -> LangGraphState:
        """
        Optional node: applies FlashRank cross-encoder reranking to the
        retrieved documents for each source, keeping only the top-K most
        relevant results before they are assembled into the LLM context.

        Mutates state.retrieved_documents in-place — no extra state field needed.
        Falls back silently to top-K truncation if FlashRank is unavailable.
        """
        if not settings.RERANKER_ENABLED:
            return state

        for source, documents in state.retrieved_documents.items():
            if not documents:
                continue

            top_n = SOURCE_FINAL_LIMITS.get(source, 5)

            reranked = rerank_service.rerank(
                query=state.user_query,
                documents=documents,
                top_n=top_n,
                score_threshold=settings.RERANKER_SCORE_THRESHOLD,
            )

            state.retrieved_documents[source] = reranked
            logger.info(
                "Reranked '%s': %d → %d docs", source, len(documents), len(reranked)
            )

        return state


    # ─────────────────────────────────────────────────────────
    # Shared helper: Build context string from state
    # ─────────────────────────────────────────────────────────
    def _build_context(self, state: LangGraphState) -> str:
        """
        Compiles all retrieved documents + web search results into a single context string.
        Source links are dynamically extracted directly from the Qdrant metadata payload.
        """
        context_sections = []

        # 1. Add web search results with URLs
        if state.web_search_results:
            web_context = "\n--- WEB SEARCH RESULTS ---\n"
            for i, doc in enumerate(state.web_search_results):
                title = doc.get("title", "Web Source")
                url = doc.get("url", "").strip()
                content = doc.get("content", "")
                web_context += (
                    f"{i+1}.\n"
                    f"Title: {title}\n"
                    f"Content: {content}\n"
                )
                DISALLOWED_DOMAINS = (
                    "facebook.com", "instagram.com", "twitter.com", "x.com",
                    "reddit.com", "pinterest.com", "tiktok.com", "youtube.com"
                )
                if url and not any(d in url.lower() for d in DISALLOWED_DOMAINS):
                    web_context += f"Source URL: {url}\n"
                web_context += "\n"
            context_sections.append(web_context)

        # 2. Add retrieved documents by source, extracting authentic source links directly from metadata
        for source_type, documents in state.retrieved_documents.items():
            if not documents:
                continue

            s_type = source_type.lower()
            source_context = f"\n--- {source_type.upper()} SOURCES ---\n"

            for i, doc in enumerate(documents):
                meta = doc.get("metadata", {})
                content = doc.get("content", "")

                # ── 1. Quran Collection: Direct verse link to https://quran.com/{surah}:{ayah} ──
                if "quran" in s_type:
                    arabic = meta.get("arabic", "")
                    surah = meta.get("surah", "")
                    ayah = meta.get("ayah_number", meta.get("reference", ""))
                    ref = meta.get("reference", f"{surah} {ayah}")

                    ref_str = str(meta.get("reference", "")).strip()
                    if ref_str and ":" in ref_str:
                        quran_url = f"https://quran.com/{ref_str}"
                    else:
                        surah_val = meta.get("surah_number") or meta.get("surah", "")
                        ayah_val = meta.get("ayah_number", "")
                        quran_url = f"https://quran.com/{surah_val}:{ayah_val}" if (surah_val and ayah_val) else "https://quran.com"

                    source_context += (
                        f"{i+1}.\n"
                        f"Surah: {surah} (Ayah {ayah})\n"
                        f"Arabic Ayah: {arabic}\n"
                        f"English Translation: {content}\n"
                        f"Reference: {ref}\n"
                        f"Source URL: {quran_url}\n\n"
                    )

                # ── 2. Hadith Collection: Dynamic extraction from chunk metadata ──
                elif "hadith" in s_type:
                    title = meta.get("title") or meta.get("book_name") or "Hadith Collection"
                    narrator = meta.get("narrator", "")
                    source_url = _extract_source_url(meta)

                    source_context += (
                        f"{i+1}.\n"
                        f"Hadith Collection: {title}\n"
                        f"Narrator: {narrator}\n"
                        f"Hadith Text: {content}\n"
                    )
                    if source_url:
                        source_context += f"Source URL: {source_url}\n"
                    source_context += "\n"

                # ── 3. Tafsir Collection: Dynamic extraction from chunk metadata ──
                elif "tafsir" in s_type or "tafseer" in s_type:
                    tafsir_name = (
                        meta.get("En_tafsir_source")
                        or meta.get("tafsir_source")
                        or "Tafsir Commentary"
                    )
                    surah = meta.get("surah", "")
                    ayah = meta.get("ayah_number", "")
                    source_url = _extract_source_url(meta)

                    source_context += (
                        f"{i+1}.\n"
                        f"Tafsir Commentary: {tafsir_name}\n"
                        f"Surah: {surah} (Ayah {ayah})\n"
                        f"Commentary Text: {content}\n"
                    )
                    if source_url:
                        source_context += f"Source URL: {source_url}\n"
                    source_context += "\n"

                # ── 4. General Islamic Info: Dynamic extraction from chunk metadata ──
                else:
                    book_name = meta.get("book_name") or meta.get("title") or "Islamic Knowledge Base"
                    source_url = _extract_source_url(meta)

                    source_context += (
                        f"{i+1}.\n"
                        f"Book / Source: {book_name}\n"
                        f"Content: {content}\n"
                    )
                    if source_url:
                        source_context += f"Source URL: {source_url}\n"
                    source_context += "\n"

            context_sections.append(source_context)

        return "\n\n".join(context_sections)


    # ─────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────
    # Node 3: Assemble context and generate final response
    # ─────────────────────────────────────────────────────────
    async def _generate_response(self, state: LangGraphState) -> LangGraphState:
        """
        Third node: Compiles all retrieved documents + web search results 
        into a single context string and calls LLM asynchronously for the final response.
        Enables LangGraph native astream to capture token chunks.
        """
        try:
            if state.error_message and not state.retrieved_documents:
                state.final_response = f"I apologize, but I encountered an error: {state.error_message}"
                return state

            full_context = self._build_context(state)

            if not full_context.strip():
                state.final_response = "I could not find relevant information in the Islamic knowledge base for your query. Please try rephrasing your question or consult a qualified Islamic scholar."
                return state

            logger.info("Generating final response from LLM via agenerate_response...")
            response = await self.openai_service.agenerate_response(state.user_query, full_context)

            if response["status"] == "success":
                state.final_response = _remove_sources_section(response["message"])
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
    @traceable(name="run_web_search", run_type="tool")
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
        Build the 4-node LangGraph pipeline:
            classify_and_search → parallel_retrieve → rerank_documents → generate_response → END

        rerank_documents is a thin node that cross-encoder re-scores and trims
        the retrieved candidates; it is a no-op when RERANKER_ENABLED=False.
        """
        workflow = StateGraph(LangGraphState)

        workflow.add_node("classify_and_search", self._classify_and_search)
        workflow.add_node("parallel_retrieve", self._parallel_retrieve)
        workflow.add_node("rerank_documents", self._rerank_documents)
        workflow.add_node("generate_response", self._generate_response)

        workflow.set_entry_point("classify_and_search")
        workflow.add_edge("classify_and_search", "parallel_retrieve")
        workflow.add_edge("parallel_retrieve", "rerank_documents")
        workflow.add_edge("rerank_documents", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()



    # ─────────────────────────────────────────────────────────
    # Public API: process a user query end-to-end
    # ─────────────────────────────────────────────────────────
    async def aquery(self, user_query: str) -> str:
        """
        Process a user query asynchronously through the full compiled LangGraph.
        Returns the generated response string.
        """
        try:
            initial_state = LangGraphState(user_query=user_query)
            logger.info(f"Processing query asynchronously: {user_query[:80]}...")
            final_state = await self.graph.ainvoke(initial_state)

            if isinstance(final_state, dict):
                return final_state.get("final_response", "")
            return final_state.final_response

        except Exception as e:
            logger.error(f"Error in aquery pipeline: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"


    def query(self, user_query: str) -> str:
        """
        Synchronous entry point — wraps aquery.
        """
        try:
            return asyncio.run(self.aquery(user_query))
        except RuntimeError:
            # Fallback if already inside a running loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, self.aquery(user_query)).result()



    # ─────────────────────────────────────────────────────────
    # Public API: stream a user query via LangGraph native astream
    # ─────────────────────────────────────────────────────────
    async def query_stream(self, user_query: str):
        """
        Async generator that yields SSE event dicts using LangGraph's native astream().
        Executes the full compiled StateGraph:
            classify_and_search → parallel_retrieve → generate_response → END

        - Mode 'updates': captures node completion events (progress updates).
        - Mode 'messages': captures token-by-token streaming directly from the LLM node.
        """
        try:
            logger.info(f"[STREAM] Processing query via LangGraph astream: {user_query[:80]}...")

            # Phase 1: Initial searching status
            yield {"status": "searching", "message": "Analyzing and retrieving from Islamic sources..."}

            initial_state = LangGraphState(user_query=user_query)
            full_response = ""

            # Execute native LangGraph astream
            async for mode, payload in self.graph.astream(
                initial_state,
                stream_mode=["updates", "messages"],
            ):
                if mode == "updates":
                    # Transition from retrieval to generation
                    if "parallel_retrieve" in payload:
                        yield {"status": "generating", "message": "Composing response..."}
                    elif "generate_response" in payload:
                        node_state = payload["generate_response"]
                        if isinstance(node_state, dict):
                            full_response = node_state.get("final_response", full_response)
                        elif hasattr(node_state, "final_response"):
                            full_response = node_state.final_response or full_response

                elif mode == "messages":
                    msg, meta = payload
                    # Stream tokens emitted exclusively by the generate_response node
                    if meta.get("langgraph_node") == "generate_response" and msg.content:
                        full_response += msg.content
                        yield {"token": msg.content, "done": False}

            logger.info("[STREAM] Response streamed successfully via LangGraph native astream")
            yield {"done": True, "full_response": _remove_sources_section(full_response)}

        except Exception as e:
            logger.error(f"Error in query_stream: {e}")
            yield {"done": True, "full_response": f"I apologize, but I encountered an error: {str(e)}"}