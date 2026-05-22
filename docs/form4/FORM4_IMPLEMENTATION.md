# PART 4 — IMPLEMENTATION

> **Form 4 — isi teknis (Part A–E).** Cover: `[FORM4_COVER.md](FORM4_COVER.md)` · Screenshot: `[FORM4_SCREENSHOTS.md](FORM4_SCREENSHOTS.md)` · Panduan: `[README.md](README.md)`

---

## Implementation vs Form 3 Deltas

The following items represent substantive changes or additions from the Form 3 design to the delivered codebase:

- **SOC IP Management page** is named "IP Management" (sidebar key `nav.ipManagement`, route `/blocked-ips`, file `frontend/src/pages/BlockedIPs.js`) and contains two tabs: **Blocked** and **Rate Limited**. The design document referred to this page only as "Blocked IPs."
- **Live Traffic route** is `/traffic` (not `/live-traffic`) as registered in `frontend/src/App.js`.
- **Notification delivery** is implemented via `ResponseManager._notify_async()` using a Python `threading.Thread` daemon; Celery `.delay()` is an optional overlay (Celery worker container is included in Docker Compose but the thread path is always reliable without a running worker).
- **FILE_UPLOAD incident** triggers only when the log contains a dangerous file extension in a `file=` or `avatar=` field (e.g., `shell.php`, `image.php.jpg`). A safe upload such as `notes.txt` is recorded in the access log and appears in Live Traffic as a normal request but does not create a FILE_UPLOAD incident.
- **Command injection detection** (`COMMAND_INJECTION`) includes patterns for `cmd=;whoami` (with metacharacter) and `cmd=whoami` (plain keyword, no leading semicolon) — both tested via `/cmd?cmd=` on vuln-web.
- **Phase 3 environment flags** (`VULN_UNSAFE_CMD`, `VULN_UNSAFE_UPLOAD`) are implemented in `vuln-web/config.py` via `_env_bool()` and require a vuln-web process restart when changed; Docker Compose passes these as `environment:` keys, not a volume-mounted `.env`.
- **Live Traffic "Attack" tag with HTTP 200 does not imply a block.** A block is evidenced by an Incident record in PostgreSQL and a subsequent request returning HTTP 403 (tag: Blocked).
- **vuln-web has no direct connection to PostgreSQL.** Enforcement is achieved exclusively through the shared Docker volume `vuln_logs`, which carries `blocked_ips.json` and `rate_limited.json` read by `vuln-web/middleware/security.py` on every incoming request.

---

## A. DESIGNS IMPLEMENTATION

### 1. Functions, Procedures, and Classes

This section maps each Form 3 subsystem to its concrete implementation in the SME-Guard codebase. All file paths are relative to the repository root.

#### 1.1 Log Ingestion Layer

The log ingestion layer corresponds to Form 3 subsystem P1 (log collection) and is implemented across `backend/app/core/log_parser.py` and `backend/app/core/log_monitor.py`. Its responsibility is to transform raw web server log lines into structured records that the Detection Engine can analyse on every poll cycle.

`**parse_log_line(line: str)`** in `log_parser.py` is the entry point for a single log line. It applies the compiled `NGINX_PATTERN` regular expression to decode the NCSA Combined Log Format fields: client IP, timestamp, HTTP method, request path, query string, HTTP version, status code, response size, referer, and User-Agent. Malformed or blank lines return `None` and are discarded. A second pattern, `POST_DATA_PATTERN`, detects the custom suffix `POST_DATA:` that vuln-web appends through `middleware/logging.py` after the standard log fields. When this suffix is present, the POST body content (for example `username=admin' OR '1'='1' --` or `file=shell.php`) is merged into the `query` field of the returned dictionary. This design allows the Detection Engine to inspect login and upload parameters without placing an inline proxy or reading uploaded files from disk.

`**LogTailer**` implements continuous monitoring using a polling loop equivalent to the Unix `tail -f` command. On initialisation it opens the file at `WEB_SERVER_LOG_PATH` (Docker: `/app/watched_logs/access.log` via volume `vuln_logs`; manual: `../vuln-web/logs/access.log`), seeks to end-of-file to avoid re-processing historical entries, then reads new lines on each interval (default one second). Inode tracking detects log rotation and resets the read position when the underlying file is replaced.

`**SimulatedLogFeeder**` provides pre-crafted attack log lines when `USE_SIMULATED_LOGS=true` in the backend environment. This supports first-run development without vuln-web. Production and capstone demonstration set `USE_SIMULATED_LOGS=false` and use `LogTailer` exclusively.

`**log_monitor.py**` orchestrates the pipeline. The `start_monitor()` function launches a daemon `threading.Thread` that iterates over lines from either `LogTailer` or `SimulatedLogFeeder`. For each line, `_process_log_line()` calls `parse_log_line()`, then `DetectionEngine.analyze()`. If a threat is returned, the monitor queries PostgreSQL for an existing incident with the same `source_ip` and `attack_type` within the last five minutes; only if none exists does it insert a new `Incident` row and invoke `ResponseManager.respond()`. The module-level timestamp `last_log_received_at` is updated on every successfully parsed line; the dashboard API exposes this value so the SOC UI can warn operators when no log activity has been received for more than 60 seconds.

#### 1.2 Detection Engine

The detection engine (Form 3 subsystem P2) is implemented in `backend/app/core/detection_engine.py` as the class `DetectionEngine`, supported by `BruteForceTracker` and the module-level dictionaries `DETECTION_PATTERNS`, `SEVERITY_WEIGHTS`, and `RESPONSE_ACTIONS`.

**Pattern sources.** Detection uses two sources merged at runtime: (1) built-in OWASP-aligned patterns in `DETECTION_PATTERNS`, and (2) administrator-defined rules stored in PostgreSQL table `detection_rules`, loaded through `_load_rules_from_db()`. Rules are **not** stored in JSON files; only block and rate-limit enforcement uses JSON on the vuln-web side.

**Supported attack types** (eight primary types used in demonstration): `SQL_INJECTION` (critical), `XSS` (critical), `BRUTE_FORCE` (high, threshold only), `PATH_TRAVERSAL` (high), `FILE_UPLOAD` (high), `COMMAND_INJECTION` (critical), `SCANNER` (medium), and `LFI_RFI` (critical). A `CSRF` pattern exists in code but rarely triggers in normal lab traffic.

`**FILE_UPLOAD` behaviour (important).** Incidents are created only when the log line contains `file=` or `avatar=` followed by a dangerous extension (`.php`, `.jsp`, double extensions such as `image.php.jpg`, etc.). Uploading `notes.txt` or a benign `.jpg` avatar name produces a log entry visible in Live Traffic but **does not** create a `FILE_UPLOAD` incident.

`**COMMAND_INJECTION` behaviour.** Patterns match both `cmd=;whoami` (metacharacter form) and `cmd=whoami` (plain keyword on `/cmd`), so demonstration works after a backend restart without requiring only semicolon payloads.

`**DetectionEngine.analyze(log_entry)`** builds one searchable string from method, path, query (including POST data), and User-Agent. It evaluates all compiled patterns and returns the highest-severity match using `SEVERITY_WEIGHTS`. For POST requests to login paths it also calls `BruteForceTracker`. A tie-break rule prefers `PATH_TRAVERSAL` over `LFI_RFI` when `../` is present without `php://` or remote URL schemes.

**Rule reload.** `_maybe_reload_rules()` runs on each `analyze()` call. At most once per 60 seconds it reloads active rows from `detection_rules`. The Redis key `rules_dirty` (set by `rules.py` on CRUD) forces immediate awareness of dashboard edits.

`**BruteForceTracker`** counts failed login POSTs per IP in a 60-second window (default threshold 10). It uses Redis sorted sets when available, otherwise an in-memory deque. It emits exactly one `BRUTE_FORCE` threat per threshold crossing.

#### 1.3 Automated Response Manager

`backend/app/core/response_manager.py` implements the `ResponseManager` class, which translates threat severity into concrete enforcement actions.

The `respond()` method applies the following severity-to-action mapping defined in `RESPONSE_ACTIONS`:


| Severity | Action            | Enforcement Mechanism                                                                                 | Duration                                          |
| -------- | ----------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| Low      | `log_and_monitor` | `IncidentLog` record in PostgreSQL; Redis key `action:{ip}`                                           | Permanent record                                  |
| Medium   | `rate_limit`      | Entry in `rate_limited.json`; Redis key `ratelimit:{ip}` with configurable TTL                        | Per `RATE_LIMIT_WINDOW` (default 60 s)            |
| High     | `temporary_block` | Entry in `blocked_ips.json` via `_write_blocked_ips_json()`; `BlockedIP` DB record with `expire_time` | 24 hours (configurable via `TEMP_BLOCK_DURATION`) |
| Critical | `permanent_block` | Entry in `blocked_ips.json`; `BlockedIP` DB record with `block_type='permanent'`                      | Never expires                                     |


After applying the enforcement action, `respond()` calls `_save_incident_log()` to persist an `IncidentLog` record. For high and critical events it calls `_notify_async()`, which spawns a daemon `threading.Thread` invoking `notification_service._do_notify()` inside an application context. The thread approach is preferred over Celery `.delay()` because it is reliable regardless of whether the optional Celery worker container is running.

`_write_blocked_ips_json()` queries all active (non-whitelist) `BlockedIP` records, filters out expired temporary blocks, and writes the resulting list to `blocked_ips.json` at the path given by the `BLOCKED_IPS_JSON_PATH` environment variable. This file is read by `vuln-web/middleware/security.py` on every incoming HTTP request (the `enforce_security()` function called via Flask's `before_request` hook), causing blocked IPs to receive HTTP 403 responses without requiring a server restart or direct database access from vuln-web.

#### 1.4 REST API Layer

The backend API is a Flask application defined in `backend/app/__init__.py`. API endpoints are organized into blueprints under `backend/app/api/`:

- `auth.py` — Login (`POST /api/auth/login`), token verification, logout.
- `incidents.py` — List, retrieve, update, and export incidents; trigger AI explanation; simulate attack.
- `rules.py` — CRUD for `detection_rules`; sets Redis `rules_dirty` flag on write.
- `blocked_ips.py` — List, add, update, and delete (unblock) entries; calls `_write_blocked_ips_json()` after each mutation.
- `rate_limited.py` — List, extend, and clear rate-limited IPs; updates `rate_limited.json` and Redis.
- `dashboard.py` — Aggregate statistics: total incidents, last-24-hour counts, blocked IP count, MTTR, severity breakdown, seven-day timeline.
- `traffic.py` — Returns the most recent parsed log entries for the Live Traffic page.
- `settings.py` — Read/write `AppSetting` key-value pairs for API keys and detection thresholds.
- `audit.py` — Paginated `AuditLog` query.
- `chatbot.py` — AI chat assistant (Groq) for general security questions.
- `ip_history.py` — Per-IP incident history drawer.

All protected endpoints validate the Bearer JWT using `auth_middleware.py`'s `verify_token()` function, registered as a `before_request` hook. Tokens are signed with HS256 using the `SECRET_KEY` environment variable and carry a 24-hour expiry.

#### 1.5 AI and External Services

`backend/app/services/ai_service.py` implements `build_prompt()`, which constructs a structured natural-language prompt from incident attributes, and `_call_groq_with_fallback()`, which attempts the Groq Cloud API using a four-model chain in order: `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` → `meta-llama/llama-4-scout-17b-16e-instruct` → `meta-llama/llama-guard-4-12b`. If all four models fail (HTTP 400/404/422 or network error), the system returns a curated static explanation so that every incident always has human-readable analysis. The `model_used` field in `IncidentExplanation` records which model or the literal string `"fallback-static"` generated the explanation, preserving full auditability.

`backend/app/services/threat_intel_service.py` queries the AbuseIPDB v2 API with the incident's source IP to retrieve an `abuse_confidence_score` (0–100), stored on the `Incident` record and displayed in the incident detail panel.

`backend/app/services/notification_service.py` sends alerts via SMTP email or Telegram Bot API. Settings (SMTP host, port, credentials, recipient, Telegram bot token, and chat ID) are stored in the `AppSetting` table and editable through the Settings page without modifying environment files.

#### 1.6 vuln-web Target Application

The deliberately vulnerable Flask shop (`vuln-web/`) serves as the monitored target. It is composed of route blueprints in `vuln-web/routes/`: `main.py` (home, catalog), `auth.py` (login with intentionally weak credentials), `shop.py` (product listing, cart), `profile.py` (profile update with unrestricted `avatar` field), `files.py` (file upload and download), `cmd.py` (simulated or live command execution), and `api.py` (AJAX endpoints for cart). The `middleware/security.py` module registers `enforce_security()` as a `before_request` hook that reads `blocked_ips.json` and `rate_limited.json` on every request, returning HTTP 403 (blocked) or HTTP 429 (rate limited) as appropriate. The `middleware/logging.py` module registers an `after_request` hook that writes one Combined Log Format line per request to `logs/access.log`, appending `POST_DATA:` fields for login and file-upload endpoints so the detection engine can inspect form parameters without intercepting the request inline.

Two optional Phase 3 flags, read by `vuln-web/config.py` via `_env_bool()`, enable more aggressive vulnerability modes for isolated security lab use:

- `VULN_UNSAFE_CMD=1` — causes `routes/cmd.py` to execute the `cmd` parameter via `subprocess.run(shell=True)` with the timeout from `VULN_CMD_TIMEOUT` (default: 5 s), instead of returning the simulated response. A red warning banner is displayed on the vuln-web shop pages.
- `VULN_UNSAFE_UPLOAD=1` — causes `routes/files.py` to use the raw client-supplied filename (allowing path traversal outside `safe_files/uploads/`) instead of `werkzeug.utils.secure_filename`.

Changing either flag requires a vuln-web process restart. In the Docker Compose deployment, these values are passed via the `environment:` block of the `vuln_web` service; they are not set by default.

#### 1.7 SOC Frontend

The React 18 frontend (`frontend/`) is structured around page-level components in `frontend/src/pages/`: `Dashboard.js`, `Incidents.js`, `IncidentDetail.js`, `BlockedIPs.js`, `DetectionRules.js`, `LiveTraffic.js`, `Settings.js`, and `AuditLog.js`. Routing is defined in `frontend/src/App.js`:


| Route            | Component             | Description                                     |
| ---------------- | --------------------- | ----------------------------------------------- |
| `/`              | `Dashboard`           | Metric cards, incident timeline, severity chart |
| `/incidents`     | `Incidents` (ongoing) | Active incidents list with filters              |
| `/incidents/all` | `Incidents` (all)     | Full incident history                           |
| `/incidents/:id` | `IncidentDetail`      | Detail, AI explanation, notes, status           |
| `/blocked-ips`   | `BlockedIPs`          | IP Management — Blocked and Rate Limited tabs   |
| `/rules`         | `DetectionRules`      | Rules CRUD with pattern test                    |
| `/traffic`       | `LiveTraffic`         | Real-time log stream                            |
| `/settings`      | `Settings`            | API keys and thresholds                         |
| `/audit`         | `AuditLog`            | Admin action history                            |


The sidebar navigation uses the `nav.ipManagement` i18n key (rendered as "IP Management" in English), pointing to `/blocked-ips`. All API calls are made through `frontend/src/services/api.js` using Axios with the JWT stored in `localStorage`. The UI supports English/Indonesian language switching via `react-i18next`. The Live Traffic page filters out static asset requests (`.css`, `.js`, favicon) via a client-side toggle to reduce noise during demonstrations.

### 2. Database Implementation

SME-Guard uses PostgreSQL 15 as its primary relational store, accessed via SQLAlchemy 2.x ORM. All models are defined in `backend/app/models/__init__.py`. The schema is initialized by `db.create_all()` and populated by `seed_all()` in `backend/app/utils/seeder.py`, which runs automatically via `backend/docker_entrypoint.sh` on the first container start. The default seed creates one `admin` user (username `admin`, password `Admin@Incidentra2026!`) and 11 active detection rules covering all supported OWASP attack categories.


| Model Class           | Table                   | Key Columns                                                                                                                                                                                |
| --------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `User`                | `users`                 | `id`, `username`, `email`, `password_hash` (PBKDF2-SHA256), `role`                                                                                                                         |
| `Incident`            | `incidents`             | `source_ip`, `attack_type`, `severity` (enum), `status` (enum), `raw_payload`, `request_path`, `rule_id` (FK), `assigned_to` (FK), `country_code`, `abuse_confidence_score`, `resolved_at` |
| `DetectionRule`       | `detection_rules`       | `rule_name`, `attack_type`, `pattern`, `severity_level` (enum), `is_active`, `match_count`                                                                                                 |
| `BlockedIP`           | `blocked_ips`           | `ip_address`, `reason`, `block_type` (`permanent`/`temporary`), `expire_time`, `incident_count`, `is_whitelist`                                                                            |
| `IncidentLog`         | `incident_logs`         | `incident_id` (FK), `action_taken`, `action_detail`, `performed_by`                                                                                                                        |
| `IncidentExplanation` | `incident_explanations` | `incident_id` (FK), `ai_summary`, `threat_explanation`, `recommended_actions`, `mitre_technique`, `model_used`, `generated_at`                                                             |
| `IncidentNote`        | `incident_notes`        | `incident_id` (FK), `note_content`, `created_by`, `created_at`                                                                                                                             |
| `AppSetting`          | `app_settings`          | `key`, `value` (API keys, SMTP config, thresholds)                                                                                                                                         |
| `AuditLog`            | `audit_logs`            | `user_id` (FK), `action`, `target`, `details`, `created_at`                                                                                                                                |


Rate-limiting state is stored outside PostgreSQL for performance. The `rate_limited.json` file (path: `RATE_LIMITED_JSON_PATH` env variable) maintains the set of rate-limited IPs and per-IP policy overrides. Redis stores `ratelimit:{ip}` keys with a TTL for enforcement expiry. Neither structure has a PostgreSQL table; the API provides endpoints to read and modify `rate_limited.json` directly.

### 3. User Interface Implementation

The SOC Dashboard is a React 18 single-page application built with Material UI (MUI) and served by Nginx on port 3000. The dark theme (`frontend/src/theme/index.js`) is optimized for prolonged use in security operations environments. Key UI behaviors verified against the codebase are as follows.

The Dashboard page displays four metric cards: Total Incidents (all time), Detections in Last 24 Hours, Blocked IP Addresses (active blocks from `BlockedIP` table), and MTTR (Mean Time to Resolution). A collapsible system status banner, driven by `last_log_received_at` from the log monitor, alerts operators when no log lines have been received in the last 60 seconds. The Incident Timeline (Chart.js line chart, 7-day window) and By Severity donut chart auto-refresh every 30 seconds.

The Incidents page renders a filterable, paginated table with columns for detection timestamp, source IP, attack type badge, severity badge, status badge, request path, and the automated response action icon. Dropdown filters cover severity and status. A full-text search field covers IP address, attack type, and path. The "Simulate Attack" button submits a synthetic SQL injection payload through the backend's `/api/incidents/simulate` endpoint to generate a demonstration incident. The "Export CSV" button downloads up to 1,000 records including the columns ID, Date, Source IP, Attack Type, Severity, Status, Path, and Country.

The Incident Detail page (`/incidents/:id`) has a two-panel layout. The left panel displays all technical attributes: Source IP with AbuseIPDB confidence score badge, Attack Type, Severity, HTTP method, request path, HTTP status code, country code, detection timestamp, and resolution timestamp. A "Raw Payload" section shows the original access log line. The right panel has two states: before AI explanation generation it shows a "Generate AI Explanation" button; after generation it shows four color-coded panels (Summary, Why It's Dangerous, Recommended Actions, MITRE ATT&CK mapping) and the model name badge. The Automated Actions timeline, populated from `IncidentLog` records, and the Investigation Notes section (append-only, timestamped, stored in `IncidentNote`) are displayed below both panels.

The IP Management page (`/blocked-ips`) presents two tabs. The **Blocked** tab lists `BlockedIP` records with columns for IP address, reason, block type, blocked-at timestamp, expiry (or "Never" for permanent blocks), incident count, and unblock/edit actions. The **Rate Limited** tab reads `rate_limited.json` via the `/api/rate-limited/` endpoint and displays each rate-limited IP with its policy (max requests per window, window seconds, Redis TTL remaining) and a per-IP extend or clear action. A "+ Block IP" dialog allows administrators to manually add an IP with a configurable block type and duration.

The Detection Rules page lists all `DetectionRule` records in a table with columns for rule name, attack type badge, severity badge, regex pattern excerpt, match count, active toggle, and edit/delete actions. The "+ Add Rule" modal collects a rule name, attack type (from a fixed enum), severity level, regex pattern, and optional description. The Live Traffic page auto-refreshes every three seconds via HTTP polling of `/api/traffic/`. Each row shows timestamp, IP, HTTP method, path, query/payload excerpt, HTTP status, and a classification tag (Attack / Suspicious / Blocked / Normal) derived from pattern-matching in the backend.

[SCREENSHOT: Figure 1 — SME-Guard Login Page. Shows the dark-themed card with the shield logo, username/admin field, password field, and default credentials hint.]

[SCREENSHOT: Figure 2 — SOC Dashboard. Shows four metric cards, system status banner, seven-day Incident Timeline chart, and By Severity donut chart.]

[SCREENSHOT: Figure 3 — Incidents List. Filterable table with SQL_INJECTION row (Critical severity, New status, path /search, lock icon for IP block).]

[SCREENSHOT: Figure 4 — Incident Detail (Before AI Explanation). Left panel: source IP, attack type SQL_INJECTION, severity Critical, GET /search, HTTP 200, Automated Actions showing permanent block. Right panel: "AI Explanation Not Generated" state with Generate button.]

[SCREENSHOT: Figure 5 — Incident Detail (After AI Explanation). Right panel shows AI-Powered Analysis with Summary (blue-green), Why It's Dangerous (orange), Recommended Actions (purple), MITRE ATT&CK mapping, and llama-3.3-70b-versatile model badge.]

[SCREENSHOT: Figure 6 — IP Management, Blocked Tab. Table with one permanent block row, reason "Auto-blocked (CRITICAL): SQL_INJECTION", Expires Never, unblock icon.]

[SCREENSHOT: Figure 7 — IP Management, Rate Limited Tab. Table showing rate-limited IP with policy (max requests, window), TTL remaining, and Extend / Clear actions.]

[SCREENSHOT: Figure 8 — Detection Rules. Table with 11 active rules including Brute Force – Login, Command Injection (critical), XSS – Script Tag (critical), match_count column, active toggle per row.]

[SCREENSHOT: Figure 9 — Create Detection Rule Modal. Fields: Rule Name, Attack Type (dropdown: SQL INJECTION), Severity (high), Regex Pattern text area, Description.]

[SCREENSHOT: Figure 10 — Live Traffic Monitor. Rows showing Attack tag with HTTP 200 for /cmd?cmd=;whoami, then a Blocked tag with HTTP 403 on the subsequent request from the same IP. Normal tags for ordinary shop requests.]

[SCREENSHOT: Figure 11 — Settings Page. Sections for AI Assistant (Groq API key, model selector, Test Connection), Threat Intelligence (AbuseIPDB key), Email Notifications (SMTP), Telegram Bot, Detection Thresholds.]

[SCREENSHOT: Figure 12 — vuln-web Shop (Phase 3 enabled). Red banner: "⚠ LAB MODE – VULN_UNSAFE_CMD is enabled". Shop catalog visible below banner.]

[SCREENSHOT: Figure 13 — vuln-web 403 Page. Dark-themed "🔒 403 Access Forbidden — Your IP has been blocked by SME-Guard" page after IP block.]

[SCREENSHOT: Figure 14 — vuln-web 429 Page. Yellow-themed "⏱ 429 Too Many Requests" page with rate limit and retry countdown.]

### 4. Hardware Implementation

**Not applicable.** SME-Guard is a software-only system. No microcontrollers, IoT sensors, or dedicated hardware appliances are required. The minimum recommended specification for the demonstration environment is a laptop or PC with at least 8 GB RAM and Docker Desktop installed, or a Linux VPS with 2 vCPUs and 4 GB RAM. All processing, storage, and network communication occur within Docker containers on the host machine.

### 5. Integration Among Modules

The complete integration flow is illustrated below. The `vuln_logs` Docker named volume is the sole shared state between the monitored application and the detection backend; vuln-web has no direct database connection.

```
5. Integration Among Modules

The complete integration flow is illustrated below. The vuln_logs Docker named volume is the sole shared state between the monitored application and the detection backend; vuln-web has no direct database connection.
```

Four integration points deserve particular attention. First, vuln-web has no PostgreSQL connection; it receives enforcement signals exclusively through the two JSON files written by the Response Manager. Second, the `POST_DATA:file=filename` suffix in the access log is the mechanism by which the Detection Engine classifies file uploads without reading the uploaded file from disk — the dangerous extension is matched against the log line itself. Third, when an administrator unblocks an IP via the SOC dashboard, the `blocked_ips.py` API calls `_write_blocked_ips_json()` to remove the IP from the enforcement file, and also sets a Redis `unblocked:{ip}` key (10-minute TTL) to temporarily waive deduplication so the IP's next legitimate requests are not re-detected. Fourth, the Detection Engine's 60-second rule-reload cycle (triggered by the Redis `rules_dirty` flag) allows administrators to add or modify detection rules through the SOC dashboard and have them take effect within one minute without any service restart.

---

## B. PRODUCT DISPLAY

### 1. Software Product Display

The SME-Guard system consists of two browser-accessible components: the SOC Dashboard (React, port 3000) and the vuln-web target shop (Flask, port 5050). The following subsections describe the key screens as implemented.

**Login Page.** The login page (`frontend/src/pages/Login.js`) presents a centered card on a dark background with the SME-Guard shield logo, "Intelligent Web-SOC Platform" subtitle, username and password fields, and a "Sign In" button. On successful authentication the Flask `/api/auth/login` endpoint issues a JWT (HS256, 24-hour expiry). A hint displays the default credentials (`admin / Admin@Incidentra2026!`) to assist new operators.

[SCREENSHOT: Figure 1 — Login Page with default credentials hint.]

**SOC Dashboard.** The dashboard provides a real-time overview with four KPI metric cards: Total Incidents, Detections in Last 24 Hours, Blocked IPs, and MTTR. A system status banner dynamically changes between "All Systems Normal" and a warning when the log monitor has received no entries in the last 60 seconds. The Incident Timeline uses Chart.js to render a seven-day bar/line chart, and the By Severity donut chart shows the breakdown across low, medium, high, and critical incidents.

[SCREENSHOT: Figure 2 — SOC Dashboard with KPI cards, system status banner, and charts.]

**Incidents List.** The incidents table supports filtering by severity and status, full-text search across IP, attack type, and path, and pagination. Each row shows a colour-coded attack type badge and severity badge. A lock icon in the Response column indicates an automated IP block. "Simulate Attack" and "Export CSV" buttons appear in the header.

[SCREENSHOT: Figure 3 — Incidents List with SQL_INJECTION entry marked Critical, automated IP block icon.]

**Incident Detail — Before AI Analysis.** The detail page shows the full technical breakdown on the left (source IP, AbuseIPDB score, attack type, severity, HTTP method, path, response code, country, timestamps) and the "AI Explanation Not Generated" placeholder with a "Generate AI Explanation" call-to-action on the right. The Automated Actions section below shows what the system executed automatically at detection time (e.g., permanent block of the source IP). The Investigation Notes section is available for analyst annotations.

[SCREENSHOT: Figure 4 — Incident Detail before AI generation, showing HTTP 200 response code and automated permanent block action in the Automated Actions log.]

**Incident Detail — After AI Analysis.** After clicking "Generate AI Explanation," the right panel is replaced by the AI-Powered Analysis section containing four color-coded blocks: Summary, Why It's Dangerous, Recommended Actions, and MITRE ATT&CK mapping. The model name badge (e.g., `llama-3.3-70b-versatile`) appears in the panel header.

[SCREENSHOT: Figure 5 — Incident Detail after Groq LLM analysis with four color-coded explanation panels and model badge.]

**IP Management — Blocked Tab.** The Blocked tab of the IP Management page lists all `BlockedIP` records. Each row shows the IP address, reason (including the attack type that triggered the block), block type (permanent or temporary), blocked-at timestamp, expiry time (or "Never" for permanent blocks), incident count, and an unblock button. A "+ Block IP" button opens a dialog for manual IP blocking.

[SCREENSHOT: Figure 6 — IP Management, Blocked tab with one permanent block entry for a SQL injection source.]

**IP Management — Rate Limited Tab.** The Rate Limited tab reads from `rate_limited.json` via the API and displays each rate-limited IP with its per-IP policy and enforcement TTL from Redis. Extend and Clear action buttons are provided per row.

[SCREENSHOT: Figure 7 — IP Management, Rate Limited tab with rate-limited IP, max-requests and window policy columns, and action buttons.]

**Detection Rules.** The rules table lists each `DetectionRule` record with its name, attack type badge, severity badge, pattern excerpt, match count, active toggle, and edit/delete actions. Toggling a rule sets `is_active` in PostgreSQL and writes the Redis `rules_dirty` flag.

[SCREENSHOT: Figure 8 — Detection Rules page with 11 active rules, match counters, and active toggles.]

**Create Detection Rule.** The "+ Add Rule" modal collects Rule Name, Attack Type (dropdown of supported enums), Severity Level, Regex Pattern, and Description. Upon submission the rule is saved to the `detection_rules` table and `rules_dirty` is set.

[SCREENSHOT: Figure 9 — Create Detection Rule modal with SQL INJECTION selected and high severity.]

**Live Traffic.** The Live Traffic page (`/traffic`) displays parsed access log entries refreshed every three seconds. Each row shows timestamp, source IP, HTTP method, path, query/payload excerpt, HTTP status code, and a classification tag. Tag colour coding: Attack (red), Suspicious (amber), Blocked (purple), Normal (green). The critical distinction is that an "Attack" tag with HTTP status 200 means the request reached the application before the Detection Engine processed the log line — no block has been applied yet. Only subsequent requests from that IP after an Incident has been created and `blocked_ips.json` updated will receive a "Blocked" tag with HTTP 403.

[SCREENSHOT: Figure 10 — Live Traffic showing Attack (200) tag for GET /cmd?cmd=;whoami, then Blocked (403) tag for a subsequent request from the same IP after incident creation.]

**Settings.** The Settings page stores all external integration keys and detection thresholds in the `AppSetting` table. Configurable items include Groq API key and model, AbuseIPDB API key, SMTP host/port/credentials/recipient, Telegram bot token and chat ID, and the numerical thresholds for brute force detection, rate limiting, and temporary block duration. Keys are masked (asterisks) in the UI.

[SCREENSHOT: Figure 11 — Settings page showing AI Assistant (Groq), Threat Intelligence (AbuseIPDB), Email Notifications, and Detection Thresholds sections.]

**vuln-web Shop.** The target application provides a simple e-commerce interface: product catalog, shopping cart, login, profile (with avatar upload field), file browser, and command execution page. When Phase 3 is enabled (`VULN_UNSAFE_CMD=1`), a red warning banner reading "⚠ LAB MODE – VULN_UNSAFE_CMD is enabled" appears on all pages.

[SCREENSHOT: Figure 12 — vuln-web shop catalog page with red Phase 3 lab mode banner at the top.]

**vuln-web 403 and 429 Pages.** When a blocked IP makes a request, `middleware/security.py` returns the `FORBIDDEN_HTML` template (HTTP 403) which displays the blocked IP address in a dark-themed error page. A rate-limited IP receives the `TOO_MANY_REQUESTS_HTML` template (HTTP 429) displaying the per-minute limit and a retry countdown.

[SCREENSHOT: Figure 13 — vuln-web 403 Forbidden page ("Your IP has been blocked by SME-Guard").]

[SCREENSHOT: Figure 14 — vuln-web 429 Too Many Requests page with rate limit value and retry countdown.]

---

## C. COST ANALYSIS

All software components used by SME-Guard are open-source and carry no licensing cost. The table below presents the cost structure for two deployment scenarios: local demonstration (Docker Compose on a developer laptop) and optional production deployment on a VPS.


| Item                                          | Local Demo (Docker) | Optional VPS Production         | Notes                                                                                                            |
| --------------------------------------------- | ------------------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Operating system (Ubuntu Linux)               | Rp 0                | Rp 0                            | Open source                                                                                                      |
| Docker / Docker Compose                       | Rp 0                | Rp 0                            | Open source                                                                                                      |
| PostgreSQL 15                                 | Rp 0                | Rp 0                            | Open source                                                                                                      |
| Redis 7                                       | Rp 0                | Rp 0                            | Open source                                                                                                      |
| Flask / Python libraries                      | Rp 0                | Rp 0                            | Open source (PyPI)                                                                                               |
| React / Node.js / MUI                         | Rp 0                | Rp 0                            | Open source (npm)                                                                                                |
| Groq Cloud API (Groq free tier)               | Rp 0                | Rp 0                            | Free tier sufficient for capstone demo; paid tier required for high-volume production use                        |
| AbuseIPDB API (free tier, 1,000 checks/day)   | Rp 0                | Rp 0                            | Free tier                                                                                                        |
| SMTP relay (Gmail SMTP with app password)     | Rp 0                | Rp 0                            | No cost at low volume                                                                                            |
| VPS hosting (e.g., 2 vCPU / 4 GB RAM, Ubuntu) | N/A                 | ≈ Rp 1,500,000–1,600,000 / year | Price estimate based on Indonesian cloud providers (IDCloudHost, Biznet Gio) as of 2026; subject to market rates |
| Domain name (optional)                        | N/A                 | ≈ Rp 150,000 / year             | Optional `.my.id` or `.id` TLD                                                                                   |
| **Total (local demo)**                        | **Rp 0**            | —                               | —                                                                                                                |
| **Total (optional VPS, first year)**          | —                   | **≈ Rp 1,650,000–1,750,000**    | —                                                                                                                |


The zero-cost local deployment makes SME-Guard immediately accessible to small and medium enterprises without requiring any IT budget. The optional VPS deployment provides persistent availability for monitoring a production web server at a cost of approximately Rp 1.5–1.6 million per year — substantially below the cost of any commercial SIEM or WAF solution.

---

## D. TEST SCENARIOS

Testing is conducted against the Docker Compose deployment (six services: `postgres`, `redis`, `vuln_web`, `backend`, `celery_worker`, `frontend`). The SOC Dashboard is accessed at `http://localhost:3000`; the vuln-web target at `http://localhost:5050`. Complete **Output Result** during rehearsal using `[../AUDIT.md](../AUDIT.md)` (sections D–J). Replace `*(isi setelah uji)`* with `PASS — [date]` or `FAIL — [reason]`.

### D.1 — Authentication


| No. | Scenario          | Input                                                                                                        | Expected Output                                                      | Output Result       |
| --- | ----------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- | ------------------- |
| 1   | Successful login  | Navigate to `http://localhost:3000`; enter username `admin`, password `Admin@Incidentra2026!`; click Sign In | JWT issued; redirect to Dashboard; all sidebar items visible         | *(isi setelah uji)* |
| 2   | Wrong credentials | Enter username `admin`, password `wrongpass`; click Sign In                                                  | HTTP 401 "Invalid credentials" displayed; user remains on login page | *(isi setelah uji)* |
| 3   | No token (API)    | `GET http://localhost:5000/api/incidents` without Authorization header                                       | HTTP 401 "Authorization required"; no data returned                  | *(isi setelah uji)* |


### D.2 — SQL Injection Detection


| No. | Scenario                          | Input                                                                                 | Expected Output                                                                                      | Output Result       |
| --- | --------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | **Login POST SQLi (demo sidang)** | `http://localhost:5050/login` — username `admin' OR '1'='1' --`, password any; Submit | Incident: `SQL_INJECTION`, `severity=critical`; `POST_DATA` in raw payload; IP in `blocked_ips.json` | *(isi setelah uji)* |
| 2   | Automated block enforcement       | After step 1, open `http://localhost:5050/` from same IP                              | HTTP 403 Forbidden (SME-Guard branding); Live Traffic shows **Blocked** on next row                  | *(isi setelah uji)* |
| 3   | Reflected SQLi via search         | `http://localhost:5050/search?q=admin'+OR+'1'='1'--`                                  | Incident: `SQL_INJECTION`, critical                                                                  | *(isi setelah uji)* |
| 4   | Blind time-based SQLi             | `http://localhost:5050/search?q=1' AND SLEEP(5)--`                                    | Incident: `SQL_INJECTION` if pattern matches                                                         | *(isi setelah uji)* |


### D.3 — XSS Detection


| No. | Scenario                     | Input                                                                                              | Expected Output                                                                                                                   | Output Result       |
| --- | ---------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | Reflected XSS via script tag | Navigate to `http://localhost:5050/profile?name=<script>alert(document.cookie)</script>`; wait 3 s | Incident: `attack_type=XSS`, `severity=critical`; IP permanently blocked; tagged "Attack" in Live Traffic (HTTP 200 on first hit) | *(isi setelah uji)* |
| 2   | XSS event handler            | Navigate to `http://localhost:5050/search?q=<img onerror=alert(1) src=x>`; wait 3 s                | Incident: `attack_type=XSS`, `severity=critical`                                                                                  | *(isi setelah uji)* |
| 3   | Benign search query          | Navigate to `http://localhost:5050/search?q=laptop`; wait 3 s                                      | No incident created; entry appears as "Normal" in Live Traffic                                                                    | *(isi setelah uji)* |


### D.4 — Path Traversal / LFI


| No. | Scenario                   | Input                                                                             | Expected Output                                                                               | Output Result       |
| --- | -------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------- |
| 1   | Classic path traversal     | Navigate to `http://localhost:5050/files?file=../../etc/passwd`; wait 3 s         | Incident: `attack_type=PATH_TRAVERSAL`, `severity=high`; IP temporarily blocked (24 h)        | *(isi setelah uji)* |
| 2   | Enforcement file targeting | Navigate to `http://localhost:5050/files?file=E:/path/blocked_ips.json`; wait 3 s | Incident: `attack_type=PATH_TRAVERSAL` (pattern `blocked_ips\.json` in `detection_engine.py`) | *(isi setelah uji)* |
| 3   | Benign file access         | Navigate to `http://localhost:5050/files?file=readme.txt`                         | No incident; entry appears as Normal in Live Traffic                                          | *(isi setelah uji)* |


### D.5 — File Upload


| No. | Scenario                            | Input                                                     | Expected Output                                                                                                            | Output Result       |
| --- | ----------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | Safe upload — no incident           | POST `/files` via vuln-web upload form; file: `notes.txt` | Request logged in `access.log`; appears in Live Traffic as Normal; **no** FILE_UPLOAD incident created                     | *(isi setelah uji)* |
| 2   | Dangerous upload — single extension | POST `/files` via upload form; file: `shell.php`          | Log line contains `POST_DATA:file=shell.php`; incident: `attack_type=FILE_UPLOAD`, `severity=high`; IP temporarily blocked | *(isi setelah uji)* |
| 3   | Dangerous upload — double extension | POST `/files` via upload form; file: `image.php.jpg`      | FILE_UPLOAD incident (matches `(?i)(?:file|avatar)=[^&\s"]*\.(php|jsp|...)[^&\s"]*\.(jpg|...)\b`)                          | *(isi setelah uji)* |
| 4   | Profile avatar CTF vector           | POST `/profile` with field `avatar=shell.php`             | Log line contains `POST_DATA:avatar=shell.php`; FILE_UPLOAD incident created; no extension whitelist in vuln-web           | *(isi setelah uji)* |


### D.5b — Command Injection


| No. | Scenario                                      | Input                                                                  | Expected Output                                                                                                                                                          | Output Result       |
| --- | --------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------- |
| 1   | Metacharacter payload                         | Navigate to `http://localhost:5050/cmd?cmd=;whoami`; wait 3 s          | Incident: `attack_type=COMMAND_INJECTION`, `severity=critical`; IP permanently blocked; subsequent request returns HTTP 403                                              | *(isi setelah uji)* |
| 2   | Plain keyword payload (after backend restart) | Navigate to `http://localhost:5050/cmd?cmd=whoami`; wait 3 s           | Incident: `attack_type=COMMAND_INJECTION`, `severity=critical` (matched by `cmd=whoami` pattern in `DETECTION_PATTERNS`)                                                 | *(isi setelah uji)* |
| 3   | Live Traffic — Attack tag before block        | First request to `/cmd?cmd=;whoami` (before detection cycle completes) | Live Traffic entry shows tag **Attack**, HTTP status **200** — this is the request that was logged and subsequently detected; the block is applied to the *next* request | *(isi setelah uji)* |


### D.5c — Phase 3 Environment Toggle


| No. | Scenario                 | Input                                                                                                                                     | Expected Output                                                                                                                                  | Output Result       |
| --- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------- |
| 1   | Unsafe CMD off (default) | `VULN_UNSAFE_CMD` not set (or `0`); navigate to `http://localhost:5050/cmd?cmd=whoami`                                                    | vuln-web shows `[Simulated] Would execute: whoami` message; no real shell execution                                                              | *(isi setelah uji)* |
| 2   | Unsafe CMD on            | Set `VULN_UNSAFE_CMD=1` in `vuln-web/.env`; restart vuln-web container (`docker compose restart vuln_web`); navigate to `/cmd?cmd=whoami` | Real shell output (`www-data` or container username); red Phase 3 warning banner on all shop pages; SOC still creates COMMAND_INJECTION incident | *(isi setelah uji)* |
| 3   | Unsafe upload on         | Set `VULN_UNSAFE_UPLOAD=1`; restart vuln-web; upload file with `../` in filename via `/files` form                                        | File saved outside `safe_files/uploads/` (path traversal in upload); FILE_UPLOAD incident still created by SOC if extension is dangerous         | *(isi setelah uji)* |


### D.6 — Brute Force Detection


| No. | Scenario                  | Input                                                                                                                                 | Expected Output                                                                                                                  | Output Result       |
| --- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | Threshold-based detection | Send 11+ POST requests to `http://localhost:5050/login` with incorrect passwords within 60 s (using curl or browser rapid submission) | BRUTE_FORCE incident created on the 10th attempt (`severity=high`); source IP rate-limited; subsequent requests receive HTTP 429 | *(isi setelah uji)* |


### D.7 — IP Block and Unblock


| No. | Scenario                      | Input                                                                              | Expected Output                                                                                                                         | Output Result       |
| --- | ----------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | Auto-block on critical attack | Trigger any critical-severity attack (e.g., SQL injection from D.2)                | Source IP written to `blocked_ips.json`; subsequent requests from that IP receive HTTP 403                                              | *(isi setelah uji)* |
| 2   | Manual unblock via SOC        | Navigate to IP Management → Blocked tab; click Unblock for the blocked IP; confirm | IP removed from `BlockedIP` DB record and from `blocked_ips.json`; subsequent requests from that IP receive HTTP 200 (normal shop page) | *(isi setelah uji)* |
| 3   | Manual block via SOC          | Click "+ Block IP"; enter IP `10.0.0.99`; select permanent; submit                 | IP added to `blocked_ips.json`; requests from `10.0.0.99` to vuln-web return HTTP 403                                                   | *(isi setelah uji)* |


### D.8 — Rate Limiting


| No. | Scenario          | Input                                                                                                                                                                                     | Expected Output                                                                                         | Output Result       |
| --- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | Exceed rate limit | Trigger medium-severity attack (Scanner UA detection); IP is written to `rate_limited.json`; then send rapid requests exceeding the default limit (10 req/min) to `http://localhost:5050` | HTTP 429 Too Many Requests page returned by vuln-web; page shows current IP, limit, and retry countdown | *(isi setelah uji)* |


### D.9 — Live Traffic


| No. | Scenario                                        | Input                                                                                                                                       | Expected Output                                                                                                                                                                                | Output Result       |
| --- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | Hide static assets                              | On Live Traffic page, enable "Hide static assets" toggle                                                                                    | Requests for `.css`, `.js`, and favicon paths are filtered from the table; only application requests remain visible                                                                            | *(isi setelah uji)* |
| 2   | Attack tag (HTTP 200) vs Blocked tag (HTTP 403) | Navigate to `http://localhost:5050/cmd?cmd=;whoami` (first hit); wait ~5 s for detection; then refresh `http://localhost:5050` from same IP | First row: tag **Attack**, status **200** (request was served before block was applied); subsequent row: tag **Blocked**, status **403** (enforcement active after `blocked_ips.json` updated) | *(isi setelah uji)* |
| 3   | Normal traffic                                  | Browse vuln-web catalog pages without any attack payloads                                                                                   | All rows tagged Normal (green); no incidents created                                                                                                                                           | *(isi setelah uji)* |


### D.10 — Detection Rules CRUD


| No. | Scenario                          | Input                                                                                                                                  | Expected Output                                                                                                 | Output Result       |
| --- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | Create new rule                   | Detection Rules → "+ Add Rule"; Name: `Custom Test`, Type: `SQL INJECTION`, Severity: `high`, Pattern: `(?i)testpayload`; click Create | Rule saved to `detection_rules` table with `match_count=0`; Redis `rules_dirty` flag set; rule appears in table | *(isi setelah uji)* |
| 2   | Toggle rule inactive              | Click active toggle on any rule                                                                                                        | `is_active=false` saved to DB; detection engine skips rule on next 60-second reload                             | *(isi setelah uji)* |
| 3   | Rule triggers on matching request | With custom rule from step 1 active, send request containing `testpayload` to vuln-web; wait 60 s for reload; wait 3 s for detection   | Incident created using the custom rule's attack type; `match_count` increments                                  | *(isi setelah uji)* |


### D.11 — AI Explanation


| No. | Scenario                               | Input                                                               | Expected Output                                                                        | Output Result       | Ref (AUDIT) |
| --- | -------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------- | ----------- |
| 1   | Generate explanation (Groq configured) | Open any incident; click "Generate AI Explanation"; wait up to 30 s | AI panel: Summary, Why It's Dangerous, Recommended Actions, MITRE mapping; model badge | *(isi setelah uji)* | B10         |
| 2   | Static fallback (no API key)           | Empty `GROQ_API_KEY`; trigger incident; generate                    | Static text; `model_used` = fallback                                                   | *(isi setelah uji)* | —           |


### D.12 — Scanner Detection (Rate Limit)


| No. | Scenario                          | Input                                          | Expected Output                                                                | Output Result       | Ref (AUDIT) |
| --- | --------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------ | ------------------- | ----------- |
| 1   | Scanner User-Agent                | `curl -A "Nikto/2.1.6" http://localhost:5050/` | Incident **SCANNER**, medium; IP in **Rate Limited** tab (not permanent block) | *(isi setelah uji)* | B5 / E4     |
| 2   | Rapid requests while rate limited | 10+ requests/min from same IP after scanner    | HTTP **429** on vuln-web                                                       | *(isi setelah uji)* | C6.4        |


### D.13 — Simulate Attack (Mode B)


| No. | Scenario           | Input                                               | Expected Output                                               | Output Result       | Ref (AUDIT) |
| --- | ------------------ | --------------------------------------------------- | ------------------------------------------------------------- | ------------------- | ----------- |
| 1   | Inject log via SOC | Incidents → Simulate Attack → Mode B → e.g. LFI_RFI | Toast success; incident appears ~5 s without vuln-web request | *(isi setelah uji)* | B8          |


### D.14 — LFI / RFI Detection


| No. | Scenario                  | Input                                                               | Expected Output                                 | Output Result       | Ref (AUDIT) |
| --- | ------------------------- | ------------------------------------------------------------------- | ----------------------------------------------- | ------------------- | ----------- |
| 1   | PHP wrapper in file param | `GET /files?file=php://filter/convert.base64-encode/resource=index` | Incident **LFI_RFI**, critical, permanent block | *(isi setelah uji)* | C7          |
| 2   | Remote filter in search   | `GET /search?q=test.php://filter`                                   | Incident **LFI_RFI** if pattern matches         | *(isi setelah uji)* | C7          |


### D.15 — Incident Workflow


| No. | Scenario         | Input                                 | Expected Output                                    | Output Result       | Ref (AUDIT) |
| --- | ---------------- | ------------------------------------- | -------------------------------------------------- | ------------------- | ----------- |
| 1   | Resolve incident | Mark one incident **Resolved** in SOC | Row moves to `/incidents/all`; leaves ongoing list | *(isi setelah uji)* | B9          |
| 2   | Export CSV       | Incidents → Export CSV                | CSV file downloads with incident columns           | *(isi setelah uji)* | F6          |


> **Cara isi kolom Output Result:** Jalankan tes di `[../AUDIT.md](../AUDIT.md)` (Docker: bagian D, E, F–J). Ganti `*(isi setelah uji)`* dengan `PASS — [tanggal]` atau `FAIL — [alasan]`.

---

## E. MANUAL GUIDE

### E.1 — System Build (Developer / Demonstrator)

The primary deployment method is Docker Compose, which provisions all six services with a single command and requires no manual database or virtual environment setup.

**Prerequisites:** Git, Docker Desktop (Windows/macOS) or Docker Engine + Docker Compose v2 (Linux). The developer machine must have at least 8 GB RAM and ports 3000, 5000, 5050, 5432, and 6379 available.

**Step 1 — Clone the repository.**

```bash
git clone https://github.com/HardInCode/sme-guard.git
cd sme-guard
```

**Step 2 — Configure the backend environment file.**

```bash
copy backend\.env.docker.example backend\.env.docker   # Windows
# or
cp backend/.env.docker.example backend/.env.docker      # Linux/macOS
```

Open `backend/.env.docker` and populate the optional keys: `GROQ_API_KEY` (from console.groq.com, free tier), `ABUSEIPDB_API_KEY`, and SMTP/Telegram credentials. Core detection and blocking operate without any external API keys.

**Step 3 — Build and start all containers.**

```bash
docker compose up --build -d
```

Docker Compose starts six services: `postgres` (port 5432), `redis` (port 6379), `vuln_web` (port 5050), `backend` (port 5000), `frontend` (port 3000, served by Nginx), and `celery_worker`. The `backend` entrypoint script (`docker_entrypoint.sh`) runs `db.create_all()`, seeds the admin user and 11 default detection rules, then starts Gunicorn. The log monitor thread starts automatically and begins tailing the shared `vuln_logs` volume.

**Step 4 — Access the system.**

- SOC Dashboard: `http://localhost:3000` — Login with `admin / Admin@Incidentra2026!`
- vuln-web target: `http://localhost:5050`

**Step 5 — Verify operation.**
Browse `http://localhost:5050` and check that new entries appear in Live Traffic within 3–6 seconds.

**Step 6 — Enable Phase 3 (optional, isolated lab only).**
Edit `docker-compose.yml` and add `VULN_UNSAFE_CMD: "1"` to the `vuln_web` service `environment:` block, then restart:

```bash
docker compose restart vuln_web
```

The red warning banner will appear on all vuln-web pages.

**Step 7 — Reset for demonstration (Docker).**
From the repository root (with Docker stack running):

```powershell
$env:DATABASE_URL = "postgresql://smeguard:smeguard123@localhost:5432/smeguard_db"
$env:REDIS_URL = "redis://localhost:6379/0"
python scripts/reset_smeguard.py

docker compose exec vuln_web sh -c ":> /app/logs/access.log"
docker compose exec vuln_web sh -c 'echo "{\"blocked\":[],\"details\":{},\"updated_at\":\"\"}" > /app/logs/blocked_ips.json'
docker compose exec vuln_web sh -c 'echo "{\"rate_limited\":[],\"updated_at\":\"\"}" > /app/logs/rate_limited.json'

docker compose restart backend vuln_web
```

For manual mode only: `python scripts/reset_smeguard.py --clear-logs` then restart backend and vuln-web.

**Manual (3-terminal) alternative.** For development without Docker, open three terminals:

- Terminal 1: `cd backend && pip install -r requirements.txt && python run.py`
- Terminal 2: `cd frontend && npm install && npm start`
- Terminal 3: `cd vuln-web && pip install -r requirements.txt && python app.py`

PostgreSQL and Redis must be running locally. Copy `backend/.env.example` to `backend/.env` and set `DATABASE_URL`, `REDIS_URL`, and `WEB_SERVER_LOG_PATH` to the absolute path of `vuln-web/logs/access.log`.

### E.2 — End-User Installation

SME-Guard is a server-side platform. End-user installation requires no software installation on the administrator's workstation beyond a modern web browser.


| Component                | Requirement                                                                                                                                                                                     |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Server                   | VPS running Ubuntu 22.04+ with Docker Engine and Docker Compose v2 installed; minimum 2 vCPU, 4 GB RAM, 20 GB disk                                                                              |
| Alternative              | Single PC running Windows 10/11 or macOS with Docker Desktop                                                                                                                                    |
| Browser (SOC user)       | Google Chrome or Microsoft Edge (latest version); access `http://<server-ip>:3000`                                                                                                              |
| Monitored application    | Any web application that writes NCSA Combined Log Format access logs; replace vuln-web's log path with the production log path via `WEB_SERVER_LOG_PATH` in `backend/.env.docker`               |
| Network                  | Expose port 3000 (SOC UI) to trusted administrator IPs; port 5000 (API) should not be publicly accessible; port 5050 (vuln-web) is for demonstration only and must not be exposed in production |
| External APIs (optional) | Outbound HTTPS to `api.groq.com` (AI explanations), `api.abuseipdb.com` (IP reputation), `smtp.gmail.com:587` (email alerts), `api.telegram.org` (Telegram alerts)                              |


No client-side installation is required. The SOC Dashboard is served as a pre-built React application by Nginx and accessed entirely in the browser.

### E.3 — User Guide per Role

SME-Guard defines three user roles, each with a distinct set of responsibilities and access paths within the system.


| Role                              | Access Level                  | Primary Responsibilities                                                                                                            | Typical Workflow                                                                                                                                                                                                                                                                               |
| --------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Admin**                         | Full SOC access               | Manage detection rules; block or unblock IPs; configure API keys and thresholds; review audit log; assign incidents; export reports | Login → Dashboard (review KPIs) → Incidents (filter Critical/High → open incident → change status to Investigating → Generate AI Explanation → add note → mark Resolved) → IP Management (Blocked tab → Unblock false positive) → Detection Rules (Add/Edit rule) → Settings (update Groq key) |
| **Analyst**                       | Read + incident status update | Monitor live threats; triage incidents; review AI explanations; annotate with investigation notes; update status                    | Login → Dashboard (check 24-hour detection count) → Live Traffic (watch for Attack tags) → Incidents (filter New/Investigating → open critical incident → review details → add investigation note → change status to Investigating)                                                            |
| **Shop Lab User** (vuln-web demo) | vuln-web only (no SOC access) | Browse catalog; demonstrate attack payloads for lab exercises                                                                       | Open `http://localhost:5050` → browse catalog → attempt payloads (search, files, cmd, login) → observe 403/429 responses after SOC detection; do not use `.php` or dangerous extensions in production                                                                                          |


**Detailed procedure — Admin: Unblock an IP**

1. Open `http://localhost:3000` in a browser and sign in as `admin`.
2. In the left sidebar, click **IP Management** (under the Block icon).
3. Confirm the **Blocked** tab is selected.
4. Locate the IP address to unblock (e.g., `127.0.0.1`).
5. Click the Unblock (trash) icon in the Actions column; confirm in the dialog.
6. Verify: navigate to `http://localhost:5050` — the shop catalog should load normally (HTTP 200) instead of the 403 Forbidden page.

**Detailed procedure — Admin: Add a Custom Detection Rule**

1. In the sidebar, click **Detection Rules**.
2. Click **+ Add Rule** in the top right.
3. Fill in Rule Name, select Attack Type from the dropdown, choose Severity, and enter the Regex Pattern.
4. Click **Create**. The rule appears in the table with `match_count = 0`.
5. Within 60 seconds (or immediately if the `rules_dirty` Redis flag is set), the Detection Engine reloads and includes the new pattern.

**Detailed procedure — Analyst: Triage a Critical Incident**

1. From the Dashboard, observe a spike in the Incident Timeline or a new entry in the last-24-hours card.
2. Click **Incidents** in the sidebar; apply filter Severity = Critical, Status = New.
3. Click the row to open Incident Detail.
4. Review Source IP, Attack Type, HTTP Path, Raw Payload, and Automated Actions.
5. Click **Generate AI Explanation**; review the Summary and Recommended Actions panels.
6. In the Investigation Notes section, type an observation and click **+ Add**.
7. Change the status dropdown from **New** to **Investigating** (or **Resolved** if the threat has been contained).

---

*Form 4 — Implementation | SME-Guard "Intelligent Web-SOC Platform with Automated Incident Response" | President University Capstone Design Project 2026 | Hardin Irfan (001202300066) · Nasywa Kamila (001202300211) · Zaidan Mahfudz Azzam Saidi (001202300144)*