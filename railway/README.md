# Deploying Incidentra to Railway

This folder contains **Railway-only** deployment files. They are additive — nothing here
changes `docker-compose.yml` or local development, which keep working exactly as before.

## Why this layout

Locally, `backend`, `celery_worker`, and `vuln_web` share a Docker volume for
`access.log` / `blocked_ips.json` / `rate_limited.json`. Railway has no volume shared
across multiple services, so this deployment merges `backend` + `vuln-web` + the Celery
worker/beat + the log monitor into **one service** ("core") that shares one container
filesystem. Postgres and Redis become Railway's managed plugins instead of containers.

Result: **4 Railway services** — `Postgres` (plugin), `Redis` (plugin), `core` (backend
API + `/lab` vuln-web demo + Celery + log monitor), `frontend` (static React via nginx).

Files in this folder:
- `core/Dockerfile` — builds the merged backend+vuln-web image (build context = repo root).
- `core/wsgi.py` — combines both Flask apps with `DispatcherMiddleware` (backend at `/`,
  vuln-web at `/lab`).
- `core/entrypoint.sh` — migrate → seed → init vuln-web DB → start log monitor + Celery
  worker/beat in background → `exec gunicorn`.

## 1. Create the project and datastores

1. Railway dashboard → **New Project** → **Empty Project** (so you can wire things up
   before the first deploy).
2. **+ Create** → **Database** → **Add PostgreSQL**.
3. **+ Create** → **Database** → **Add Redis**.

## 2. Create the "core" service (backend API + `/lab` + workers)

1. **+ Create** → **GitHub Repo** → select this repo. Railway creates a service — rename
   it to `core`.
2. Service → **Settings**:
   - **Root Directory**: leave **blank** (must stay the repo root — the Dockerfile's
     `COPY backend/ ...` / `COPY vuln-web/ ...` need that build context).
   - **Networking**: click **Generate Domain** (exposes the service publicly on the port
     it listens on, which Railway sets via `$PORT`).
3. Service → **Variables** tab → add:
   - `RAILWAY_DOCKERFILE_PATH` = `railway/core/Dockerfile` (tells Railway to use this
     Dockerfile instead of looking for one at the repo root).
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - `REDIS_URL` = `${{Redis.REDIS_URL}}/0`
   - `CELERY_BROKER_URL` = `${{Redis.REDIS_URL}}/1`
   - `CELERY_RESULT_BACKEND` = `${{Redis.REDIS_URL}}/2`
   - `FLASK_ENV` = `production`
   - `SECRET_KEY` = *(generate a random 32+ char value)*
   - `DEMO_ADMIN_PASSWORD` / `DEMO_ANALYST_PASSWORD` = *(set explicit values, or leave
     blank to auto-generate — printed once to the deploy logs on first seed)*
   - `GROQ_API_KEY`, `GROQ_MODEL` = *(optional, for AI incident explanations)*
   - `ABUSEIPDB_API_KEY` = *(optional, for IP reputation lookups)*
   - `USE_SIMULATED_LOGS` = `false`
   - `DEMO_MODE` = `false`
   - `TEMP_BLOCK_DURATION` = `86400`
   - `RATE_LIMIT_WINDOW` = `60`
   - `RATE_LIMIT_MAX_REQUESTS` = `10`
   - `BRUTE_FORCE_THRESHOLD` = `10`
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL`,
     `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` = *(optional, for alert notifications)*
   - `CORS_ORIGINS` = `https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}` (add once the
     `frontend` service exists — step 3 below)

   You do **not** need to set `PORT`, `WATCHED_LOG_DIR`, `WEB_SERVER_LOG_PATH`,
   `BLOCKED_IPS_JSON_PATH`, `RATE_LIMITED_JSON_PATH`, `VULN_LOG_FILE`,
   `BLOCKED_IPS_JSON`, `RATE_LIMITED_JSON`, `VULN_DB_PATH`, `VULN_SAFE_FILES_DIR`,
   `VULN_UNSAFE_CMD`, or `VULN_UNSAFE_UPLOAD` — these are already baked into
   `railway/core/Dockerfile` as sane defaults pointing both apps at the same
   `/app/shared/*` paths. Override only if you have a specific reason to.

4. Service → **Settings** → **Deploy** → **Healthcheck Path** = `/api/health`.
5. Deploy. Watch the build + deploy logs for migration/seed/Celery/log-monitor startup
   messages (from `railway/core/entrypoint.sh`).

## 3. Create the "frontend" service

1. **+ Create** → **GitHub Repo** → same repo again. Rename the service to `frontend`.
2. Service → **Settings**:
   - **Root Directory**: `frontend` (Railway will auto-detect `frontend/Dockerfile`).
   - **Networking**: **Generate Domain**.
3. Service → **Variables** tab → add:
   - `REACT_APP_API_URL` = `https://${{core.RAILWAY_PUBLIC_DOMAIN}}/api`

   This must be set **before** the first build — `frontend/Dockerfile` already declares
   `ARG REACT_APP_API_URL`, and Railway automatically forwards any variable of the same
   name from this tab into the Docker build as that arg. It's baked into the JS bundle
   at `npm run build` time, so changing it later requires a redeploy.
4. Deploy.
5. Go back to the **core** service's Variables and set `CORS_ORIGINS` (step 2) now that
   `frontend`'s domain exists, then redeploy `core`.

## 4. Validate

1. `core` service logs show migrations + seed succeeding, and both
   `Starting log monitor...` / `Starting Celery worker + beat...` lines.
2. `https://<core-domain>/api/health` → `200 {"status":"ok"}`.
3. `https://<core-domain>/lab/` → vuln-web homepage renders with `/lab/...` links.
4. Open the frontend at `https://<frontend-domain>`, log in, and submit
   `https://<core-domain>/lab/forms` without the CSRF token → confirm a CSRF incident
   appears on the dashboard (end-to-end detection pipeline check).
5. Block an IP from the dashboard → confirm `https://<core-domain>/lab/...` returns the
   "Access Forbidden" page for that IP (confirms the shared-state fix works without a
   Docker volume).

## Known, accepted risk

`vuln-web`'s lab pages (`/lab/cmd`, `/lab/files` upload) are genuinely exploitable, not
simulated — anyone who finds the public Railway URL could run commands or upload files
inside that container. Acceptable for a temporary capstone demo window; redeploy
afterward to wipe state, or note this as a deliberate, acknowledged risk in your report.

A Railway **Volume** mounted at `/app/shared` on the `core` service is optional —
recommended so blocked-IP/rate-limit state survives restarts, but incidents themselves
always persist via Postgres regardless.
