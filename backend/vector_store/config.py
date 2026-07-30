"""
Central configuration for the Islamic AI Chatbot vector store pipeline.

All settings — Qdrant connection, embedding model, chunking parameters,
and collection names — live here so you only ever need to change one file.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Qdrant Connection
# ──────────────────────────────────────────────────────────────────────────────

# URL of the locally running Qdrant Docker container
QDRANT_URL: str = "http://localhost:6333"

# API key — leave empty string "" if no authentication is set on your container
QDRANT_API_KEY: str = ""

# ──────────────────────────────────────────────────────────────────────────────
# Embedding Model
# ──────────────────────────────────────────────────────────────────────────────

# Multilingual model — supports Arabic, Urdu, English, Russian and 50+ others.
# Downloads automatically from HuggingFace on first run (~450 MB).
EMBEDDING_MODEL_NAME: str = "text-embedding-3-small"

# Vector dimension produced by the model above.
# MUST match the model output — do not change unless you switch models.
EMBEDDING_DIMENSION: int = 1536

CHUNK_SIZE: int = 1200

CHUNK_OVERLAP: int = 150



COLLECTION_NAMES: dict[str, str] = {
    "quran":               "quran",
    "hadith":              "hadith",
    "tafsir":              "tafsir",
    "general_islamic_info": "general_islamic_info",
}


# Number of chunks to embed and upload per batch
BATCH_SIZE: int = 500

# Set to True to delete & re-ingest collections from scratch.
# Set to False to auto-resume from the last uploaded batch if interrupted.
FORCE_RECREATE: bool = True
