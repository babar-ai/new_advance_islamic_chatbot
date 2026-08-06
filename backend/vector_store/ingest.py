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

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.custom_logger import setup_logger
from utils.config import settings
from services.qdrant_service import QdrantService

from document_loader import preprocess_docs, split_documents

logger = setup_logger(__name__)


# Legacy wrapper functions delegating to QdrantService
def setup_qdrant_collection(client: Any, collection_name: str) -> None:
    """Delegates collection setup to QdrantService."""
    qdrant_service = QdrantService()
    qdrant_service.setup_collection(collection_name)


def embed_and_upload(
    client: Any,
    chunks: List[Document],
    collection_name: str,
    embeddings: Any,
) -> None:
    """Delegates batched embedding and upload to QdrantService."""
    qdrant_service = QdrantService()
    qdrant_service.embed_and_upload(chunks, collection_name, embeddings)


if __name__ == "__main__":
    base_dir = Path(__file__).parent / "storage"

    SOURCES = {
        "quran":                base_dir / "quran",
        "hadith":               base_dir / "hadith",
        "tafsir":               base_dir / "tafsir",
        "general_islamic_info": base_dir / "general islamic books",
    }

    qdrant_service = QdrantService()

    logger.info("Loading OpenAI embedding model: %s ...", settings.EMBEDDING_MODEL)
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY or None,
    )
    logger.info("OpenAI Embedding model ready.")

    summary: dict[str, dict] = {}

    for engine_name, source_path in SOURCES.items():
        collection_name = settings.COLLECTION_NAMES[engine_name]

        logger.info("=" * 50)
        logger.info("Engine: %s | Collection: %s", engine_name.upper(), collection_name)
        logger.info("=" * 50)

        raw_docs = preprocess_docs(str(source_path))

        # Split long text books; JSON records (Quran, Hadith, Tafsir) are already 1 doc per entry
        if engine_name == "general_islamic_info":
            chunks = split_documents(raw_docs)
            logger.info(
                "%d raw books → %d chunks (chunk_size=%d, overlap=%d)",
                len(raw_docs), len(chunks), settings.CHUNK_SIZE, settings.CHUNK_OVERLAP
            )
        else:
            chunks = raw_docs
            logger.info("%d record(s) kept as 1-to-1 documents (no text splitting needed)", len(chunks))

        qdrant_service.setup_collection(collection_name)
        qdrant_service.embed_and_upload(chunks, collection_name, embeddings)

        summary[engine_name] = {"raw": len(raw_docs), "chunks": len(chunks)}

    logger.info("=" * 50)
    logger.info("INGESTION COMPLETE")
    logger.info("%-25s %10s  %10s", "Engine", "Raw Docs", "Chunks")
    logger.info("-" * 50)
    for engine_name, stats in summary.items():
        logger.info("%-25s %10d  %10d", engine_name, stats["raw"], stats["chunks"])
    logger.info("=" * 50)



