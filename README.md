# Islamic AI Chatbot — Vector Store Pipeline

An enterprise-grade Data Ingestion and Vector Pipeline for an Islamic AI Chatbot, built with Python, LangChain, Qdrant, and HuggingFace Sentence Transformers.

---

## 🚀 Key Architectural Highlights

### Custom Document Loader (`IslamicJSONLoader`) vs Built-in Loaders

Rather than using LangChain's built-in `JSONLoader`, this project uses a custom `IslamicJSONLoader` extending `BaseLoader`.

#### Why Use a Custom Loader?

1. **Windows Native & `jq`-Free Deployment**:
   - LangChain's built-in `JSONLoader` requires `jq` (a C-based JSON parsing library) which is notoriously difficult to install on Windows environments.
   - `IslamicJSONLoader` uses Python's native `json` module, making the pipeline 100% portable across Windows, Linux, macOS, and Docker.

2. **Heterogeneous Dataset Auto-Detection**:
   - Islamic datasets store primary texts under different keys (Quran/Hadith → `"translation"`, Tafsir → `"tafsir"`).
   - `IslamicJSONLoader` dynamically detects content keys using `CONTENT_KEY_PRIORITY`, eliminating hardcoded per-file schemas.

3. **Multi-Field Context Fusion (Hadiths)**:
   - Built-in loaders only support extracting a single key as page content.
   - `IslamicJSONLoader` dynamically fuses `narrator` + `translation` into `page_content` (*e.g., "Narrated 'Umar bin Al-Khattab: I heard Allah's Messenger..."*), preserving full semantic context for vector embeddings.

4. **Payload & Deployment Cost Optimization**:
   - Selectively flattens nested metadata (`meta_data`) and excludes unused heavy text bloat, significantly lowering vector storage costs in Qdrant.

---

## 🤖 Embedding Model — BGE-M3

This pipeline uses **[BGE-M3](https://huggingface.co/BAAI/bge-m3)** (`BAAI/bge-m3`), developed by the Beijing Academy of Artificial Intelligence (BAAI). It is one of the most capable open-source multilingual embedding models available.

### Why BGE-M3?

| Capability | Details |
| :--- | :--- |
| **Multi-functional** | Supports dense, sparse, and multi-vector retrieval in a single model |
| **Multi-lingual** | Covers 100+ languages including Arabic, Urdu, English, and Russian |
| **Multi-granularity** | Handles inputs from short sentences up to 8,192 tokens (long documents) |

### ⚠️ Points to Be Aware Of

- **Generalizability**: Performs well on benchmarks but may need validation on specific real-world Islamic datasets.
- **Computational cost**: Processing very long documents (near 8,192 tokens) is resource-intensive on CPU.
- **Language variance**: Performance may vary slightly across different language families.

> For English-only use cases, consider lighter alternatives: `bge-base-en-v1.5` or `bge-en-icl`.

---



```
Raw Storage (JSON / TXT) 
       │
       ▼
1. Preprocess Docs (IslamicJSONLoader / DirectoryLoader)
       │
       ▼
2. Chunking (RecursiveCharacterTextSplitter)
       │
       ▼
3. Qdrant Setup (Cosine Similarity, 768-dim Vectors)
       │
       ▼
4. Embed & Upload (HuggingFace Multilingual Embeddings)
```

---

## 📂 Project Structure

```
├── clean.py                         # Utility script to sanitize and remove unused dataset bloat
├── requirements.txt                 # Project dependencies
├── docker-compose.yaml              # Local Qdrant container configuration
└── backend/
    └── vector_store/
        ├── config.py                # Central pipeline configuration
        ├── ingest.py                # Core ingestion pipeline & IslamicJSONLoader
        └── storage/                 # Datasets (Quran, Hadith, Tafsir, General Books)
```

---

## ⚙️ Setup & Ingestion

1. **Start Qdrant Vector Store**:
   ```bash
   docker-compose up -d
   ```

2. **Sanitize Raw Datasets**:
   ```bash
   python clean.py
   ```

3. **Run Ingestion Pipeline**:
   ```bash
   python backend/vector_store/ingest.py
   ```
