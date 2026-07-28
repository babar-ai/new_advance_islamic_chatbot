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
EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"

# Vector dimension produced by the model above.
# MUST match the model output — do not change unless you switch models.
EMBEDDING_DIMENSION: int = 1024

# Device to run the embedding model on.
# "cpu"  → safe on any machine (slower)
# "cuda" → requires a compatible NVIDIA GPU + CUDA toolkit (much faster)
EMBEDDING_DEVICE: str = "cpu"


# ──────────────────────────────────────────────────────────────────────────────
# Text Splitting / Chunking
# ──────────────────────────────────────────────────────────────────────────────

# Maximum number of characters per chunk (optimized for BGE-M3).
CHUNK_SIZE: int = 1200

# Number of characters that overlap between consecutive chunks.
CHUNK_OVERLAP: int = 150


# ──────────────────────────────────────────────────────────────────────────────
# Qdrant Collection Names  (one collection per query engine)
# ──────────────────────────────────────────────────────────────────────────────

COLLECTION_NAMES: dict[str, str] = {
    "quran":               "islamic_quran",
    "hadith":              "islamic_hadith",
    "tafsir":              "islamic_tafsir",
    "general_islamic_info": "islamic_general",
}
