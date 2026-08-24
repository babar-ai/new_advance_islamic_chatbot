
import json
import numpy as np
from typing import Any, Optional, List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
from cachetools import TTLCache
import redis

from schemas.structured_outputs.query_classification import QueryClassificationSchema
from services.prompt_templates import QUERY_CLASSIFICATION_PROMPT, ENGLISH_RESPONSE_PROMPT
from services.qdrant_service import QdrantService
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

        # In-memory fallback caches
        self._classification_cache = TTLCache(maxsize=500, ttl=3600)  
        self._semantic_cache: List[tuple] = []
        self._semantic_cache_max_size = 200
        self._semantic_similarity_threshold = 0.85

        # Initialize Redis connection (Layer 1)
        self.redis_client = None
        try:
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_timeout=2.0
            )
            r.ping()
            self.redis_client = r
            logger.info("Connected to Redis at %s:%d successfully.", settings.REDIS_HOST, settings.REDIS_PORT)
        except Exception as e:
            logger.warning("Redis not available (%s). Layer 1 will fallback to in-memory cache.", e)

        # Initialize Qdrant Service (Layer 2)
        try:
            self.qdrant_service = QdrantService()
        except Exception as e:
            self.qdrant_service = None
            logger.warning("Qdrant service connection warning for caching: %s", e)



    def _get_from_exact_cache(self, normalized_query: str) -> Optional[QueryClassificationSchema]:
        """Layer 1 exact match: Checks Redis key-value first, then in-memory cache."""
        # 1. Try Redis
        if self.redis_client:
            try:
                cached_json = self.redis_client.get(f"exact_cache:{normalized_query}")
                if cached_json:
                    logger.info("Classification cache HIT (Layer 1 - Redis exact match)")
                    data = json.loads(cached_json)
                    return QueryClassificationSchema(**data)
            except Exception as e:
                logger.warning("Redis exact match error: %s", e)

        # 2. Fallback to in-memory TTLCache
        if normalized_query in self._classification_cache:
            logger.info("Classification cache HIT (Layer 1 - In-Memory exact match)")
            return self._classification_cache[normalized_query]

        return None

    def _get_from_semantic_cache(self, query_embedding: List[float]) -> Optional[dict]:
        """Layer 2 semantic match: Checks Qdrant vector collection first, then in-memory vectors."""
        # 1. Try Qdrant Cache Collection
        if self.qdrant_service:
            try:
                qdrant_hit = self.qdrant_service.search_cache_vector(
                    collection_name=settings.CLASSIFICATION_CACHE_COLLECTION_NAME,
                    query_vector=query_embedding,
                    score_threshold=self._semantic_similarity_threshold
                )
                if qdrant_hit:
                    logger.info("Classification cache HIT (Layer 2 - Qdrant vector match, sim=%.4f)", qdrant_hit["similarity_score"])
                    cls_obj = QueryClassificationSchema(**qdrant_hit["classification"])
                    return {
                        "classification": cls_obj,
                        "similarity_score": qdrant_hit["similarity_score"],
                        "matched_query": qdrant_hit["matched_query"]
                    }
            except Exception as e:
                logger.warning("Qdrant semantic cache search error: %s", e)

        # 2. Fallback to in-memory vector list
        if self._semantic_cache:
            best_similarity = 0.0
            best_result = None
            best_query = None
            for cached_emb, cached_result, cached_query in self._semantic_cache:
                similarity = self._cosine_similarity(query_embedding, cached_emb)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_result = cached_result
                    best_query = cached_query
            if best_similarity > self._semantic_similarity_threshold:
                logger.info("Classification cache HIT (Layer 2 - In-Memory vector match, sim=%.4f)", best_similarity)
                return {
                    "classification": best_result,
                    "similarity_score": round(best_similarity, 4),
                    "matched_query": best_query
                }

        return None

    def _write_to_caches(self, query: str, query_embedding: Optional[List[float]], classification: QueryClassificationSchema) -> None:
        """Writes classification result to Redis, Qdrant collection, and in-memory caches."""
        normalized = query.strip().lower()

        # Save to Memory
        self._classification_cache[normalized] = classification
        if query_embedding:
            self._semantic_cache.append((query_embedding, classification, normalized))
            if len(self._semantic_cache) > self._semantic_cache_max_size:
                self._semantic_cache.pop(0)

        # Save to Redis (Layer 1)
        if self.redis_client:
            try:
                json_str = classification.model_dump_json()
                if settings.REDIS_TTL > 0:
                    self.redis_client.setex(f"exact_cache:{normalized}", settings.REDIS_TTL, json_str)
                else:
                    self.redis_client.set(f"exact_cache:{normalized}", json_str)
                logger.info("Saved exact match to Redis for '%s'", normalized)
            except Exception as e:
                logger.warning("Failed to save exact cache to Redis: %s", e)

        # Save to Qdrant Cache Collection (Layer 2)
        if self.qdrant_service and query_embedding:
            try:
                self.qdrant_service.upsert_cache_vector(
                    collection_name=settings.CLASSIFICATION_CACHE_COLLECTION_NAME,
                    query_text=query,
                    query_vector=query_embedding,
                    classification_payload=classification.model_dump()
                )
            except Exception as e:
                logger.warning("Failed to save vector cache to Qdrant: %s", e)

    def classify_query(self, query: str, query_embedding: Optional[List[float]] = None) -> dict:
        """
        Classify a query to determine which Islamic sources to search.
        Uses 2-layer persistent caching (Redis + Qdrant) with in-memory fallbacks.
        """
        normalized = query.strip().lower()

        # Layer 1 Check
        l1_match = self._get_from_exact_cache(normalized)
        if l1_match:
            return {"status": "success", "message": l1_match}

        # Layer 2 Check
        if query_embedding:
            l2_match = self._get_from_semantic_cache(query_embedding)
            if l2_match:
                return {"status": "success", "message": l2_match["classification"]}

        # Layer 3: LLM Fallback Call
        logger.info("Classification cache MISS — calling LLM")
        result = self._process_request(QUERY_CLASSIFICATION_PROMPT, query, QueryClassificationSchema)

        if result["status"] == "success":
            classification = result["message"]
            self._write_to_caches(query, query_embedding, classification)

        return result

    def classify_query_with_metadata(self, query: str, query_embedding: Optional[List[float]] = None) -> dict:
        """
        Same as classify_query() but returns rich metadata for the Streamlit demo UI.
        """
        import time
        start = time.perf_counter()
        normalized = query.strip().lower()

        # Layer 1: Exact match
        l1_match = self._get_from_exact_cache(normalized)
        if l1_match:
            latency = (time.perf_counter() - start) * 1000
            return {
                "status": "success",
                "classification": l1_match,
                "cache_layer": "L1",
                "cache_label": "⚡ Exact Match Cache Hit (Redis/RAM)",
                "latency_ms": round(latency, 2),
                "similarity_score": None,
                "matched_query": normalized,
            }

        # Layer 2: Semantic similarity
        if query_embedding:
            l2_match = self._get_from_semantic_cache(query_embedding)
            if l2_match:
                latency = (time.perf_counter() - start) * 1000
                return {
                    "status": "success",
                    "classification": l2_match["classification"],
                    "cache_layer": "L2",
                    "cache_label": "🔵 Semantic Cache Hit (Qdrant/RAM)",
                    "latency_ms": round(latency, 2),
                    "similarity_score": l2_match["similarity_score"],
                    "matched_query": l2_match["matched_query"],
                }

        # Layer 3: LLM fallback
        result = self._process_request(QUERY_CLASSIFICATION_PROMPT, query, QueryClassificationSchema)
        latency = (time.perf_counter() - start) * 1000

        if result["status"] == "success":
            classification = result["message"]
            self._write_to_caches(query, query_embedding, classification)
            return {
                "status": "success",
                "classification": classification,
                "cache_layer": "LLM",
                "cache_label": "🤖 LLM Fallback",
                "latency_ms": round(latency, 2),
                "similarity_score": None,
                "matched_query": None,
            }

        return {"status": "error", "message": result["message"]}



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
