# Deploying Incidentra to Railway

This folder contains **Railway-only** deployment files. They are additive — nothing here
changes `docker-compose.yml` or local development, which keep working exactly as before.

## Table of contents

1. [Quick reference — services & where state lives](#quick-reference--services--where-state-lives)
2. [One-time setup: CLI + SSH (Windows)](#one-time-setup-cli--ssh-windows)
3. [Generate secret values](#generate-secret-values)
4. [Two ways to deploy vuln-web (Option A vs B)](#two-ways-to-deploy-vuln-web)
5. [Initial deploy — step by step](#1-create-the-project-and-datastores)
6. [Validate deployment](#4-validate)
7. [Full demo reset (Postgres + Redis + files)](#full-demo-reset-postgres--redis--files)
8. [Day-to-day commands cheat sheet](#day-to-day-commands-cheat-sheet)
9. [Troubleshooting (Windows)](#troubleshooting-windows)
10. [Turn lab off / pause credits / client IP fix / risks](#turning-the-lab-demo-off-without-touching-the-api)

---

## Quick reference — services & where state lives


| Railway service             | Role                                                   | Persists?                 |
| --------------------------- | ------------------------------------------------------ | ------------------------- |
| **Postgres**                | Incidents, users, rules, `blocked_ips` table           | ✅ Yes (volume)            |
| **Redis** (`/0`)            | Escalation tier, rate-limit cache, block cache         | ✅ Yes (TTL up to 30 days) |
| **Redis** (`/1`, `/2`)      | Celery broker + results                                | Transient                 |
| **core**                    | Backend API + log monitor + Celery + (Option A) `/lab` | Container filesystem      |
| **frontend**                | React static site                                      | Stateless                 |
| **vulnweb** (Option B only) | Standalone vulnerable demo site                        | SQLite ephemeral          |


**What each store holds (important for reset):**


| Store               | Examples                                                                                     | Cleared how                             |
| ------------------- | -------------------------------------------------------------------------------------------- | --------------------------------------- |
| **Postgres**        | `incidents`, `blocked_ips`, users, rules                                                     | `railway connect Postgres` → SQL        |
| **Redis db `/0`**   | `escalation_count:IP`, `escalation_severity:IP`, `blocked:IP`, `ratelimit:IP`, `bf:IP:/path` | SSH into `core` → `flushdb` (see below) |
| **Files in `core`** | `/app/shared/access.log`, `blocked_ips.json`, `rate_limited.json`                            | SSH into `core` → truncate files        |


Unblocking an IP via the dashboard removes it from Postgres + syncs JSON, but `**escalation_*` keys in Redis stay** (by design — repeat-offender tier). For a truly fresh demo, reset all three stores.

---

## One-time setup: CLI + SSH (Windows)

Do this **once** on your dev machine. After that you only need the [day-to-day commands](#day-to-day-commands-cheat-sheet).

### 1. Install & link Railway CLI

```powershell
npm i -g @railway/cli
railway login          # opens browser — sign in
railway link           # pick: workspace → project → environment → service "core"
```

### 2. Generate SSH key (for shell access into containers)

```powershell
ssh-keygen -t ed25519 -C "your@email.com" -f "$env:USERPROFILE\.ssh\railway_ed25519"
```

Press Enter twice for empty passphrase (simplest for demo).

Show the public key:

```powershell
Get-Content "$env:USERPROFILE\.ssh\railway_ed25519.pub"
```

Copy the whole line (`ssh-ed25519 AAAA...`).

### 3. Upload public key to Railway

Dashboard → **Workspace Settings** → **SSH Keys** → **Add SSH Key** → paste → Save.

URL: [railway.com/workspace/ssh-keys](https://railway.com/workspace/ssh-keys)

### 4. Trust Railway host (first connect only)

First time you SSH, type `**yes**` when asked about `ssh.railway.com` fingerprint. This is saved to `~/.ssh/known_hosts` and won't ask again.

Optional pre-trust:

```powershell
ssh-keyscan ssh.railway.com >> "$env:USERPROFILE\.ssh\known_hosts" 2>$null
```

### 5. Connect (always use `-i` on Windows)

```powershell
railway ssh -s core -i "$env:USERPROFILE\.ssh\railway_ed25519"
```

Without `-i`, the CLI may say "No SSH keys registered" even though your key is on Railway — it just can't find the right local key file.

Optional PowerShell alias (add to your profile):

```powershell
function railway-core { railway ssh -s core -i "$env:USERPROFILE\.ssh\railway_ed25519" @args }
# then: railway-core
```

**Note:** `ssh-agent` / `Start-Service ssh-agent` often fails on Windows without Administrator. You do **not** need ssh-agent if you always pass `-i`.

---

## Generate secret values

For `SECRET_KEY`, `INTERNAL_API_TOKEN` (Option B), etc.:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```


| Variable              | Where                               | Notes                                          |
| --------------------- | ----------------------------------- | ---------------------------------------------- |
| `SECRET_KEY`          | `core` only                         | JWT signing                                    |
| `INTERNAL_API_TOKEN`  | `core` **and** `vulnweb` (Option B) | **Must be identical** on both services         |
| `DEMO_ADMIN_PASSWORD` | `core` only                         | Or leave blank → auto-generated in deploy logs |


Never commit these to git.

---

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

## Two ways to deploy vuln-web


|                        | **Option A — merged** `/lab` (default, steps below) | **Option B — separate domain**                                           |
| ---------------------- | --------------------------------------------------- | ------------------------------------------------------------------------ |
| Domain                 | Same domain as `core`, path `/lab/*`                | Its own distinct Railway domain, no path prefix                          |
| Services               | 4 total (`core` bundles vuln-web)                   | 5 total (`core` + standalone `vulnweb`)                                  |
| Shared state transport | Same container filesystem (no network hop)          | HTTP, over `backend/app/api/internal.py`                                 |
| Setup effort           | Lower (nothing extra)                               | Higher (2 extra variables + own service)                                 |
| Looks like, in a demo  | One SOC app with a `/lab` sub-path                  | Two independent sites: a "target website" and a separate "SOC dashboard" |


Both options run the **exact same detection engine, unmodified**: a raw HTTP request
hits an intentionally vulnerable Flask route in vuln-web, gets appended as one line to
an access-log file, and the backend's log monitor tails that file and runs it through
`detection_engine.py` exactly as it always has. The only thing that differs between A
and B is *how that log line, and the current blocklist, physically travel from vuln-web
to the backend* — see the next section.

### Why local Docker Compose, Option A, and Option B can legitimately differ (and how to describe this in your report)

`docker-compose.yml` (local) and Option A (Railway, merged) both move state via **a
shared filesystem** — a Docker named volume locally, one container's own filesystem on
Railway. Option B moves the *identical* state over **HTTP between two independent
services** instead, because that's the only way to give vuln-web its own domain without
a filesystem in common. This is a completely normal, expected divergence between a local
dev topology and a cloud/PaaS production topology — it happens on real projects any time
a platform doesn't offer a feature (here: cross-service shared volumes) that a
single-host `docker-compose` setup gets "for free". Frame it in your report as:

- **Local Docker Compose**: simplest topology for development — one Docker volume
(`vuln_logs`) shared by `backend`, `vuln_web`, and `celery_worker` containers.
- **Production (Railway)**: PaaS platforms typically don't support a volume mounted by
more than one service, so state exchange is re-architected around the same
boundary that any real microservice split would use — an authenticated internal HTTP
API (`POST /api/internal/logs`, `GET /api/internal/blocklist`) — while the detection
logic itself, and the local Docker setup, are **completely unchanged**.

This is a legitimate, deliberate architecture decision to point out in your
report/sidang, not a shortcut — it's the same "log shipping" pattern real SOC/observability
stacks use (e.g. Filebeat → Logstash) when log producer and log consumer aren't on the
same host.

### Setting up Option B

Everything below is **additive** on top of Option A's steps (1 and 2) further down —
follow those first for `Postgres`, `Redis`, and `core`, except set `ENABLE_LAB=false` on
`core` (vuln-web no longer lives inside it), then come back here.

1. **On** `core`**'s Variables tab**, add:
  - `INTERNAL_API_TOKEN` = *(generate a random 32+ char value — this is the shared
   secret between* `core` *and the new* `vulnweb` *service)*
  - `ENABLE_LAB` = `false` *(vuln-web is no longer mounted inside* `core`*; it's its own
  service now)*
2. **+ Create** → **GitHub Repo** → same repo again. Rename the service to `vulnweb`.
3. Service → **Settings**:
  - **Root Directory**: leave **blank** (must stay the repo root, same reason as
   `core` — the Dockerfile's `COPY vuln-web/ ...` needs that build context).
  - **Build** → set `RAILWAY_DOCKERFILE_PATH` = `railway/vulnweb/Dockerfile`.
  - **Networking**: **Generate Domain** — this is vuln-web's own, independent public URL.
4. Service → **Variables** tab → add:
  - `LOG_INGEST_URL` = `https://${{core.RAILWAY_PUBLIC_DOMAIN}}/api/internal/logs`
  - `BLOCKLIST_API_URL` = `https://${{core.RAILWAY_PUBLIC_DOMAIN}}/api/internal/blocklist`
  - `INTERNAL_API_TOKEN` = *(same exact value you set on* `core` *in step 1)*
  - `VULN_UNSAFE_CMD` = `1`, `VULN_UNSAFE_UPLOAD` = `1` *(needed for the command-injection
  / file-upload labs to actually work — same as Option A's baked-in defaults)*
  - `RATE_LIMIT_MAX_REQUESTS` = `10`, `RATE_LIMIT_WINDOW` = `60` *(cosmetic — only shown
  on vuln-web's own 429 page; real enforcement now comes from* `core` *via*
  `BLOCKLIST_API_URL`*)*
5. Deploy. Validate:
  - `https://<vulnweb-domain>/` → vuln-web homepage renders, **on its own domain**.
  - Trigger an attack (e.g. submit `/forms` without the CSRF token) → within a couple
  seconds an incident appears on the dashboard, exactly like Option A — confirms
  `LOG_INGEST_URL` → `/api/internal/logs` → the same log monitor/detection pipeline.
  - Block that IP from the dashboard → refresh `https://<vulnweb-domain>/` → "Access
  Forbidden" page — confirms `BLOCKLIST_API_URL` enforcement.
  - `https://<core-domain>/lab/` should now 404 (vuln-web is no longer mounted there).

Reverting to Option A later is just: delete the `vulnweb` service, set `ENABLE_LAB=true`
back on `core`, redeploy `core`. Nothing about `core`'s own image or entrypoint changes
between A and B — only whether vuln-web is bundled inside it or not.

---

## Deployment checklist (summary)

Follow this order so nothing is missed. Details in each section below.

### A. Push code to GitHub

```powershell
git add .
git commit -m "your message"
git push origin main
```

Railway auto-redeploys linked services on push. Key commits for this project:


| Commit / topic              | What it adds                                                       |
| --------------------------- | ------------------------------------------------------------------ |
| Railway Deployment          | `railway/core/*`, merged `/lab` topology, health check             |
| Railway Deployment 2        | `get_client_ip()` fix for real client IP behind Railway proxy      |
| Railway Deployment vuln-web | Option B: `railway/vulnweb/*`, `/api/internal/*` HTTP log shipping |


### B. Railway dashboard — create services (first time)

- [ ] **Empty project** → add **PostgreSQL** + **Redis** plugins
- [ ] `**core**` service — repo root, `RAILWAY_DOCKERFILE_PATH=railway/core/Dockerfile`, all env vars, healthcheck `/api/health`, Generate Domain
- [ ] `**frontend**` service — root dir `frontend`, `REACT_APP_API_URL=https://${{core.RAILWAY_PUBLIC_DOMAIN}}/api`, Generate Domain
- [ ] Back on `**core**`: set `CORS_ORIGINS=https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}` → redeploy

### C. Option B only — separate vuln-web domain

- [ ] On `**core**`: `ENABLE_LAB=false`, `INTERNAL_API_TOKEN=<generated secret>`
- [ ] Create `**vulnweb**` service — `RAILWAY_DOCKERFILE_PATH=railway/vulnweb/Dockerfile`, Generate Domain
- [ ] On `**vulnweb**`: `LOG_INGEST_URL`, `BLOCKLIST_API_URL`, same `INTERNAL_API_TOKEN`, `VULN_UNSAFE_CMD=1`, `VULN_UNSAFE_UPLOAD=1`

### D. One-time on your PC (CLI + SSH)

- [ ] `npm i -g @railway/cli` → `railway login` → `railway link` (pick `core`)
- [ ] `ssh-keygen` → upload `.pub` to Railway Workspace SSH Keys
- [ ] Test: `railway ssh -s core -i "$env:USERPROFILE\.ssh\railway_ed25519"`

### E. Before each demo

- [ ] Services running (not "removed deployment")
- [ ] [Full demo reset](#full-demo-reset-postgres--redis--files) if previous testing left data

---

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

## Turning the `/lab` demo off without touching the API

(Option A only — if you're on Option B, just remove the standalone `vulnweb` service instead.)

Set `ENABLE_LAB` = `false` as a variable on the `core` service and redeploy (just a
restart — no rebuild needed) to take vuln-web's `/lab/*` endpoints offline entirely.
`railway/core/wsgi.py` then never even imports vuln-web's code (its unsafe `/cmd`,
`/files` routes don't exist in the running process), and `/lab/*` falls through to the
backend's own 404. The `/api/...` dashboard endpoints are unaffected either way. Flip it
back to `true` (or unset it — that's the default) to re-enable for a demo/presentation.

This only reduces exposed attack surface — it does **not** reduce Railway usage/billing,
since the `core` container (and its Celery worker/beat/log monitor) keeps running either
way. See the next section for that.

## Pausing services to save trial credits

Railway has no single "pause project" button, but two real options per service
(Settings → Deploy, or the Deployments tab):

- **Remove the active deployment** (Deployments tab → active deployment's `...` menu →
**Remove**, or `railway down` via CLI). This fully stops the service and its resource
usage/billing while keeping all variables and config intact — redeploy anytime from
the same menu.
- **Serverless** (Settings → Deploy → toggle **Serverless**) auto-sleeps a service after
10 minutes with no *outbound* traffic and auto-wakes on the next request (small
cold-start delay, occasional first-request 502). This works well for `frontend`
(static nginx has no background outbound traffic), but **won't reliably sleep** `core`
— its Celery worker/beat keep an open connection to Redis, which counts as continuous
outbound traffic and prevents Railway from ever considering it inactive. Use "Remove
deployment" for `core` instead when you want to pause it.
- Postgres/Redis plugins can also be paused via "Remove deployment" — their volumes
(and data) are untouched, only the running instance stops. Fine to do between work
sessions; just remember to redeploy `core` (and it) before your next demo, in that
order (Postgres/Redis need to be up first).

## Client IP behind Railway's edge proxy

Railway terminates the connection at their edge and forwards to the container, so
`request.remote_addr` is one of Railway's own internal IPs (always in the
`100.64.0.0/10` shared-address range) — **not** the real visitor. Worse, it can be a
*different* internal IP on every single request to the same app from the same real
client, since Railway load-balances across edge/routing nodes. This broke every
IP-keyed feature: `/lab` IP blocking, brute-force/rate-limit counters, and the incidents'
`source_ip` (parsed from `access.log`, which vuln-web writes using whatever IP it sees) —
symptom: the same client gets blocked/rate-limited inconsistently, "randomly" per
refresh, and attacks look like they come from a handful of unrelated IPs.

Fixed in `backend/app/utils/net.py` / `vuln-web/ip_utils.py` (`get_client_ip()`): both
now prefer the `X-Real-IP` header, which Railway's edge always sets/overwrites with the
true client IP (their docs confirm it cannot be spoofed by the client, since the proxy
is the only path into the container), falling back to `X-Forwarded-For`'s first entry,
then `request.remote_addr` as a last resort (this last case is what still runs locally
under Docker Compose, since there's no reverse proxy there — zero behavior change).
Every place that used `request.remote_addr` for a security decision (vuln-web's
logging/enforcement, backend's `/auth/register` rate limit, audit log IP) now goes
through this helper. **Requires redeploying** `core` (it's a code change, not a
variable) to take effect.

## Full demo reset (Postgres + Redis + files)

Use this before a fresh demo/presentation when ZAP testing left incidents, blocks, and
escalation tiers behind. **All four steps** — skipping Redis leaves "offense #2" labels
even after Postgres is clean.

### Step 1 — Postgres: clear incidents & blocked IPs

From your project folder (PowerShell):

```powershell
railway connect Postgres
```

At the `railway=#` prompt (this is **psql**, not the Linux shell):

```sql
TRUNCATE incidents, incident_logs, incident_explanations, incident_notes
  RESTART IDENTITY CASCADE;
DELETE FROM blocked_ips;
\q
```

Success looks like: `TRUNCATE TABLE` then back to PowerShell.

### Step 2 — Redis: clear escalation / rate-limit / block cache

`railway connect Redis` often **fails on Windows** (`Unrecognized option ... '-u'`).
Use the SSH workaround instead:

```powershell
railway ssh -s core -i "$env:USERPROFILE\.ssh\railway_ed25519"
```

Inside the container (`root@...:/app#`):

```bash
python -c "
import os, redis
r = redis.from_url(os.environ['REDIS_URL'])
before = r.dbsize()
r.flushdb()
print(f'Redis db 0 flushed ({before} keys deleted, {r.dbsize()} left)')
"
exit
```

This removes keys like `escalation_count:IP`, `escalation_severity:IP`, `blocked:IP`,
`ratelimit:IP`, `bf:IP:/path`.

**Alternative (no SSH):** Dashboard → **Redis** → **Data** → search `escalation_` → delete
each key via ⋮ menu. Slower but works.

### Step 3 — Files in `core`: clear log + JSON enforcement state

SSH into `core` again (or stay in the same session before `exit`):

```bash
> /app/shared/access.log
truncate -s 0 /app/shared/access.log
python -c "import json; json.dump({'blocked': [], 'updated_at': ''}, open('/app/shared/blocked_ips.json', 'w'))"
python -c "import json; json.dump({'rate_limited': [], 'limits': {}, 'updated_at': ''}, open('/app/shared/rate_limited.json', 'w'))"
```

cek:

```bash
wc -c /app/shared/access.log
cat /app/shared/blocked_ips.json
```

### Step 4 — Verify

- Dashboard → Incidents: empty
- Dashboard → IP Management: empty
- Redis → Data: no `escalation_*` keys (or very few)
- Hit vuln-web / run ZAP again → fresh incidents with your real IP (not `100.64.0.x`)

### Optional — re-seed detection rules

If you also wiped rules or want defaults back (inside `core` SSH):

```bash
python -c "from app import create_app; from app.utils.seeder import seed_all; app=create_app(); app.app_context().push(); seed_all()"
```

---

## Day-to-day commands cheat sheet


| Task                | Command                                                                 |
| ------------------- | ----------------------------------------------------------------------- |
| Link project (once) | `railway link`                                                          |
| SSH into `core`     | `railway ssh -s core -i "$env:USERPROFILE\.ssh\railway_ed25519"`        |
| Postgres shell      | `railway connect Postgres`                                              |
| Stream deploy logs  | `railway logs -s core`                                                  |
| Full demo reset     | Steps 1–3 in [Full demo reset](#full-demo-reset-postgres--redis--files) |


**What SSH is for:** optional maintenance only (reset files, run scripts, flush Redis).
Deploy, env vars, and normal app use do **not** require SSH.

---

## Troubleshooting (Windows)


| Symptom                                              | Cause                                           | Fix                                                     |
| ---------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------- |
| `No SSH keys found`                                  | No key in agent / wrong default key             | Always use `-i "$env:USERPROFILE\.ssh\railway_ed25519"` |
| `No SSH keys registered with Railway` (without `-i`) | CLI can't find local key                        | Same — use `-i` flag                                    |
| `Are you sure you want to continue connecting?`      | First SSH to Railway                            | Type `**yes**` once                                     |
| `Connection closed` immediately                      | `core` deployment stopped/removed               | Redeploy `core` in dashboard                            |
| `RESTART: command not found` in shell                | Pasted SQL into **Linux shell** instead of psql | Use `railway connect Postgres` for SQL                  |
| `railway connect Redis` → `-u` error                 | Windows `redis-cli` too old for URL/TLS         | Use SSH + Python `flushdb` (Step 2 above)               |
| One-liner `railway ssh -- python -c "..."` fails     | PowerShell mangles quotes                       | Use interactive SSH shell instead                       |
| `Start-Service ssh-agent` Access denied              | Needs Administrator                             | Skip agent; use `-i`                                    |
| Incidents show IP `100.64.0.x`                       | Old deploy before X-Real-IP fix                 | Redeploy `core` with latest code; reset state           |
| Option B: no incidents from vuln-web                 | `INTERNAL_API_TOKEN` missing/mismatch           | Set **same token** on `core` and `vulnweb`              |
| Option B: blocks don't apply on vuln-web             | `BLOCKLIST_API_URL` wrong or token missing      | Check vars; redeploy `vulnweb`                          |


---

## Resetting demo state / running one-off commands (legacy section)

See [Full demo reset](#full-demo-reset-postgres--redis--files) above for the complete
checklist. Quick file-only reset (does **not** clear Postgres or Redis):

```powershell
railway ssh -s core -i "$env:USERPROFILE\.ssh\railway_ed25519"
```

```bash
> /app/shared/access.log
python -c "import json; json.dump({'blocked': [], 'updated_at': ''}, open('/app/shared/blocked_ips.json', 'w'))"
python -c "import json; json.dump({'rate_limited': [], 'limits': {}, 'updated_at': ''}, open('/app/shared/rate_limited.json', 'w'))"
exit
```

**Unblock your own IP** without full reset — use dashboard **IP Management** (recommended).
On Option B, `vulnweb` picks up the change within ~3s via `BLOCKLIST_API_URL`.

**Option B's** `vulnweb` **service** — redeploy for a clean SQLite lab DB; no shared files to reset.

## Known, accepted risk

`vuln-web`'s lab pages (`/cmd`, `/files` upload — at `/lab/cmd` etc. on Option A, or at
the domain root on Option B) are genuinely exploitable, not simulated — anyone who finds
the public URL could run commands or upload files inside that container. Option B's own
domain makes this marginally *more* discoverable (no `/lab` prefix hinting "this is a
sub-feature of something else"), so treat it with the same caution. Acceptable for a
temporary capstone demo window either way; redeploy afterward to wipe state, or note this
as a deliberate, acknowledged risk in your report.

On Option B, also double-check `INTERNAL_API_TOKEN` is set on **both** `core` and
`vulnweb` before your demo — if it's missing on either side, `/api/internal/*` silently
stays disabled (404/401), which quietly degrades to "no logs reach the dashboard, no
blocks are enforced" rather than a loud failure.

A Railway **Volume** mounted at `/app/shared` on the `core` service is optional —
recommended so blocked-IP/rate-limit state survives restarts, but incidents themselves
always persist via Postgres regardless.