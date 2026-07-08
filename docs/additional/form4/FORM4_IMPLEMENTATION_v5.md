Form4

Capstone Design Implementation

Title :

**Incidentra**

“Intelligent Web-SOC Platform with Automated Incident Response”

GROUP MEMBER:

| No. | Student Name | Student ID |
| --- | --- | --- |
| 1. | Hardin Irfan | 001202300066 |
| 2. | Zaidan Mahfudz Azzam Saidi | 001202300144 |

Advisor:  Mr. Abdul Ghofir S. Kom., M. Kom.

Submitted for

Capstone Design Project

to Faculty of Computer Science

President University

**TABLE OF CONTENT**

Contents

		A.	DESIGNS IMPLEMENTATION	1

	1. Functions, Procedures, and Classes	1

	1.1 Log Ingestion Layer  — log_parser.py, log_monitor.py	1

	1.2 Detection Engine —  detection_engine.py	6

	1.3 Automated Response Manager — response_manager.py	11

	1.4 REST API Layer  — backend/app/api/	14

	1.5 AI and External Services — backend/app/services/	16

	1.6 vuln-web Target Application — vuln-web/	17

	1.7 SOC Frontend	19

	2. Database Implementation	21

	3. User Interface Implementation	23

	4. Hardware Implementation	25

	5. Integration Among Modules	25

		B.	PRODUCT DISPLAY	27

		1.	Software Product Display	27

		C.	COMPONENT COST ANALYSIS	49

		

D.	FUNCTIONAL TESTING	50

	D.1 — Authentication	50

	D.2 — SQL Injection Detection	50

	D.3 — XSS Detection	51

	D.4 — Path Traversal / LFI Detection	52

	D.5 — File Upload Detection	53

	D.6 — Command Injection Detection	53

	D.7 — Brute Force Detection	54

	D.8 — Scanner Detection	55

	D.9 — IP Block / Unblock / Whitelist	55

	D.10 — Ongoing vs All Incidents	56

	D.11 — Export CSV	56

	D.12 — IP History Drawer	57

	D.13 — Lab Mode	57

	D.14 — Bulk Resolve	58

	D.15 — Detection Rules CRUD	58

	D.16 — AI Explanation	59

	D.17 — Chatbot / Notifications / Session	60

	D.18 — Live Traffic	60

	D.19 — Simulate Attack	60

	D.20 — Escalating Block / Repeat Offender	61

		E.	MANUAL GUIDE	62

	E.1 — System Build Documentation (Developer Perspective)	62

	E.2 — End-User System Installation (User Perspective)	65

	E.3 — User Guide per User Role	66

**STATEMENT OF ORIGINALITY**

In my capacity as an active student at President University and as the author of the Capstone Design Project stated below:

Name			: 1. Hardin Irfan – 001202300066

			  2. Zaidan Mahfudz Azzam Saidi – 001202300144

Faculty			: Computer Science

I hereby declare that my Capstone Design Project entitled “**Incidentra**” is to the best of my knowledge and belief, an original piece of work based on sound academic principles. If there is any plagiarism detected in this final project, I am willing to be personally responsible for the consequences of these acts of plagiarism and will accept the sanctions against these acts in accordance with the rules and policies of President University.

I also declare that this work, either in whole or in part, has not been submitted to another university to obtain a degree.

Cikarang, June 2026

| Signer 1 | Signer 2 |
| --- | --- |
|  |  |
| Hardin Irfan – 001202300066 | Zaidan Mahfudz Azzam Saidi – 001202300144 |

**SCREENSHOT OF ZEROGPT**

 

 DESIGNS IMPLEMENTATION

1. Functions, Procedures, and Classes

This section maps each Form 3 subsystem to its concrete implementation in the Incidentra codebase. All file paths are relative to the repository root.

1.1 Log Ingestion Layer  — log_parser.py, log_monitor.py

The log ingestion layer (P1 Form 3 subsystem) is implemented in backend/app/core/log_parser.py and backend/app/core/log_monitor.py. Its responsibility is to convert raw web server log lines into structured records that can be analyzed by the Detection Engine.

**parse_log_line()** in log_parser.py is the entry point for a single log line. This function applies the NGINX_PATTERN regex to decode the fields of the NCSA Combined Log Format: client IP, timestamp, HTTP method, request path, query string, HTTP version, status code, response size, referer, and User-Agent. Empty lines or lines that do not conform to the format are returned as None. The second pattern, POST_DATA_PATTERN, detects the custom POST_DATA: suffix added by vuln-web via middleware/logging.py. When this suffix is present, the POST body content (e.g., username=admin' OR ‘1’='1' -- or file=shell.php) is merged into the returned query dictionary field.

																*# backend/app/core/log_parser.py — L14–60*

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

																        line = line[: m.start()]    *# strip POST_DATA suffix before parsing*

																

																    match = NGINX_PATTERN.match(line)

																    if not match:

																        return None

																

																    full_path = match.group('path')

																    parsed = urlparse(full_path)

																    path = unquote_plus(parsed.path)

																    query = unquote_plus(parsed.query)

																

																    if post_data:

																        query = (query + post_data).strip()

																					*# merge POST body into query field*

																    return {

																        'ip':          match.group('ip'),

																        'method':      match.group('method'),

																        'path':        path,

																        'query':       query,          *# includes POST_DATA if present*

																        'user_agent':  match.group('ua'),

																        'status_code': int(match.group('status')),

																        'raw':         line + (post_data if post_data else ''),

																    }

Figure 1. NGINX_PATTERN and POST_DATA_PATTERN regex in log_parser.py

**LogTailer** implements continuous monitoring using a polling loop equivalent to tail -f. During initialization, the file is opened at WEB_SERVER_LOG_PATH, the read head is moved to the end of the file (to prevent historical entries from being reprocessed), and then a new line is read at each polling interval (default 1 second). Inode tracking detects log rotation.

																*# backend/app/core/log_parser.py — LogTailer.tail()*

																def tail(self) -> Generator[str, None, None]:

																    """Yield new lines as they appear."""

																    try:

																        with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:

																            f.seek(0, 2)             *# seek to end of file*

																            self._pos = f.tell()

																            self._inode = self._get_inode()

																    except FileNotFoundError:

																        logger.warning(f"Log file not found: {self.filepath}")

																

																    while True:

																        current_inode = self._get_inode()

																        if current_inode != self._inode:   *# log rotation detected*

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

Figure 2. LogTailer.tail() continuous monitoring method in log_parser.py

**log_monitor.py**** **coordinates the pipeline. start_monitor() launches a daemon threading.Thread that iterates over lines from LogTailer or SimulatedLogFeeder. For each line, _process_log_line() calls parse_log_line(), then DetectionEngine.analyze(). If a threat is detected, the monitor queries PostgreSQL for incidents matching the same criteria (IP + attack_type) within the last 5 minutes; only if none are found is a new Incident line created and ResponseManager.respond() called.

																*# backend/app/core/log_monitor.py — _process_log_line()** (summary)*

																def _process_log_line(line, engine, responder, db, redis_client, app) -> Optional[int]:

																    """Parse one line, run detection, create incident if needed."""

																    entry = parse_log_line(line)

																    if not entry:

																        return None

																

																    threat = engine.analyze(entry)

																    if not threat:

																        return None

																

																    *# Deduplication: skip same IP+attack within 5 minutes*

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

																        *# ... other fields*

																    )

																

																    db.session.add(incident)

																    db.session.commit()

																

																    responder.respond(threat, incident.id)

																    return incident.id

Figure 3. _process_log_line() pipeline function in log_monitor.py

1.2 Detection Engine —  detection_engine.py

The detection engine (P2 Form 3 subsystem) is implemented in backend/app/core/detection_engine.py as the DetectionEngine class, supported by BruteForceTracker and the module-level dictionaries DETECTION_PATTERNS, SEVERITY_WEIGHTS, and RESPONSE_ACTIONS. 

**Pattern sources.** Detection uses two sources that are merged at runtime: (1) built-in OWASP patterns in DETECTION_PATTERNS, and (2) administrator-defined rules stored in the PostgreSQL table detection_rules, loaded via _load_rules_from_db().

**Supported attack types (8 main types):** SQL_INJECTION (critical), XSS (critical), BRUTE_FORCE (high, threshold-based), PATH_TRAVERSAL (high), FILE_UPLOAD (high), COMMAND_INJECTION (critical), SCANNER (medium), and LFI_RFI (critical).

																*# backend/app/core/detection_engine.py — DETECTION_PATTERNS*

																DETECTION_PATTERNS = {

																    'SQL_INJECTION': {

																        'patterns': [

																            r"(?i)(union\s+select|select\s+(\*|[\w]+\s*,\s*[\w\s,`]*)\s+from\s+\w|...)",

																            r"(?i)(\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)",

																            r"(?i)(sleep\s*\(|benchmark\s*\(|waitfor\s+delay)",

																            *# ... 7 more patterns*

																        ],

																        'severity': 'critical',

																        'mitre': 'T1190 - Exploit Public-Facing Application',

																    },

																    'BRUTE_FORCE': {

																        'patterns': [],           *# threshold-based, not regex*

																        'severity': 'high',

																        'mitre': 'T1110 - Brute Force',

																        'threshold_based': True,

																    },

																 *# ... XSS, PATH_TRAVERSAL, FILE_UPLOAD, COMMAND_INJECTION, SCANNER, LFI_RFI*

																}

																SEVERITY_WEIGHTS = {'critical': 100, 'high': 70, 'medium': 40, 'low': 10}

																

																

																RESPONSE_ACTIONS = {

																    'low':      'log_and_monitor',

																    'medium':   'rate_limit',

																    'high':     'escalating_block',

																    'critical': 'escalating_block',

																}

Figure 4. DETECTION_PATTERNS, SEVERITY_WEIGHTS, and RESPONSE_ACTIONS in detection_engine.py

**Lab mode and reload rules:** _load_rules_from_db() loads active rules from the database. If lab mode is enabled (via Settings), the OWASP baseline is not appended—only rules created via the UI are used. _maybe_reload_rules() is executed on every analyze() call, and is forced to run immediately if the Redis key rules_dirty is set.

																*# backend/app/core/detection_engine.py — _load_rules_from_db() **and** analyze()*

																def _load_rules_from_db(self):

																    lab_only = is_lab_mode_ui_only()

																    rules = DetectionRule.query.filter_by(is_active=True).all()

																    compiled = {}

																    for rule in rules:

																        *# compile each DB rule regex ...*

																        compiled[rule.attack_type].append({

																            'pattern': re.compile(rule.pattern, re.IGNORECASE),

																            'severity': rule.severity_level.value,

																            'rule_id': rule.id,

																        })

																    if not lab_only:

																        *# Append OWASP baseline patterns (production default)*

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

																    *# Whitelist check — whitelisted IPs skip detection entirely*

																    if ip:

																        if BlockedIP.query.filter_by(ip_address=ip, is_whitelist=True).first():

																            return None

																

																    *# Build searchable string from method + path + query (incl. POST_DATA) + user_agent*

																    searchable = f"{method} {path} {query} {user_agent}"

																    threats = []

																    for attack_type, patterns in self._get_compiled().items():

																        for p in patterns:

																            pattern = p['pattern'] if isinstance(p, dict) else p

																            match = pattern.search(searchable)

																            if match:

																                threats.append({'attack_type': attack_type, 'severity': ..., ...})

																                break

																

																    *# Brute force: threshold-based for POST to login paths*

																    if is_login_path and is_post and self._brute_force_enabled():

																        if self.bf_tracker.is_brute_force(ip, path):

																            threats.append({'attack_type': 'BRUTE_FORCE', ...})

																    if not threats:

																        return None

																

																    *# Return highest-severity threat*

																    primary = max(threats, key=lambda t: t['score'])

																    return {

																        'ip': ip, 'attack_type': primary['attack_type'],

																        'severity': primary['severity'],

																        'recommended_action': RESPONSE_ACTIONS[primary['severity']],

																        *# ...*

																    }

Figure 5. _load_rules_from_db() and analyze() methods in detection_engine.py

BruteForceTracker counts failed login POST requests per IP address within a 60-second sliding window (default threshold of 10). It uses Redis sorted sets if available, and falls back to an in-memory deque otherwise. It emits exactly one BRUTE_FORCE threat the first time the threshold is exceeded.

																*# backend/app/core/detection_engine.py — BruteForceTracker*

																class BruteForceTracker:

																    def record_attempt(self, ip: str, path: str) -> int:

																        now = time.time()

																        key = f"bf:{ip}:{path}"

																        if self.redis:

																            pipe = self.redis.pipeline()

																            pipe.zadd(key, {str(now): now})

																            pipe.zremrangebyscore(key, 0, now - self.window)  *# remove old entries*

																            pipe.zcard(key)

																            pipe.expire(key, self.window * 2)

																            results = pipe.execute()

																            return results[2]    *# count within window*

																        *# fallback: in-memory deque*

																        dq = self._local[key]

																        dq.append(now)

																        while dq and dq[0] < now - self.window:

																            dq.popleft()

																        return len(dq)

																

																    def is_brute_force(self, ip: str, path: str) -> bool:

																        """Fire only when threshold is first crossed (== not >=)."""

																        return self.record_attempt(ip, path) == self.threshold

Figure 6. BruteForceTracker class in detection_engine.py

1.3 Automated Response Manager — response_manager.py

backend/app/core/response_manager.py implements the ResponseManager class, which translates threat severity into specific enforcement actions.

The respond() method applies the following severity-to-action mapping:

| **Severity** | **Action** | **Enforcement Mechanism** | **Duration** |
| --- | --- | --- | --- |
| Low | log_and_monitor | IncidentLog record in PostgreSQL; Redis key action:{ip} | Permanent record |
| Medium | rate_limit | Entry in rate_limited.json; Redis key ratelimit:{ip} with configurable TTL | Per RATE_LIMIT_WINDOW (default 60 s) |
| High | escalating_block | Entry in blocked_ips.json via _write_blocked_ips_json(); BlockedIP DB record with expire_time | Default: 1h → 24h → 7d per offense tier |
| Critical | escalating_block | Same as high, using critical duration list | Default: 24h → 7d → 30d per offense tier |

Table 1. Automated Response Severity-to-Action Mapping

Automatic responses **never** apply permanent blocks. Permanent blocking is available only through manual admin action in IP Management. When an IP reaches the Repeat Offender threshold (default: 3 offenses, configurable in Settings), `is_repeat_offender=True` is set for admin review. This phased policy replaces the earlier automatic permanent-block design, reflecting client feedback on shared-IP environments (NAT, corporate proxies, CGNAT) documented in Form 5.

																*# backend/app/core/response_manager.py — respond() **and** _escalating_block() (summary)*

																def respond(self, threat: dict, incident_id: int) -> dict:

																    action = threat.get('recommended_action', 'log_and_monitor')

																    if action == 'log_and_monitor':

																        self._log_to_redis(ip, 'monitor')

																    elif action == 'rate_limit':

																        self._apply_rate_limit(ip)

																        _write_rate_limited_json(ip, add=True)

																    elif action == 'escalating_block':

																        block_result = self._escalating_block(

																            ip=ip, severity=severity,

																            attack_type=threat.get('attack_type', ''),

																            incident_id=incident_id,

																        )

																        *# writes BlockedIP (temporary) + blocked_ips.json*

																    *# Legacy: temporary_block / permanent_block still supported for manual API calls*

																    self._save_incident_log(incident_id, result)

																    return result

																

																def _escalating_block(self, ip, severity, attack_type, incident_id) -> dict:

																    repeat_threshold = get_repeat_offender_threshold()  *# default 3*

																    durations = get_escalating_critical_durations() if effective_severity == 'critical' \

																                else get_escalating_high_durations()

																    hours = _pick_escalating_duration(durations, offense_index)

																    *# Sets BlockedIP.block_type='temporary', expire_time, incident_count,*

																    *# is_repeat_offender; persists escalation_count:{ip} in Redis (survives admin unblock)*

																    _write_blocked_ips_json()

																    return result

Figure 7. respond() and _escalating_block() methods in response_manager.py

**_write_blocked_ips_json()** retrieves all active BlockedIP records (excluding whitelisted ones), filters out temporary blocks that have expired, and writes the results to blocked_ips.json. This file is read by vuln-web/middleware/security.py for every incoming HTTP request via the before_request hook, causing blocked IPs to receive an HTTP 403 response without requiring a server restart or direct database access from vuln-web.

																*# backend/app/core/response_manager.py — _write_blocked_ips_json()*

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

Figure 8. _write_blocked_ips_json() method in response_manager.py

1.4 REST API Layer  — backend/app/api/

The backend API is a Flask application defined in backend/app/__init__.py. API endpoints are organized into blueprints under backend/app/api/:

| **Blueprint** | **File** | **Responsibility** |
| --- | --- | --- |
| auth | auth.py | Login (POST /api/auth/login), token verification, logout |
| incidents | incidents.py | List, retrieve, update, export incidents; trigger AI explanation; simulate attack; bulk status update |
| rules | rules.py | CRUD for detection_rules; sets Redis rules_dirty flag on write |
| blocked_ips | blocked_ips.py | List, add, update, delete (unblock), whitelist upsert; calls _write_blocked_ips_json() |
| rate_limited | rate_limited.py | List, extend, and clear rate-limited IPs; updates rate_limited.json and Redis |
| dashboard | dashboard.py | Aggregate statistics: total incidents, 24-hour count, blocked IPs, MTTR, severity breakdown, 7-day timeline |
| traffic | traffic.py | Recently parsed log entries for Live Traffic (display-only, not detection) |
| settings | settings.py | Read/write AppSetting key-value pairs for API keys and thresholds |
| audit | audit.py | Paginated AuditLog query |
| chatbot | chatbot.py | AI chat assistant (Groq) for general security questions |
| ip_history | ip_history.py | IP History drawer: per-IP timeline data |
| notifications | notifications.py | New notifications, mark-read |

Table 2. API Blueprint Structure of Incidentra Backend

All protected endpoints validate a Bearer JWT using the verify_token() function in auth_middleware.py, which is registered as a before_request hook. Tokens are signed with HS256 using the SECRET_KEY environment variable and expire after 24 hours.

**Scope filter (Ongoing vs All Incidents):**

																*# backend/app/api/incidents.py — list endpoint (summary)*

																

																list_scope = (args.get('list_scope') or '').strip().lower()

																if list_scope == 'ongoing' and not status and not status_in:

																    query = query.filter(

																        Incident.status.in_([IncidentStatus.NEW, IncidentStatus.INVESTIGATING])

																    )

Figure 9. Scope filter in incidents.py API endpoint

**Whitelist upsert (no 409 when marking a trusted IP):**

																*# backend/app/api/blocked_ips.py — whitelist upsert*

																

																if existing and is_whitelist:

																    existing.is_whitelist = True

																    existing.reason = data.get('reason', 'Whitelisted — trusted IP')

																    existing.block_type = 'permanent'

																    existing.expire_time = None

																    db.session.commit()

Figure 10. Whitelist upsert in blocked_ips.py API endpoint

1.5 AI and External Services — backend/app/services/

**ai_service.py** implements build_prompt(), which constructs a structured natural-language prompt from incident attributes, and _call_groq_with_fallback(), which calls the Groq Cloud API using a sequence of four models:

- llama-3.3-70b-versatile

- llama-3.1-8b-instant

- meta-llama/llama-4-scout-17b-16e-instruct

- meta-llama/llama-guard-4-12b

If all four models fail (HTTP 400/404/422 or network error), the system returns a predefined static explanation so that every incident always has a human-readable analysis. The model_used field in IncidentExplanation records which model—or the literal string “fallback-static”—generated the explanation.

**threat_intel_service.py** queries the AbuseIPDB v2 API using the incident's source IP to retrieve an abuse_confidence_score (0–100), which is stored in the Incident record and displayed in the incident details panel.

**notification_service.py** sends alerts via SMTP email or the Telegram Bot API. Notification delivery runs in a separate daemon thread via _notify_async() in ResponseManager—this thread-based approach is more reliable than Celery's .delay() because it works without requiring a running worker container.

1.6 vuln-web Target Application — vuln-web/

The deliberately vulnerable Flask shop (vuln-web/) serves as the monitored target. It consists of route blueprints in vuln-web/routes/:

| **Blueprint** | **File** | **Exposed Vulnerability** |
| --- | --- | --- |
| main | main.py | Home, product catalog |
| auth | auth.py | Login with intentionally weak credentials |
| shop | shop.py | Product listing, shopping cart |
| profile | profile.py | Profile update with unrestricted avatar field (CTF vector) |
| files | files.py | File upload and download; path traversal if VULN_UNSAFE_UPLOAD=1 |
| cmd | cmd.py | Simulated or real command execution if VULN_UNSAFE_CMD=1 |
| api | api.py | AJAX endpoints for the cart |

Table 3. vuln-web Route Blueprints and Exposed Vulnerabilities

middleware/security.py registers enforce_security() as a before_request hook that reads blocked_ips.json and rate_limited.json on every request. middleware/logging.py registers an after_request hook that writes one Combined Log Format line per request to logs/access.log, appending the POST_DATA: 

suffix for login and file upload endpoints.

**Phase 3 flags** (read by vuln-web/config.py via _env_bool()):

																*# docker-compose.yml — vuln_web service environment*

																environment: 

																  VULN_UNSAFE_CMD: "1"     

																*# real shell execution via subprocess.run(shell=True)*

																  VULN_UNSAFE_UPLOAD: "1"  

																*# raw client-supplied filename (path traversal risk)*

Figure 11. vuln-web Phase 3 environment flags in docker-compose.yml

Changing either flag requires a vuln-web process restart: docker compose restart vuln_web.

1.7 SOC Frontend

The React 18 frontend (frontend/) is structured around page-level components in frontend/src/pages/. Routing is defined in frontend/src/App.js:

																*// frontend/src/App.js — L39–48*

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

																<ChatbotWidget />         {*/* draggable FAB, always present */*}

Figure 12. Route definitions in frontend/src/App.js

| **Route** | **Component** | **Description** |
| --- | --- | --- |
| / | Dashboard | Metric cards, incident timeline, severity chart |
| /incidents | Incidents (ongoing) | Active incidents list with filters |
| /incidents/all | Incidents (all) | Full incident history |
| /incidents/:id | IncidentDetail | Detail, AI explanation, notes, status |
| /blocked-ips | BlockedIPs | IP Management — Blocked and Rate Limited tabs |
| /rules | DetectionRules | Rules CRUD with pattern test |
| /traffic | LiveTraffic | Real-time log stream |
| /settings | Settings | API keys and thresholds |
| /audit | AuditLog | Admin action history |

Table 4. SOC Frontend Route and Component Mapping

**Global**** ****widgets:** 

NotificationBell (header, new incident badge), ChatbotWidget (draggable FAB, Groq), SessionTimeoutWarning (idle logout dialog).

**Export CSV per scope:**

																*// frontend/src/pages/Incidents.js — handleExportCsv()*

																const handleExportCsv = async () => {

																    const params = { list_scope: isAllMode ? 'all' : 'ongoing' };

																    *// ... apply filters*

																    a.download = isAllMode ? 'incidents-all.csv' : 'incidents-ongoing.csv';

																};

Figure 13. handleExportCsv() function in Incidents.js

All API calls are made through frontend/src/services/api.js using Axios with the JWT stored in localStorage under the key incidentra_token. The UI supports language switching between English and Indonesian via react-i18next.

2. Database Implementation

*Incidentra* uses PostgreSQL 15 as its primary relational store, accessed via SQLAlchemy 2.x ORM. All models are defined in backend/app/models/__init__.py. The schema is initialized by db.create_all() and populated by seed_all() in backend/app/utils/seeder.py, which runs automatically via backend/docker_entrypoint.sh on the first container start. The default seed creates admin and analyst users and **18** active detection rules (11 core OWASP rules plus 7 lab-specific EXTRA_RULES) covering all supported attack categories.

| **Model Class** | **Table** | **Columns** |
| --- | --- | --- |
| User | users | id, username, email, password_hash (PBKDF2-SHA256), role, created_at, is_active |
| Incident | incidents | id, created_at, updated_at, source_ip, attack_type, severity (enum), status (enum), raw_payload, request_path, request_method, user_agent, response_code, rule_id (FK→detection_rules), assigned_to (FK→users), resolved_at, country_code, abuse_confidence_score |
| DetectionRule | detection_rules | id, rule_name, attack_type, pattern, severity_level (enum), description, is_active, created_at, updated_at, match_count |
| BlockedIP | blocked_ips | id, ip_address, reason, block_type (permanent/temporary), block_time, expire_time, incident_count, **is_repeat_offender**, **is_whitelist**, created_by |
| IncidentLog | incident_logs | id, incident_id (FK→incidents), action_taken, action_detail, action_time, performed_by |
| IncidentExplanation | incident_explanations | id, incident_id (FK→incidents), ai_summary, threat_explanation, recommended_actions, mitre_technique, generated_at, model_used |
| IncidentNote | incident_notes | id, incident_id (FK→incidents), note_content, created_at, created_by |
| AppSetting | app_settings | id, key, value (API keys, SMTP config, thresholds), updated_at |
| AuditLog | audit_logs | id, timestamp, user_id (FK→users), username, action, resource_type, resource_id, details, ip_address |

Table 5. Database Model Summary

**Outside PostgreSQL: **Rate-limiting state is stored outside PostgreSQL for performance reasons. The file rate_limited.json maintains the list of rate-limited IPs and per-IP policy overrides. Redis stores ratelimit:{ip} keys with a TTL for enforcement expiration. Both are accessed through API endpoints, not direct ORM queries.

**Dual-write enforcement:** BlockedIP DB + blocked_ips.json for vuln-web enforcement. Vuln-web has no PostgreSQL connection; enforcement is handled exclusively via the JSON files on the Docker named volume vuln_logs.

3. User Interface Implementation

The SOC Dashboard is a React 18 single-page application built with Material UI (MUI) and served by Nginx on port 3000 (local). The dark theme (frontend/src/theme/index.js) is optimized for extended use in security operations environments.

**Dashboard** displays four metric cards: Total Incidents (all time), Detections in the Last 24 Hours, BlockedIP Addresses (active blocks from the BlockedIP table), and MTTR (Mean Time to Resolution). A collapsible system status banner, driven by the last_log_received_at field from the log monitor, alerts the operator when no log lines have been received in the last 60 seconds. The Incident Timeline (Chart.js line chart, 7-day window) and By Severity donut chart automatically refresh every 15 seconds (configurable via REACT_APP_REFRESH_INTERVAL).

**Incidents** component renders a filterable, paginated table. Filter dropdowns include severity and status. A full-text search field covers IP address, attack type, and path. The Incidents component is used twice with different mode props (“ongoing” and “all”), so /incidents displays only new and ongoing incidents, while /incidents/all displays the full history, including resolved incidents.

**Incident Detail** page (/incidents/:id) features a two-panel layout. The left panel displays all technical attributes. The right panel has two states: before the AI explanation is generated, it displays a “Generate AI Explanation” call-to-action button; after generation, it displays four color-coded panels (Summary, Why It's Dangerous, Recommended Actions, MITRE ATT&CK mapping) and a model name badge. The Automated Actions timeline, populated from IncidentLog records, and the Investigation Notes section (append-only, timestamped, stored in IncidentNote) are displayed below both panels.

**IP Management** (/blocked-ips) displays three tabs. The Blocked tab lists BlockedIP records with block type, expiry, incident count, and a Repeat Offender badge when `is_repeat_offender=True`; filters support block type and repeat-offender-only views. The Rate Limited tab retrieves rate_limited.json via the /api/rate-limited/ endpoint. The Whitelisted tab lists trusted IPs via GET /api/blocked-ips/?whitelist=true, with add and remove actions.

**Detection Rules** lists all DetectionRule records with columns for name, attack type badge, severity badge, regex pattern excerpt, match count, active toggle, and edit/delete actions.

**Live Traffic** auto-refreshes every 3 seconds via HTTP polling of /api/traffic/. Each row displays the timestamp, IP, HTTP method, path, query/payload excerpt, HTTP status, and a classification tag (Attack/Suspicious/Blocked/Normal). An Attack tag with an HTTP status of 200 means the request reached the application before the Detection Engine processed the log line—no block has been applied yet. Only subsequent requests from that IP, after the incident is created and blocked_ips.json is updated, will receive a “Blocked” tag with HTTP 403.

4. Hardware Implementation

**Not applicable.** Incidentra is a software-only system. No microcontrollers, IoT sensors, or dedicated hardware appliances are required. The minimum recommended specification for the demonstration environment is a laptop or PC with at least 8 GB RAM and Docker Desktop installed, or a Linux VPS with 2 vCPUs and 4 GB RAM. All processing, storage, and network communication occur within Docker containers on the host machine.

5. Integration Among Modules

The complete integration flow is illustrated below. The vuln_logs Docker named volume is the sole shared state between the monitored application and the detection backend; vuln-web has no direct database connection.

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

Figure 14. Integration pipeline flow of Incidentra modules

Four key integration points:

- vuln-web has no PostgreSQL connection. Enforcement is received exclusively through the two JSON files written by the Response Manager.

- FILE_UPLOAD detection mechanism. The POST_DATA:file=filename suffix in the access log enables the Detection Engine to classify malicious file uploads without reading the uploaded file from disk — dangerous extensions are matched directly against the log line.

- Unblock Redis waiver.  When an administrator unblocks an IP via the SOC dashboard, the blocked_ips.py API calls _write_blocked_ips_json() to remove the IP from the enforcement file, and also sets the Redis key unblocked:{ip} (TTL 10 minutes) to temporarily bypass deduplication so the IP's next legitimate requests are not re-detected. Escalation tier counters (escalation_count:{ip}, escalation_severity:{ip}, 30-day TTL) persist across unblock so repeat offenders resume at the correct offense tier.

- 60-second rule reload. The Detection Engine rule reload cycle (triggered by the Redis rules_dirty flag) allows administrators to add or modify detection rules through the SOC dashboard and have them take effect within one minute without restarting any service.

Figure 15. System architecture and integration flow diagram of Incidentra

 PRODUCT DISPLAY

- Software Product Display

The Incidentra system consists of two browser-accessible components: the SOC Dashboard (React, port 3000) and the vuln-web target shop (Flask, port 5050). The following subsections describe the key screens as implemented.

Login Page. The login page (frontend/src/pages/Login.js) presents a centered card on a dark background with the Incidentra shield logo, "Intelligent Web-SOC Platform" subtitle, username and password fields, and a "Sign In" button. On successful authentication the Flask /api/auth/login endpoint issues a JWT (HS256, 24-hour expiry). A hint displays the default credentials to assist thesis defense.

Figure 16. Login Page with default credentials hint for demo.

**SOC Dashboard.** Four KPI metric cards: Total Incidents, Detections in Last 24 Hours, Blocked IPs, and MTTR. A system status banner dynamically changes between "All Systems Normal" and a warning when the log monitor has received no entries in the last 60 seconds. The Incident Timeline uses Chart.js to render a seven-day bar/line chart, and the By Severity donut chart shows the breakdown across low, medium, high, and critical incidents.

Figure 17. SOC Dashboard with KPI cards and system status banner (empty state).

Figure 18. SOC Dashboard with KPI cards, charts, and active incidents.

**Ongoing Incidents****.** The incidents table supports filtering by severity and status, full-text search across IP, attack type, and path, and pagination. Each row shows a colour-coded attack type badge and severity badge. A lock icon in the Response column indicates an automated IP block. "Simulate Attack" and "Export CSV" buttons appear in the header.

Figure 19. Ongoing Incidents page.

**Ongoing Incidents**** – Incident Status update****. **The status of each incident can be changed directly via the list table displayed on the page.

Figure 20. Ongoing Incidents — inline status update.

**Ongoing Incidents**** – Simulate Attack****. **There are two types of incident injection: direct database injection for UI testing, and injection through logs that are generated and recorded by the web application as traffic.

Figure 21. Ongoing Incidents — Simulate Attack modal with two injection modes.

**Ongoing Incidents**** – Pop Up and In App ****N****otification****. **There are two types of pop-ups in the app: pop-ups that appear when an incident is created, and pop-ups that appear alongside in-app notifications.

Figure 22. Ongoing Incidents — pop-up and in-app notification on incident creation.

**Ongoing Incidents**** – Sorting and Filtering****. **There are options for sorting and filtering, such as by status, by severity, by attack type, and by source IP. There is also a search field for more specific searches.

Figure 23. Ongoing Incidents — sorting and filtering options.

**Ongoing Incidents**** - IP History Drawer****. **There is a drawer that appears when clicking on an IP address in the Incidents tab. This drawer displays details about the IP address, including pattern analysis, the total number of incidents generated by this IP address, the daily frequency, the types of attacks frequently carried out, and incidents recently created by it. 

Figure 24. Ongoing Incidents — IP History Drawer.

**Ongoing Incidents**** – Export as ****CSV****. **Export button on the navigation bar to export data to CSV for a specific time range.

Figure 25. Ongoing Incidents — Export as CSV with date range selector. 

**All Incidents. **The difference between this tab and the Ongoing Incident tab is that this tab displays all incidents and their statuses, particularly those that have been resolved or marked as false positives.

Figure 26. All Incidents page showing resolved and false positive entries.

**Incident Detail — Before AI Analysis.** The detail page shows the full technical breakdown on the left (source IP, AbuseIPDB score, attack type, severity, HTTP method, path, response code, country, timestamps) and the "AI Explanation Not Generated" placeholder with a "Generate AI Explanation" call-to-action on the right. The Automated Actions section below shows what the system executed automatically at detection time (e.g., escalating temporary block of the source IP, Offense #1). The Investigation Notes section is available for analyst annotations.

Figure 27. Incident Detail page before AI explanation is generated.

**Incident Detail — After AI Analysis.** After clicking "Generate AI Explanation," the right panel is replaced by the AI-Powered Analysis section containing four color-coded blocks: Summary, Why It's Dangerous, Recommended Actions, and MITRE ATT&CK mapping. The model name badge (e.g., llama-3.3-70b-versatile) appears in the panel header.

Figure 28. Incident Detail page after Groq LLM analysis with four explanation panels.

**IP Management — Blocked Tab.** Lists all BlockedIP records, including the IP address, reason, block type (permanent or temporary escalating), block-start timestamp, expiration time, Repeat Offender badge (when threshold reached), incident count, and an unblock button. Filter chips support permanent/temporary and repeat-offender-only views. A “+ Block IP” button opens a dialog for manually blocking an IP address.

Figure 29. IP Management — Blocked tab. 

**IP Management — **** Add Block IP****.** The “+ Block IP” button allows users to manually block an IP address. The fields include IP address, reason, and block duration (permanent or temporary, ranging from 1 hour to 7 days).

Figure 30. IP Management — Add Block IP dialog.

**IP Management — **** Update and Delete**** Block****ed**** IP****.** Users can edit blocked IP addresses (reason and block type) and unblock them using a dedicated button.

 

Figure 31. IP Management — Edit and Unblock IP.

**IP Management — Rate Limited Tab**** and whitelisted IP Tab****.** Rate Limited tab reads data from rate_limited.json via the API and displays each rate-limited IP along with its per-IP policy and enforcement TTL from Redis. And Whitelist tab reads data from API GET /blocked-ips/?whitelist=true. Action buttons are provided for each row.

Figure 32. IP Management — Rate Limited & whitelisted IPS tab.

**Detection Rules.** Lists each DetectionRule record, including the name, attack type badge, severity badge, pattern excerpt, match count, active toggle, and edit/delete actions. Toggling a rule sets the is_active column in PostgreSQL and sets the rules_dirty flag in Redis.

Figure 33. Detection Rules page with active and inactive rules.

**Detection Rule****s **- **Update and Delete Detection Rules. **Users can edit existing detection rules in the list and can delete or disable those rules.

Figure 34. Detection Rules — Edit rule card, active toggle, and delete action.

**Create Detection Rule.** The "+ Add Rule" modal collects Rule Name, Attack Type (dropdown of supported enums), Severity Level, Regex Pattern, and Description. Upon submission the rule is saved to the detection_rules table and rules_dirty is set.

Figure 35. Detection Rules — Create Detection Rule modal.

**Detection Rules**** - ****Rule Testing Sandbox****.** The sandbox allows users to test whether a regex payload matches; two modes available: payload test and test log line.

Figure 36. Detection Rules — Rule Testing Sandbox.

**Live Traffic.** Displays parsed access log entries refreshed every three seconds. Each row shows timestamp, source IP, HTTP method, path, query/payload excerpt, HTTP status code, and a classification tag. Tag colour coding: Attack (red), Suspicious (amber), Blocked (purple), Normal (green). The critical distinction is that an "Attack" tag with HTTP status 200 means the request reached the application before the Detection Engine processed the log line — no block has been applied yet. Only subsequent requests from that IP after an Incident has been created and blocked_ips.json updated will receive a "Blocked" tag with HTTP 403.

Figure 37. Live Traffic page showing Attack and Blocked tag sequence.

**Live Traffic**** – Hide Static Assets checkbox****.**** **Checkbox to display or hide static assets such as CSS or JavaScript.

Figure 38. Live Traffic — Hide Static Assets checkbox.

**Settings**** — Appearance ****&**** Detection.** Configurable options include Dark/Light mode, language (English/Indonesian), in-app notifications toggle, Detection Lab Mode toggle, and Detection Thresholds (brute-force threshold, escalating block Policy, rate limit window).

Figure 39. Settings — Appearance and Detection section.

**Settings**** **** — API Keys ****&**** Integrations. **Stores external integration keys in the AppSetting table: Groq API key and model, AbuseIPDB API key, SMTP host/port/credentials/recipient, and Telegram bot token and chat ID. Keys are masked (asterisks) in the UI**.** 

Figure 40. Settings — API Keys and Integrations section.

**Audit Log.** Records all audit logs generated by users such as the Admin. Activity logs include changing incident status, creating detection rules, unblocking IP addresses, and so on.

Figure 41. Audit Log page.

**Chatbot. **The Chatbot panel answers cybersecurity questions ranging from basic inquiries to assisting with tasks like creating a regex detection rule. Uses the same Groq model and fallback chain as the AI Incident Analyst.

Figure 42. AI Security Assistant Chatbot panel.

**Idle Session Warning**. This warning appears when a user logged into the dashboard remains inactive—with no mouse or keyboard activity—for 15 minutes. If the user does not click the “Stay Active” button, the session will expire and the user will be automatically logged out.

Figure 43. Idle Session Warning dialog.

**External Notifications ****–**** Gmail**** ****&**** ****Telegram**** Bot**. The app sends alerts via SMTP email or the Telegram Bot API; the messages include details such as the attack, IP address, path, and action. 

Figure 44. External Notifications — email alert via Gmail SMTP. 

Figure 45. External Notifications — Telegram bot alert.

**vuln-web Shop.** The target application provides a simple e-commerce interface: product catalog, shopping cart, login, profile (with avatar upload field), file browser, and command execution page. When Phase 3 is enabled (VULN_UNSAFE_CMD=1), a red warning banner reading "⚠ LAB MODE – VULN_UNSAFE_CMD is enabled" appears on all pages.

Figure 46. vuln-web shop catalog page with Phase 3 lab mode banner.

**vuln-web 403 and 429 Pages.** When a blocked IP makes a request, middleware/security.py returns the FORBIDDEN_HTML template (HTTP 403) which displays the blocked IP address in a dark-themed error page. A rate-limited IP receives the TOO_MANY_REQUESTS_HTML template (HTTP 429) displaying the per-minute limit and a retry countdown.

Figure 47. vuln-web 403 Forbidden page.

Figure 48. vuln-web 429 Too Many Requests page.

 COMPONENT COST ANALYSIS

All software components used by Incidentra are open-source and carry no licensing cost. The table below presents the cost structure for two deployment scenarios: local demonstration (Docker Compose on a developer laptop) and an optional production deployment on a VPS.

| **No.** | **Item** | **Unit** | **Price per Unit (IDR)** | **Total (IDR)** |
| --- | --- | --- | --- | --- |
| 1 | Developer laptop | 2 | ~Rp12.000.000 | ~Rp 24.000.000 |
| 2 | VPS 2 vCPU / 4 GB RAM *(optional, production)* | 1 year | ~Rp 1.500.000 | ~Rp 1.500.000 |
| 3 | Domain .id *(optional)* | 1 year | ~Rp 150.000 | ~Rp 150.000 |
|  | **Total** |  |  | **~Rp 25.650.000** |

Table 6. Component Cost Analysis

The zero-cost local deployment makes Incidentra immediately accessible to small and medium enterprises without requiring any IT budget. The optional VPS deployment provides persistent availability for monitoring a production web server at a cost of approximately Rp 1.5–1.6 million per year — significantly below any commercial SIEM or WAF solution.

FUNCTIONAL TESTING

Testing was conducted against the Docker Compose deployment (six services: postgres, redis, vuln_web, backend, celery_worker, frontend). The SOC Dashboard was accessed at http://localhost:3000; the vuln-web target at [http://localhost:5050](http://localhost:5050).

D.1 — Authentication

| **No.** | **Scenario** | **Every Possible Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Successful login | username admin, password Admin@Incidentra2026!; click Sign In | JWT issued; redirect to Dashboard; all sidebar items visible | ✅ Pass |
| 2 | Wrong credentials | username admin, password wrongpass; click Sign In | HTTP 401 "Invalid credentials" displayed; user remains on login page | ✅ Pass |
| 3 | No token (API) | GET http://localhost:5000/api/incidents without Authorization header | HTTP 401 "Authorization required"; no data returned | ✅ Pass |

Table 7. Functional Testing — Authentication

D.2 — SQL Injection Detection

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Login POST SQLi (thesis defense demo) | http://localhost:5050/login — username admin' OR '1'='1' --, any password | Incident: SQL_INJECTION, severity=critical; POST_DATA in raw payload; IP in blocked_ips.json with escalating block (Offense #1, ~24h) | ✅ Pass |
| 2 | Automatic block enforcement | After step 1, open http://localhost:5050/ from the same IP | HTTP 403 Forbidden (Incidentra branding); Live Traffic shows **Blocked** on the next row | ✅ Pass |
| 3 | Reflected SQLi via search | http://localhost:5050/search?q=admin'+OR+'1'='1'-- | Incident: SQL_INJECTION, critical | ✅ Pass |
| 4 | Blind time-based SQLi | http://localhost:5050/search?q=1' AND SLEEP(5)-- | Incident: SQL_INJECTION if pattern matches | ✅ Pass |

Table 8. Functional Testing — SQL Injection Detection

D.3 — XSS Detection

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Reflected XSS via script tag | http://localhost:5050/profile?name=<script>alert(document.cookie)</script> | Incident: attack_type=XSS, severity=critical; escalating block (Offense #1, ~24h) | ✅ Pass |
| 2 | XSS event handler | http://localhost:5050/search?q=<img onerror=alert(1) src=x> | Incident: attack_type=XSS, severity=critical | ✅ Pass |
| 3 | Normal query | http://localhost:5050/search?q=laptop | No incident; entry appears as "Normal" in Live Traffic | ✅ Pass |

Table 9. Functional Testing — XSS Detection

D.4 — Path Traversal / LFI Detection

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Classic path traversal | http://localhost:5050/files?file=../../etc/passwd | Incident: attack_type=PATH_TRAVERSAL, severity=high; escalating block (Offense #1, ~1h) | ✅ Pass |
| 2 | Enforcement file targeting | http://localhost:5050/files?file=E:/path/blocked_ips.json | Incident: attack_type=PATH_TRAVERSAL | ✅ Pass |
| 3 | Normal file access | http://localhost:5050/files?file=readme.txt | No incident; Normal entry in Live Traffic | ✅ Pass |
| 4 | PHP wrapper (LFI) | http://localhost:5050/files?file=php://filter/convert.base64-encode/resource=index | Incident: attack_type=LFI_RFI, severity=critical; escalating block (Offense #1, ~24h) | ✅ Pass |

Table 10. Functional Testing — Path Traversal / LFI Detection

D.5 — File Upload Detection

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Safe upload — no incident | POST /files via form upload; file: notes.txt | Request logged in access.log; appears in Live Traffic as Normal; **no** FILE_UPLOAD incident | ✅ Pass |
| 2 | Dangerous upload — single extension | POST /files via form upload; file: shell.php | Log contains POST_DATA:file=shell.php; incident: attack_type=FILE_UPLOAD, severity=high; escalating block (Offense #1, ~1h) | ✅ Pass |
| 3 | Dangerous upload — double extension | POST /files via form upload; file: image.php.jpg | FILE_UPLOAD incident (matches double extension pattern) | ✅ Pass |
| 4 | Avatar CTF vector | POST /profile with field avatar=shell.php | Log contains POST_DATA:avatar=shell.php; FILE_UPLOAD incident created | ✅ Pass |

Table 11. Functional Testing — File Upload Detection

D.6 — Command Injection Detection

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Metacharacter payload | http://localhost:5050/cmd?cmd=;whoami | Incident: attack_type=COMMAND_INJECTION, severity=critical; escalating block (Offense #1, ~24h) | ✅ Pass |
| 2 | Plain keyword payload | http://localhost:5050/cmd?cmd=whoami | Incident: attack_type=COMMAND_INJECTION, severity=critical (pattern cmd=whoami) | ✅ Pass |
| 3 | Phase 3 OFF (default) | VULN_UNSAFE_CMD not set; /cmd?cmd=whoami | vuln-web displays [Simulated] Would execute: whoami; no real shell execution | ✅ Pass |
| 4 | Phase 3 ON | VULN_UNSAFE_CMD=1; restart vuln_web; /cmd?cmd=whoami | Real shell output; red warning banner on all pages; SOC still creates COMMAND_INJECTION incident | ✅ Pass |

Table 12. Functional Testing — Command Injection Detection

D.7 — Brute Force Detection

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Threshold-based detection | 10+ POST requests to /login with wrong passwords within 60 seconds | BRUTE_FORCE incident created on the 10th attempt (severity=high); escalating block (Offense #1, ~1h); subsequent requests receive HTTP 403 | ✅ IP Blocked |

Table 13. Functional Testing — Brute Force Detection

D.8 — Scanner Detection

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Scanner User-Agent | curl -A "Nikto/2.1.6" http://localhost:5050/ | Incident: SCANNER, medium; IP in the **Rate Limited** tab (not permanent block) | ✅ Pass |
| 2 | Rapid requests while rate-limited | 10+ requests/minute from the same IP after scanner detection | HTTP **429** from vuln-web | ✅ Pass |

Table 14. Functional Testing — Scanner Detection

D.9 — IP Block / Unblock / Whitelist

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Auto block (critical attack) | Any critical attack | IP in blocked_ips.json; HTTP 403 | ✅ Pass |
| 2 | Unblock via SOC | IP Management → Unblock → confirm | HTTP 200; shop loads normally | ✅ Pass |
| 3 | Manual block via SOC | "+ Block IP"; enter IP; select permanent; submit | IP added to blocked_ips.json; requests from that IP to vuln-web receive HTTP 403 | ✅ Pass |
| 4 | Whitelist IP | IP History drawer → Whitelist | No new incidents from IP; excluded from JSON block list | ✅ Pass |
| 5 | Whitelist a previously blocked IP | Same IP was previously blocked | Upsert succeeds (no 409 conflict); IP is whitelisted | ✅ Pass |

Table 15. Functional Testing — IP Block / Unblock / Whitelist

D.10 — Ongoing vs All Incidents

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Ongoing list | Navigate to /incidents | New + investigating incidents only | ✅ Pass |
| 2 | Resolve one incident | Change status → Resolved | Disappears from the ongoing list | ✅ Pass |
| 3 | All list | Navigate to /incidents/all | Resolved row is visible | ✅ Pass |

Table 16. Functional Testing — Ongoing vs All Incidents

D.11 — Export CSV

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Export ongoing | Export from /incidents | Download incidents-ongoing.csv; no resolved-only rows | ✅ Pass |
| 2 | Export all | Export from /incidents/all | Download incidents-all.csv; includes resolved and false positive | ✅ Pass |

Table 17. Functional Testing — Export CSV

D.12 — IP History Drawer

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Open drawer | Click IP on any incident row | History API; past incidents; enforcement status | ✅ Pass |
| 2 | Pattern summary | IP with multiple attacks | Attack type breakdown displayed | ✅ Pass |

Table 18. Functional Testing — IP History Drawer

D.13 — Lab Mode

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Enable lab mode | Settings → Lab mode → Save | Rules ⓘ warning; OWASP baseline disabled | ✅ Pass |
| 2 | Payload with no active CMD rule | No CMD rule active; cmd=;whoami | No incident created (lab only) | ✅ Pass |
| 3 | Custom UI rule active | Add regex rule; send matching payload | Incident created from UI rule only | ✅ Pass |
| 4 | Disable lab mode | Save | OWASP baseline re-enabled | ✅ Pass |

Table 19. Functional Testing — Lab Mode

D.14 — Bulk Resolve

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Select multiple incidents | Selection mode on Incidents page | Checkboxes visible per row | ✅ Pass |
| 2 | Apply bulk resolve | Confirm resolve | Toast success; rows move to All Incidents archive | ✅ Pass |

Table 20. Functional Testing — Bulk Resolve

D.15 — Detection Rules CRUD

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Create new rule | "+ Add Rule"; fill all fields; Create | Rule saved to detection_rules; Redis rules_dirty set; rule visible in table | ✅ Pass |
| 2 | Toggle rule inactive | Click active toggle on a rule | is_active=false saved to DB; engine skips rule on the next 60-second reload | ✅ Pass |
| 3 | Edit rule | Click edit; change severity; Save | DB record updated; rules_dirty set | ✅ Pass |
| 4 | Delete rule | Click delete; confirm | Rule removed from DB | ✅ Pass |
| 5 | Rule Testing Sandbox | Enter regex + test payload | Match/no-match result displayed | ✅ Pass |

Table 21. Functional Testing — Detection Rules CRUD

D.16 — AI Explanation

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Generate with Groq configured | Open incident; click "Generate AI Explanation" | AI panels: Summary, Why It's Dangerous, Recommended Actions, MITRE; model badge | ✅ Pass |
| 2 | Static fallback (no API key) | GROQ_API_KEY empty; trigger incident; generate | Static text; model_used = fallback-static | ✅ Pass |

Table 22. Functional Testing — AI Explanation

D.17 — Chatbot / Notifications / Session

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Chatbot query | Ask about SQLi regex | Groq or fallback reply | ✅ Pass |
| 2 | Notification bell | New incident (if alerts enabled) | Toast + badge increment | ✅ Pass |
| 3 | Test email/Telegram | Test button in Settings | Sent or clear error message (optional) | ✅ Pass |
| 4 | Session timeout | Idle past threshold | Warning dialog; logout on confirm | ✅ Pass |

Table 23. Functional Testing — Chatbot / Notifications / Session

D.18 — Live Traffic

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Attack vs Blocked sequence | /cmd?cmd=;whoami then refresh | Attack (200) row; Blocked (403) row | ✅ Pass |
| 2 | Hide static assets | Toggle checkbox | CSS/JS/favicon requests hidden | ✅ Pass |
| 3 | Normal traffic | Browse catalog without payloads | All rows tagged Normal (green) | ✅ Pass |

Table 24. Functional Testing — Live Traffic

D.19 — Simulate Attack

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | DB inject (Mode A) | Incidents → Simulate Attack → Mode A | Incident appears immediately without vuln-web | ✅ Pass |
| 2 | Log inject (Mode B) | Mode B → select attack type (e.g., LFI_RFI) | Toast success; incident appears ~5 seconds; visible in Live Traffic | ✅ Pass |

Table 25. Functional Testing — Simulate Attack

D.20 — Escalating Block / Repeat Offender

| **No.** | **Scenario** | **Input** | **Expected Output** | **Output Result** |
| --- | --- | --- | --- | --- |
| 1 | Second offense (same IP) | Repeat critical attack from same IP after first block expires or is unblocked | Block duration uses offense tier 2 (e.g., ~7 days for critical); incident_count incremented | ✅ Pass |
| 2 | Repeat Offender flag | Same IP triggers ≥ threshold offenses (default 3) | BlockedIP.is_repeat_offender=True; Repeat Offender badge visible in IP Management Blocked tab | ✅ Pass |
| 3 | Settings override | Settings → Escalating Block Policy → change REPEAT_OFFENDER_THRESHOLD or duration tiers → Save | Subsequent blocks use updated values from AppSetting | ✅ Pass |

Table 26. Functional Testing — Escalating Block / Repeat Offender

MANUAL GUIDE

E.1 — System Build Documentation (Developer Perspective)

The primary deployment method is Docker Compose, which provisions all six services with a single command and requires no manual database setup or virtual environment configuration.

**Prerequisites:** Git, Docker Desktop (Windows/macOS) or Docker Engine + Docker Compose v2 (Linux). The developer machine must have at least 8 GB RAM and ports 3000, 5000, 5050, 5432, and 6379 available.

**Step 1 — Clone the repository.**

																git clone https://github.com/HardInCode/incidentra.git

																cd incidentra

Figure 49. Step 1 — Clone repository command

**Step 2 — Configure the backend environment file.**

																copy backend\.env.docker.example backend\.env.docker   *# Windows*

																*# or*

																cp backend/.env.docker.example backend/.env.docker     *# Linux/macOS*

Figure 50. Step 2 — Configure backend environment file command

Open backend/.env.docker and fill in the optional keys: GROQ_API_KEY (from console.groq.com, free tier), ABUSEIPDB_API_KEY, and SMTP/Telegram credentials. Core detection and blocking operate without any external API keys.

**Step 3 — Build and start all containers.**

																docker compose up --build -d

Figure 51. Step 3 — Build and start all containers command

Docker Compose starts six services: postgres (port 5432), redis (port 6379), vuln_web (port 5050), backend (port 5000), frontend (port 3000, served by Nginx), and celery_worker. The backend entrypoint script (docker_entrypoint.sh) runs db.create_all(), seeds admin and analyst users and 18 default detection rules, then starts Gunicorn. The log monitor thread starts automatically and begins tailing the shared vuln_logs volume.

**Step 4 — Access the system.**

- SOC Dashboard: 

http://localhost:3000 — Login with admin / Admin@Incidentra2026!

- vuln-web target: 

http://localhost:5050

**Step 5 — Verify operation.**

Browse http://localhost:5050 and confirm that new entries appear in Live Traffic within 3–6 seconds.

**Step 6 — Enable Phase 3 (optional, isolated lab only).**

docker-compose.yml already includes VULN_UNSAFE_CMD: "1" and VULN_UNSAFE_UPLOAD: "1" in the vuln_web service. To disable them, remove or set to "0" then restart:

																docker compose restart vuln_web

Figure 52. Step 6 — Restart vuln-web command

A red warning banner will appear on all vuln-web pages when Phase 3 is active.

**Step 7 — Reset for demonstration (Docker).**

From the repository root (with the Docker stack running):

																$env:DATABASE_URL ="postgresql+psycopg://postgres:HrdnxPostgres@localhost:5432/incidentra_db"

																$env:REDIS_URL = "redis://localhost:6379/0"

																python scripts/reset_incidentra_docker.ps1

																

																docker compose exec vuln_web sh -c ":> /app/logs/access.log"

																docker compose exec vuln_web sh -c 'echo "{\"blocked\":[],\"updated_at\":\"\"}" > /app/logs/blocked_ips.json'

																docker compose exec vuln_web sh -c 'echo "{\"rate_limited\":[],\"updated_at\":\"\"}" > /app/logs/rate_limited.json'

																

																docker compose restart backend vuln_web

Figure 53. Step 7 — Reset for demonstration commands (Docker)

**Manual alternative (3 terminals):**

- Terminal 1: cd backend && pip install -r requirements.txt && python run.py

- Terminal 2: cd frontend && npm install && npm start

- Terminal 3: cd vuln-web && pip install -r requirements.txt && python app.py

PostgreSQL and Redis must be running locally. Copy backend/.env.example to backend/.env and set DATABASE_URL, REDIS_URL, and WEB_SERVER_LOG_PATH to the absolute path of vuln-web/logs/access.log.

E.2 — End-User System Installation (User Perspective)

Incidentra is a server-side platform. End-user installation requires no software on the administrator's workstation beyond a modern web browser.

| **Component** | **Requirement** |
| --- | --- |
| Server | VPS with Ubuntu 22.04+ and Docker Engine + Docker Compose v2; minimum 2 vCPU, 4 GB RAM, 20 GB disk |
| Alternative | Single PC with Windows 10/11 or macOS with Docker Desktop |
| Browser (SOC user) | Google Chrome or Microsoft Edge (latest version); access http://<server-ip>:3000 |
| Monitored application | Any web application writing NCSA Combined Log Format; replace the vuln-web log path with the production log path via WEB_SERVER_LOG_PATH in backend/.env.docker |
| Network | Expose port 3000 (SOC UI) to trusted administrator IPs only; port 5000 (API) must not be publicly accessible; port 5050 (vuln-web) is for demonstration only |
| External APIs *(optional)* | Outbound HTTPS to api.groq.com, api.abuseipdb.com, smtp.gmail.com:587, api.telegram.org |

Table 27. End-User System Requirements (E.2)

No client-side installation is required. The SOC Dashboard is served as a pre-built React application by Nginx and is accessed entirely in the browser.

E.3 — User Guide per User Role

Incidentra defines three user roles, each with a distinct set of responsibilities and access paths within the system.

| **Role** | **Access Level** | **Primary Responsibilities** | **Typical Workflow** |
| --- | --- | --- | --- |
| **Admin** | Full SOC access + Audit Log | Manage detection rules; block or unblock IPs; configure API keys and thresholds; review audit logs; assign incidents; export reports | Login → Dashboard (review KPIs) → Incidents (filter Critical/High → open incident → Generate AI Explanation → add notes → mark Resolved) → IP Management (unblock false positives) → Detection Rules (add/edit rules) → Settings (update Groq key) |
| **Analyst** | Read + update incident status | Monitor live threats; triage incidents; review AI explanation; annotate notes; update status | Login → Dashboard (check 24-hour count) → Live Traffic (monitor Attack tags) → Incidents (filter New/Investigating → open critical incident → review details → add notes → change status to Investigating) |
| **Lab User** (vuln-web demo) | vuln-web only (no SOC access) | Browse catalog; demonstrate attack payloads for lab exercises | Open http://localhost:5050 → browse catalog → try payloads (search, files, cmd, login) → observe 403/429 responses after SOC detection |

Table 28. User Role Access and Responsibilities (E.3)

Detailed procedure — Admin: Unblock IP

- Open http://localhost:3000 in a browser and sign in as admin.

- In the left sidebar, click IP Management.

- Ensure the Blocked tab is selected.

- Locate the IP address to unblock.

- Click the Unblock icon in the Actions column; confirm in the dialog.

- Verify: navigate to http://localhost:5050 — the shop catalog should load normally (HTTP 200).

Detailed procedure — Admin: Add Custom Detection Rule

- In the sidebar, click Detection Rules.

- Click + Add Rule in the upper right.

- Fill in Rule Name, select Attack Type from the dropdown, select Severity, and enter the Regex Pattern.

- Click Create. The rule appears in the table with match_count = 0.

- Within 60 seconds (or immediately if the Redis rules_dirty flag is set), the Detection Engine reloads and includes the new pattern.

Detailed procedure — Admin: Whitelist a Trusted IP

- Click an IP address on any incident row.

- The IP History drawer opens — review the incident history for that IP.

- Click the Whitelist button in the drawer; confirm.

- Verify: no new incidents are created from that IP; the IP does not appear in blocked_ips.json.

Detailed procedure — Analyst: Triage a Critical Incident

- From the Dashboard, observe a spike in the Incident Timeline or a new entry in the last-24-hours card.

- Click Incidents in the sidebar; apply filters Severity = Critical, Status = New.

- Click a row to open the Incident Detail page.

- Review Source IP, Attack Type, HTTP Path, Raw Payload, and Automated Actions.

- Click Generate AI Explanation; review the Summary and Recommended Actions panels.

- In the Investigation Notes section, type an observation and click + Add.

- Change the status dropdown from New to Investigating (or Resolved if the threat has been remediated).

** **

**REFERENCES**

- OWASP Top 10 (2021) — A03 Injection, A04 Insecure Design. [https://owasp.org/Top10/](https://owasp.org/Top10/)

- MITRE ATT&CK — Enterprise matrix. [https://attack.mitre.org/](https://attack.mitre.org/)

- NCSA Combined Log Format — web server logging conventions.

- Flask Documentation — [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)

- React 18 Documentation — [https://react.dev/](https://react.dev/)

- PostgreSQL 15 Documentation — [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)

- Redis Documentation — [https://redis.io/docs/](https://redis.io/docs/)

- Docker Compose Specification — [https://docs.docker.com/compose/](https://docs.docker.com/compose/)

- Groq API Documentation — [https://console.groq.com/docs](https://console.groq.com/docs)

- AbuseIPDB API v2 — [https://www.abuseipdb.com/api-documentation](https://www.abuseipdb.com/api-documentation)

- Material UI (MUI) — [https://mui.com/](https://mui.com/)

- Chart.js — [https://www.chartjs.org/](https://www.chartjs.org/)

2