import sys
from pathlib import Path
from typing import List, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
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

