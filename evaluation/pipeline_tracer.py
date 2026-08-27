"""
pipeline_tracer.py
------------------
A thin wrapper around LangGraphService that captures the full pipeline
state (retrieved contexts + generated answer) needed for RAGAS evaluation.

Production code is NOT modified — this is evaluation-only.
"""

import sys
import time
from pathlib import Path
from typing import Optional

# Ensure project root is on path when run directly
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schemas.data_classes.langraph_state import LangGraphState
from services.langgraph_service import LangGraphService
from utils.custom_logger import setup_logger

logger = setup_logger(__name__)


class PipelineTrace:
    """Holds captured data from a single pipeline run."""

    def __init__(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        sources_used: list[str],
        latency_ms: float,
        error: Optional[str] = None,
    ):
        self.question = question
        self.answer = answer
        self.contexts = contexts          # flat list of context strings for RAGAS
        self.sources_used = sources_used  # e.g. ["quran", "hadith"]
        self.latency_ms = latency_ms
        self.error = error

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "contexts": self.contexts,
            "sources_used": self.sources_used,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
        }


class TracingLangGraphService(LangGraphService):
    """
    Subclass of LangGraphService that captures the full LangGraphState
    after the pipeline runs — exposing retrieved_documents and final_response
    so RAGAS can use them.

    The graph nodes (_classify_and_search, _parallel_retrieve, _generate_response)
    are inherited unchanged from LangGraphService.
    """

    def query_with_trace(self, user_query: str) -> PipelineTrace:
        """
        Runs the full LangGraph pipeline and returns a PipelineTrace
        containing all the data needed for RAGAS evaluation.
        """
        start = time.perf_counter()
        error = None

        try:
            initial_state = LangGraphState(user_query=user_query)
            final_state_dict = self.graph.invoke(initial_state)

            # Extract fields from returned state dict
            answer: str = final_state_dict.get("final_response", "")
            retrieved_docs: dict = final_state_dict.get("retrieved_documents", {})
            web_results: list = final_state_dict.get("web_search_results", [])
            sources_used: list = final_state_dict.get("required_sources", [])

            # Build flat list of context strings for RAGAS
            # RAGAS expects: contexts = List[str], one string per retrieved chunk
            contexts: list[str] = []

            # Add Qdrant retrieved documents
            for source_type, docs in retrieved_docs.items():
                for doc in docs:
                    content = doc.get("content", "").strip()
                    metadata = doc.get("metadata", {})
                    # Prefix with source type for clarity in evaluation
                    if content:
                        prefix = f"[{source_type.upper()}]"
                        if metadata:
                            prefix += f" {metadata}"
                        contexts.append(f"{prefix}\n{content}")

            # Add web search results as additional contexts
            for web_doc in web_results:
                content = web_doc.get("content", "").strip()
                title = web_doc.get("title", "")
                url = web_doc.get("url", "")
                if content:
                    contexts.append(f"[WEB: {title}] ({url})\n{content}")

        except Exception as e:
            logger.error("Pipeline trace failed for query '%s': %s", user_query[:60], e)
            answer = ""
            contexts = []
            sources_used = []
            error = str(e)

        latency_ms = (time.perf_counter() - start) * 1000

        trace = PipelineTrace(
            question=user_query,
            answer=answer,
            contexts=contexts,
            sources_used=sources_used,
            latency_ms=latency_ms,
            error=error,
        )

        logger.info(
            "Pipeline trace complete | sources=%s | contexts=%d | latency=%.0fms",
            sources_used,
            len(contexts),
            latency_ms,
        )
        return trace
