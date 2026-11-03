# Warranty Agent — Complete Codebase Directory & File Guide

This document provides a comprehensive, file-by-file and folder-by-folder breakdown of the entire **Warranty Agent** repository. It explains what each component does, how they interact, and where every piece of business logic resides.

---

## High-Level Architecture Overview

```
warranty-agent/
├── 📁 backend/                # Python 3.11 + FastAPI Server, AI Engines, Database & Tests
│   ├── 📁 app/               # Application code (routers, services, database models, schemas)
│   ├── 📁 tests/             # Automated test suite (130 pytest cases)
│   ├── 📁 scripts/           # Validation and database smoke-test scripts
│   └── 📁 frontend_dist/     # Pre-built static frontend bundle for single-container hosting
├── 📁 frontend/               # React 19 + Vite + Tailwind CSS v4 Client Dashboard
│   ├── 📁 public/            # Static assets (favicons, SVGs)
│   └── 📁 src/               # Application source (views, components, animations, utilities)
├── 📁 .github/workflows/      # Automated CI/CD pipelines (GitHub Actions)
└── 📄 Deployment Configs      # Dockerfile, render.yaml, vercel.json, netlify.toml
```

---

## 1. Root Repository Files

These files configure repository management, local containerization, cloud hosting, and top-level documentation:

| File / Folder | Purpose & Description |
| :--- | :--- |
| **`.github/workflows/ci.yml`** | **Continuous Integration (CI) Pipeline**: Runs automatically on every push or pull request to GitHub. It installs Python dependencies, runs linters, and executes the 130-test `pytest` suite to prevent regressions. |
| **`.dockerignore`** | Specifies files and folders that Docker should ignore during build (e.g., `node_modules`, `.venv`, `.git`, temporary log files), ensuring small image sizes. |
| **`.gitattributes`** | Enforces consistent line-ending handling (`LF` vs `CRLF`) across different operating systems (Windows, macOS, Linux). |
| **`.gitignore`** | Tells Git which files never to commit to the repository (e.g., secrets `.env`, Python cache `__pycache__`, local databases `*.db`, compiled assets). |
| **`Dockerfile`** | **Multi-stage Production Dockerfile**: Builds both the React frontend and the Python backend into a single production container for platforms like Render or Railway. |
| **`docker-compose.yml`** | **Local Development Orchestration**: Spins up the FastAPI backend and a local PostgreSQL database with a single command (`docker compose up`). |
| **`render.yaml`** | **Render Cloud Blueprint**: Infrastructure-as-code configuration specifying how Render should deploy the web service, set environment variables, and manage PostgreSQL. |
| **`railway.json`** | Configuration specifying build and deployment parameters when hosting on Railway. |
| **`vercel.json`** | Defines routing rules and URL rewrites so that single-page client routing works seamlessly when hosted on Vercel. |
| **`netlify.toml`** | Build commands and redirection rules for deploying the static frontend to Netlify. |
| **`README.md`** | Primary project documentation: quickstart commands, environment variables list, architecture diagram, and feature summary. |
| **`CHANGELOG.md`** | Chronological record of features, milestone progressions, improvements, and bug fixes across project versions. |
| **`DEPLOYMENT.md`** | Comprehensive production deployment guide with instructions for Google Cloud OAuth, Render, Vercel, and Netlify. |
| **`WARRANTY_AGENT_OVERVIEW.md`** | In-depth product document detailing market gaps (India vs. USA/China), all 11 features, system architecture, and technology justifications. |

---

## 2. Backend (`backend/`)

The backend is built with **Python 3.11** using **FastAPI** for high-concurrency asynchronous API routing, **SQLAlchemy 2.0** for database ORM, and **Alembic** for schema migrations.

### 2.1 Backend Root Files
* **`backend/main.py`**: **The Application Entry Point**.
  - Configures CORS middleware for frontend communication.
  - Implements the `lifespan` handler that starts the background daily alert scheduler on startup and shuts it down cleanly on exit.
  - Mounts all sub-routers (`/auth/gmail`, `/ingest`, `/purchases`, `/alerts`, `/agent`).
  - Serves static pre-compiled frontend assets when deployed in single-server mode.
* **`backend/requirements.txt`**: Lists all Python library dependencies, including `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic`, `google-api-python-client`, `apscheduler`, `pdfplumber`, `pytesseract`, and `google-genai`.
* **`backend/Procfile`**: Instruction file for cloud platform process managers (e.g., Render/Heroku) indicating how to run the web server (`uvicorn main:app --host 0.0.0.0 --port $PORT`).
* **`backend/runtime.txt`**: Specifies the exact Python runtime version (`python-3.11.x`) required by cloud deployment environments.
* **`backend/alembic.ini`**: Configuration file for Alembic database migration tool.
* **`backend/pytest.ini`**: Settings for running backend test suites with pytest.
* **`backend/.env.example`**: Template of all environment variables required (e.g., `DATABASE_URL`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
* **`backend/Dockerfile`**: Standalone Dockerfile specifically for containerizing the backend service independently.

---

### 2.2 Core Database & Schemas (`backend/app/`)
* **`backend/app/database.py`**:
  - Initializes the SQLAlchemy database engine (`create_engine`).
  - Configures thread-safe database session factories (`SessionLocal`).
  - Provides the `get_db()` dependency generator used by FastAPI routes.
* **`backend/app/models.py`**: **SQLAlchemy Relational Database Models**:
  - `User`: Stores user ID, email, and encrypted OAuth tokens.
  - `Purchase`: Stores purchase records (product name, vendor, order ID, purchase date, price, currency, invoice reference).
  - `WarrantyPeriod`: Stores calculated warranty start/end dates, return window end date, and confidence level.
  - `Alert`: Stores scheduled and triggered alerts (30-day, 15-day, 7-day expiration warnings).
  - `PriceDropRecord`: Stores monitored festival discounts, drop amounts, and refund eligibility.
* **`backend/app/schemas.py`**: **Pydantic v2 Models**:
  - Defines data validation rules, request schemas, and JSON response models for all API endpoints.

---

### 2.3 Database Migrations (`backend/app/alembic/`)
* **`backend/app/alembic/env.py`**: The migration runner script that connects Alembic to the SQLAlchemy metadata.
* **`backend/app/alembic/versions/`**:
  - `0001_initial_schema.py`: Initial migration creating the five core tables (`users`, `purchases`, `warranty_periods`, `alerts`, `price_drop_records`).
  - `0002_add_household_member.py`: Adds household member tracking.
  - `0003_add_family_member.py`: Adds family tagging support for warranty sharing.

---

### 2.4 API Route Handlers (`backend/app/routers/`)
* **`auth_gmail.py`**: Handles Google Cloud OAuth 2.0 authorization:
  - `GET /auth/gmail/url`: Generates consent URL for user login.
  - `GET /auth/gmail/callback`: Exchanges authorization codes for access and refresh tokens.
  - `POST /auth/gmail/disconnect`: Revokes tokens and clears user session.
* **`ingestion.py`**: **Receipt & Invoice Processing**:
  - `POST /ingest/scan-gmail`: Scans connected Gmail inbox for retailer order confirmations.
  - `POST /ingest/file`: Accepts uploaded PDF/image invoices, runs OCR, and triggers deduplication.
* **`extraction.py`**: Provides preview endpoints (`POST /extraction/extract`) to test extraction against raw text without persisting data.
* **`purchases.py`**: Full CRUD operations for purchases:
  - List all purchases with category filtering and search.
  - Retrieve single purchase details and associated warranty timeline.
  - Update or delete records.
* **`alerts.py`**: Manages warranty expiry and price drop notifications (`GET /alerts`, `POST /alerts/{id}/dismiss`).
* **`agent.py`**: AI Assistant endpoint (`POST /agent/query`) accepting natural language questions and returning contextual answers in English.
* **`health.py`**: Health-check endpoint (`GET /health`) returning database connection status and server uptime for monitoring.

---

### 2.5 Business Logic & AI Services (`backend/app/services/`)
* **`gmail_client.py`**: Queries the Gmail REST API with targeted queries (`from:amazon.in OR from:flipkart.com ... -in:sent`) using OAuth tokens.
* **`extractor_regex.py`**: **Tier-1 Fast Extractor**: Deterministic regular expression patterns that extract order IDs, product names, prices, and dates from major Indian retailers in under 10 milliseconds.
* **`extractor_llm.py`**: **Tier-2 AI Fallback**: Calls the Google Gemini Flash model when receipts have unusual layouts or low regex confidence.
* **`ocr.py`**: Optical Character Recognition engine using Tesseract and Pillow (PIL) to parse photos of warranty cards and thermal receipts.
* **`vendor_normalizer.py`**: Cleans messy merchant strings (e.g., maps `AMZN Mktp IN` or `Amazon Seller Services` to `Amazon India`).
* **`category_fallback.py`**: Assigns standard statutory or industry warranty estimates (e.g., Laptops = 12 months) when an invoice omits warranty duration.
* **`price_radar.py`**: Calculates price drops during festive sales (Diwali, Big Billion Days), verifies active return windows (7–10 days), and generates retailer price-match scripts.
* **`legal_generator.py`**: **Consumer Rights Generator**: Generates formal 15-day pre-litigation legal notices citing **Sections 84–87 of the Indian Consumer Protection Act, 2019**, NCH 1915 helpline drafts, and e-Jagriti filing guidance.
* **`warranty_agent.py`**: Powers the conversational AI concierge, enforcing English language output and grounding answers in user purchase records.
* **`alert_engine.py`**: Configures **APScheduler** to run daily cron checks flagging warranties expiring in 30, 15, and 7 days.
* **`encryption.py`**: Cryptographic service encrypting sensitive OAuth refresh tokens using AES-256 before persisting to disk.
* **`recall_watcher.py`**: Service monitoring public safety recall databases for registered consumer products.

---

### 2.6 Tests & Validation (`backend/tests/` & `backend/scripts/`)
* **`backend/tests/conftest.py`**: Pytest fixtures creating temporary in-memory test databases and mock clients.
* **`backend/tests/test_unit_coverage.py`**: Unit tests for schema validation, vendor normalizers, and category heuristics.
* **`backend/tests/test_extraction_precision.py`**: Tests accuracy against real-world sample receipt files.
* **`backend/tests/test_auth_security.py`**: Tests OAuth token lifecycle and AES-256 encryption.
* **`backend/tests/test_alert_timeliness.py`**: Tests cron schedule triggers and notification thresholds.
* **`backend/tests/test_enhancements.py`**: Tests festival price radar, legal notice drafting, and portal URL validity.
* **`backend/tests/labeled_dataset.json`**: Ground-truth dataset used for benchmarking receipt parsing accuracy.
* **`backend/scripts/test_db.py`**: Standalone Python script to quickly verify live database connectivity.
* **`backend/scripts/run_validation.py`**: Automated validation report generator verifying all milestones.

---

## 3. Frontend (`frontend/`)

The frontend is a modern Single Page Application (SPA) built with **React 19**, bundled via **Vite**, and styled with **Tailwind CSS v4** and **Framer Motion**.

### 3.1 Frontend Root & Build Configuration
* **`frontend/index.html`**: Host HTML page mounting the React root and importing Google Fonts (Inter, Space Grotesk).
* **`frontend/vite.config.js`**: Vite configuration providing React JSX compilation, port setup (`5173`), and local proxying of `/api` requests to `localhost:8000`.
* **`frontend/package.json`**: NPM package manifest specifying dependencies (`react`, `motion`, `lucide-react`, `tailwindcss`) and build scripts.
* **`frontend/.oxlintrc.json`**: Linter configuration for code quality checks.
* **`frontend/public/`**: Contains static assets like `favicon.svg` and `icons.svg`.

---

### 3.2 Main Views (`frontend/src/views/`)
* **`DashboardView.jsx`**: **The Primary Command Center**:
  - Displays summary counters (Active Warranties, Expiring Soon, Monitored Value).
  - Hosts the **Festival Price Drop Radar** banner for claiming sale refunds.
  - Renders purchase cards with search, sorting, and filter chips.
* **`UploadView.jsx`**: Document ingestion screen allowing users to drag-and-drop PDF invoices, upload warranty card photos, or manually enter extended warranty terms.
* **`DetailView.jsx`**: Deep-dive product inspection view showing warranty expiration countdowns, invoice attachments, direct store links, and the Legal Notice trigger.
* **`AlertsView.jsx`**: Dedicated notifications center listing impending warranty expirations and price-drop alerts.
* **`LookupView.jsx`**: Utility screen allowing users to paste raw email text or test extraction previews without saving to the database.
* **`LandingView.jsx`**: Clean onboarding hero screen introducing features to first-time visitors before connecting accounts.
* **`DossierView.jsx`**: Formats all purchase data, warranty cards, and invoices into a structured, printable claim document for service center visits.

---

### 3.3 Core Components (`frontend/src/components/`)
* **`Shell.jsx`**: Global layout wrapper containing the top navigation bar, brand logo, dark/light theme toggle, and copyright footer.
* **`PurchaseCard.jsx`**: Interactive card displaying individual products, retailer badges, expiration countdowns, and quick actions.
* **`PriceDropRadarCard.jsx`**: Highlights detected price drops during festival sales, displays potential refund savings in INR, and provides the 1-click refund script.
* **`LegalNoticeModal.jsx`**: Interactive modal that drafts formal 15-day pre-litigation notices under the Consumer Protection Act, 2019, NCH 1915 summaries, and links to e-Jagriti.
* **`FloatingAgentModal.jsx`**: Floating conversational chat popup allowing users to ask natural-language questions to the AI assistant.
* **`WarrantyTimeline.jsx`**: Visual progress bar indicating purchase date, return window boundary, warranty expiration date, and elapsed time.
* **`RadarScanner.jsx`**: Animated radar sweep graphic indicating active real-time account monitoring.
* **`Icon.jsx`**: Standardized Lucide SVG icon wrapper.
* **`ui.jsx`**: Reusable design system primitives (Buttons, Inputs, Status Badges, Spinners, Glass Cards).
* **`charts.jsx`**: Lightweight SVG data visualization charts for spend and category breakdowns.

---

### 3.4 Animation & Visual Effects (`frontend/src/components/aceternity/`, `magicui/`, `reactbits/`)
* **`reactbits/Aurora.jsx` & `Aurora.css`**: GPU-accelerated WebGL / CSS aurora background gradient effect.
* **`reactbits/Particles.jsx`**: Ambient floating particle effect for visual depth.
* **`reactbits/SpotlightCard.jsx` & `TiltCard.jsx`**: Interactive 3D hover effects that tilt and illuminate cards based on cursor movement.
* **`magicui/border-beam.jsx`**: Animated glowing border beam highlighting active cards.
* **`magicui/number-ticker.jsx`**: Smooth numeric roll-up animation for stats and price totals.
* **`aceternity/lamp.jsx` & `spotlight.jsx`**: High-impact decorative lighting effects.

---

### 3.5 Utilities & Contexts (`frontend/src/lib/`)
* **`utils.js`**: Universal helper functions, including `cn` for conditional Tailwind class merging.
* **`format.js`**: Specialized formatters for Indian Rupees (`fmtCompactINR`), ordinal dates, and relative countdown times.
* **`hooks.js`**: Custom React hooks for responsive window dimensions, search parameters, and local storage state.
* **`theme-context.js`**: Context provider managing seamless switching between dark and light modes.
* **`animation-theme.js`**: Spring animation constants and motion curve presets.

---

## Summary Mapping: How Frontend Connects to Backend

```
┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
│     FRONTEND (React Views)      │                 │     BACKEND (FastAPI API)       │
├─────────────────────────────────┤                 ├─────────────────────────────────┤
│ DashboardView.jsx               │  ───────────►   │ GET /purchases                  │
│ UploadView.jsx                  │  ───────────►   │ POST /ingest/file               │
│ LegalNoticeModal.jsx            │  ───────────►   │ POST /purchases/{id}/legal-not..│
│ PriceDropRadarCard.jsx          │  ───────────►   │ GET /purchases (price_radar)    │
│ FloatingAgentModal.jsx          │  ───────────►   │ POST /agent/query               │
│ AlertsView.jsx                  │  ───────────►   │ GET /alerts                     │
└─────────────────────────────────┘                 └─────────────────────────────────┘
```

Every file in the repository has a single, well-defined responsibility, ensuring clean separation of concerns, high testability, and smooth maintainability.
