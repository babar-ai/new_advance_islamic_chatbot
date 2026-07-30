# Islamic AI Chatbot — Vector Store Pipeline

An enterprise-grade Data Ingestion and Vector Pipeline for an Islamic AI Chatbot, built with Python, LangChain, Qdrant, and OpenAI Embeddings.

---

## 🚀 Key Architectural Highlights & Interview Talking Points

### 1. Custom Document Loader (`IslamicJSONLoader`) vs Built-in Loaders

Rather than using LangChain's built-in `JSONLoader`, this project uses a custom `IslamicJSONLoader` extending `BaseLoader`.

#### Why Use a Custom Loader?
* **Windows Native & `jq`-Free Deployment**: Standard `JSONLoader` requires `jq` (a C-based library) which is difficult to install/configure on Windows. `IslamicJSONLoader` uses standard Python `json`, rendering the pipeline 100% portable across Windows, Linux, macOS, and Docker.
* **Heterogeneous Dataset Auto-Detection**: Dynamically scans for content keys (`translation`, `tafsir`, `text`, `content`) via `CONTENT_KEY_PRIORITY`, eliminating hardcoded per-file JSON schemas.
* **Multi-Field Context Fusion**: Fuses `narrator` + `translation` into `page_content` (*e.g., "Narrated 'Umar bin Al-Khattab: I heard Allah's Messenger..."*), preserving full semantic context for vector embeddings.
* **Metadata Optimization**: Selectively flattens nested metadata and excludes redundant text bloat, minimizing vector database storage overhead in Qdrant.

---

### 2. Embedding Model — OpenAI `text-embedding-3-small` (1536-Dim)

The pipeline utilizes OpenAI's state-of-the-art **`text-embedding-3-small`** model.

* **Vector Dimension**: `1,536`
* **Context Window**: `8,191 tokens` (~32,000 English characters / ~14,000 Arabic characters)
* **Multilingual Coverage**: Superior semantic representation across English, Arabic, Urdu, Russian, and 50+ languages.

---

### 3. Chunking Strategy & Granularity (1200 Characters)

* **Why 1,200 Characters (~250–400 Tokens)?**
  Even though `text-embedding-3-small` supports up to 8,191 tokens, embedding massive chunks dilutes vector specificity (semantic noise). `1200 characters` with `150 overlap` is the proven "sweet spot" for RAG: it preserves exact factual precision while providing complete paragraph context to the downstream LLM.
* **Domain-Specific Handling**:
  * **Quran, Hadith, Tafsir**: Preserved as intact **1-to-1 JSON records** without arbitrary text splitting to maintain theological integrity.
  * **General Islamic Books**: Split dynamically using `RecursiveCharacterTextSplitter`.

---

### 4. Production Batching & Resiliency (`BATCH_SIZE = 500` & Auto-Resume)

* **Batching Strategy**: Embeds and uploads vectors in batches of 500 chunks. Reduces 50,000 individual HTTP calls into 100 bulk requests, preventing `HTTP 429 Rate Limits` and payload exhaustion.
* **Stateful Auto-Resume**: Before uploading, the pipeline inspects existing Qdrant `points_count`. If interrupted halfway, it skips previously indexed chunks and resumes automatically, preventing redundant embedding costs.
* **Cross-Platform UTF-8 Safety**: Implements stream reconfiguration (`sys.stdout.reconfigure(encoding="utf-8")`) to prevent Windows `UnicodeEncodeError` (CP1252) when printing multilingual Arabic/Urdu texts and terminal logs.

---

## 🎯 Technical Q&A for System Design & Technical Interviews

<details>
<summary><b>Q1: Why not embed full chapters or larger chunks since OpenAI supports 8k tokens?</b></summary>

> **Answer:** Large chunks dilute vector embeddings. A single vector representing 3,000 words must average out many topics, making similarity search noisy and imprecise for specific queries. 1200 characters (~250–300 words) captures a single, dense semantic concept, maximizing retrieval precision for RAG.
</details>

<details>
<summary><b>Q2: How do you handle schema differences across Quran, Hadith, and Tafsir datasets?</b></summary>

> **Answer:** We implemented `IslamicJSONLoader` which uses priority candidate keys (`CONTENT_KEY_PRIORITY`) and conditional field fusion (e.g. combining Hadith narrator with translation text), ensuring uniform `Document` objects regardless of input source format.
</details>

<details>
<summary><b>Q3: What happens if your ingestion script crashes at 80% completion?</b></summary>

> **Answer:** The pipeline is idempotent and resilient. It checks Qdrant's `points_count` per collection before starting upload, skipping already ingested batches and resuming right where it left off, avoiding duplicate vectors or unnecessary OpenAI API billing.
</details>

---

## 🏗️ Data Pipeline Architecture

```
Raw Storage (JSON / TXT: Quran, Hadith, Tafsir, Books) 
       │
       ▼
1. Document Preprocessing (`IslamicJSONLoader` / `DirectoryLoader`)
       │
       ▼
2. Domain-Aware Chunking (`RecursiveCharacterTextSplitter` - 1200 chars for books; 1-to-1 for Quran/Hadith)
       │
       ▼
3. Qdrant Collection Setup (Cosine Distance, 1536-Dim Vectors)
       │
       ▼
4. Batched Embedding & Upload (OpenAI `text-embedding-3-small`, Batch Size: 500, Auto-Resume)
```

---

## 📂 Project Structure

```
├── clean.py                         # Utility script to sanitize raw datasets
├── requirements.txt                 # Project dependencies (langchain-openai, qdrant-client, python-dotenv)
├── docker-compose.yaml              # Local Qdrant container configuration
└── backend/
    └── vector_store/
        ├── .env                     # Environment variables (OPENAI_API_KEY)
        ├── config.py                # Central pipeline configuration (1536-dim, batching, collections)
        ├── document_loader.py       # Custom IslamicJSONLoader & preprocess_docs
        ├── ingest.py                # Main ingestion orchestrator & batched uploader
        └── storage/                 # Datasets (quran, hadith, tafsir, general islamic books)
```

---

## ⚙️ Setup & Ingestion

1. **Start Qdrant Vector Store**:
   ```bash
   docker-compose up -d
   ```

2. **Configure Environment Variables**:
   Create `backend/vector_store/.env`:
   ```env
   OPENAI_API_KEY="sk-proj-..."
   ```

3. **Install Dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

4. **Run Ingestion Pipeline**:
   ```bash
   python backend/vector_store/ingest.py
   ```

