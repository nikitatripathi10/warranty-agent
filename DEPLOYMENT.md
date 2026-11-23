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

## 4. Google Cloud OAuth Setup (Allowing Any User / Production)

By default, Google sets new OAuth projects to **"Testing"** mode. In Testing mode, Google restricts access **strictly to accounts listed in Test users**. To allow anyone to connect with their own email:

### Step 1: Set OAuth Consent Screen to Production
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → **APIs & Services → OAuth consent screen**.
2. Under **Publishing status**, click **"PUBLISH APP"** and confirm.
   - Once published as an External app, **any Google user in the world** can sign in.
   - *Note on verification:* Because `gmail.readonly` is a sensitive scope, Google will show an *"Unverified app"* warning screen. Users simply click **"Advanced" → "Go to Warranty Radar (unsafe)"** and check the box to grant Gmail read access.
3. *Alternative (instant without the unverified screen for select testers):* Keep it in Testing mode and add your friends/evaluators under **Audience → Test users → + ADD USERS**.

### Step 2: Configure Authorized Redirect URIs
1. In Google Cloud Console → **APIs & Services → Credentials** → click your OAuth 2.0 Client ID.
2. Under **Authorized redirect URIs**, ensure you have:
   ```
   https://warranty-agent.onrender.com/auth/gmail/callback
   http://localhost:8000/auth/gmail/callback
   ```
3. Under **Authorized JavaScript origins**, add:
   ```
   https://warranty-agent-nikita-54bd.vercel.app
   https://venerable-boba-fb4868.netlify.app
   http://localhost:5173
   ```
4. Click **Save**.

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

---

## 11. Serving the SPA from the backend (Python-runtime hosts)

Some hosts (for example Render, when it builds the Python app directly instead of
the root `Dockerfile`) never run the frontend build. In that case `main.py`
serves `backend/frontend_dist` at `/`, but only when the directory exists, so
backend-only deployments are unaffected.

Regenerate and commit it after any frontend change:

```bash
npm --prefix frontend run build
rm -rf backend/frontend_dist && cp -r frontend/dist backend/frontend_dist
```

The directory is generated output (see `.gitattributes`) - never edit those files
by hand. Docker builds ignore the checked-in copy and build the SPA fresh in the
image.


---

## 12. WhatsApp Bot Setup (Optional)

You can turn on **"Add bills from WhatsApp"** (plus proactive WhatsApp warranty-expiry reminders) using **either** Twilio (no Facebook account needed) or Meta Cloud API directly.

### Option A: Twilio WhatsApp Sandbox (Recommended — No Facebook Account Required)

1. Sign up for a free trial at [twilio.com](https://www.twilio.com/) using only your email and phone number (no credit card or Facebook account needed).
2. In the Twilio Console open **Messaging → Try it out → Send a WhatsApp message**. Note your sandbox number (`+1 415 523 8886`) and two-word join code (e.g. `join alpha-beta`).
3. On your **Render / Railway** backend, set:
   ```env
   TWILIO_ACCOUNT_SID=<Account SID from Twilio Console home>
   TWILIO_AUTH_TOKEN=<Auth Token from Twilio Console home>
   TWILIO_WHATSAPP_NUMBER=14155238886
   TWILIO_SANDBOX_JOIN_CODE=<your join phrase, e.g. join alpha-beta>
   TWILIO_WEBHOOK_URL=https://<your-backend-domain>/whatsapp/twilio-webhook
   ```
4. Back in Twilio Console → **Messaging → Settings → WhatsApp sandbox settings**:
   - Set **When a message comes in** to `https://<your-backend-domain>/whatsapp/twilio-webhook` (`HTTP POST`) and click **Save**.
5. Any user can now open **Upload → Link my WhatsApp**, send the join phrase + `LINK <code>`, and forward bills directly in WhatsApp. *(Note: Sandbox connections expire every 72 hours — users simply resend the join phrase to reconnect.)*

### Option B: Meta WhatsApp Business Cloud API (Unlimited Public Production)

1. Open [Meta for Developers](https://developers.facebook.com/), create (or select) an app, and add the **WhatsApp** product.
2. In **WhatsApp → API Setup**, generate a permanent System User access token and copy your **Phone Number ID**.
3. Set the following backend environment variables (and redeploy / restart):
   ```env
   WHATSAPP_ACCESS_TOKEN=<permanent Meta Graph API token>
   WHATSAPP_PHONE_NUMBER_ID=<Meta phone number ID>
   WHATSAPP_APP_SECRET=<Meta App Secret from App Settings → Basic>
   WHATSAPP_VERIFY_TOKEN=<any random string you pick>
   WHATSAPP_BOT_NUMBER=<bot phone digits with country code, e.g. 919876543210>
   WHATSAPP_GRAPH_VERSION=v21.0
   ```
4. In **WhatsApp → Configuration → Webhook**:
   - **Callback URL**: `https://<your-backend-domain>/whatsapp/webhook`
   - **Verify Token**: the exact `WHATSAPP_VERIFY_TOKEN` you set above
   - Click **Verify and Save**, then subscribe to the **`messages`** webhook field.

*(Database note: run `alembic upgrade head` if using manual migrations; `main.py` also ensures `whatsapp_links` and `purchase_payment_methods` exist via `CREATE TABLE IF NOT EXISTS` on startup.)*


---

## 13. Forward-to-Email Setup (Optional)

Lets every user forward order / invoice emails from **any** mail app to a private address
(`bills+<token>@your-domain`). No Gmail OAuth, so no Google security audit is needed.

1. Buy a domain (a `.in` domain is roughly ₹500-800/year) and add it to a free Cloudflare account.
2. Enable **Email → Email Routing** in Cloudflare.
3. Deploy the worker in `infra/cloudflare-email-worker/` (steps in its `README.md`) and point the
   catch-all routing rule at it.
4. Set on the backend (Render → Environment):
   ```env
   INBOUND_EMAIL_DOMAIN=warrantyagent.in
   INBOUND_EMAIL_SECRET=<the same long random string stored in the worker>
   ```
5. Run `alembic upgrade head` if you migrate manually (`main.py` also creates the `email_inboxes`
   table on startup with `CREATE TABLE IF NOT EXISTS`).

Users find their address under **Upload → Forward bills by email**. The app also captures Gmail's
one-time forwarding confirmation code and shows it next to the address.


---

## 14. Production Hardening (Session Auth, Cloud Storage, Cron & Monitoring)

These settings harden the backend for real public users (zero domain required):

### 1. Signed JWT Session Auth
* **`SESSION_SECRET`**: Set a long random string on Render (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). Falls back to `FERNET_KEY` if unset.
* **`REQUIRE_AUTH_TOKEN=true`** (default): Every `/purchases`, `/alerts`, `/agent`, `/ingestion/upload`, `/ingestion/fetch-emails`, `/ingestion/forwarding-address`, and `/whatsapp/status` call requires a signed Bearer JWT or `wa_session` cookie.
* **`DELETE /auth/gmail/account`**: Erases the user, cascaded DB records, and stored invoice files (DPDP Act 2023 compliance).

### 2. Permanent Cloud Storage (Cloudflare R2 or Supabase S3)
On Render's free tier, local `uploads/` files reset on deploy. To store invoices permanently for free (Cloudflare R2 gives 10 GB free):
```env
STORAGE_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
STORAGE_BUCKET=warranty-agent-invoices
STORAGE_ACCESS_KEY_ID=<R2 access key>
STORAGE_SECRET_ACCESS_KEY=<R2 secret key>
STORAGE_REGION=auto
```
Files are stored privately (`s3://invoices/...`) and served only through short-lived 5-minute pre-signed URLs (`GET /purchases/{id}/invoice-url`).

### 3. External Daily Alert Cron (GitHub Actions)
1. Set `CRON_SECRET` on Render and optionally `DISABLE_INPROCESS_SCHEDULER=true`.
2. In GitHub Repository → **Settings → Secrets and variables → Actions**, add:
   * `BACKEND_URL` = `https://warranty-agent.onrender.com`
   * `CRON_SECRET` = same secret as Render
`.github/workflows/daily-alerts.yml` then triggers `POST /alerts/cron/run-daily` every day at `08:00 UTC`.

### 4. Error & Uptime Monitoring (Free)
* **Sentry**: Create a free Sentry Python project and set `SENTRY_DSN` on Render (`sentry-sdk` optional).
* **UptimeRobot**: Monitor `GET https://warranty-agent.onrender.com/health/ready` every 5 minutes (also reports storage, WhatsApp, email, and auth readiness).
