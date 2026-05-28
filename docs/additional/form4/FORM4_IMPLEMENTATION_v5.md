# PART 4 — IMPLEMENTATION (v5, May 2026)

> **Form 4 — primary reference for the Word document.**  
> Cover: [FORM4_COVER.md](FORM4_COVER.md) · Screenshots: [FORM4_SCREENSHOTS.md](FORM4_SCREENSHOTS.md) · Changelog: [REVISION_LOG.md](REVISION_LOG.md)  
> **v5** = complete narrative from v3 translated to English + code snippets from v2 + Section B from v4 (already in English).

---

## Implementation vs Form 3 Deltas (May 2026)

| Item | Delivered Behavior | Evidence in Code |
|------|-------------------|-----------------|
| Sidebar **Ongoing** + **All Incidents** | Two routes, one `Incidents` component, different `mode` prop | `App.js` L40–41, `Layout.js` |
| Export CSV scope | `list_scope` param + different filename (`incidents-ongoing.csv` / `incidents-all.csv`) | `Incidents.js`, `incidents.py` |
| IP History drawer | Per-IP timeline, whitelist & block actions | `IPHistoryDrawer.js`, `ip_history.py` |
| Whitelist | Skip detection + excluded from JSON block list | `detection_engine.py` L76–82, `response_manager.py` L25 |
| Bulk resolve | Admin multi-select → resolved simultaneously | `Incidents.js` |
| Lab mode | UI rules only; OWASP baseline OFF | `settings_reader.py`, `_load_rules_from_db` |
| Phase 3 lab | Real CMD + unsafe upload via Docker env | `docker-compose.yml`, `vuln-web/config.py` |
| Live Traffic | Heuristic tag ≠ incident from Detection Engine | `traffic.py` (module docstring) |
| PATH_TRAVERSAL severity | **High** → temporary block (not permanent) | `RESPONSE_ACTIONS` in `detection_engine.py` |
| IP Management route | `/blocked-ips`, Blocked + Rate Limited tabs | `BlockedIPs.js` |
| Notifications | Bell toast + optional email/Telegram | `NotificationBell.js`, `notification_service.py` |

---

## A. DESIGNS IMPLEMENTATION

### 1. Functions, Procedures, and Classes

This section maps every subsystem from Form 3 to its concrete implementation in the Incidentra codebase. All file paths are relative to the repository root.

#### 1.1 Log Ingestion Layer — `log_parser.py`, `log_monitor.py`

The log ingestion layer (subsystem P1 of Form 3) is implemented in `backend/app/core/log_parser.py` and `backend/app/core/log_monitor.py`. Its responsibility is to transform raw web server log lines into structured records that can be analyzed by the Detection Engine.

**`parse_log_line()`** in `log_parser.py` is the entry point for a single log line. The function applies the `NGINX_PATTERN` regex to decode NCSA Combined Log Format fields: client IP, timestamp, HTTP method, request path, query string, HTTP version, status code, response size, referer, and User-Agent. Empty or non-conforming lines are returned as `None`. A second pattern, `POST_DATA_PATTERN`, detects the custom `POST_DATA:` suffix appended by vuln-web through `middleware/logging.py`. When this suffix is present, the POST body content (e.g., `username=admin' OR '1'='1' --` or `file=shell.php`) is merged into the `query` field of the returned dictionary.

```python
# backend/app/core/log_parser.py — L14–60

NGINX_PATTERN = re.compile(
    r'(?P<ip>[\d\.a-fA-F:]+)\s+-\s+-\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<path>[^\s"]*)\s+HTTP/[\d\.]+"  \s+'
    r'(?P<status>\d+)\s+(?P<size>\d+)\s+"[^"]*"\s+"(?P<ua>[^"]*)"'
)
POST_DATA_PATTERN = re.compile(r'\s+POST_DATA:(.+)$')

def parse_log_line(line: str) -> Optional[dict]:
    """Parse a single Nginx/Apache combined log line. Appends POST_DATA to query for detection."""
    line = line.strip()
    if not line:
        return None

    post_data = ''
    m = POST_DATA_PATTERN.search(line)
    if m:
        post_data = ' ' + m.group(1)
        line = line[: m.start()]    # strip POST_DATA suffix before parsing

    match = NGINX_PATTERN.match(line)
    if not match:
        return None

    full_path = match.group('path')
    parsed = urlparse(full_path)
    path = unquote_plus(parsed.path)
    query = unquote_plus(parsed.query)

    if post_data:
        query = (query + post_data).strip()   # merge POST body into query field

    return {
        'ip':          match.group('ip'),
        'method':      match.group('method'),
        'path':        path,
        'query':       query,          # includes POST_DATA if present
        'user_agent':  match.group('ua'),
        'status_code': int(match.group('status')),
        'raw':         line + (post_data if post_data else ''),
    }
```

**`LogTailer`** implements continuous monitoring using a polling loop equivalent to `tail -f`. On initialization, the file is opened at `WEB_SERVER_LOG_PATH`, seeked to end-of-file (so that historical entries are not reprocessed), and then new lines are read every polling interval (default 1 second). Inode tracking detects log rotation.

```python
# backend/app/core/log_parser.py — LogTailer.tail()

def tail(self) -> Generator[str, None, None]:
    """Yield new lines as they appear."""
    try:
        with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(0, 2)             # seek to end of file
            self._pos = f.tell()
            self._inode = self._get_inode()
    except FileNotFoundError:
        logger.warning(f"Log file not found: {self.filepath}")

    while True:
        current_inode = self._get_inode()
        if current_inode != self._inode:   # log rotation detected
            self._pos = 0
            self._inode = current_inode
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(self._pos)
                new_lines = f.readlines()
                self._pos = f.tell()
            for line in new_lines:
                yield line
        except FileNotFoundError:
            pass
        time.sleep(self.poll_interval)
```

**`log_monitor.py`** orchestrates the pipeline. `start_monitor()` launches a daemon `threading.Thread` that iterates over lines from `LogTailer` or `SimulatedLogFeeder`. For each line, `_process_log_line()` calls `parse_log_line()`, then `DetectionEngine.analyze()`. If a threat is detected, the monitor queries PostgreSQL for an existing incident with the same IP + attack_type within the last 5 minutes; only if none exists is a new `Incident` row inserted and `ResponseManager.respond()` called.

```python
# backend/app/core/log_monitor.py — _process_log_line() (summary)

def _process_log_line(line, engine, responder, db, redis_client, app) -> Optional[int]:
    """Parse one line, run detection, create incident if needed."""
    entry = parse_log_line(line)
    if not entry:
        return None

    threat = engine.analyze(entry)
    if not threat:
        return None

    # Deduplication: skip same IP+attack within 5 minutes
    dedup_window = datetime.utcnow() - timedelta(minutes=5)
    recent = Incident.query.filter(
        Incident.source_ip == threat['ip'],
        Incident.attack_type == threat['attack_type'],
        Incident.created_at >= dedup_window,
    ).first()
    if recent:
        return None

    incident = Incident(
        source_ip=threat['ip'],
        attack_type=threat['attack_type'],
        severity=sev_map.get(threat['severity'], SeverityLevel.MEDIUM),
        status=IncidentStatus.NEW,
        raw_payload=threat.get('raw_payload', ''),
        # ... other fields
    )
    db.session.add(incident)
    db.session.commit()

    responder.respond(threat, incident.id)
    return incident.id
```

#### 1.2 Detection Engine — `detection_engine.py`

The detection engine (subsystem P2 of Form 3) is implemented in `backend/app/core/detection_engine.py` as the `DetectionEngine` class, backed by `BruteForceTracker` and module-level dictionaries `DETECTION_PATTERNS`, `SEVERITY_WEIGHTS`, and `RESPONSE_ACTIONS`.

**Pattern sources.** Detection uses two sources that are merged at runtime: (1) OWASP built-in patterns in `DETECTION_PATTERNS`, and (2) administrator-defined rules stored in the PostgreSQL `detection_rules` table, loaded via `_load_rules_from_db()`.

**Supported attack types** (8 main types): `SQL_INJECTION` (critical), `XSS` (critical), `BRUTE_FORCE` (high, threshold-based), `PATH_TRAVERSAL` (high), `FILE_UPLOAD` (high), `COMMAND_INJECTION` (critical), `SCANNER` (medium), and `LFI_RFI` (critical).

```python
# backend/app/core/detection_engine.py — DETECTION_PATTERNS (excerpt)

DETECTION_PATTERNS = {
    'SQL_INJECTION': {
        'patterns': [
            r"(?i)(union\s+select|select\s+(\*|[\w]+\s*,\s*[\w\s,`]*)\s+from\s+\w|...)",
            r"(?i)(\bor\b\s+['"]?\d+['"]?\s*=\s*['"]?\d+['"]?)",
            r"(?i)(sleep\s*\(|benchmark\s*\(|waitfor\s+delay)",
            # ... 7 more patterns
        ],
        'severity': 'critical',
        'mitre': 'T1190 - Exploit Public-Facing Application',
    },
    'BRUTE_FORCE': {
        'patterns': [],           # threshold-based, not regex
        'severity': 'high',
        'mitre': 'T1110 - Brute Force',
        'threshold_based': True,
    },
    # ... XSS, PATH_TRAVERSAL, FILE_UPLOAD, COMMAND_INJECTION, SCANNER, LFI_RFI
}

SEVERITY_WEIGHTS = {'critical': 100, 'high': 70, 'medium': 40, 'low': 10}

RESPONSE_ACTIONS = {
    'low':      'log_and_monitor',
    'medium':   'rate_limit',
    'high':     'temporary_block',
    'critical': 'permanent_block',
}
```

**Lab mode and rule reload:** `_load_rules_from_db()` loads active rules from the DB. If lab mode is active (from Settings), the OWASP baseline is not appended — only rules created via the UI are used. `_maybe_reload_rules()` is executed on every `analyze()` call, and is forced immediately if the Redis key `rules_dirty` is set.

```python
# backend/app/core/detection_engine.py — _load_rules_from_db() and analyze() (summary)

def _load_rules_from_db(self):
    lab_only = is_lab_mode_ui_only()
    rules = DetectionRule.query.filter_by(is_active=True).all()
    compiled = {}
    for rule in rules:
        # compile each DB rule regex ...
        compiled[rule.attack_type].append({
            'pattern': re.compile(rule.pattern, re.IGNORECASE),
            'severity': rule.severity_level.value,
            'rule_id': rule.id,
        })

    if not lab_only:
        # Append OWASP baseline patterns (production default)
        for attack_type, info in DETECTION_PATTERNS.items():
            for raw in info['patterns']:
                compiled[attack_type].append({
                    'pattern': re.compile(raw, re.IGNORECASE),
                    'severity': info['severity'],
                    'rule_id': None,
                })
    else:
        logger.info("Detection lab mode: UI rules only (OWASP baseline disabled)")

def analyze(self, log_entry: dict) -> Optional[dict]:
    self._refresh_runtime_settings()
    self._maybe_reload_rules()

    ip = log_entry.get('ip', '')
    # Whitelist check — whitelisted IPs skip detection entirely
    if ip:
        if BlockedIP.query.filter_by(ip_address=ip, is_whitelist=True).first():
            return None

    # Build searchable string from method + path + query (incl. POST_DATA) + user_agent
    searchable = f"{method} {path} {query} {user_agent}"

    threats = []
    for attack_type, patterns in self._get_compiled().items():
        for p in patterns:
            pattern = p['pattern'] if isinstance(p, dict) else p
            match = pattern.search(searchable)
            if match:
                threats.append({'attack_type': attack_type, 'severity': ..., ...})
                break

    # Brute force: threshold-based for POST to login paths
    if is_login_path and is_post and self._brute_force_enabled():
        if self.bf_tracker.is_brute_force(ip, path):
            threats.append({'attack_type': 'BRUTE_FORCE', ...})

    if not threats:
        return None

    # Return highest-severity threat
    primary = max(threats, key=lambda t: t['score'])
    return {
        'ip': ip, 'attack_type': primary['attack_type'],
        'severity': primary['severity'],
        'recommended_action': RESPONSE_ACTIONS[primary['severity']],
        # ...
    }
```

**`BruteForceTracker`** counts failed login POSTs per IP within a 60-second sliding window (default threshold 10). It uses Redis sorted sets if available, and falls back to an in-memory deque otherwise. It emits exactly one `BRUTE_FORCE` threat the first time the threshold is crossed.

```python
# backend/app/core/detection_engine.py — BruteForceTracker

class BruteForceTracker:
    def record_attempt(self, ip: str, path: str) -> int:
        now = time.time()
        key = f"bf:{ip}:{path}"
        if self.redis:
            pipe = self.redis.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - self.window)   # remove old entries
            pipe.zcard(key)
            pipe.expire(key, self.window * 2)
            results = pipe.execute()
            return results[2]    # count within window
        # fallback: in-memory deque
        dq = self._local[key]
        dq.append(now)
        while dq and dq[0] < now - self.window:
            dq.popleft()
        return len(dq)

    def is_brute_force(self, ip: str, path: str) -> bool:
        """Fire only when threshold is first crossed (== not >=)."""
        return self.record_attempt(ip, path) == self.threshold
```

#### 1.3 Automated Response Manager — `response_manager.py`

`backend/app/core/response_manager.py` implements the `ResponseManager` class, which translates threat severity into concrete enforcement actions.

The `respond()` method applies the following severity-to-action mapping:

| Severity | Action | Enforcement Mechanism | Duration |
|----------|--------|----------------------|----------|
| Low | `log_and_monitor` | `IncidentLog` record in PostgreSQL; Redis key `action:{ip}` | Permanent record |
| Medium | `rate_limit` | Entry in `rate_limited.json`; Redis key `ratelimit:{ip}` with TTL | Per `RATE_LIMIT_WINDOW` (default 60 s) |
| High | `temporary_block` | Entry in `blocked_ips.json`; `BlockedIP` DB record with `expire_time` | 24 hours (configurable `TEMP_BLOCK_DURATION`) |
| Critical | `permanent_block` | Entry in `blocked_ips.json`; `BlockedIP` DB record `block_type='permanent'` | Never expires |

```python
# backend/app/core/response_manager.py — respond() and _block_ip()

def respond(self, threat: dict, incident_id: int) -> dict:
    severity = threat.get('severity', 'low')
    action = threat.get('recommended_action', 'log_and_monitor')

    if action == 'log_and_monitor':
        self._log_to_redis(ip, 'monitor')

    elif action == 'rate_limit':
        self._apply_rate_limit(ip)
        _write_rate_limited_json(ip, add=True)

    elif action == 'temporary_block':
        ok = self._block_ip(ip, permanent=False,
                            reason=f"Auto-blocked: {threat.get('attack_type')}")
        if ok:
            _write_blocked_ips_json()       # update JSON for vuln-web enforcement
            self._notify_async(incident_id, 'high')

    elif action == 'permanent_block':
        ok = self._block_ip(ip, permanent=True,
                            reason=f"Auto-blocked (CRITICAL): {threat.get('attack_type')}")
        if ok:
            _write_blocked_ips_json()
            self._notify_async(incident_id, 'critical')

    self._save_incident_log(incident_id, result)
    return result

def _block_ip(self, ip: str, permanent: bool, reason: str) -> bool:
    expire_time = None if permanent else (
        datetime.utcnow() + timedelta(seconds=self.temp_block_duration)
    )
    existing = BlockedIP.query.filter_by(ip_address=ip).first()
    if existing:
        existing.is_whitelist = False      # clear whitelist flag if previously trusted
        existing.reason = reason
        existing.block_type = 'permanent' if permanent else 'temporary'
        existing.expire_time = expire_time
        existing.incident_count = (existing.incident_count or 0) + 1
    else:
        blocked = BlockedIP(ip_address=ip, reason=reason,
                            block_type='permanent' if permanent else 'temporary',
                            expire_time=expire_time, is_whitelist=False)
        self.db.session.add(blocked)
    self.db.session.commit()
    return True
```

**`_write_blocked_ips_json()`** queries all active `BlockedIP` records (non-whitelist), filters out temporary blocks that have already expired, and writes the result to `blocked_ips.json`. This file is read by `vuln-web/middleware/security.py` on every incoming HTTP request via the `before_request` hook, causing blocked IPs to receive an HTTP 403 response without any server restart or direct database access from vuln-web.

```python
# backend/app/core/response_manager.py — _write_blocked_ips_json()

def _write_blocked_ips_json():
    now = datetime.utcnow()
    blocked = BlockedIP.query.filter_by(is_whitelist=False).all()
    active_ips = []
    for b in blocked:
        if b.block_type == 'permanent':
            active_ips.append(b.ip_address)
        elif b.expire_time and b.expire_time > now:
            active_ips.append(b.ip_address)

    data = {"blocked": active_ips, "updated_at": now.isoformat()}
    with open(BLOCKED_IPS_JSON, 'w') as f:
        json.dump(data, f)
```

#### 1.4 REST API Layer — `backend/app/api/`

The backend API is a Flask application defined in `backend/app/__init__.py`. API endpoints are organized into blueprints in `backend/app/api/`:

| Blueprint | File | Responsibility |
|-----------|------|---------------|
| `auth` | `auth.py` | Login (`POST /api/auth/login`), token verification, logout |
| `incidents` | `incidents.py` | List, retrieve, update, export incidents; trigger AI explanation; simulate attack; bulk status update |
| `rules` | `rules.py` | CRUD for `detection_rules`; sets Redis `rules_dirty` flag on write |
| `blocked_ips` | `blocked_ips.py` | List, add, update, delete (unblock), whitelist upsert; calls `_write_blocked_ips_json()` |
| `rate_limited` | `rate_limited.py` | List, extend, and clear rate-limited IPs; updates `rate_limited.json` and Redis |
| `dashboard` | `dashboard.py` | Aggregate statistics: total incidents, 24-hour count, blocked IPs, MTTR, severity breakdown, 7-day timeline |
| `traffic` | `traffic.py` | Recently parsed log entries for Live Traffic (display-only, not detection) |
| `settings` | `settings.py` | Read/write `AppSetting` key-value pairs for API keys and thresholds |
| `audit` | `audit.py` | Paginated `AuditLog` query |
| `chatbot` | `chatbot.py` | AI chat assistant (Groq) for general security questions |
| `ip_history` | `ip_history.py` | IP History drawer: per-IP timeline data |
| `notifications` | `notifications.py` | New notifications, mark-read |

All protected endpoints validate a Bearer JWT using the `verify_token()` function in `auth_middleware.py`, registered as a `before_request` hook. Tokens are signed with HS256 using the `SECRET_KEY` environment variable and have a 24-hour expiry.

**Scope filter (Ongoing vs All Incidents):**

```python
# backend/app/api/incidents.py — list endpoint (summary)

list_scope = (args.get('list_scope') or '').strip().lower()
if list_scope == 'ongoing' and not status and not status_in:
    query = query.filter(
        Incident.status.in_([IncidentStatus.NEW, IncidentStatus.INVESTIGATING])
    )
```

**Whitelist upsert (no 409 when marking a trusted IP):**

```python
# backend/app/api/blocked_ips.py — whitelist upsert

if existing and is_whitelist:
    existing.is_whitelist = True
    existing.reason = data.get('reason', 'Whitelisted — trusted IP')
    existing.block_type = 'permanent'
    existing.expire_time = None
    db.session.commit()
```

#### 1.5 AI and External Services — `backend/app/services/`

**`ai_service.py`** implements `build_prompt()`, which constructs a structured natural-language prompt from incident attributes, and `_call_groq_with_fallback()`, which attempts the Groq Cloud API using a chain of four models in sequence:

1. `llama-3.3-70b-versatile`
2. `llama-3.1-8b-instant`
3. `meta-llama/llama-4-scout-17b-16e-instruct`
4. `meta-llama/llama-guard-4-12b`

If all four models fail (HTTP 400/404/422 or network error), the system returns a curated static explanation so that every incident always has a human-readable analysis. The `model_used` field in `IncidentExplanation` records which model or the literal string `"fallback-static"` generated the explanation.

**`threat_intel_service.py`** queries the AbuseIPDB v2 API with the incident's source IP to retrieve an `abuse_confidence_score` (0–100), stored on the `Incident` record and displayed in the incident detail panel.

**`notification_service.py`** sends alerts via SMTP email or Telegram Bot API. Notification delivery runs in a separate daemon thread through `_notify_async()` in ResponseManager — the thread approach is more reliable than Celery `.delay()` because it works without requiring a running worker container.

#### 1.6 vuln-web Target Application — `vuln-web/`

The deliberately vulnerable Flask shop (`vuln-web/`) serves as the monitored target. It consists of route blueprints in `vuln-web/routes/`:

| Blueprint | File | Exposed Vulnerability |
|-----------|------|-----------------------|
| `main` | `main.py` | Home, product catalog |
| `auth` | `auth.py` | Login with intentionally weak credentials |
| `shop` | `shop.py` | Product listing, shopping cart |
| `profile` | `profile.py` | Profile update with unrestricted `avatar` field (CTF vector) |
| `files` | `files.py` | File upload and download; path traversal if `VULN_UNSAFE_UPLOAD=1` |
| `cmd` | `cmd.py` | Simulated or real command execution if `VULN_UNSAFE_CMD=1` |
| `api` | `api.py` | AJAX endpoints for the cart |

`middleware/security.py` registers `enforce_security()` as a `before_request` hook that reads `blocked_ips.json` and `rate_limited.json` on every request. `middleware/logging.py` registers an `after_request` hook that writes one Combined Log Format line per request to `logs/access.log`, appending the `POST_DATA:` suffix for login and file upload endpoints.

**Phase 3 flags** (read by `vuln-web/config.py` via `_env_bool()`):

```python
# docker-compose.yml — vuln_web service environment

environment:
  VULN_UNSAFE_CMD: "1"     # real shell execution via subprocess.run(shell=True)
  VULN_UNSAFE_UPLOAD: "1"  # raw client-supplied filename (path traversal risk)
```

Changing either flag requires a vuln-web process restart: `docker compose restart vuln_web`.

#### 1.7 SOC Frontend — `frontend/src/`

The React 18 frontend (`frontend/`) is structured around page-level components in `frontend/src/pages/`. Routing is defined in `frontend/src/App.js`:

```jsx
// frontend/src/App.js — L39–48

<Routes>
  <Route path="/" element={<Dashboard />} />
  <Route path="/incidents/all" element={<Incidents key="incidents-all" mode="all" />} />
  <Route path="/incidents" element={<Incidents key="incidents-ongoing" mode="ongoing" />} />
  <Route path="/incidents/:id" element={<IncidentDetail />} />
  <Route path="/blocked-ips" element={<BlockedIPs />} />
  <Route path="/rules" element={<DetectionRules />} />
  <Route path="/traffic" element={<LiveTraffic />} />
  <Route path="/settings" element={<Settings />} />
  <Route path="/audit" element={<AuditLog />} />
</Routes>
<ChatbotWidget />         {/* draggable FAB, always present */}
```

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `Dashboard` | Metric cards, incident timeline, severity chart |
| `/incidents` | `Incidents` (mode=ongoing) | Active incident list (new + investigating) |
| `/incidents/all` | `Incidents` (mode=all) | Full incident history including resolved |
| `/incidents/:id` | `IncidentDetail` | Detail, AI explanation, notes, status |
| `/blocked-ips` | `BlockedIPs` | IP Management — Blocked and Rate Limited tabs |
| `/rules` | `DetectionRules` | Rules CRUD + regex pattern sandbox test |
| `/traffic` | `LiveTraffic` | Real-time log stream (3-second poll) |
| `/settings` | `Settings` | API keys, lab mode, thresholds |
| `/audit` | `AuditLog` | Admin action history |

**Global widgets:** `NotificationBell` (header, new incident badge), `ChatbotWidget` (draggable FAB, Groq), `SessionTimeoutWarning` (idle logout dialog).

**Export CSV per scope:**

```javascript
// frontend/src/pages/Incidents.js — handleExportCsv()

const handleExportCsv = async () => {
    const params = { list_scope: isAllMode ? 'all' : 'ongoing' };
    // ... apply filters
    a.download = isAllMode ? 'incidents-all.csv' : 'incidents-ongoing.csv';
};
```

All API calls are made through `frontend/src/services/api.js` using Axios with the JWT stored in `localStorage` under the key `incidentra_token`. The UI supports language switching between English and Indonesian via `react-i18next`.

---

### 2. Database Implementation

Incidentra uses PostgreSQL 15 as its primary relational store, accessed via SQLAlchemy 2.x ORM. All models are defined in `backend/app/models/__init__.py`. The schema is initialized by `db.create_all()` and seeded by `seed_all()` in `backend/app/utils/seeder.py`, which runs automatically via `backend/docker_entrypoint.sh` on first container start. The default seed creates one `admin` user and 11 active detection rules covering all supported OWASP attack categories.

| Model Class | Table | Columns |
|-------------|-------|---------|
| `User` | `users` | `id`, `username`, `email`, `password_hash` (PBKDF2-SHA256), `role`, `created_at`, `is_active` |
| `Incident` | `incidents` | `id`, `created_at`, `updated_at`, `source_ip`, `attack_type`, `severity` (enum), `status` (enum), `raw_payload`, `request_path`, `request_method`, `user_agent`, `response_code`, `rule_id` (FK→detection_rules), `assigned_to` (FK→users), `resolved_at`, `country_code`, `abuse_confidence_score` |
| `DetectionRule` | `detection_rules` | `id`, `rule_name`, `attack_type`, `pattern`, `severity_level` (enum), `description`, `is_active`, `created_at`, `updated_at`, `match_count` |
| `BlockedIP` | `blocked_ips` | `id`, `ip_address`, `reason`, `block_type` (`permanent`/`temporary`), `block_time`, `expire_time`, `incident_count`, **`is_whitelist`**, `created_by` |
| `IncidentLog` | `incident_logs` | `id`, `incident_id` (FK→incidents), `action_taken`, `action_detail`, `action_time`, `performed_by` |
| `IncidentExplanation` | `incident_explanations` | `id`, `incident_id` (FK→incidents), `ai_summary`, `threat_explanation`, `recommended_actions`, `mitre_technique`, `generated_at`, `model_used` |
| `IncidentNote` | `incident_notes` | `id`, `incident_id` (FK→incidents), `note_content`, `created_at`, `created_by` |
| `AppSetting` | `app_settings` | `id`, `key`, `value` (API keys, SMTP config, thresholds), `updated_at` |
| `AuditLog` | `audit_logs` | `id`, `timestamp`, `user_id` (FK→users), `username`, `action`, `resource_type`, `resource_id`, `details`, `ip_address` |

**Outside PostgreSQL:** Rate-limiting state is stored outside PostgreSQL for performance. The file `rate_limited.json` maintains the set of rate-limited IPs and per-IP policy overrides. Redis stores `ratelimit:{ip}` keys with TTL for enforcement expiry. Both are accessed through API endpoints, not direct ORM queries.

**Dual-write enforcement:** `BlockedIP` DB + `blocked_ips.json` for vuln-web enforcement. vuln-web has **no** PostgreSQL connection; enforcement is received exclusively via the JSON files on the Docker named volume `vuln_logs`.

---

### 3. User Interface Implementation

The SOC Dashboard is a React 18 single-page application built with Material UI (MUI) and served by Nginx on port 3000. The dark theme (`frontend/src/theme/index.js`) is optimized for extended use in security operations environments.

**Dashboard** displays four metric cards: Total Incidents (all time), Detections in Last 24 Hours, Blocked IP Addresses (active blocks from the `BlockedIP` table), and MTTR (Mean Time to Resolution). A collapsible system status banner, driven by `last_log_received_at` from the log monitor, warns the operator when no log lines have been received in the last 60 seconds. The Incident Timeline (Chart.js line chart, 7-day window) and By Severity donut chart auto-refresh every 30 seconds.

**Incidents** renders a filterable, paginated table. Filter dropdowns cover severity and status. A full-text search field covers IP address, attack type, and path. The `Incidents` component is used twice with a different `mode` prop (`"ongoing"` and `"all"`), so `/incidents` shows only new+investigating, while `/incidents/all` shows the full history including resolved incidents.

**Incident Detail** (`/incidents/:id`) has a two-panel layout. The left panel displays all technical attributes. The right panel has two states: before AI explanation generation it shows a "Generate AI Explanation" call-to-action button; after generation it shows four color-coded panels (Summary, Why It's Dangerous, Recommended Actions, MITRE ATT&CK mapping) and a model name badge. The Automated Actions timeline, populated from `IncidentLog` records, and the Investigation Notes section (append-only, timestamped, stored in `IncidentNote`) are displayed below both panels.

**IP Management** (`/blocked-ips`) displays two tabs. The Blocked tab lists `BlockedIP` records. The Rate Limited tab reads `rate_limited.json` via the `/api/rate-limited/` endpoint.

**Detection Rules** lists all `DetectionRule` records with columns for name, attack type badge, severity badge, regex pattern excerpt, match count, active toggle, and edit/delete actions.

**Live Traffic** auto-refreshes every 3 seconds via HTTP polling of `/api/traffic/`. Each row displays timestamp, IP, HTTP method, path, query/payload excerpt, HTTP status, and a classification tag (Attack/Suspicious/Blocked/Normal). An **Attack** tag with HTTP status **200** means the request reached the application before the Detection Engine processed the log line — no block has been applied yet. Only subsequent requests from that IP, after the incident is created and `blocked_ips.json` is updated, will receive a **Blocked** tag with HTTP 403.

---

### 4. Hardware Implementation

**Not applicable.** Incidentra is a software-only system. No microcontrollers, IoT sensors, or dedicated hardware appliances are required. The minimum recommended specification for a demonstration environment is a laptop or PC with at least 8 GB RAM and Docker Desktop installed, or a Linux VPS with 2 vCPU and 4 GB RAM. All processing, storage, and network communication occur inside Docker containers on the host machine.

---

### 5. Integration Among Modules

The complete integration flow is illustrated below. The Docker named volume `vuln_logs` is the sole shared state between the monitored application and the detection backend; vuln-web has no direct database connection.

```
Browser → vuln-web (:5050)
              │
              ├─ access.log (Combined Log Format + POST_DATA suffix)
              │           ↓
              │   Backend LogTailer (thread)
              │           ↓
              │   log_parser.parse_log_line()
              │           ↓
              │   DetectionEngine.analyze()
              │           ↓
              │   PostgreSQL → Incident record
              │           ↓
              │   ResponseManager.respond()
              │           ↓
              ├─ blocked_ips.json  ←── (Docker volume vuln_logs)
              └─ rate_limited.json ←── (Docker volume vuln_logs)
                      ↑
              vuln-web middleware/security.py (before_request)
              → HTTP 403 (blocked) / HTTP 429 (rate limited)

Frontend (:3000) ← REST API (:5000) ← PostgreSQL + Redis
```

Four key integration points:

1. **vuln-web has no PostgreSQL connection.** Enforcement is received exclusively through the two JSON files written by the Response Manager.
2. **FILE_UPLOAD detection mechanism.** The `POST_DATA:file=filename` suffix in the access log enables the Detection Engine to classify malicious file uploads without reading the uploaded file from disk — dangerous extensions are matched directly against the log line.
3. **Unblock Redis waiver.** When an administrator unblocks an IP via the SOC dashboard, the `blocked_ips.py` API calls `_write_blocked_ips_json()` to remove the IP from the enforcement file, and also sets the Redis key `unblocked:{ip}` (TTL 10 minutes) to temporarily bypass deduplication so the IP's next legitimate requests are not re-detected.
4. **60-second rule reload.** The Detection Engine rule reload cycle (triggered by the Redis `rules_dirty` flag) allows administrators to add or modify detection rules through the SOC dashboard and have them take effect within one minute without restarting any service.

---

## B. PRODUCT DISPLAY

### 1. Software Product Display

The Incidentra system consists of two browser-accessible components: the SOC Dashboard (React, port 3000) and the vuln-web target shop (Flask, port 5050).

**Login Page.** Centered card on a dark background with the Incidentra shield logo, "Intelligent Web-SOC Platform" subtitle, username and password fields, and a "Sign In" button. On successful authentication the Flask `/api/auth/login` endpoint issues a JWT (HS256, 24-hour expiry). A hint displays the default credentials to assist thesis defense.

[SCREENSHOT: Figure 1 — Login Page with default credentials hint for demo.]

**SOC Dashboard.** Four KPI metric cards: Total Incidents, Detections in Last 24 Hours, Blocked IPs, and MTTR. A system status banner dynamically changes between "All Systems Normal" and a warning when the log monitor has received no entries in the last 60 seconds. The Incident Timeline uses Chart.js to render a seven-day bar/line chart, and the By Severity donut chart shows the breakdown across low, medium, high, and critical incidents.

[SCREENSHOT: Figure 2 — SOC Dashboard with KPI cards, system status banner, and charts.]

**Ongoing Incidents.** The incidents table supports filtering by severity and status, full-text search across IP, attack type, and path, and pagination. Each row shows a colour-coded attack type badge and severity badge. A lock icon in the Response column indicates an automated IP block. "Simulate Attack" and "Export CSV" buttons appear in the header.

[SCREENSHOT: Figure 3 — Ongoing Incidents page.]

**Ongoing Incidents – Incident Status update.** The status of each incident can be changed directly via the list table displayed on the page.

[SCREENSHOT: Figure 3b — Ongoing Incidents status update.]

**Ongoing Incidents – Simulate Attack.** There are two types of incident injection: direct database injection for UI testing, and injection through logs that are being generated and recorded by the web application as traffic.

[SCREENSHOT: Figure 3c — Ongoing Incidents — Incident injection 2 modes; database and logs.]

**Ongoing Incidents – Pop Up and In App Notification.** There are two types of pop-ups in the app: pop-ups that appear when an incident is created, and pop-ups that appear alongside in-app notifications.

[SCREENSHOT: Figure 3d — Ongoing Incidents – Pop up & In app notification]

**Ongoing Incidents – Sorting and Filtering.** There are options for sorting and filtering, such as by status, by severity, by attack type, and by source IP. There is also a search field for more specific searches.

[SCREENSHOT: Figure 3e — Ongoing Incidents sorting and filtering]

**Ongoing Incidents - IP History Drawer.** There is a drawer that appears when clicking on an IP address in the Incidents tab. This drawer displays details about the IP address, including pattern analysis, the total number of incidents generated by this IP address, the daily frequency, the types of attacks frequently carried out, and incidents recently created by it.

[SCREENSHOT: Figure 3f — Ongoing incidents IP history drawer]

**Ongoing Incidents – Export as CSV.** Export button on the navigation bar to export data to CSV for a specific time range.

[SCREENSHOT: Figure 3g — Ongoing incidents export incidents]

**All Incidents.** The difference between this tab and the Ongoing Incident tab is that this tab displays all incidents and their statuses, particularly those that have been resolved or marked as false positives.

[SCREENSHOT: Figure 3h — All incidents page.]

**Incident Detail — Before AI Analysis.** The detail page shows the full technical breakdown on the left (source IP, AbuseIPDB score, attack type, severity, HTTP method, path, response code, country, timestamps) and the "AI Explanation Not Generated" placeholder with a "Generate AI Explanation" call-to-action on the right. The Automated Actions section below shows what the system executed automatically at detection time. The Investigation Notes section is available for analyst annotations.

[SCREENSHOT: Figure 4 — Incident Detail before AI generation, showing HTTP 200 response code and automated permanent block action in the Automated Actions log.]

**Incident Detail — After AI Analysis.** After clicking "Generate AI Explanation," the right panel is replaced by the AI-Powered Analysis section containing four color-coded blocks: Summary, Why It's Dangerous, Recommended Actions, and MITRE ATT&CK mapping. The model name badge (e.g., `llama-3.3-70b-versatile`) appears in the panel header.

[SCREENSHOT: Figure 5 — Incident Detail after Groq LLM analysis with four color-coded explanation panels and model badge.]

**IP Management — Blocked Tab.** Lists all `BlockedIP` records with IP address, reason, block type (permanent or temporary), blocked-at timestamp, expiry time, incident count, and an unblock button. A "+ Block IP" button opens a dialog for manual IP blocking.

[SCREENSHOT: Figure 6 — IP Management, Blocked tab with one permanent block entry for a SQL injection source.]

**IP Management — Add Block IP.** The "+ Block IP" button allows users to manually block an IP address. Fields include IP address, reason, and block duration (permanent or temporary from 1 hour to 7 days).

[SCREENSHOT: Figure 6b — IP Management, add block IP]

**IP Management — Update and Delete Blocked IP.** Users can edit blocked IP addresses (reason and block type) and unblock them via a dedicated button.

[SCREENSHOT: Figure 6c — IP Management, update & unblock]

**IP Management — Rate Limited Tab.** Reads from `rate_limited.json` via the API and displays each rate-limited IP with its per-IP policy and enforcement TTL from Redis. Extend and Clear action buttons are provided per row.

[SCREENSHOT: Figure 7 — IP Management, Rate Limited tab with rate-limited IP, max-requests and window policy columns, and action buttons.]

**Detection Rules.** Lists each `DetectionRule` record with name, attack type badge, severity badge, pattern excerpt, match count, active toggle, and edit/delete actions. Toggling a rule sets `is_active` in PostgreSQL and writes the Redis `rules_dirty` flag.

[SCREENSHOT: Figure 8 — Detection Rules page with active & inactive rules, match counters, and active toggles.]

**Detection Rules – Update and Delete.** Users can edit existing detection rules in the list and can delete or disable those rules.

[SCREENSHOT: Figure 8b — Detection Rules – Edit rule card, Active toggles, and delete rules]

**Create Detection Rule.** The "+ Add Rule" modal collects Rule Name, Attack Type (dropdown), Severity Level, Regex Pattern, and Description. Upon submission the rule is saved to `detection_rules` and `rules_dirty` is set.

[SCREENSHOT: Figure 8c — Detection Rules – Create detection rule]

**Detection Rules – Rule Testing Sandbox.** The sandbox allows users to test whether a regex payload matches; two modes available: payload test and test log line.

[SCREENSHOT: Figure 8d — Detection Rules - Rule Testing Sandbox]

**Live Traffic.** Displays parsed access log entries refreshed every three seconds. Tag colour coding: Attack (red), Suspicious (amber), Blocked (purple), Normal (green). An "Attack" tag with HTTP status 200 means the request reached the application before the Detection Engine processed the log line — no block has been applied yet.

[SCREENSHOT: Figure 10 — Live Traffic showing Attack (200) tag for GET /cmd?cmd=;whoami, then Blocked (403) tag for a subsequent request from the same IP after incident creation.]

**Live Traffic – Hide Static Assets checkbox.** Checkbox to display or hide static assets such as CSS or JavaScript.

[SCREENSHOT: Figure 10b — Live Traffic hide or display static assets.]

**Settings — Appearance & Detection.** Configurable options include Dark/Light mode, language (English/Indonesian), in-app notifications toggle, Detection Lab Mode toggle, and Detection Thresholds (brute-force threshold, temporary block duration, rate limit window).

[SCREENSHOT: Figure 11 — Settings page displaying Appearance, In-app alerts, Detection Lab Mode, and Detection Thresholds sections.]

**Settings — API Keys & Integrations.** Stores external integration keys in the `AppSetting` table: Groq API key and model, AbuseIPDB API key, SMTP host/port/credentials/recipient, and Telegram bot token and chat ID. Keys are masked (asterisks) in the UI.

[SCREENSHOT: Figure 11b — Settings page showing AI Assistant (Groq), Threat Intelligence (AbuseIPDB), Email Notifications, and Detection Thresholds sections.]

**Audit Log.** Records all audit logs generated by users such as the Admin. Activity logs include changing incident status, creating detection rules, unblocking IP addresses, and so on.

[SCREENSHOT: Figure 12 — Audit Log Page displaying all audit log records of user activities.]

**Chatbot.** The Chatbot panel answers cybersecurity questions ranging from basic inquiries to assisting with tasks like creating a regex detection rule. Uses the same Groq model and fallback chain as the AI Incident Analyst.

[SCREENSHOT: Figure 13 — Chatbot]

---

### 2. Hardware Product Display

**Not applicable.** Incidentra is a software-only system. No microcontrollers, IoT sensors, or dedicated hardware appliances are required. The minimum recommended specification for a demonstration environment is a laptop or PC with at least 8 GB RAM and Docker Desktop installed, or a Linux VPS with 2 vCPU and 4 GB RAM. All processing, storage, and network communication occur inside Docker containers on the host machine.

---

## C. COMPONENT COST ANALYSIS

All software components used by Incidentra are open-source and carry no licensing cost. The table below presents the cost structure for two deployment scenarios: local demonstration (Docker Compose on a developer laptop) and an optional production deployment on a VPS.

| No. | Item | Unit | Price per Unit (IDR) | Total (IDR) |
|-----|------|------|----------------------|-------------|
| 1 | Ubuntu Linux | 1 | Rp 0 | Rp 0 |
| 2 | Docker / Docker Compose | 1 | Rp 0 | Rp 0 |
| 3 | PostgreSQL 15 | 1 | Rp 0 | Rp 0 |
| 4 | Redis 7 | 1 | Rp 0 | Rp 0 |
| 5 | Flask / Python libraries (PyPI) | 1 stack | Rp 0 | Rp 0 |
| 6 | React / Node.js / MUI (npm) | 1 stack | Rp 0 | Rp 0 |
| 7 | Groq Cloud API (free tier) | 1 account | Rp 0 | Rp 0 |
| 8 | AbuseIPDB API (free tier, 1,000 checks/day) | 1 account | Rp 0 | Rp 0 |
| 9 | Gmail SMTP (app password, low volume) | 1 | Rp 0 | Rp 0 |
| 10 | Developer laptop (existing device) | 1 | Rp 0 | Rp 0 |
| 11 | VPS 2 vCPU / 4 GB RAM *(optional, production)* | 1 year | ~Rp 1.500.000 | ~Rp 1.500.000 |
| 12 | Domain `.id` *(optional)* | 1 year | ~Rp 150.000 | ~Rp 150.000 |
| | **Total (local demo)** | | | **Rp 0** |
| | **Total (optional VPS, year 1)** | | | **~Rp 1.650.000** |

The zero-cost local deployment makes Incidentra immediately accessible to small and medium enterprises without requiring any IT budget. The optional VPS deployment provides persistent availability for monitoring a production web server at a cost of approximately Rp 1.5–1.6 million per year — significantly below any commercial SIEM or WAF solution.

---

## D. FUNCTIONAL TESTING

Testing was conducted against the Docker Compose deployment (six services: `postgres`, `redis`, `vuln_web`, `backend`, `celery_worker`, `frontend`). The SOC Dashboard was accessed at `http://localhost:3000`; the vuln-web target at `http://localhost:5050`.

### D.1 — Authentication

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|-----|----------|----------------------|-----------------|---------------|
| 1 | Successful login | username `admin`, password `Admin@Incidentra2026!`; click Sign In | JWT issued; redirect to Dashboard; all sidebar items visible | |
| 2 | Wrong credentials | username `admin`, password `wrongpass`; click Sign In | HTTP 401 "Invalid credentials" displayed; user remains on login page | |
| 3 | No token (API) | `GET http://localhost:5000/api/incidents` without Authorization header | HTTP 401 "Authorization required"; no data returned | |

### D.2 — SQL Injection Detection

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Login POST SQLi (thesis defense demo) | `http://localhost:5050/login` — username `admin' OR '1'='1' --`, any password | Incident: `SQL_INJECTION`, `severity=critical`; `POST_DATA` in raw payload; IP in `blocked_ips.json` | |
| 2 | Automatic block enforcement | After step 1, open `http://localhost:5050/` from the same IP | HTTP 403 Forbidden (Incidentra branding); Live Traffic shows **Blocked** on the next row | |
| 3 | Reflected SQLi via search | `http://localhost:5050/search?q=admin'+OR+'1'='1'--` | Incident: `SQL_INJECTION`, critical | |
| 4 | Blind time-based SQLi | `http://localhost:5050/search?q=1' AND SLEEP(5)--` | Incident: `SQL_INJECTION` if pattern matches | |

### D.3 — XSS Detection

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Reflected XSS via script tag | `http://localhost:5050/profile?name=<script>alert(document.cookie)</script>` | Incident: `attack_type=XSS`, `severity=critical`; IP permanently blocked | |
| 2 | XSS event handler | `http://localhost:5050/search?q=<img onerror=alert(1) src=x>` | Incident: `attack_type=XSS`, `severity=critical` | |
| 3 | Normal query | `http://localhost:5050/search?q=laptop` | No incident; entry appears as "Normal" in Live Traffic | |

### D.4 — Path Traversal / LFI Detection

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Classic path traversal | `http://localhost:5050/files?file=../../etc/passwd` | Incident: `attack_type=PATH_TRAVERSAL`, `severity=high`; IP **temporary** block (24 hours) | |
| 2 | Enforcement file targeting | `http://localhost:5050/files?file=E:/path/blocked_ips.json` | Incident: `attack_type=PATH_TRAVERSAL` | |
| 3 | Normal file access | `http://localhost:5050/files?file=readme.txt` | No incident; Normal entry in Live Traffic | |
| 4 | PHP wrapper (LFI) | `http://localhost:5050/files?file=php://filter/convert.base64-encode/resource=index` | Incident: `attack_type=LFI_RFI`, `severity=critical`, permanent block | |

### D.5 — File Upload Detection

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Safe upload — no incident | POST `/files` via form upload; file: `notes.txt` | Request logged in `access.log`; appears in Live Traffic as Normal; **no** FILE_UPLOAD incident | |
| 2 | Dangerous upload — single extension | POST `/files` via form upload; file: `shell.php` | Log contains `POST_DATA:file=shell.php`; incident: `attack_type=FILE_UPLOAD`, `severity=high`; IP temporary block | |
| 3 | Dangerous upload — double extension | POST `/files` via form upload; file: `image.php.jpg` | FILE_UPLOAD incident (matches double extension pattern) | |
| 4 | Avatar CTF vector | POST `/profile` with field `avatar=shell.php` | Log contains `POST_DATA:avatar=shell.php`; FILE_UPLOAD incident created | |

### D.6 — Command Injection Detection

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Metacharacter payload | `http://localhost:5050/cmd?cmd=;whoami` | Incident: `attack_type=COMMAND_INJECTION`, `severity=critical`; IP permanently blocked | |
| 2 | Plain keyword payload | `http://localhost:5050/cmd?cmd=whoami` | Incident: `attack_type=COMMAND_INJECTION`, `severity=critical` (pattern `cmd=whoami`) | |
| 3 | Phase 3 OFF (default) | `VULN_UNSAFE_CMD` not set; `/cmd?cmd=whoami` | vuln-web displays `[Simulated] Would execute: whoami`; no real shell execution | |
| 4 | Phase 3 ON | `VULN_UNSAFE_CMD=1`; restart `vuln_web`; `/cmd?cmd=whoami` | Real shell output; red warning banner on all pages; SOC still creates COMMAND_INJECTION incident | |

### D.7 — Brute Force Detection

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Threshold-based detection | 10+ POST requests to `/login` with wrong passwords within 60 seconds | BRUTE_FORCE incident created on the 10th attempt (`severity=high`); IP rate-limited; subsequent requests receive HTTP 429 | |

### D.8 — Scanner Detection

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Scanner User-Agent | `curl -A "Nikto/2.1.6" http://localhost:5050/` | Incident: `SCANNER`, medium; IP in the **Rate Limited** tab (not permanent block) | |
| 2 | Rapid requests while rate-limited | 10+ requests/minute from the same IP after scanner detection | HTTP **429** from vuln-web | |

### D.9 — IP Block / Unblock / Whitelist

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Auto block (critical attack) | Any critical attack | IP in `blocked_ips.json`; HTTP 403 | |
| 2 | Unblock via SOC | IP Management → Unblock → confirm | HTTP 200; shop loads normally | |
| 3 | Manual block via SOC | "+ Block IP"; enter IP; select permanent; submit | IP added to `blocked_ips.json`; requests from that IP to vuln-web receive HTTP 403 | |
| 4 | Whitelist IP | IP History drawer → Whitelist | No new incidents from IP; excluded from JSON block list | |
| 5 | Whitelist a previously blocked IP | Same IP was previously blocked | Upsert succeeds (no 409 conflict); IP is whitelisted | |

### D.10 — Ongoing vs All Incidents

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Ongoing list | Navigate to `/incidents` | New + investigating incidents only | |
| 2 | Resolve one incident | Change status → Resolved | Disappears from the ongoing list | |
| 3 | All list | Navigate to `/incidents/all` | Resolved row is visible | |

### D.11 — Export CSV

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Export ongoing | Export from `/incidents` | Download `incidents-ongoing.csv`; no resolved-only rows | |
| 2 | Export all | Export from `/incidents/all` | Download `incidents-all.csv`; includes resolved | |

### D.12 — IP History Drawer

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Open drawer | Click IP on any incident row | History API; past incidents; enforcement status | |
| 2 | Pattern summary | IP with multiple attacks | Attack type breakdown displayed | |

### D.13 — Lab Mode

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Enable lab mode | Settings → Lab mode → Save | Rules ⓘ warning; OWASP baseline disabled | |
| 2 | Payload with no active CMD rule | No CMD rule active; `cmd=;whoami` | No incident created (lab only) | |
| 3 | Custom UI rule active | Add regex rule; send matching payload | Incident created from UI rule only | |
| 4 | Disable lab mode | Save | OWASP baseline re-enabled | |

### D.14 — Bulk Resolve

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Select multiple incidents | Selection mode on Incidents page | Checkboxes visible per row | |
| 2 | Apply bulk resolve | Confirm resolve | Toast success; rows move to All Incidents archive | |

### D.15 — Detection Rules CRUD

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Create new rule | "+ Add Rule"; fill all fields; Create | Rule saved to `detection_rules`; Redis `rules_dirty` set; rule visible in table | |
| 2 | Toggle rule inactive | Click active toggle on a rule | `is_active=false` saved to DB; engine skips rule on the next 60-second reload | |
| 3 | Edit rule | Click edit; change severity; Save | DB record updated; `rules_dirty` set | |
| 4 | Delete rule | Click delete; confirm | Rule removed from DB | |
| 5 | Rule Testing Sandbox | Enter regex + test payload | Match/no-match result displayed | |

### D.16 — AI Explanation

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Generate with Groq configured | Open incident; click "Generate AI Explanation" | AI panels: Summary, Why It's Dangerous, Recommended Actions, MITRE; model badge | |
| 2 | Static fallback (no API key) | `GROQ_API_KEY` empty; trigger incident; generate | Static text; `model_used` = `fallback-static` | |

### D.17 — Chatbot / Notifications / Session

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Chatbot query | Ask about SQLi regex | Groq or fallback reply | |
| 2 | Notification bell | New incident (if alerts enabled) | Toast + badge increment | |
| 3 | Test email/Telegram | Test button in Settings | Sent or clear error message (optional) | |
| 4 | Session timeout | Idle past threshold | Warning dialog; logout on confirm | |

### D.18 — Live Traffic

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | Attack vs Blocked sequence | `/cmd?cmd=;whoami` then refresh | Attack (200) row; Blocked (403) row | |
| 2 | Hide static assets | Toggle checkbox | CSS/JS/favicon requests hidden | |
| 3 | Normal traffic | Browse catalog without payloads | All rows tagged Normal (green) | |

### D.19 — Simulate Attack

| No. | Scenario | Input | Expected Output | Output Result |
|-----|----------|-------|-----------------|---------------|
| 1 | DB inject (Mode A) | Incidents → Simulate Attack → Mode A | Incident appears immediately without vuln-web | |
| 2 | Log inject (Mode B) | Mode B → select attack type (e.g., LFI_RFI) | Toast success; incident appears ~5 seconds; visible in Live Traffic | |

---

## E. MANUAL GUIDE

### E.1 — System Build Documentation (Developer Perspective)

The primary deployment method is Docker Compose, which provisions all six services with a single command and requires no manual database setup or virtual environment configuration.

**Prerequisites:** Git, Docker Desktop (Windows/macOS) or Docker Engine + Docker Compose v2 (Linux). The developer machine must have at least 8 GB RAM and ports 3000, 5000, 5050, 5432, and 6379 available.

**Step 1 — Clone the repository.**

```powershell
git clone https://github.com/HardInCode/incidentra.git
cd incidentra
```

**Step 2 — Configure the backend environment file.**

```powershell
copy backend\.env.docker.example backend\.env.docker   # Windows
# or
cp backend/.env.docker.example backend/.env.docker     # Linux/macOS
```

Open `backend/.env.docker` and fill in the optional keys: `GROQ_API_KEY` (from console.groq.com, free tier), `ABUSEIPDB_API_KEY`, and SMTP/Telegram credentials. Core detection and blocking operate without any external API keys.

**Step 3 — Build and start all containers.**

```powershell
docker compose up --build -d
```

Docker Compose starts six services: `postgres` (port 5432), `redis` (port 6379), `vuln_web` (port 5050), `backend` (port 5000), `frontend` (port 3000, served by Nginx), and `celery_worker`. The backend entrypoint script (`docker_entrypoint.sh`) runs `db.create_all()`, seeds the admin user and 11 default detection rules, then starts Gunicorn. The log monitor thread starts automatically and begins tailing the shared `vuln_logs` volume.

**Step 4 — Access the system.**

- SOC Dashboard: `http://localhost:3000` — Login with `admin / Admin@Incidentra2026!`
- vuln-web target: `http://localhost:5050`

**Step 5 — Verify operation.**

Browse `http://localhost:5050` and confirm that new entries appear in Live Traffic within 3–6 seconds.

**Step 6 — Enable Phase 3 (optional, isolated lab only).**

`docker-compose.yml` already includes `VULN_UNSAFE_CMD: "1"` and `VULN_UNSAFE_UPLOAD: "1"` in the `vuln_web` service. To disable them, remove or set to `"0"` then restart:

```powershell
docker compose restart vuln_web
```

A red warning banner will appear on all vuln-web pages when Phase 3 is active.

**Step 7 — Reset for demonstration (Docker).**

From the repository root (with the Docker stack running):

```powershell
$env:DATABASE_URL = "postgresql://incidentra:incidentra123@localhost:5432/incidentra_db"
$env:REDIS_URL = "redis://localhost:6379/0"
python scripts/reset_incidentra.py

docker compose exec vuln_web sh -c ":> /app/logs/access.log"
docker compose exec vuln_web sh -c 'echo "{\"blocked\":[],\"updated_at\":\"\"}" > /app/logs/blocked_ips.json'
docker compose exec vuln_web sh -c 'echo "{\"rate_limited\":[],\"updated_at\":\"\"}" > /app/logs/rate_limited.json'

docker compose restart backend vuln_web
```

**Manual alternative (3 terminals):**

- Terminal 1: `cd backend && pip install -r requirements.txt && python run.py`
- Terminal 2: `cd frontend && npm install && npm start`
- Terminal 3: `cd vuln-web && pip install -r requirements.txt && python app.py`

PostgreSQL and Redis must be running locally. Copy `backend/.env.example` to `backend/.env` and set `DATABASE_URL`, `REDIS_URL`, and `WEB_SERVER_LOG_PATH` to the absolute path of `vuln-web/logs/access.log`.

---

### E.2 — End-User System Installation (User Perspective)

Incidentra is a server-side platform. End-user installation requires no software on the administrator's workstation beyond a modern web browser.

| Component | Requirement |
|-----------|-------------|
| Server | VPS with Ubuntu 22.04+ and Docker Engine + Docker Compose v2; minimum 2 vCPU, 4 GB RAM, 20 GB disk |
| Alternative | Single PC with Windows 10/11 or macOS with Docker Desktop |
| Browser (SOC user) | Google Chrome or Microsoft Edge (latest version); access `http://<server-ip>:3000` |
| Monitored application | Any web application writing NCSA Combined Log Format; replace the vuln-web log path with the production log path via `WEB_SERVER_LOG_PATH` in `backend/.env.docker` |
| Network | Expose port 3000 (SOC UI) to trusted administrator IPs only; port 5000 (API) must not be publicly accessible; port 5050 (vuln-web) is for demonstration only |
| External APIs *(optional)* | Outbound HTTPS to `api.groq.com`, `api.abuseipdb.com`, `smtp.gmail.com:587`, `api.telegram.org` |

No client-side installation is required. The SOC Dashboard is served as a pre-built React application by Nginx and is accessed entirely in the browser.

---

### E.3 — User Guide per User Role

Incidentra defines three user roles, each with a distinct set of responsibilities and access paths within the system.

| Role | Access Level | Primary Responsibilities | Typical Workflow |
|------|-------------|-------------------------|-----------------|
| **Admin** | Full SOC access + Audit Log | Manage detection rules; block or unblock IPs; configure API keys and thresholds; review audit logs; assign incidents; export reports | Login → Dashboard (review KPIs) → Incidents (filter Critical/High → open incident → Generate AI Explanation → add notes → mark Resolved) → IP Management (unblock false positives) → Detection Rules (add/edit rules) → Settings (update Groq key) |
| **Analyst** | Read + update incident status | Monitor live threats; triage incidents; review AI explanation; annotate notes; update status | Login → Dashboard (check 24-hour count) → Live Traffic (monitor Attack tags) → Incidents (filter New/Investigating → open critical incident → review details → add notes → change status to Investigating) |
| **Lab User** (vuln-web demo) | vuln-web only (no SOC access) | Browse catalog; demonstrate attack payloads for lab exercises | Open `http://localhost:5050` → browse catalog → try payloads (search, files, cmd, login) → observe 403/429 responses after SOC detection |

**Detailed procedure — Admin: Unblock IP**

1. Open `http://localhost:3000` in a browser and sign in as `admin`.
2. In the left sidebar, click **IP Management**.
3. Ensure the **Blocked** tab is selected.
4. Locate the IP address to unblock.
5. Click the Unblock icon in the Actions column; confirm in the dialog.
6. Verify: navigate to `http://localhost:5050` — the shop catalog should load normally (HTTP 200).

**Detailed procedure — Admin: Add Custom Detection Rule**

1. In the sidebar, click **Detection Rules**.
2. Click **+ Add Rule** in the upper right.
3. Fill in Rule Name, select Attack Type from the dropdown, select Severity, and enter the Regex Pattern.
4. Click **Create**. The rule appears in the table with `match_count = 0`.
5. Within 60 seconds (or immediately if the Redis `rules_dirty` flag is set), the Detection Engine reloads and includes the new pattern.

**Detailed procedure — Admin: Whitelist a Trusted IP**

1. Click an IP address on any incident row.
2. The IP History drawer opens — review the incident history for that IP.
3. Click the **Whitelist** button in the drawer; confirm.
4. Verify: no new incidents are created from that IP; the IP does not appear in `blocked_ips.json`.

**Detailed procedure — Analyst: Triage a Critical Incident**

1. From the Dashboard, observe a spike in the Incident Timeline or a new entry in the last-24-hours card.
2. Click **Incidents** in the sidebar; apply filters Severity = Critical, Status = New.
3. Click a row to open the Incident Detail page.
4. Review Source IP, Attack Type, HTTP Path, Raw Payload, and Automated Actions.
5. Click **Generate AI Explanation**; review the Summary and Recommended Actions panels.
6. In the Investigation Notes section, type an observation and click **+ Add**.
7. Change the status dropdown from **New** to **Investigating** (or **Resolved** if the threat has been remediated).

---

## REFERENCES

1. OWASP Top 10 (2021) — A03 Injection, A04 Insecure Design. https://owasp.org/Top10/
2. MITRE ATT&CK — Enterprise matrix. https://attack.mitre.org/
3. NCSA Combined Log Format — web server logging conventions.
4. Flask Documentation — https://flask.palletsprojects.com/
5. React 18 Documentation — https://react.dev/
6. PostgreSQL 15 Documentation — https://www.postgresql.org/docs/
7. Redis Documentation — https://redis.io/docs/
8. Docker Compose Specification — https://docs.docker.com/compose/
9. Groq API Documentation — https://console.groq.com/docs
10. AbuseIPDB API v2 — https://www.abuseipdb.com/api-documentation
11. Material UI (MUI) — https://mui.com/
12. Chart.js — https://www.chartjs.org/

---

*Form 4 Implementation v5 | Incidentra "Intelligent Web-SOC Platform with Automated Incident Response" | President University Capstone 2026 | Hardin Irfan (001202300066) · Nasywa Kamila (001202300211) · Zaidan Mahfudz Azzam Saidi (001202300144)*
