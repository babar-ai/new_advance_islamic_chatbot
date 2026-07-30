"""
Main Ingestion Orchestrator for the Islamic AI Chatbot.
Loads documents, splits general text books into chunks, creates Qdrant collections,
and uploads vector embeddings across all query engines with batching and auto-resume.
"""

import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from pathlib import Path
from typing import List, Any

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Load environment variables (.env contains OPENAI_API_KEY)
load_dotenv(Path(__file__).parent / ".env")

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.custom_logger import setup_logger

import config
from document_loader import preprocess_docs, split_documents

logger = setup_logger(__name__)


def setup_qdrant_collection(client: QdrantClient, collection_name: str) -> None:
    """Creates or ensures a Qdrant collection exists. Resets if FORCE_RECREATE is True."""
    existing_collections = [col.name for col in client.get_collections().collections]

    if config.FORCE_RECREATE and collection_name in existing_collections:
        logger.warning("FORCE_RECREATE=True. Deleting collection '%s' for clean re-index.", collection_name)
        client.delete_collection(collection_name=collection_name)
        existing_collections.remove(collection_name)

    if collection_name not in existing_collections:
        logger.info("Creating fresh Qdrant collection: '%s' ...", collection_name)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=config.EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Collection '%s' created (dim=%d, metric=COSINE)", collection_name, config.EMBEDDING_DIMENSION)
    else:
        info = client.get_collection(collection_name)
        logger.info("Collection '%s' exists with %d existing point(s).", collection_name, info.points_count)


def embed_and_upload(
    client: QdrantClient,
    chunks: List[Document],
    collection_name: str,
    embeddings: Any,
) -> None:
    """Embeds document chunks in batches and auto-resumes from last uploaded point if interrupted."""
    if not chunks:
        logger.warning("No chunks to upload for '%s', skipping.", collection_name)
        return

    total_chunks = len(chunks)
    info = client.get_collection(collection_name)
    existing_count = info.points_count

    if existing_count >= total_chunks and not config.FORCE_RECREATE:
        logger.info("Collection '%s' is already fully uploaded (%d / %d chunks). Skipping!", collection_name, existing_count, total_chunks)
        return

    start_idx = existing_count if not config.FORCE_RECREATE else 0

    if start_idx > 0:
        logger.info("🔄 Resuming '%s': Skipping first %d chunk(s). Uploading remaining %d chunk(s) ...",
                    collection_name, start_idx, total_chunks - start_idx)
    else:
        logger.info("🚀 Starting upload of %d chunk(s) to '%s' ...", total_chunks, collection_name)

    batch_size = config.BATCH_SIZE
    total_batches = (total_chunks - start_idx + batch_size - 1) // batch_size

    for i in range(start_idx, total_chunks, batch_size):
        batch = chunks[i : i + batch_size]
        current_batch_num = (i - start_idx) // batch_size + 1

        logger.info(
            "Uploading Batch %d/%d (chunks %d–%d / %d) to '%s' ...",
            current_batch_num, total_batches, i + 1, min(i + batch_size, total_chunks), total_chunks, collection_name
        )

        QdrantVectorStore.from_documents(
            documents=batch,
            embedding=embeddings,
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY or None,
            collection_name=collection_name,
            force_recreate=False,
        )

    logger.info("✅ Upload complete for '%s' (Total points in Qdrant: %d)", collection_name, client.get_collection(collection_name).points_count)


if __name__ == "__main__":
    base_dir = Path(__file__).parent / "storage"

    SOURCES = {
        "quran":                base_dir / "quran",
        "hadith":               base_dir / "hadith",
        "tafsir":               base_dir / "tafsir",
        "general_islamic_info": base_dir / "general islamic books",
    }

    logger.info("Connecting to Qdrant at %s ...", config.QDRANT_URL)
    qdrant_client = QdrantClient(
        url=config.QDRANT_URL,
        api_key=config.QDRANT_API_KEY or None,
    )
    logger.info("Connected to Qdrant successfully.")

    logger.info("Loading OpenAI embedding model: %s ...", config.EMBEDDING_MODEL_NAME)
    
    embeddings = OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL_NAME,
    )
    logger.info("OpenAI Embedding model ready.")

    summary: dict[str, dict] = {}

    for engine_name, source_path in SOURCES.items():
        collection_name = config.COLLECTION_NAMES[engine_name]

        logger.info("=" * 50)
        logger.info("Engine: %s | Collection: %s", engine_name.upper(), collection_name)
        logger.info("=" * 50)

        raw_docs = preprocess_docs(str(source_path))

        # Split long text books; JSON records (Quran, Hadith, Tafsir) are already 1 doc per entry
        if engine_name == "general_islamic_info":
            chunks = split_documents(raw_docs)
            logger.info(
                "%d raw books → %d chunks (chunk_size=%d, overlap=%d)",
                len(raw_docs), len(chunks), config.CHUNK_SIZE, config.CHUNK_OVERLAP
            )
        else:
            chunks = raw_docs
            logger.info("%d record(s) kept as 1-to-1 documents (no text splitting needed)", len(chunks))

        setup_qdrant_collection(qdrant_client, collection_name)
        embed_and_upload(qdrant_client, chunks, collection_name, embeddings)

        summary[engine_name] = {"raw": len(raw_docs), "chunks": len(chunks)}

    logger.info("=" * 50)
    logger.info("INGESTION COMPLETE")
    logger.info("%-25s %10s  %10s", "Engine", "Raw Docs", "Chunks")
    logger.info("-" * 50)
    for engine_name, stats in summary.items():
        logger.info("%-25s %10d  %10d", engine_name, stats["raw"], stats["chunks"])
    logger.info("=" * 50)


