
import json
import numpy as np
from typing import Any, Optional, List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
from cachetools import TTLCache

from schemas.structured_outputs.query_classification import QueryClassificationSchema
from services.prompt_templates import QUERY_CLASSIFICATION_PROMPT, ENGLISH_RESPONSE_PROMPT
from utils.custom_logger import setup_logger
from utils.config import settings

logger = setup_logger(__name__)


class OpenAIService:
    """Handles all OpenAI interactions: classification, embedding, and response generation."""

    def __init__(self):

        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )

        # Classification cache — Layer 1: exact string match (TTL 1 hour, max 500 entries)
        self._classification_cache = TTLCache(maxsize=500, ttl=3600)

        # Classification cache — Layer 2: semantic similarity cache
        # Stores (embedding_vector, classification_result) tuples
        self._semantic_cache: List[tuple] = []
        self._semantic_cache_max_size = 200
        self._semantic_similarity_threshold = 0.92



    def classify_query(self, query: str, query_embedding: Optional[List[float]] = None) -> dict:
        """
        Classify a query to determine which Islamic sources to search.
        Uses 2-layer caching: exact match → semantic similarity → LLM fallback.
        """

        # Layer 1: Exact cache lookup (normalized query string)
        normalized = query.strip().lower()
        if normalized in self._classification_cache:
            logger.info("Classification cache HIT (exact match)")
            return {"status": "success", "message": self._classification_cache[normalized]}

        # Layer 2: Semantic similarity cache 
        if query_embedding and self._semantic_cache:
            for cached_emb, cached_result in self._semantic_cache:
                similarity = self._cosine_similarity(query_embedding, cached_emb)
                if similarity > self._semantic_similarity_threshold:
                    logger.info(f"Classification cache HIT (semantic, similarity={similarity:.3f})")
                    return {"status": "success", "message": cached_result}

        # Layer 3: LLM call (cache miss)
        logger.info("Classification cache MISS — calling LLM")
        result = self._process_request(
            QUERY_CLASSIFICATION_PROMPT, query, QueryClassificationSchema
        )

        if result["status"] == "success":
            classification = result["message"]
            # Store in exact cache
            self._classification_cache[normalized] = classification
            # Store in semantic cache (if we have the embedding)
            
            if query_embedding:
                self._semantic_cache.append((query_embedding, classification))
                if len(self._semantic_cache) > self._semantic_cache_max_size:
                    self._semantic_cache.pop(0)

        return result



    def embed_query(self, query: str) -> List[float]:
        """Embed a query string into a vector. Called once per request."""
        return self.embeddings.embed_query(query)



    def generate_response(self, query: str, context: str) -> dict:
        """Generate the final comprehensive Islamic response using retrieved context."""
        prompt = ENGLISH_RESPONSE_PROMPT.replace("{context}", context)
        return self._process_request(prompt, query, schema=None)



    def _process_request(self, prompt: str, text: str, schema=None) -> dict:
        """Generic method to handle requests to OpenAI via LangChain."""
        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=text)
            ]

            # Use structured output if schema is provided, otherwise use plain LLM
            llm_instance = self.llm.with_structured_output(schema) if schema else self.llm
            response = llm_instance.invoke(messages)

            return {
                "status": "success",
                "message": response.content if not schema else response
            }

        except Exception as e:
            logger.error(f"Error in _process_request: {e}")
            return {"status": "error", "message": f"Error processing request: {e}"}



    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(vec_a)
        b = np.array(vec_b)
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm == 0:
            return 0.0
        return float(dot / norm)


# Module-level singleton instance
openai_service = OpenAIService()
