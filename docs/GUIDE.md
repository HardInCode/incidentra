# Incidentra — Operational Guide

Single guide: **run** the system (Docker or manual), **defense demo**, and **troubleshooting**.

**Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) · **Full audit:** [AUDIT.md](AUDIT.md)

**Repo:** [github.com/HardInCode/incidentra](https://github.com/HardInCode/incidentra)

---

## Prerequisites


| Mode       | Required                                                    |
| ---------- | ----------------------------------------------------------- |
| **Docker** | Docker Desktop **Running** (green icon)                     |
| **Manual** | Python 3.10–3.13 · Node 18–20 LTS · PostgreSQL 15 · Redis 7 |


---

## What Will Run

```
PostgreSQL + Redis
        │
        ▼
Backend (Flask :5000) ◄── tail access.log vuln-web
        │
        ▼
Frontend (React :3000)     vuln-web (:5050) ──► logs/access.log
                              └── blocked_ips.json, rate_limited.json
```


| Service       | URL                                                    |
| ------------- | ------------------------------------------------------ |
| SOC Dashboard | [http://localhost:3000](http://localhost:3000)         |
| Backend API   | [http://localhost:5000/api](http://localhost:5000/api) |
| Vuln-web      | [http://localhost:5050](http://localhost:5050)         |


**SOC Login:** `admin` / `analyst` — password is whatever you set via `DEMO_ADMIN_PASSWORD` /
`DEMO_ANALYST_PASSWORD` in `.env` / `.env.docker` (see [Environment Files](#environment-files)
below). If left blank, a random password is generated on first seed and printed **once** to
the startup log (`python run.py` output or `docker compose logs backend`) — it is never stored
in plaintext.

---

## Environment Files


| File                          | Used by                         | Do not                              |
| ----------------------------- | ------------------------------- | ----------------------------------- |
| `backend/.env.example`        | Manual mode template            | Commit as `.env` with secrets       |
| `backend/.env`                | Manual `python run.py`          | Push to GitHub                      |
| `backend/.env.docker.example` | Docker mode template            | —                                   |
| `backend/.env.docker`         | Docker compose                  | Push if it contains API keys        |
| `vuln-web/.env.example`       | Lab target template             | —                                   |
| `vuln-web/.env`               | Manual `python app.py` (Phase 3)| Push to GitHub                      |
| `docker-compose.yml`          | Container DB/Redis URLs         | Edit `localhost` for DB in Docker   |


**Docker:** `DATABASE_URL` is set in `docker-compose.yml`, not in `.env.docker`.  
**Phase 3 in Docker:** `vuln-web/.env` is **not** auto-read by the container — add variables in `docker-compose.yml` service `vuln_web` (see § Phase 3) or demo Phase 3 using **manual** mode.

### `vuln-web/.env` Variables

Copy from `vuln-web/.env.example` → `vuln-web/.env`. Active values for boolean flags: `1`, `true`, or `yes` (case-insensitive). Any other value / empty = **off** (same as `0`).


| Variable                 | Default                  | If `=1` (or true/yes)                                                     |
| ------------------------ | ------------------------ | ------------------------------------------------------------------------- |
| `VULN_PORT`              | `5050`                   | Flask port                                                                |
| `VULN_LOG_FILE`          | `logs/access.log`        | Access log path                                                           |
| `BLOCKED_IPS_JSON`       | `logs/blocked_ips.json`  | Block file (read by middleware)                                           |
| `RATE_LIMITED_JSON`      | `logs/rate_limited.json` | Rate limit file                                                          |
| **`VULN_UNSAFE_CMD`**    | **off**                  | `/cmd` runs a **real shell** (`subprocess`, timeout `VULN_CMD_TIMEOUT`)   |
| **`VULN_UNSAFE_UPLOAD`** | **off**                  | Upload at `/files` allows **path escape** (`../` in filename)             |
| `VULN_CMD_TIMEOUT`       | `5`                      | Seconds (only when `VULN_UNSAFE_CMD=1`)                                   |


**Important:**

- Editing `.env` → **must restart** vuln-web (`Ctrl+C` → `python app.py`). Browser refresh is **not** enough.
- `VULN_UNSAFE_CMD=1` **does not** change SOC detection/blocking — only the output on the lab page. Blocking still works: **COMMAND_INJECTION** incident in backend → `blocked_ips.json`.
- Without flags: `/cmd` runs in **simulated** mode; profile upload **avatar without extension filter** (CTF scenario) remains at `/profile`.

---

## Run — Docker (Recommended)

```powershell
git clone https://github.com/HardInCode/incidentra.git
cd incidentra
copy backend\.env.docker.example backend\.env.docker
docker compose up --build -d
docker compose ps
```

Wait ~2 minutes. All services should be **running**.

**Volume `vuln_logs`:** backend `/app/watched_logs/` = vuln-web `/app/logs/`.

```powershell
docker compose logs backend --tail 30
```

Should show: `PostgreSQL ready`, `DB init complete`, `Log monitor started`.

**Stop:** `docker compose down`

### Docker Troubleshooting


| Problem                          | Solution                                                        |
| -------------------------------- | --------------------------------------------------------------- |
| `dockerDesktopLinuxEngine` fails | Start Docker Desktop first                                      |
| Port 3000/5000/5050 in use       | Close manual processes or `docker compose down`                 |
| Backend restart loop             | `docker compose logs backend` — check `postgresql+psycopg`      |
| Build frontend `ajv` error       | `docker compose build --no-cache frontend`                      |
| UI not calling API               | Rebuild frontend; `REACT_APP_API_URL=http://localhost:5000/api` |


---

## Run — Manual (3 Terminals)

### PostgreSQL & Redis

```powershell
psql -U postgres -f scripts/init_postgres.sql
redis-cli ping
```

Should return `PONG`.

### Terminal 1 — Backend

```powershell
cd backend
copy .env.example .env
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

First run (simulation): `USE_SIMULATED_LOGS=true`, `DEMO_MODE=true` in `.env`.

### Terminal 2 — Frontend

```powershell
cd frontend
npm install
npm start
```

Optional charts: `python scripts/seed_chart_demo.py` (backend venv, from root).

### Terminal 3 — vuln-web

```powershell
cd vuln-web
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

### Connect Real Logs

Edit `backend\.env`:

```env
USE_SIMULATED_LOGS=false
DEMO_MODE=false
WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log
BLOCKED_IPS_JSON_PATH=../vuln-web/logs/blocked_ips.json
RATE_LIMITED_JSON_PATH=../vuln-web/logs/rate_limited.json
```

Restart backend. Log should show: `Tailing real log: ...`

---

## Utility Scripts & Demo Reset

### Manual (from repo root)

Backend venv active (`pip install psycopg redis` if not already installed):


| Command                                         | Purpose                                     |
| ------------------------------------------------ | ------------------------------------------- |
| `python scripts/reset_incidentra.py`              | Clear incidents, blocks, rate JSON, Redis   |
| `python scripts/reset_incidentra.py --clear-logs` | + clear `vuln-web/logs/access.log`          |
| `python scripts/seed_chart_demo.py`              | Dashboard chart data (7 days)               |


After reset → restart backend + vuln-web.

### Docker (stack `docker compose up` running)

Log & JSON block files are in **Docker volume** `vuln_logs`, not in the `vuln-web/logs/` folder on Windows. The host reset script can **still** clear DB + Redis (ports 5432/6379 are exposed), then clear files inside the container:

```powershell
cd E:\Capstone\CapstoneProject\incidentra

# Reset script
docker compose up -d
.\scripts\reset_incidentra_docker.ps1 -ClearLogs

# access.log + JSON in volume (must go through container)
docker compose exec vuln_web sh -c ":> /app/logs/access.log"
docker compose exec vuln_web sh -c 'echo "{\"blocked\":[],\"details\":{},\"updated_at\":\"\"}" > /app/logs/blocked_ips.json'
docker compose exec vuln_web sh -c 'echo "{\"rate_limited\":[],\"updated_at\":\"\"}" > /app/logs/rate_limited.json'

# Clean backend log tail
docker compose restart backend vuln_web
```

**Hard reset** (deletes all volume data including DB): `docker compose down -v` then `docker compose up --build -d` — only if you are OK with a completely empty database.

**Chart demo in Docker:** run `seed_chart_demo.py` with the same `$env:DATABASE_URL` (see below).

---

## Simulate Attack — Mode A vs Mode B (Log Injection)

This is **not** a `docker compose exec` command to the log file. Log injection goes through the **backend API** (SOC button or `curl`), which writes to volume `vuln_logs` **and** immediately runs the detection engine.

### Mode A — Direct Simulation (instant)

1. Login SOC → **Incidents** → **Simulate Attack**
2. Select **Mode A — Direct Simulation**
3. Choose attack type → **Launch**

Incident goes directly into PostgreSQL (without reading `access.log`). Good for UI testing.

### Mode B — Log Injection (full pipeline) — **recommended for Docker**

1. Ensure stack is running: `docker compose up -d`
2. Login `http://localhost:3000` (`admin` / password from `.env.docker` or startup log — see above)
3. **Incidents** → **Simulate Attack**
4. Select **Mode B — Log Injection**
5. Choose attack type e.g., **LFI/RFI** or **SQL Injection**
6. **Source IP:** change if you tested the same IP < 5 minutes ago (e.g., `203.0.113.99`)
7. **Launch**


| Toast result                                  | Meaning                                                                                   |
| --------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Green: `Log injected — N incident(s) created` | Success — refresh table; incident + block (if critical)                                   |
| Yellow: `no new incident (duplicate...)`      | Log written, but same IP + attack type within 5 min → **change IP** or wait 5 min         |
| Red: `Could not write to log file`            | Backend cannot write to volume — check `docker compose ps`, restart `backend`              |


**Not** waiting 5 seconds for tailer — backend processes the line **immediately** via `ingest_log_lines`. Live Traffic may populate when tailer reads the same line (~1–3 s).

### Mode B via PowerShell (debug, Docker)

```powershell
$body = @{ username = "admin"; password = "<your DEMO_ADMIN_PASSWORD>" } | ConvertTo-Json
$login = Invoke-RestMethod -Method POST -Uri "http://localhost:5000/api/auth/login" `
  -ContentType "application/json" -Body $body
$headers = @{ Authorization = "Bearer $($login.token)" }

$inject = @{ attack_type = "LFI_RFI"; ip = "203.0.113.77" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "http://localhost:5000/api/detection/inject-log" `
  -Headers $headers -ContentType "application/json" -Body $inject
```

Successful response contains `incident_ids` (non-empty array).

### Do Not Confuse With


| What you tried                                             | Problem                                                                                                                                                                    |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docker compose exec vuln_web` append to `access.log` only | Backend **does not** auto-process without tailer/inject API; path in vuln-web container = `/app/logs/access.log` (same volume as backend `/app/watched_logs/access.log`)   |
| `seed_chart_demo.py` without `DATABASE_URL`                | Error `password authentication failed` — Docker Postgres uses user/pass from compose (see below)                                                                           |
| Mode B with IP `45.33.32.156` repeatedly                   | Dedup 5 min → change IP in dialog                                                                                                                                          |


### `seed_chart_demo.py` — Fill 7-Day Chart (not Mode B)

**Purpose:** incidents in PostgreSQL with **different `created_at` per day** (timeline + severity donut).  
**Not** the Simulate Attack Mode B button (that's a single-line detection + log pipeline).

**Important (Windows):** `localhost:5432` often = **Windows PostgreSQL** (`backend/.env`: `postgres` / `incidentra_db`), **not** the Docker database (`incidentra` / `incidentra_db`). Docker dashboard reads the container DB — seeding from host with `$env:DATABASE_URL=incidentra...` can fail (`password authentication failed`).

**Correct approach when using Docker Compose:**

```powershell
cd E:\Capstone\CapstoneProject\incidentra
docker compose up -d
.\scripts\seed_chart_docker.ps1
# Preview plan first:
.\scripts\seed_chart_docker.ps1 -DryRun
```

**Manual approach** (backend `python run.py` + Postgres from `backend/.env`):

```powershell
python scripts/seed_chart_demo.py
python scripts/seed_chart_demo.py --dry-run
```

Then refresh Dashboard (`http://localhost:3000`).


| Option          | Purpose                                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| (default)       | Insert ~15–25 incidents, `created_at` spread over 7 days                                                                       |
| `--dry-run`     | Show plan without writing to DB                                                                                                |
| `--append-logs` | Plus lines in `access.log` (Live Traffic); **do not** use when backend tail is active if you don't want extra incidents today   |


Before a live demo (not charts), clear old incidents: `.\scripts\seed_chart_docker.ps1` is only for charts — or `reset_incidentra.py` + restart. Old seed incidents can trigger toast/bell with `203.0.113.x` IP and confusing dates.

**AI Explanation:** only appears after clicking **Generate AI Explanation** in incident detail — not automatic on detection / log inject.

**Docker vs manual — when to change `DATABASE_URL`?**


| Situation                                                  | `DATABASE_URL` for scripts in PowerShell                                          |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Docker** Postgres at `localhost:5432`, user `incidentra`  | `postgresql://incidentra:incidentra123@localhost:5432/incidentra_db`              |
| **Manual** backend using same `backend/.env`               | **Same** — no change needed, or unset `$env:` and let script read `.env`         |
| **Manual** Postgres with different user/password           | Match the `DATABASE_URL` line in `backend/.env`                                  |


`REDIS_URL` is only needed if backend/app requires Redis while the script runs; for `seed_chart_demo` the important variable is **DATABASE_URL**. Manual backend `python run.py` reads `backend/.env` — it does not auto-follow `$env` in the terminal unless you export before `python run.py`.

**Summary:** If Postgres/Redis remain at `localhost` with credentials `incidentra` / `incidentra123`, **one set of URLs works** for both Docker and host scripts. Change only if you switch to a manual database with different credentials.

---

## IP Management

Menu: **IP Management** (`/blocked-ips`).


| Tab              | Function                                                                      |
| ---------------- | ----------------------------------------------------------------------------- |
| **Blocked**      | Escalating/temporary/permanent (manual) blocks, Repeat Offender, unblock (DB + `blocked_ips.json`) |
| **Rate Limited** | Rate limited IPs, **Clear**, **Extend**                                       |


Unblock on the Blocked tab also removes the rate limit for that IP.

---

## Banner "No logs in 60s" (Dashboard)

This banner = backend **has not received log activity** in 60 seconds (does not mean vuln-web is down).


| Mode                         | How it works                                                                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Docker**                   | Log monitor runs in a separate process (`docker_log_monitor.py`). Heartbeat stored in **Redis** + checks **mtime** of `access.log` in volume `vuln_logs`. |
| **Manual** (`python run.py`) | Single process — heartbeat in-memory, same as Redis if Redis is running.                                                               |


**To dismiss:** open shop `http://localhost:5050` (a few pages), wait ~5 seconds, refresh Dashboard.


| Symptom                        | Cause                                            | Solution                                                                                               |
| ------------------------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Banner persists despite shop   | Backend image is old (before heartbeat fix)       | `docker compose up --build -d backend`                                                                 |
| Banner + empty Live Traffic    | Volume log not shared / vuln-web down             | `docker compose ps`; check `docker compose exec vuln_web tail -3 /app/logs/access.log`                 |
| Manual: banner persists        | `USE_SIMULATED_LOGS=true` or wrong log path       | `.env`: `USE_SIMULATED_LOGS=false`, `WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log`, restart backend |


---

## Three Layers: Live Traffic ≠ Incidents ≠ Blocking


| Layer                 | In UI                             | Meaning                                                                |
| --------------------- | --------------------------------- | ---------------------------------------------------------------------- |
| **A. Log**            | Live Traffic                      | Every HTTP to vuln-web → `access.log`                                  |
| **B. Tag**            | Live Traffic TAG column           | Quick heuristic (`cmd=` → **Attack**) — **not** a SOC decision          |
| **C. Incident + block** | **Incidents** + **IP Management** | `DetectionEngine` → PostgreSQL + `blocked_ips.json` → vuln-web **403** |


**Common symptom:** an **Attack** line with status **200** = pattern seen in log, **does not necessarily** mean there is an incident. Without an incident → **no** automatic block.

**After a real block:** new requests to vuln-web → **403**, tag **Blocked** in Live Traffic.

**Blocked IP** = the IP shown in the Live Traffic column (could be `192.168.x.x`, not always `127.0.0.1`).

---

## Lab Mode & OWASP Baseline


| Mode                 | Setting          | Detection                                                                          |
| -------------------- | ---------------- | ---------------------------------------------------------------------------------- |
| Production (default) | Lab mode **OFF** | Active UI rules **+** built-in regex `DETECTION_PATTERNS` in `detection_engine.py` |
| Defense (custom rule)| Lab mode **ON**  | **Only** active rules in Detection Rules                                           |


Detection code map: [ARCHITECTURE.md](ARCHITECTURE.md) § Detection Engine.

**Custom SQLi rule example:** pattern `(?i)lorem\s+ipsum` → POST login with `username=lorem ipsum` → **SQL_INJECTION** incident (your rule, `match_count` increments).

**Toggle rule OFF** in UI (lab mode OFF): detection may still fire from **baseline**, not from the DB rule — this is normal.

---

## HTTP 429 (yellow) vs 403 (red)


| Code    | Cause                                                                             |
| ------- | --------------------------------------------------------------------------------- |
| **403** | IP in `blocked_ips.json` (escalating block high/critical, or manual block)        |
| **429** | IP in `rate_limited.json` + too many requests within window (e.g., 10/minute)     |


How to trigger 429: **SCANNER** attack (User-Agent Nikto/sqlmap) → severity medium → rate limit, then refresh vuln-web repeatedly. Tab **IP Management → Rate Limited** shows the IP; chip "JSON only" = enforcement via file, Redis TTL empty (see tooltip).

---

## Defense Demo — Preparation

### Terminals (manual)

```powershell
# T1 — Backend
cd backend
.\venv\Scripts\Activate.ps1
# .env: USE_SIMULATED_LOGS=false, WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log
python run.py

# T2 — vuln-web
cd vuln-web
.\venv\Scripts\Activate.ps1
python app.py

# T3 — Frontend (optional)
cd frontend
npm start
```

### Reset (recommended before demo)

- **Manual:** `python scripts/reset_incidentra.py --clear-logs` → restart backend + vuln-web.
- **Docker:** follow § **Utility Scripts — Docker** above (not just `--clear-logs` on host).

### Check Your IP

Open `http://localhost:5050/` — in Live Traffic check the **IP** column. That is the IP that will be blocked.

---

## Defense Demo — Step by Step

### 1. SQL Injection → escalating block (offense #1 ≈ 24 hours)

1. Unblock IP in SOC → **IP Management** → Blocked tab (if present).
2. Browser: `http://localhost:5050/login`
3. Username: `admin' OR '1'='1' --` , password: anything → Submit.
4. Wait 5–10 seconds.
5. SOC → **Incidents** → **SQL_INJECTION**, critical.
6. **IP Management** → IP blocked, **Offense #1**, duration ~24 hours.
7. Refresh `http://localhost:5050/` → **403 Forbidden Incidentra**.

### 2. XSS

1. Unblock IP.
2. `http://localhost:5050/search?q=<script>alert(1)</script>`
3. Incidents → **XSS** → refresh vuln-web → **403**.

### 3. Command Injection

Use **one of** (after **restarting backend** `python run.py` if detection was just updated):

```
http://localhost:5050/cmd?cmd=;whoami
http://localhost:5050/cmd?cmd=whoami
http://localhost:5050/cmd?cmd=whoami%20%26%20id
```

**Expected:** Incidents → **COMMAND_INJECTION**, critical → vuln-web **403** on next request.

### 4. Scanner & Brute Force (summary)


| Attack      | Steps                                          | Expected                                           |
| ----------- | ---------------------------------------------- | -------------------------------------------------- |
| Scanner     | `curl -A "Nikto/2.1.6" http://localhost:5050/` | **SCANNER**, medium, rate limit (Rate Limited tab) |
| Brute force | 12× POST login with wrong password              | **BRUTE_FORCE**, high, escalating block (offense #1 ≈ 1 hour) |


### 5. Dangerous vs Safe Upload


| Test      | Steps                                                        | Expected                                           |
| --------- | ------------------------------------------------------------ | -------------------------------------------------- |
| Safe      | `/files` POST `notes.txt`                                    | Live Traffic only — **no** FILE_UPLOAD incident    |
| Dangerous | `/files` POST `shell.php` or `/profile` avatar `shell.php`  | **FILE_UPLOAD**, high, temporary block             |


### 6. Demo Sequence (~15 minutes)

1. SOC Dashboard (clean).
2. vuln-web shop (normal).
3. SQLi login → incident → 403.
4. Unblock → XSS search → incident → 403.
5. Unblock → `cmd?cmd=;whoami` → incident → 403.
6. (Optional) Phase 3: banner + shell output.
7. Live Traffic: Attack vs Blocked + hide static.
8. IP Management: blocked list + unblock.

---

## Phase 3 Lab (`VULN_UNSAFE_CMD` / `VULN_UNSAFE_UPLOAD`)

File: `vuln-web/.env` (create from `.env.example` if it doesn't exist):

```env
VULN_UNSAFE_CMD=1
# VULN_UNSAFE_UPLOAD=1
# VULN_CMD_TIMEOUT=5
```

**Must restart vuln-web** after editing (Ctrl+C → `python app.py`).  
Check: red banner on shop + `/cmd` page says **Live shell enabled**.

**Docker (optional Phase 3):** add to `docker-compose.yml` on service `vuln_web` → `environment:`:

```yaml
VULN_UNSAFE_CMD: "1"
# VULN_UNSAFE_UPLOAD: "1"
```

Then `docker compose up -d --build vuln_web`.

### Command Demo (Phase 3)

1. Reset + unblock IP.
2. Shop — **red banner** "Phase 3 lab mode active".
3. `http://localhost:5050/cmd?cmd=;whoami` → output is **real shell** (not "Simulated").
4. SOC **Incidents** → **COMMAND_INJECTION** (not just Live Traffic).
5. Refresh vuln-web → **403**; Live Traffic latest line → **Blocked**.

### Upload Demo (Phase 3, optional)

1. Set `VULN_UNSAFE_UPLOAD=1`, restart vuln-web.
2. Unblock IP → `/files` → upload `shell.php` → **FILE_UPLOAD** incident.
3. Upload `notes.txt` → Live Traffic only, no incident.

---

## OWASP Upload & FILE_UPLOAD (summary)


| Standard             | Label                                             |
| -------------------- | ------------------------------------------------- |
| OWASP Top 10         | A04 — Insecure Design / misconfig upload          |
| CWE                  | **CWE-434** Unrestricted Upload of Dangerous Type |
| MITRE (in Incidentra) | **T1105** Ingress Tool Transfer                   |


**Incidentra detection:** incident only if log contains `file=` or `avatar=` + dangerous extension (`.php`, `.jsp`, etc.). Upload of `.jpg` / `.txt` → log only.

Detail on lab path traversal: [ARCHITECTURE.md](ARCHITECTURE.md) § Security Lab.

---

## Development Status (July 2026)


| Phase                    | Contents                                                            | Status |
| ------------------------ | ------------------------------------------------------------------- | ------ |
| Core SOC + vuln-web shop | Backend, frontend, detection, IP mgmt                               | Done   |
| Phase 2                  | `/files` read + upload, FILE_UPLOAD (dangerous extensions)          | Done   |
| Phase 3                  | `VULN_UNSAFE_CMD`, `VULN_UNSAFE_UPLOAD`, profile avatar no filter   | Done   |
| Form 4                   | Documentation & screenshots                                        | Team   |


---

## Troubleshooting


| Problem                                        | Cause                               | Solution                                                                                                                             |
| ---------------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Live Traffic **Attack 200**, no incident        | Heuristic tag ≠ SOC incident        | Restart backend `run.py`; check **Incidents**; use `;whoami`                                                                       |
| No incidents at all                             | Log not being tailed                | `USE_SIMULATED_LOGS=false`, correct log path, restart backend                                                                      |
| Incident exists, no 403                         | Different IP (LAN vs 127.0.0.1)     | Unblock the correct IP from Live Traffic column                                                                                    |
| 403 persists                                    | Still in `blocked_ips.json`         | Unblock in SOC or `reset_incidentra.py --clear-logs`                                                                               |
| Phase 3 not real shell                          | `.env` not read / not restarted     | Ensure `vuln-web/.env` exists; `VULN_UNSAFE_CMD=1`; restart `python app.py`; `/cmd` page should show **Live shell enabled**        |
| Phase 3 in Docker not working                   | Container missing Phase 3 env       | Add `VULN_UNSAFE_CMD: "1"` in `docker-compose.yml` or demo manually                                                               |
| Database / Redis error                          | Service down                        | Check `DATABASE_URL`, `redis-cli ping`                                                                                             |
| Many duplicate incidents                        | Dedup 5 min per IP+type             | Normal behavior                                                                                                                    |


---

## Next Steps

- [ARCHITECTURE.md](ARCHITECTURE.md) — architecture, detection & API
- [AUDIT.md](AUDIT.md) — full defense audit (July 2026)
- [GITHUB.md](additional/GITHUB.md) — clone, pull, push for team
- [LEARNING.md](additional/LEARNING.md) — JWT, Chapter 3 concepts
