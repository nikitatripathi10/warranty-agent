# Warranty Radar — Deployment Guide

Complete instructions for deploying Warranty Radar to production:
- **Backend** → [Railway](https://railway.app) (Docker, auto-deploy from GitHub)
- **Frontend** → [Netlify](https://netlify.com) or [Vercel](https://vercel.com) (Vite/React, auto-deploy from GitHub)
- **Database** → [Supabase](https://supabase.com) or [Neon](https://neon.tech) (managed PostgreSQL)

---

## Architecture

```
GitHub ──► GitHub Actions CI ──► tests pass?
             │                         │
             │ (main branch)           │ (all green)
             ▼                         ▼
         Railway (backend)       Netlify (frontend)
         Docker image            npm run build → CDN
              │
              ▼
         Supabase / Neon
         (PostgreSQL)
```

---

## 1. Database Setup (Supabase)

### Option A: Supabase (recommended)
1. Go to [supabase.com](https://supabase.com) → New project
2. Note the **Connection String** (Transaction pooler):
   ```
   postgresql://postgres.[project-ref]:[password]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```
3. Run Alembic migrations (one-time, or via Railway release command):
   ```bash
   cd backend
   DATABASE_URL="<your-supabase-url>" alembic upgrade head
   ```

### Option B: Neon
1. Go to [neon.tech](https://neon.tech) → New project → ap-south-1 (India)
2. Copy the **Pooled connection string** (psycopg2 format)
3. Run migrations same as above

---

## 2. Backend Deployment (Railway)

### Initial Setup
1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select the `warranty-agent` repository
3. Railway detects `railway.json` automatically → uses the Dockerfile build

### Environment Variables
Set these in **Railway → Service → Variables**:

| Variable | Value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | Supabase/Neon connection string |
| `FERNET_KEY` | `<generated>` | Run: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `GOOGLE_CLIENT_ID` | `<from GCP>` | Google Cloud Console → OAuth 2.0 Credentials |
| `GOOGLE_CLIENT_SECRET` | `<from GCP>` | Same credential |
| `GOOGLE_REDIRECT_URI` | `https://your-api.up.railway.app/auth/gmail/callback` | Must match GCP authorized redirect URI |
| `GEMINI_API_KEY` | `<from makersuite>` | [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey) |
| `FRONTEND_ORIGIN` | `https://your-app.vercel.app` | Vercel deployment URL |
| `UPLOAD_DIR` | `uploads` | Relative to /app; Railway mounts ephemeral storage here |

### Post-Deploy
1. Railway assigns a URL like `https://warranty-radar-api.up.railway.app`
2. Verify liveness: `curl https://warranty-radar-api.up.railway.app/health`
3. Verify readiness (DB): `curl https://warranty-radar-api.up.railway.app/health/ready`
4. Run Alembic migrations via Railway console:
   ```bash
   alembic upgrade head
   ```

### Auto-deploy
Railway auto-deploys on every push to `main`. The `railway.json` is already
configured with `ON_FAILURE` restart policy and `/health` healthcheck.

---

## 3. Frontend Deployment (Netlify)

### Initial Setup
1. Go to [netlify.com](https://netlify.com) → **Add new site → Import an existing project → GitHub**
2. Select the `warranty-agent` repository
3. Configure the build:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
4. Netlify reads `frontend/netlify.toml` automatically (SPA redirects, cache headers, security headers)

### Environment Variables
Set in **Netlify → Site → Site configuration → Environment variables**:

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://warranty-radar-api.up.railway.app` |

### Auto-deploy
Netlify auto-deploys on every push to `main`. Each PR gets a unique preview URL.

---

## 3b. Alternative Frontend Deployment (Vercel)

If you prefer Vercel:
1. Go to [vercel.com](https://vercel.com) → Add New → Project → Import Git Repository
2. Select `warranty-agent` → set **Root Directory** to `frontend`
3. Vercel detects Vite automatically from `frontend/vercel.json`
4. Set `VITE_API_URL` in Vercel environment variables → same value as above

---

## 4. Google Cloud OAuth Setup (Production)

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials
2. Edit your OAuth 2.0 Web Application credential
3. Add to **Authorized redirect URIs**:
   ```
   https://warranty-radar-api.up.railway.app/auth/gmail/callback
   ```
4. Add to **Authorized JavaScript origins**:
   ```
   https://your-app.netlify.app
   ```
5. Update `GOOGLE_REDIRECT_URI` in Railway to match exactly

---

## 5. Local Development with Docker Compose

```bash
# 1. Copy env files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Edit both files with your secrets

# 2. Start the database first
docker compose up postgres -d

# 3. Run Alembic migrations (first time only)
docker compose exec backend alembic upgrade head

# 4. Start everything
docker compose up

# App is now running:
#   Frontend:  http://localhost:5173
#   Backend:   http://localhost:8000
#   API docs:  http://localhost:8000/docs
#   DB:        localhost:5432
```

---

## 6. GitHub Actions CI

The `.github/workflows/ci.yml` pipeline runs automatically on every push to
`main` or `develop` and on all pull requests:

| Job | What it does |
|---|---|
| `backend-tests` | Runs `pytest tests/ -v` + `run_validation.py` on Python 3.11 and 3.12 |
| `frontend-build` | `npm ci` + `npm run build` to catch compile errors |
| `docker-build` | Builds the Docker image (main branch only) to catch Dockerfile errors |

### Required GitHub Secrets (optional — CI works with dummies)
| Secret | Purpose |
|---|---|
| `FERNET_KEY_CI` | A valid Fernet key for CI; if not set, a dummy is used (tests still pass) |

---

## 7. Post-Deployment Smoke Test Checklist

Run these after every production deploy:

```bash
API=https://warranty-radar-api.up.railway.app

# 1. Liveness
curl $API/health

# 2. Readiness (DB connectivity)
curl $API/health/ready

# 3. API docs reachable
curl -o /dev/null -s -w "%{http_code}" $API/docs

# 4. OAuth redirect works
curl -o /dev/null -s -w "%{http_code}" "$API/auth/gmail/connect?user_id=test"
```

Expected: all return 200 (OAuth returns 307 redirect — also expected).

---

## 8. Monitoring & Observability

### Railway
- **Metrics**: Railway Dashboard → Service → Metrics tab (CPU, memory, requests)
- **Logs**: Railway Dashboard → Service → Logs (structured JSON from Uvicorn)
- **Alerts**: Railway → Project → Settings → enable email alerts on crash/restart

### Vercel
- **Analytics**: Vercel Dashboard → Analytics (Core Web Vitals)
- **Function Logs**: Vercel Dashboard → Deployments → Functions

### Uptime Monitoring (recommended)
Set up a free uptime check on [UptimeRobot](https://uptimerobot.com) or
[Better Stack](https://betterstack.com) pointing to `GET /health/ready`.

---

## 9. Environment Variable Reference

### Backend (`backend/.env`)
```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
FERNET_KEY=<32-byte base64 key>
GOOGLE_CLIENT_ID=<from GCP>
GOOGLE_CLIENT_SECRET=<from GCP>
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/gmail/callback
GEMINI_API_KEY=<from makersuite>
FRONTEND_ORIGIN=http://localhost:5173
EXTRA_FRONTEND_ORIGINS=           # comma-separated, optional
UPLOAD_DIR=uploads
POPPLER_PATH=                     # Windows only: path to Poppler bin/
```

### Frontend (`frontend/.env.local`)
```env
VITE_API_URL=http://localhost:8000
```

### Frontend Netlify Production Variable
Set in **Netlify → Site configuration → Environment variables**:
```
VITE_API_URL=https://your-api.up.railway.app
```

---

## 10. Rollback Procedure

### Railway
1. Railway Dashboard → Service → Deployments
2. Click any past deployment → "Redeploy"
3. Old image is already cached — rollback completes in ~30 seconds

### Vercel
1. Vercel Dashboard → Project → Deployments
2. Click the last known-good deployment → "Promote to Production"

### Database
Alembic supports downgrade:
```bash
alembic downgrade -1   # roll back one migration
alembic downgrade base # roll back everything (DANGER — data loss)
```
