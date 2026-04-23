# Plagiarism & Duplicate Detection Tool

**Samsung PRISM Research Project**

This project provides a unified plagiarism and duplicate detection pipeline for Excel/CSV/TXT datasets. It ingests files, normalizes content, stores per-cell provenance in PostgreSQL (Supabase + pgvector), and runs exact, fuzzy, semantic, AI detection, web scanning, and license checks to generate structured results and multi-sheet reports.

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [System Overview](#system-overview)
3. [Tech Stack](#tech-stack)
4. [Repository Structure](#repository-structure)
5. [Database Schema](#database-schema)
6. [Data Flow](#data-flow)
7. [Detection Methods](#detection-methods)
8. [API Reference](#api-reference)
9. [Pipeline Output Format](#pipeline-output-format)
10. [Combined Report Format](#combined-report-format)
11. [Configuration](#configuration)
12. [How to Run Locally](#how-to-run-locally)
13. [Key Design Decisions](#key-design-decisions)

## Problem Statement

Large-scale AI training datasets sourced from Excel sheets often contain:
- **Exact duplicate** entries (identical copy-paste records)
- **Near-duplicate** entries (minor edits, typos, paraphrasing)
- **Semantically similar** content (same meaning, different words)
- **AI-generated text** (content that may not be original human writing)
- **Plagiarised web content** (scraped from online sources)
- **License/copyright violations** (content with restricted usage)

This tool detects all of the above, produces structured reports, and ensures data quality before training.

## System Overview

| Component | Technology | Role |
|---|---|---|
| Backend | Python, FastAPI | Detection services, database access, APIs |
| Frontend | Next.js (TypeScript) | Landing page, analyzer forms, batch registration |
| Database | PostgreSQL + pgvector (Supabase) | Reference batches, per-cell data, embeddings |

## Tech Stack

### Backend
| Library | Purpose |
|---|---|
| FastAPI | REST API framework (async) |
| PostgreSQL + pgvector | Relational data + vector embeddings |
| asyncpg / psycopg2 | Async and sync Postgres drivers |
| pandas | Excel/CSV ingestion and cleaning |
| sentence-transformers | SBERT semantic similarity (all-MiniLM-L6-v2) |
| transformers | AI-generated content detection (RoBERTa) |
| openpyxl | Excel report export + cross-compare reports |
| python-dotenv | Environment management |
| ddgs / duckduckgo_search | Web search |
| BeautifulSoup4 | Web page text extraction |
| requests | HTTP for web scan |
| rapidfuzz (optional) | License signature similarity |
| pydantic / pydantic-settings | Request/response models + config |

### Frontend
| Library | Purpose |  
|---|---|
| Next.js 16 (App Router) | React framework |
| TypeScript | Type-safe frontend code |
| Tailwind CSS (via PostCSS) | Styling |

## Repository Structure

```
backend/
├── requirements.txt
├── scripts/
│   └── check_db.py                    # DB connectivity check
├── tests/
│   └── test_cross_compare.py          # cross-compare tests
└── app/
    ├── __init__.py
    ├── main.py                        # FastAPI entry, lifespan model loading
    ├── core/
    │   ├── __init__.py
    │   ├── config.py                  # pydantic-settings, all env vars
    │   ├── models.py                  # shared Pydantic schemas
    │   └── model_cache.py             # SBERT + RoBERTa loaded once
    ├── models/
    │   └── schemas.py                 # (empty placeholder)
    ├── api/
    │   └── v1/
    │       ├── router.py              # includes all sub-routers
    │       ├── batches.py             # list/delete/rename batches
    │       ├── ingest.py              # file upload, preprocessing, registration
    │       ├── pipeline.py            # POST /pipeline/run
    │       ├── reports.py             # combined report download
    │       └── compare.py             # cross-file row/cell comparison
    ├── services/
    │   ├── __init__.py
    │   ├── preprocessor.py            # reads Excel/CSV/TXT with cell positions
    │   ├── exact_match.py             # SHA-256 exact duplicate detection
    │   ├── fuzzy_match.py             # Levenshtein, Jaccard, N-gram
    │   ├── semantic_match.py          # SBERT cosine similarity
    │   ├── ai_detector.py             # RoBERTa AI content detection
    │   ├── web_scanner.py             # DuckDuckGo + BeautifulSoup web scan
    │   ├── license_detector.py        # SPDX + copyright detection
    │   ├── cross_compare.py           # cross-sheet row/cell comparison
    │   └── pipeline_runner.py         # orchestrates pipeline execution
    └── storage/
        └── repository.py              # all DB queries via asyncpg pool

frontend/
├── README.md
├── package.json
├── package-lock.json
├── next.config.ts
├── eslint.config.mjs
├── postcss.config.mjs
├── tsconfig.json
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   ├── favicon.ico
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── HeroSection.tsx
│   │   ├── AboutSection.tsx
│   │   ├── Footer.tsx
│   │   ├── DetectionSelector.tsx
│   │   └── ThemeProvider.tsx
│   ├── analyze/
│   │   ├── AnalyzerLayout.tsx
│   │   ├── exact/page.tsx
│   │   ├── fuzzy/page.tsx
│   │   ├── semantic/page.tsx
│   │   ├── ai-detect/page.tsx
│   │   ├── web-scan/page.tsx
│   │   ├── license/page.tsx
│   │   └── cross-batch/page.tsx
│   └── register/
│       └── page.tsx
└── public/
        ├── file.svg
        ├── globe.svg
        ├── next.svg
        ├── vercel.svg
        └── window.svg
```

## Database Schema

```sql
CREATE TABLE reference_batch (
        id uuid primary key default gen_random_uuid(),
        name text,
        created_at timestamptz default now()
);

CREATE TABLE reference_text (
        id uuid primary key default gen_random_uuid(),
        batch_id uuid references reference_batch(id) on delete cascade,
        raw_text text not null,
        cleaned_text text not null,
        sha256 text not null,
        source text,
        license text,
        created_at timestamptz default now(),
        source_file text,
        row_number integer,
        column_name text,
        cell_ref text
);

CREATE TABLE reference_embedding (
        ref_id uuid primary key references reference_text(id) on delete cascade,
        embedding vector(384)
);

CREATE TABLE pipeline_result (
        id uuid primary key default gen_random_uuid(),
        created_at timestamptz default now(),
        status text not null default 'pending',
        methods_used jsonb,
        source_files text[],
        total_entries integer default 0,
        flagged_count integer default 0,
        summary jsonb,
        error_message text
);

CREATE TABLE duplicate_pair (
        id uuid primary key default gen_random_uuid(),
        pipeline_result_id uuid not null references pipeline_result(id) on delete cascade,
        created_at timestamptz default now(),
        original_file text not null,
        original_row integer not null,
        original_col text,
        original_cell_ref text,
        original_text text not null,
        duplicate_file text not null,
        duplicate_row integer not null,
        duplicate_col text,
        duplicate_cell_ref text,
        duplicate_text text not null,
        detection_type text not null,
        method text not null,
        similarity_pct float not null
);

CREATE TABLE web_ai_result (
        id uuid primary key default gen_random_uuid(),
        pipeline_result_id uuid not null references pipeline_result(id) on delete cascade,
        created_at timestamptz default now(),
        source_file text not null,
        row_number integer not null,
        column_name text,
        cell_ref text,
        original_text text not null,
        is_plagiarised boolean default false,
        source_url text,
        ai_detected_pct float default 0.0
);
```

## Data Flow

### Register Flow (Excel/CSV/TXT to reference_text)
1. Upload file(s) to `POST /api/v1/ingest/reference/register`.
2. `preprocessor.read_all_text_from_file()` reads the first sheet (Excel) or CSV/TXT and:
   - Skips index-like columns (S.No, ID, etc.) and mostly numeric/empty columns.
   - Emits one entry per non-empty cell with `source_file`, `row_number`, `column_name`, and `cell_ref`.
3. Each entry is normalized via `preprocess_text()` and hashed (SHA-256).
4. Rows are inserted into `reference_text` with full position metadata.
5. Optional: SBERT embeddings are generated and stored in `reference_embedding`.

### Pipeline Run Flow (files to results)
1. Upload file(s) to `POST /api/v1/pipeline/run` and choose methods.
2. Pipeline reads and normalizes entries.
3. Exact/fuzzy/semantic/AI/web/license methods run in-memory against reference texts.
4. API returns a `PipelineResult` JSON payload (no pipeline results are stored in the database).

### Server-side Pipeline Flow (registered batches only)
1. Call `POST /api/v1/pipeline/run-on-server` with batch IDs and selected methods.
2. All texts from the batches are loaded and cross-checked against each other.
3. API returns a `PipelineResult` JSON payload.

## Detection Methods

| Method | Algorithm | Thresholds | File |
|---|---|---|---|
| Exact Match | SHA-256 hash comparison | 100% identical | services/exact_match.py |
| Fuzzy Match | Levenshtein, Jaccard, N-gram | 0.85 default (Jaccard 0.68, N-gram 0.765) | services/fuzzy_match.py |
| Semantic Match | SBERT cosine similarity | 0.85 | services/semantic_match.py |
| AI Detection | RoBERTa classifier | Returns confidence 0.0–1.0 | services/ai_detector.py |
| Web Scanner | DuckDuckGo + BeautifulSoup + windowed similarity | 0.50 similarity (default), 10s timeout, 3 retries | services/web_scanner.py |
| License Detector | SPDX + copyright patterns | N/A | services/license_detector.py |
| Cross-Compare | Row/Cell comparison across Excel files | 75% (default) | services/cross_compare.py |
| Pipeline Runner | Orchestrates selected methods | N/A | services/pipeline_runner.py |

## API Reference

Base URL: http://localhost:8000
Docs: http://localhost:8000/docs

### Ingest — /api/v1/ingest
| Method | Path | Description |
|---|---|---|
| POST | /input/data | Preview file contents (original + cleaned) |
| POST | /preprocess | Clean and preview text; optional CSV/Excel download |
| POST | /reference/register | Register files as reference batches with cell positions |

### Pipeline — /api/v1/pipeline
| Method | Path | Description |
|---|---|---|
| POST | /run | Unified detection run across selected methods |
| POST | /run-on-server | Run pipeline on stored batches only |

### Batches — /api/v1/batches
| Method | Path | Description |
|---|---|---|
| GET | / | List all batches with entry counts |
| DELETE | /{batch_id} | Delete a batch and all related data |
| PATCH | /{batch_id} | Rename a batch |

### Reports — /api/v1/reports
| Method | Path | Description |
|---|---|---|
| POST | /combined | Generate multi-sheet Excel report |

### Compare — /api/v1/compare
| Method | Path | Description |
|---|---|---|
| POST | /cross | Cross-file row/cell comparison (JSON result) |
| POST | /report | Cross-file comparison report (.xlsx) |
| POST | /colored | Color-coded workbook (.xlsx) |

## Pipeline Output Format

### PipelineResult (top-level)
```json
{
        "pipeline_id": "a1b2c3d4-...",
        "status": "completed",
        "summary": {
                "total_entries": 3,
                "flagged": 1,
                "risk_breakdown": {"high": 0, "medium": 1, "low": 0, "none": 2}
        },
        "results": [
                {
                        "entry_id": 1,
                        "original_text": "...",
                        "overall_risk": "medium",
                        "methods": {
                                "exact": {"is_duplicate": false, "matched_text": null, "batch": null},
                                "fuzzy": {"is_duplicate": true, "scores": {"levenshtein": 0.91, "jaccard": 0.78, "ngram": 0.86}, "matched_text": "..."},
                                "semantic": {"is_duplicate": false, "similarity": null, "matched_text": null},
                                "ai_detection": {"is_ai_generated": false, "confidence": 0.11, "label": "Human"},
                                "web_scan": {"found_online": false, "sources": [], "error": null},
                                "license_check": {"has_license": false, "licenses": [], "risk_level": "none"}
                        }
                }
        ]
}
```

## Combined Report Format

The combined Excel report includes seven sheets:
1. Summary
2. Exact Matches
3. Fuzzy Matches
4. Semantic Matches
5. AI Detection
6. Web Scan
7. License Check

## Configuration

Create backend/.env and set:

```env
DATABASE_URL=postgresql://user:password@host:port/dbname
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
EMBEDDING_MODEL=all-MiniLM-L6-v2
AI_DETECTION_MODEL=openai-community/roberta-large-openai-detector
FUZZY_THRESHOLD=0.85
SEMANTIC_THRESHOLD=0.85
WEB_SCAN_TIMEOUT=10
WEB_SCAN_RETRIES=3
LOG_LEVEL=INFO
```

## How to Run Locally

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Database (Supabase)
1. Create a project at https://supabase.com.
2. Enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Run the schema in the Database Schema section.
4. Set `DATABASE_URL` in backend/.env.

## Key Design Decisions

| Decision | Reason |
|---|---|
| FastAPI over Flask/Django | Async-first APIs for concurrent web scanning and batch inference |
| PostgreSQL + pgvector | Single store for structured data and embeddings |
| SBERT all-MiniLM-L6-v2 | Balanced performance for sentence-level similarity |
| RoBERTa AI detector | High-accuracy AI detection with swap via env var |
| DuckDuckGo web scan | No API key required; controlled retries and timeout |
| Per-cell provenance | Enables exact row/column traceability in reports |
| Startup model cache | Single-load model initialization via lifespan |
