import sys
from pathlib import Path
from typing import List, Any, Optional

import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.custom_logger import setup_logger
from utils.config import settings

logger = setup_logger(__name__)


class QdrantService:

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):

        self.qdrant_url = qdrant_url or settings.QDRANT_URL
        self.qdrant_api_key = qdrant_api_key or settings.QDRANT_API_KEY
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL

        logger.info("Connecting to Qdrant at %s ...", self.qdrant_url)

        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key or None,
        )
    
        logger.info("Connected to Qdrant successfully.")
        self.ensure_cache_collection()

    def ensure_cache_collection(self) -> None:
        """Ensures the classification_cache collection exists in Qdrant."""
        try:
            self.setup_collection(
                collection_name=settings.CLASSIFICATION_CACHE_COLLECTION_NAME,
                embedding_dimension=settings.EMBEDDING_DIMENSION,
                force_recreate=False
            )
        except Exception as e:
            logger.warning("Failed to auto-setup Qdrant cache collection: %s", e)


    def setup_collection(
        self,
        collection_name: str,
        embedding_dimension: Optional[int] = None,
        force_recreate: Optional[bool] = None,
    ) -> None:

        """Creates or ensures a Qdrant collection exists. Resets if force_recreate is True."""
        dimension = embedding_dimension or settings.EMBEDDING_DIMENSION
        should_recreate = settings.FORCE_RECREATE if force_recreate is None else force_recreate

        existing_collections = [col.name for col in self.client.get_collections().collections]

        if should_recreate and collection_name in existing_collections:
            logger.warning("FORCE_RECREATE=True. Deleting collection '%s' for clean re-index.", collection_name)

            self.client.delete_collection(collection_name=collection_name)
            existing_collections.remove(collection_name)

        if collection_name not in existing_collections:
            logger.info("Creating fresh Qdrant collection: '%s' ...", collection_name)

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Collection '%s' created (dim=%d, metric=COSINE)", collection_name, dimension)

        else:
            info = self.client.get_collection(collection_name)
            logger.info("Collection '%s' exists with %d existing point(s).", collection_name, info.points_count)


    def embed_and_upload(
        self,
        chunks: List[Document],
        collection_name: str,
        embeddings: Any,
        batch_size: Optional[int] = None,
        force_recreate: Optional[bool] = None,
    ) -> None:

        """Embeds document chunks in batches and auto-resumes from last uploaded point if interrupted."""
        if not chunks:
            logger.warning("No chunks to upload for '%s', skipping.", collection_name)
            return

        batch_sz = batch_size or settings.BATCH_SIZE
        should_recreate = settings.FORCE_RECREATE if force_recreate is None else force_recreate

        total_chunks = len(chunks)
        info = self.client.get_collection(collection_name)
        existing_count = info.points_count

        if existing_count >= total_chunks and not should_recreate:
            logger.info("Collection '%s' is already fully uploaded (%d / %d chunks). Skipping!", collection_name, existing_count, total_chunks)
            return

        start_idx = existing_count if not should_recreate else 0

        if start_idx > 0:
            logger.info("🔄 Resuming '%s': Skipping first %d chunk(s). Uploading remaining %d chunk(s) ...",
                        collection_name, start_idx, total_chunks - start_idx)
        else:
            logger.info("🚀 Starting upload of %d chunk(s) to '%s' ...", total_chunks, collection_name)

        total_batches = (total_chunks - start_idx + batch_sz - 1) // batch_sz

        for i in range(start_idx, total_chunks, batch_sz):
            batch = chunks[i : i + batch_sz]
            current_batch_num = (i - start_idx) // batch_sz + 1

            logger.info(
                "Uploading Batch %d/%d (chunks %d–%d / %d) to '%s' ...",
                current_batch_num, total_batches, i + 1, min(i + batch_sz, total_chunks), total_chunks, collection_name
            )

            QdrantVectorStore.from_documents(
                documents=batch,
                embedding=embeddings,
                url=self.qdrant_url,
                api_key=self.qdrant_api_key or None,
                collection_name=collection_name,
                force_recreate=False,
            )

        logger.info("✅ Upload complete for '%s' (Total points in Qdrant: %d)", collection_name, self.client.get_collection(collection_name).points_count)


    def get_vector_store(self, collection_name: str, embeddings: Any) -> QdrantVectorStore:
        """Returns a LangChain QdrantVectorStore instance for querying an existing collection."""
        return QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            embedding=embeddings,
        )


    def get_retriever(self, collection_name: str, embeddings: Any, k: int = 4, search_type: str = "similarity"):
        """Returns a LangChain Retriever instance for RAG pipelines."""
        vector_store = self.get_vector_store(collection_name, embeddings)
        return vector_store.as_retriever(search_type=search_type, search_kwargs={"k": k})


    def search(self, collection_name: str, query: str, embeddings: Any, limit: int = 4) -> List[Document]:
        """Performs similarity search against a specific collection."""
        vector_store = self.get_vector_store(collection_name, embeddings)
        return vector_store.similarity_search(query=query, k=limit)


    def search_by_vector(self, collection_name: str, query_vector: List[float], limit: int = 5) -> List[dict]:
        """
        Search using a pre-computed embedding vector — avoids redundant embed_query calls.
        Returns raw dicts with 'content', 'metadata', and 'score' keys.
        """
        try:
            if hasattr(self.client, "query_points"):
                res = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                )
                results = res.points
            else:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                )

            return [
                {
                    "content": r.payload.get("page_content", ""),
                    "metadata": r.payload.get("metadata", {}),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.error("Error in search_by_vector for '%s': %s", collection_name, e)
            return []


    def upsert_cache_vector(
        self,
        collection_name: str,
        query_text: str,
        query_vector: List[float],
        classification_payload: dict,
    ) -> None:
        """Upserts a classification query vector and payload metadata into Qdrant cache collection."""
        try:
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, query_text.strip().lower()))
            point = PointStruct(
                id=point_id,
                vector=query_vector,
                payload={
                    "query_text": query_text,
                    "classification": classification_payload,
                }
            )
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            logger.info("Upserted classification vector for '%s' into Qdrant collection '%s'", query_text, collection_name)
        except Exception as e:
            logger.error("Error upserting vector into cache collection '%s': %s", collection_name, e)


    def search_cache_vector(
        self,
        collection_name: str,
        query_vector: List[float],
        score_threshold: float = 0.85
    ) -> Optional[dict]:
        """
        Searches the Qdrant classification cache collection using query vector.
        Returns closest match dict if score exceeds score_threshold, else None.
        """
        try:
            if hasattr(self.client, "query_points"):
                res = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=1,
                    score_threshold=score_threshold,
                    with_payload=True,
                    with_vectors=False
                )
                results = res.points
            else:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=1,
                    score_threshold=score_threshold,
                    with_payload=True,
                    with_vectors=False
                )

            if results:
                best_match = results[0]
                return {
                    "matched_query": best_match.payload.get("query_text", ""),
                    "classification": best_match.payload.get("classification", {}),
                    "similarity_score": round(float(best_match.score), 4),
                }
            return None
            
        except Exception as e:
            logger.error("Error searching cache collection '%s': %s", collection_name, e)
            return None
