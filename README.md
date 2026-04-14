# Plagiarism & Duplicate Detection Tool — Architecture Document

> **Samsung PRISM Research Project**  

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [System Overview](#2-system-overview)
3. [Tech Stack](#3-tech-stack)
4. [Repository Structure](#4-repository-structure)
5. [Architecture Diagram](#5-architecture-diagram)
6. [Data Flow](#6-data-flow)
7. [Detection Methods](#7-detection-methods)
8. [API Reference](#8-api-reference)
9. [Database Schema](#9-database-schema)
10. [Configuration](#10-configuration)
11. [How to Run Locally](#11-how-to-run-locally)

---

## 1. Problem Statement

Large-scale AI training datasets sourced from Excel sheets often contain:
- **Exact duplicate** entries (identical copy-paste records)
- **Near-duplicate** entries (minor edits, typos, paraphrasing)
- **Semantically similar** content (same meaning, different words)
- **AI-generated text** (content that may not be original human writing)
- **Plagiarised web content** (scraped from online sources)
- **License/copyright violations** (content with restricted usage)

This tool detects all of the above, produces structured reports, and ensures data quality before training.

---

## 2. System Overview

The system has two main components:

| Component | Technology | Role |
|---|---|---|
| **Backend** | Python, FastAPI | All detection logic, database, APIs |
| **Frontend** | Next.js (TypeScript) | User interface for uploading data, viewing results |

The backend is the core of the system. The frontend communicates with it via HTTP.

---

## 3. Tech Stack

### Backend
| Library | Purpose |
|---|---|
| **FastAPI** | REST API framework (async, high performance) |
| **PostgreSQL + pgvector** | Relational database + vector storage for semantic embeddings |
| **asyncpg / psycopg2** | Async and sync PostgreSQL drivers |
| **pandas** | Reading and processing Excel / CSV files |
| **sentence-transformers** | SBERT model for semantic embeddings (`all-MiniLM-L6-v2`) |
| **transformers (HuggingFace)** | AI-generated content detection (`roberta-large-openai-detector`) |
| **scikit-learn** | DBSCAN and K-Means clustering |
| **gensim** | Word2Vec / GloVe word embeddings |
| **ddgs / BeautifulSoup4** | Web search (DuckDuckGo) + page text extraction |
| **openpyxl** | Excel report generation |
| **python-dotenv** | Environment variable management |

### Frontend
| Library | Purpose |
|---|---|
| **Next.js 14 (App Router)** | React framework with server components |
| **TypeScript** | Type-safe JavaScript |
| **Tailwind CSS** | Styling |

---

## 4. Repository Structure

```
Plagiarism_Tool/
├── backend/
│   ├── .env                        # Local environment variables (not committed)
│   ├── .env.example                # Template for environment setup
│   ├── requirements.txt            # Python dependencies
│   └── app/
│       ├── main.py                 # FastAPI app entry point — mounts all routers
│       ├── api/
│       │   └── v1/
│       │       ├── ingest.py       # File upload, preprocessing, reference registration
│       │       ├── detect.py       # Exact / fuzzy / semantic / cross-batch detection
│       │       ├── ai_detect.py    # AI-generated content detection
│       │       ├── web_scan.py     # Web plagiarism scanning (DuckDuckGo)
│       │       ├── license_check.py# License and copyright detection
│       │       └── reports.py      # Report generation endpoints
│       ├── services/
│       │   ├── preprocess.py       # Text normalization + shared file reader
│       │   ├── detect.py           # SHA-256 exact duplicate logic
│       │   ├── fuzzy.py            # Levenshtein, Jaccard, N-gram, Hamming
│       │   ├── embeddings.py       # SBERT encoding + cosine similarity
│       │   ├── word2vec.py         # Word2Vec / GloVe similarity
│       │   ├── clustering.py       # DBSCAN and K-Means clustering
│       │   ├── ai_detection.py     # HuggingFace AI content classifier
│       │   ├── web_scan.py         # Web search + similarity scoring
│       │   ├── web_fingerprint.py  # Content hashing + domain metadata
│       │   ├── license_check.py    # SPDX license + copyright detection
│       │   └── reports.py          # DetectionResult model + Excel/CSV export
│       └── storage/
│           └── repository.py       # All database queries (asyncpg pool)
└── frontend/
    └── app/
        ├── layout.tsx
        ├── page.tsx
        ├── components/             # Navbar, Hero, About, Footer, DetectionSelector
        └── analyze/                # Per-method analyzer pages
            ├── exact/
            ├── fuzzy/
            ├── semantic/
            ├── ai-detect/
            ├── web-scan/
            ├── license/
            └── cross-batch/
```

---

## 5. Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (Next.js)                  │
│  Upload Files │ View Results │ Download Reports       │
└──────────────────────┬──────────────────────────────┘
                       │  HTTP / REST
┌──────────────────────▼──────────────────────────────┐
│               FastAPI Backend                        │
│                                                      │
│  ┌─────────────┐   ┌────────────────────────────┐   │
│  │   Ingest    │   │      Detection Layer        │   │
│  │─────────────│   │────────────────────────────│   │
│  │ /input/data │   │ /detect/exact               │   │
│  │ /preprocess │   │ /detect/fuzzy               │   │
│  │ /reference/ │   │ /detect/semantic            │   │
│  │   register  │   │ /detect/cross-batch         │   │
│  └──────┬──────┘   │ /detect/cluster             │   │
│         │          │ /ai-detect/check            │   │
│  ┌──────▼──────────│ /web-scan/scan              │   │
│  │  Preprocessing  │ /license-check/check        │   │
│  │  (all columns)  └────────────┬───────────────┘   │
│  └──────┬──────────             │                    │
│         │          ┌────────────▼───────────────┐   │
│         │          │       Services              │   │
│         │          │  SHA-256 │ Fuzzy │ SBERT   │   │
│         │          │  Word2Vec│ DBSCAN│ HugFace │   │
│         │          │  DDG Search │ License SPDX │   │
│         │          └────────────┬───────────────┘   │
└─────────┼──────────────────────-┼───────────────────┘
          │                       │
┌─────────▼───────────────────────▼───────────────────┐
│              PostgreSQL (Supabase / pgvector)         │
│                                                      │
│  reference_batch     reference_text    reference_    │
│  ─────────────────   ───────────────   embedding     │
│  id (uuid)           id (uuid)         ──────────    │
│  name                batch_id (fk)     ref_id (fk)   │
│  created_at          raw_text          embedding      │
│                      cleaned_text      (vector)       │
│                      sha256                           │
│                      source                           │
│                      license                          │
└──────────────────────────────────────────────────────┘
```

---

## 6. Data Flow

### Registering a Reference Dataset
```
User uploads Excel/CSV file(s)
        ↓
read_all_text_from_file()
  - Reads ALL text columns (skips pure-numeric columns)
  - Handles CSV, XLSX, XLS, TXT
  - Multiple files supported
        ↓
preprocess_text() per row
  - Unicode NFKC normalization
  - Lowercase
  - Strip punctuation & symbols
  - Remove stop words
        ↓
sha256_hash(cleaned_text) → stored as fingerprint
        ↓
SBERT encode_texts() → vector embeddings
        ↓
PostgreSQL: reference_batch + reference_text + reference_embedding
```

### Running Detection on New Text
```
User submits text(s) to a detection endpoint
        ↓
preprocess_text() — same normalization
        ↓
┌──────────────────────────────────────────────┐
│              Detection Methods               │
│                                              │
│  Exact:    SHA-256 hash comparison           │
│  Fuzzy:    Levenshtein + Jaccard + N-gram    │
│  Semantic: SBERT cosine similarity           │
│  AI:       roberta-large-openai-detector     │
│  Web:      DuckDuckGo → fetch → score        │
│  License:  SPDX + copyright header scan     │
└──────────────────────────────────────────────┘
        ↓
risk_level: none / low / medium / high
        ↓
JSON response  OR  Excel / CSV / ZIP download
```

---

## 7. Detection Methods

### 7.1 Exact Duplicate Detection
- **Algorithm:** SHA-256 hashing of normalized text
- **Speed:** O(1) per lookup (hash comparison)
- **Use case:** Identical text, copy-paste duplicates
- **Files:** `services/detect.py`

### 7.2 Near-Duplicate (Fuzzy) Detection
Four algorithms run in parallel, a match is flagged if **any** threshold is exceeded:

| Algorithm | What it detects | Threshold |
|---|---|---|
| **Levenshtein** | Character-level edits (typos, spelling) | 0.85 |
| **Jaccard** | Word-level overlap (paraphrasing) | 0.70 |
| **N-gram** | Structural / substring similarity | 0.75 |
| **Hamming** | Position-level differences (equal-length) | — |

- **Files:** `services/fuzzy.py`

### 7.3 Advanced Semantic Detection
- **Model:** `all-MiniLM-L6-v2` (SentenceTransformers / SBERT)
- **Algorithm:** Cosine similarity between sentence embeddings
- **Use case:** Paraphrased content, contextually similar text with different wording
- **Batch encoding:** All texts encoded in a single forward pass for efficiency
- **Storage:** Vectors stored in PostgreSQL via pgvector extension
- **Files:** `services/embeddings.py`

### 7.4 AI-Generated Content Detection
- **Model:** `openai-community/roberta-large-openai-detector` (HuggingFace Transformers)
- **Labels:** `Real` (Human-written) / `Fake` (AI-generated)
- **Confidence score:** 0.0 – 1.0 returned per text
- **Batch support:** All texts processed concurrently via asyncio
- **Model override:** Set `AI_DETECTION_MODEL` env var to swap model without code changes
- **Files:** `services/ai_detection.py`

### 7.5 Web Plagiarism Detection
- **Search engine:** DuckDuckGo (no API key required)
- **Approach:**
  1. Extract key phrases from input text (longest sentences)
  2. Search DuckDuckGo for each phrase
  3. Fetch page content from result URLs (BeautifulSoup)
  4. Sliding-window similarity scoring against page text
  5. Web fingerprinting: content hash, domain, estimated publish date
- **Scoring:** Levenshtein + Jaccard + N-gram on windowed page chunks
- **Files:** `services/web_scan.py`, `services/web_fingerprint.py`

### 7.6 License & Copyright Detection
- **Detects:** SPDX license identifiers, copyright headers, Creative Commons notices
- **Files:** `services/license_check.py`

### 7.7 Cross-Batch Detection
- Check new texts against **all stored reference batches** simultaneously
- Returns which batch each match came from (`batch_id` + `batch_name`)
- Supports exact, fuzzy, or semantic method
- **Files:** `api/v1/detect.py` → `/detect/cross-batch`

### 7.8 Clustering
- **DBSCAN:** Density-based clustering — auto-detects number of clusters, labels outliers as noise
- **K-Means:** Fixed number of clusters
- Both use SBERT embeddings internally
- **Files:** `services/clustering.py`

---

## 8. API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### Ingest — `/api/v1/ingest`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/input/data` | Preview file contents — reads all rows & text columns, returns original + cleaned |
| `POST` | `/preprocess` | Clean text from file(s) — view JSON or download CSV/Excel/ZIP |
| `POST` | `/reference/register` | Store file(s) as reference batches in the database |

**Multi-file support:** All three endpoints accept `files` as a list — upload multiple CSV/XLSX files in one request. In Swagger: click **"Add item"** under the `files` field for each additional file.

**`/reference/register` options:**
- `merge_files=false` (default): each file → its own named batch
- `merge_files=true`: all files → one merged batch

---

### Detection — `/api/v1/detect`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/exact` | Check single text for exact duplicate |
| `POST` | `/fuzzy` | Check single text for near-duplicate |
| `POST` | `/batch-fuzzy` | Find all fuzzy duplicate pairs in a submitted list |
| `POST` | `/semantic` | Check single text for semantic duplicate |
| `POST` | `/batch-semantic` | Find all semantic duplicate pairs in a submitted list |
| `POST` | `/cross-batch` | Check texts against all stored batches (exact/fuzzy/semantic) |
| `POST` | `/batch-word2vec` | Near-duplicate detection using Word2Vec/GloVe similarity |
| `POST` | `/cluster` | Group texts into similarity clusters (DBSCAN or K-Means) |

All detection endpoints accept `download_report=true` and `download_format=excel|csv|both` to stream a report file instead of returning JSON.

---

### AI Detection — `/api/v1/ai-detect`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/check` | Detect AI content in a single text or uploaded file |
| `POST` | `/batch-check` | Detect AI content in a list of texts or file |

---

### Web Scan — `/api/v1/web-scan`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/scan` | Search the web for plagiarism matches for a single text |
| `POST` | `/batch-scan` | Scan multiple texts concurrently |

---

### License Check — `/api/v1/license-check`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/check` | Detect license identifiers and copyright notices in text |

---

### Reports — `/api/v1/reports`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/download` | Generate a styled Excel/CSV report from any detection results you pass in |
| `POST` | `/from-web-scan` | Generate a report directly from a web scan JSON response — one row per matched source |

---

## 9. Database Schema

Hosted on **Supabase** with the **pgvector** extension enabled.

```sql
-- Stores named groups of reference texts (one per file upload or batch)
CREATE TABLE reference_batch (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Stores each text entry with original, cleaned, and hashed forms
CREATE TABLE reference_text (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id     UUID REFERENCES reference_batch(id) ON DELETE CASCADE,
    raw_text     TEXT NOT NULL,
    cleaned_text TEXT NOT NULL,
    sha256       TEXT NOT NULL,
    source       TEXT,
    license      TEXT,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Stores SBERT vector embeddings for semantic search
CREATE TABLE reference_embedding (
    ref_id    UUID PRIMARY KEY REFERENCES reference_text(id) ON DELETE CASCADE,
    embedding VECTOR(384)   -- dimension matches all-MiniLM-L6-v2
);
```

---

## 10. Configuration

Copy `.env.example` to `.env` in the `backend/` directory and fill in the values:

```env
# PostgreSQL connection string (Supabase or local Postgres with pgvector)
DATABASE_URL=postgresql://user:password@host:port/dbname

# Supabase project credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# SBERT model for semantic embeddings (HuggingFace model name or local path)
# Default: all-MiniLM-L6-v2
EMBEDDING_MODEL=all-MiniLM-L6-v2

# HuggingFace model for AI-generated content detection
# Default: openai-community/roberta-large-openai-detector
AI_DETECTION_MODEL=openai-community/roberta-large-openai-detector

# Detection thresholds (0.0 – 1.0)
FUZZY_THRESHOLD=0.85
SEMANTIC_THRESHOLD=0.85

# Google Custom Search API (optional — for Google-based web scanning)
GOOGLE_API_KEY=
GOOGLE_CSE_ID=
```

---

## 11. How to Run Locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- A PostgreSQL database with the `pgvector` extension enabled
  (easiest: free Supabase project at [supabase.com](https://supabase.com))

---

### Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL and other values

# 5. Start the server
uvicorn app.main:app --reload
```

Backend will be available at:
- **API:** `http://localhost:8000`
- **Interactive Docs (Swagger):** `http://localhost:8000/docs`
- **Alternative Docs (ReDoc):** `http://localhost:8000/redoc`

---

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start the dev server
npm run dev
```

Frontend will be available at: `http://localhost:3000`

---

### Database Setup (Supabase)

1. Create a free project at [supabase.com](https://supabase.com)
2. Enable the `pgvector` extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Run the three `CREATE TABLE` statements from [Section 9](#9-database-schema)
4. Copy your connection string from **Project Settings → Database → Connection string (URI mode)** into `DATABASE_URL` in your `.env`

---

### Verify Everything is Working

```bash
# Health check
curl http://localhost:8000/

# Expected response
{"message": "Plagiarism Checker Backend Running"}

# View all available endpoints
open http://localhost:8000/docs
```

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| **FastAPI over Flask/Django** | Native async support — critical for concurrent web scanning and batch ML inference |
| **PostgreSQL + pgvector** | Unified storage for both structured data and vector embeddings — avoids a separate vector DB |
| **SBERT `all-MiniLM-L6-v2`** | Best balance of speed and accuracy for short-text semantic similarity (optimised for sentences < 128 tokens) |
| **`roberta-large-openai-detector`** | Same interface as base model but significantly higher accuracy; swappable via env var |
| **DuckDuckGo (no API key)** | Zero-cost web scanning with no rate-limit registration; Google/Bing can be added when keys are available |
| **Preprocessing shared utility** | Single `preprocess_text()` function used across all services ensures consistent normalization everywhere |
| **Per-file batching** | Each uploaded file becomes a named batch — enables granular cross-file duplicate tracking |
