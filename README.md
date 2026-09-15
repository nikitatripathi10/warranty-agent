# Warranty Radar

Automatically tracks purchases from Gmail order-confirmation emails and uploaded
documents (invoices, warranty cards), extracts product/warranty/return-window
information, and stores it in a structured database for future alerting.

> **Milestone 2** — Document processing + purchase repository.
> Alerting, recall watching, and the chat agent are later milestones.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Required Environment Variables](#required-environment-variables)
3. [Google Cloud OAuth Setup](#google-cloud-oauth-setup)
4. [Local Development — Backend](#local-development--backend)
5. [Local Development — Frontend](#local-development--frontend)
6. [Database Migrations (Alembic)](#database-migrations-alembic)
7. [Extraction Approach](#extraction-approach)
8. [API Reference](#api-reference)
9. [Repo Structure](#repo-structure)
10. [Non-negotiable Quality Rules](#non-negotiable-quality-rules)

---

## Architecture

```
Gmail / Uploaded file
        │
        ▼
  Ingestion layer  ──►  Pass 1: Regex extractor (Amazon.in, Flipkart, generic)
  (routers/)               │  confidence == 'low'?
                           ▼
                      Pass 2: Claude LLM fallback (Anthropic API)
                           │
                           ▼
                   purchases + warranty_periods (PostgreSQL)
```

**Tech stack:**
- Backend: Python 3.11+, FastAPI, Uvicorn
- ORM / migrations: SQLAlchemy 2 + Alembic
- Database: PostgreSQL (Supabase / Neon / any hosted instance via `DATABASE_URL`)
- Frontend: React (Vite), plain `fetch`
- Auth to Gmail: OAuth 2.0 via `google-auth-oauthlib`
- Extraction: regex rules → Anthropic Claude API fallback
- OCR: `pdfplumber` (text PDFs) → `pdf2image` + `pytesseract` (scanned PDFs/images)
- Encryption at rest: `cryptography.Fernet` for OAuth refresh tokens

---

## Required Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in every value.
**Never commit `.env`** — it is in `.gitignore`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string, e.g. `postgresql://user:pass@host:5432/db` |
| `FERNET_KEY` | Symmetric key for encrypting OAuth refresh tokens at rest |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console (Web application OAuth 2.0 client) |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | Must match what you registered; `http://localhost:8000/auth/gmail/callback` for local dev |
| `ANTHROPIC_API_KEY` | Your Anthropic API key for the Claude LLM extraction fallback |
| `FRONTEND_ORIGIN` | CORS allowed origin, e.g. `http://localhost:5173` |
| `UPLOAD_DIR` | Directory for uploaded files (default: `uploads`, relative to `backend/`) |
| `POPPLER_PATH` | *(Windows only)* Path to Poppler `bin/` for `pdf2image` |

**Generate a Fernet key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Google Cloud OAuth Setup

You must create your own OAuth 2.0 credentials in Google Cloud Console.
This project does not ship credentials.

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth 2.0 Client ID**.
3. Application type: **Web application**.
4. Name: `Warranty Radar Local` (or anything).
5. **Authorised redirect URIs:** add `http://localhost:8000/auth/gmail/callback`.
6. Click **Create** → copy the **Client ID** and **Client Secret** into your `.env`.
7. Go to **APIs & Services → Library** → enable **Gmail API**.
8. Go to **OAuth consent screen** → set to **External**, add your email as a test user,
   add the scope `https://www.googleapis.com/auth/gmail.readonly`.

---

## Local Development — Backend

```bash
# 1. Create and activate virtual environment
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and fill environment variables
cp .env.example .env
# Edit .env with your real values

# 4. Run database migrations
alembic upgrade head

# 5. (Optional) Confirm schema with smoke test
python scripts/test_db.py

# 6. Start the dev server
uvicorn main:app --reload
# API docs: http://localhost:8000/docs
# Health:   http://localhost:8000/health
```

**System dependencies for OCR** (install separately):

| Dependency | Windows | macOS |
|---|---|---|
| Tesseract OCR | [UB-Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) | `brew install tesseract` |
| Poppler | [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) | `brew install poppler` |

On Windows, add Tesseract and Poppler `bin/` to PATH, or set the `POPPLER_PATH` env var.

---

## Local Development — Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

The frontend reads `VITE_API_BASE_URL` for the backend origin (defaults to `http://localhost:8000`).
Create `frontend/.env.local` if you need to override it:
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## Database Migrations (Alembic)

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Check current migration state
alembic current

# Auto-generate a new migration after editing models.py
alembic revision --autogenerate -m "describe your change"

# Roll back one migration
alembic downgrade -1
```

Alembic reads `DATABASE_URL` from your `.env` — never from `alembic.ini`.

---

## Extraction Approach

The extraction pipeline runs in two passes:

### Pass 1 — Regex / Rules

Found in [`backend/app/services/extractor_regex.py`](backend/app/services/extractor_regex.py).

For Amazon.in and Flipkart, we use compiled regular expressions tuned to the
specific template patterns those retailers use in their order-confirmation emails:

- **Amazon.in** — detected by the `\d{3}-\d{7}-\d{7}` order ID pattern.
  Separate patterns extract the product name, order date, and order total.
- **Flipkart** — detected by the `OD\d{15,}` order ID pattern or `flipkart` in body.
- **Generic fallback** — looks for currency symbols and date patterns for any
  other retailer.

Each extractor returns a confidence score:
- `high` — product name, date, price, and retailer/brand all extracted
- `medium` — at least product name and price found
- `low` — fewer than two key fields found

### Pass 2 — LLM Fallback (Claude)

If Pass 1 returns `low` confidence, the cleaned text is sent to Anthropic's
Claude API (`claude-haiku-4-5` model) with:

1. A system prompt that specifies the exact JSON schema to return.
2. Three few-shot examples (Amazon.in, Flipkart, ambiguous) to anchor the format.
3. An explicit instruction: *"If uncertain about a field, set it to null — do NOT guess. Set confidence to 'low' rather than fabricate data."*

The LLM call has a 30-second timeout. Malformed JSON responses are caught,
logged, and result in returning the (low-confidence) regex result rather than
crashing. The LLM API key is optional — if not set, Pass 2 is simply skipped.

### Uploaded Documents

Before extraction, uploaded PDFs and images go through the OCR pipeline
([`backend/app/services/ocr.py`](backend/app/services/ocr.py)):

1. **Text-based PDF** → `pdfplumber` extracts text directly (fast, no OCR).
2. **Scanned PDF** → `pdf2image` converts pages to images → `pytesseract` runs OCR.
3. **Images (JPG, PNG, etc.)** → `pytesseract` directly.

The resulting text is fed into the same Pass 1 / Pass 2 pipeline.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/auth/gmail/connect` | Redirect to Google OAuth consent |
| GET | `/auth/gmail/callback` | Handle OAuth callback, return `user_id` |
| POST | `/ingestion/fetch-emails?user_id=<uuid>` | Fetch Gmail order emails, extract, persist |
| POST | `/ingestion/upload` | Upload PDF/image, OCR, extract, persist |
| POST | `/extraction/test` | Test extraction on raw text (no DB write) |

Full interactive docs: `http://localhost:8000/docs`

---

## Repo Structure

```
warranty-radar/
  backend/
    main.py                          # FastAPI app factory, CORS, logging
    requirements.txt
    alembic.ini                      # Alembic config (no hardcoded DB URL)
    .env.example                     # ← commit this; never commit .env
    app/
      __init__.py
      database.py                    # SQLAlchemy engine, SessionLocal, get_db
      models.py                      # ORM: users, purchases, warranty_periods, alerts, recalls
      schemas.py                     # Pydantic v2 request/response models
      alembic/
        env.py                       # Reads DATABASE_URL from env for autogenerate
        versions/
          0001_initial_schema.py     # Initial migration
      routers/
        health.py
        auth_gmail.py                # OAuth connect + callback
        ingestion.py                 # fetch-emails + upload endpoints
        extraction.py                # /extraction/test (debug endpoint)
      services/
        encryption.py                # Fernet encrypt/decrypt
        gmail_client.py              # Gmail API search + fetch (no body storage)
        extractor_regex.py           # Pass 1: regex/rules (pure functions)
        extractor_llm.py             # Pass 2: Claude LLM fallback
        ocr.py                       # pdfplumber + pdf2image + pytesseract
    scripts/
      test_db.py                     # Schema smoke test (insert/query/delete)
  frontend/
    index.html
    src/
      main.jsx
      App.jsx                        # Single-page UI: health, OAuth, upload, fetch
      index.css                      # Dark glassmorphism design system
  .gitignore
  README.md
```

---

## Non-negotiable Quality Rules

- **No secrets committed** — `.env` is in `.gitignore`; `.env.example` has placeholders only.
- **All external calls wrapped** — Gmail API, Claude API, and Google OAuth calls
  are inside try/except with logging. Failures degrade gracefully and never crash the process.
- **Pydantic everywhere** — all request/response shapes are Pydantic v2 models.
- **Structured logging** — `logging` module with timestamps on all ingestion,
  extraction, and OAuth events.
- **Encrypted refresh tokens** — `cryptography.Fernet`; plaintext never touches the DB.
- **Pure extraction functions** — `extractor_regex.py` has no I/O, making it trivial
  to unit-test in Milestone 4.
- **Migration-based schema changes** — `alembic revision --autogenerate` for every
  future model change; never `Base.metadata.create_all` in production.
