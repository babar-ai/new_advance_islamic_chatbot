"""
Main Ingestion Orchestrator for the Islamic AI Chatbot.
Loads documents, splits general text books into chunks, creates Qdrant collections,
and uploads vector embeddings across all query engines.
"""

import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from pathlib import Path
from typing import List, Any

from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.custom_logger import setup_logger

import config
from document_loader import preprocess_docs, split_documents

logger = setup_logger(__name__)


def setup_qdrant_collection(client: QdrantClient, collection_name: str) -> None:
    """Creates or resets a Qdrant collection for a given engine."""
    existing_collections = [col.name for col in client.get_collections().collections]

    if collection_name in existing_collections:
        logger.warning("Collection '%s' already exists — deleting for clean re-index.", collection_name)
        client.delete_collection(collection_name=collection_name)

    logger.info("Creating collection: '%s' ...", collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=config.EMBEDDING_DIMENSION,
            distance=Distance.COSINE,
        ),
    )
    logger.info("Collection '%s' ready (dim=%d, metric=COSINE)", collection_name, config.EMBEDDING_DIMENSION)


def embed_and_upload(
    chunks: List[Document],
    collection_name: str,
    embeddings: Any,
) -> None:
    """Embeds document chunks and uploads them to Qdrant vector store."""
    if not chunks:
        logger.warning("No chunks to upload for '%s', skipping.", collection_name)
        return

    logger.info("Embedding and uploading %d chunk(s) to '%s' ...", len(chunks), collection_name)

    QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=config.QDRANT_URL,
        api_key=config.QDRANT_API_KEY or None,
        collection_name=collection_name,
        force_recreate=False,
    )

    logger.info("Upload complete for '%s'", collection_name)


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

    logger.info("Loading BGE-M3 embedding model: %s ...", config.EMBEDDING_MODEL_NAME)
    embeddings = HuggingFaceBgeEmbeddings(
        model_name=config.EMBEDDING_MODEL_NAME,
        model_kwargs={"device": config.EMBEDDING_DEVICE},
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info("BGE-M3 Embedding model ready.")

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
        embed_and_upload(chunks, collection_name, embeddings)

        summary[engine_name] = {"raw": len(raw_docs), "chunks": len(chunks)}

    logger.info("=" * 50)
    logger.info("INGESTION COMPLETE")
    logger.info("%-25s %10s  %10s", "Engine", "Raw Docs", "Chunks")
    logger.info("-" * 50)
    for engine_name, stats in summary.items():
        logger.info("%-25s %10d  %10d", engine_name, stats["raw"], stats["chunks"])
    logger.info("=" * 50)
