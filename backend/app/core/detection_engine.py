"""
DETECTION ENGINE — regex + threshold → threat dict atau None.
Ctrl+F: analyze, DETECTION_PATTERNS, BruteForceTracker, SEVERITY, PIPELINE

Urutan baca file ini (sesuai alur runtime):
  ① DETECTION_PATTERNS     → baseline OWASP (hardcoded regex)
  ② BruteForceTracker      → counter POST /login (bukan regex)
  ③ DetectionEngine        → compile rules + method analyze()
  ④ get_redis_client()     → helper koneksi Redis (optional)

Alur dipanggil dari log_monitor._process_log_line():
  parse_log_line(entry) → engine.analyze(entry) → threat dict | None
    → (jika threat) dedup → INSERT incident → responder.respond()
"""
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import redis
import os
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# ① DETECTION_PATTERNS — baseline OWASP (hardcoded, bukan AI)
#    Digabung dengan rule analyst dari PostgreSQL kecuali Lab mode (UI rules only).
#    AI explain terpisah: backend/app/services/ai_service.py (Groq on-demand).
# ═══════════════════════════════════════════════════════════════════════════════

DETECTION_PATTERNS = {
    'SQL_INJECTION': {
        'patterns': [
            r"(?i)(union\s+select|select\s+(\*|[\w]+\s*,\s*[\w\s,`]*|count\s*\([\w\s,*)]*\))\s+from\s+\w|insert\s+into\s+\w+\s*\(|drop\s+table\s+\w|delete\s+from\s+\w|update\s+\w+\s+set\s+\w)",
            r"(?i)(\bor\b\s+[\'\"]?\d+[\'\"]?\s*=\s*[\'\"]?\d+[\'\"]?)",  # ← classic ' OR '1'='1
            r"(?i)(\'|\")(\s*;\s*|\s+or\s+|\s+and\s+).*?(--|#|/\*)",
            r"(?i)(sleep\s*\(|benchmark\s*\(|waitfor\s+delay)",
            r"(?i)(information_schema|sys\.tables|sysobjects|syscolumns)",
            r"(?i)(char\s*\(\d+\)|concat\s*\(|group_concat\s*\()",
            r"(?i)(\bexec\b|\bexecute\b)\s*(\(|xp_)",
            r"(?i)(load_file\s*\(|into\s+outfile\s+|into\s+dumpfile)",
            r"(?i)(\bcast\s*\(|\bconvert\s*\()\s*.*\s+(as|using)\s+\w+",
            r"(?i)(order\s+by\s+\d+|group\s+by\s+\d+.*having)",
        ],
        'severity': 'critical',  # ← dipakai RESPONSE_ACTIONS → escalating_block
        'mitre': 'T1190 - Exploit Public-Facing Application',
    },
    'XSS': {
        'patterns': [
            r"(?i)(<script[\s>]|</script>|<script/?>)",
            r"(?i)(javascript\s*:|vbscript\s*:)",
            r"(?i)(onerror\s*=|onload\s*=|onclick\s*=|onmouseover\s*=|onfocus\s*=|onblur\s*=)",
            r"(?i)(<iframe[\s>]|<object[\s>]|<embed[\s>]|<form[\s>])",
            r"(?i)(alert\s*\(|confirm\s*\(|prompt\s*\(|document\.cookie|document\.write)",
            r"(?i)(eval\s*\(|setTimeout\s*\(|setInterval\s*\(|Function\s*\()",
            r"(?i)(fromcharcode|&#x[0-9a-f]+;|&#\d+;)",
            r"(?i)(expression\s*\(|url\s*\(.*javascript)",
            r"(?i)(<img[^>]+src\s*=\s*['\"]?\s*javascript)",
            r"(?i)(svg/onload|data:text/html)",
        ],
        'severity': 'critical',
        'mitre': 'T1059.007 - JavaScript',
    },
    'BRUTE_FORCE': {
        'patterns': [],  # ← kosong sengaja — deteksi pakai BruteForceTracker (threshold), bukan regex
        'severity': 'high',
        'mitre': 'T1110 - Brute Force',
        'threshold_based': True,  # ← flag: skip _compile_patterns(); logic di analyze() baris ~380
    },
    'PATH_TRAVERSAL': {
        'patterns': [
            r"(?i)(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\/|\.\.%2f|%2e\.\/)",
            r"(?i)(\/etc\/passwd|\/etc\/shadow|\/etc\/hosts|\/windows\/system32)",
            r"(?i)(boot\.ini|win\.ini|system\.ini)",
            r"(?i)(%252e%252e|%c0%ae|%c0%af)",
            r"(?i)(blocked_ips\.json|rate_limited\.json)",
            r"(?i)([/\\]logs[/\\])",
            r"(?i)(\?file=|[&;]\s*file=)[a-zA-Z]:[/\\]",
        ],
        'severity': 'high',
        'mitre': 'T1083 - File and Directory Discovery',
    },
    'FILE_UPLOAD': {
        # Incident hanya untuk ekstensi berbahaya (.php, .jsp, …) — bukan .txt/.pdf biasa
        'patterns': [
            # log_parser simpan POST body sebagai "file=name" (prefix POST_DATA: sudah di-strip di parser)
            r'(?i)(?:POST_DATA:)?(?:file|avatar)=[^&\s"]*\.(php\d*|phtml|phar|jsp|asp|aspx|exe|dll|sh|bat|cmd|ps1|htaccess|cgi)\b',
            r'(?i)(?:POST_DATA:)?(?:file|avatar)=[^&\s"]*\.(php|jsp|asp|aspx)[^&\s"]*\.(jpg|jpeg|png|gif|txt|pdf)\b',
        ],
        'severity': 'high',
        'mitre': 'T1105 - Ingress Tool Transfer',
    },
    'COMMAND_INJECTION': {
        'patterns': [
            r"(?i)(;|\||&&|\$\(|`)\s*(ls|cat|whoami|id|uname|wget|curl|bash|sh|nc|netcat|ping|python|perl|ruby)",
            r"(?i)(\bexec\b|\bsystem\b|\bpassthru\b|\bshell_exec\b|\bpopen\b)\s*\(",
            r"(?i)(\/bin\/sh|\/bin\/bash|\/usr\/bin\/perl|\/usr\/bin\/python)",
            r"(?i)(\bchmod\s+\d+|\bchown\s+|\brm\s+-|\bmv\s+|\bcp\s+)\s+\/",
            # vuln-web /cmd?cmd=whoami — query di log = "cmd=..." (tanpa leading semicolon)
            r"(?i)\bcmd=\s*[^&\s\"]*\b(whoami|id|uname|ls|pwd|cat|ping|nc|netcat|wget|curl)\b",
            r"(?i)\bcmd=[^&\s\"]*[;&|`]",
        ],
        'severity': 'critical',
        'mitre': 'T1059 - Command and Scripting Interpreter',
    },
    'SCANNER': {
        'patterns': [
            r"(?i)(nikto|nmap|masscan|sqlmap|acunetix|nessus|openvas|burpsuite|zaproxy|dirbuster|gobuster)",
            r"(?i)(python-requests\/|go-http-client\/|java\/|libwww-perl\/|curl\/\d+.*\d+.*\d+\s*$)",
            r"(?i)(zgrab|zgrabber|wfuzz|hydra|medusa|nuclei)",
        ],
        'severity': 'medium',  # ← RESPONSE_ACTIONS → rate_limit (bukan block langsung)
        'mitre': 'T1595 - Active Scanning',
    },
    'LFI_RFI': {
        'patterns': [
            r"(?i)(php://input|php://filter|php://data|expect://|data://)",
            r"(?i)(file=https?://|page=https?://|url=https?://|path=https?://)",
            # Query di parser tanpa "?" — match file= / ?file= / &file= (vuln-web /files?file=../../)
            r"(?i)(?:\?file=|[&;\s]file=|file=)[^&\s\"]*\.\.",
            r"(?i)(?:\?page=|\?path=|\?template=|\?include=)[^&\s\"]*\.\.",
        ],
        'severity': 'critical',
        'mitre': 'T1190 - Exploit Public-Facing Application',
    },
    'CSRF': {
        'patterns': [
            r"(?i)(csrf|xsrf).*token.*missing",  # ← vuln-web logging.py tulis ke access.log
        ],
        'severity': 'medium',
        'mitre': 'T1185 - Browser Session Hijacking',
    },
}

# SEVERITY: tie-breaker multi-match — bukan sumber severity (sumber=rule DB / DETECTION_PATTERNS)
SEVERITY_WEIGHTS = {
    'critical': 100,
    'high': 70,
    'medium': 40,
    'low': 10,
}

# SEVERITY → PIPELINE step 4: severity menentukan aksi respond()
RESPONSE_ACTIONS = {
    'low': 'log_and_monitor',       # ← hanya log, tidak block
    'medium': 'rate_limit',         # ← throttle request
    'high': 'escalating_block',     # ← block IP (escalating = durasi naik kalau repeat)
    'critical': 'escalating_block',
}


# ═══════════════════════════════════════════════════════════════════════════════
# ② BruteForceTracker — sliding window counter POST login (Redis + fallback lokal)
#    Key Redis: bf:{ip}:{path} — sorted set timestamp attempt
# ═══════════════════════════════════════════════════════════════════════════════

class BruteForceTracker:
    """In-memory + Redis brute force tracker"""

    def __init__(self, redis_client=None, window_seconds=60, threshold=10):
        self.window = window_seconds                        # ← sliding window detik (Settings DB / .env)
        self.threshold = threshold                          # ← attempt ke-N yang trigger incident (default 10)
        self._local: Dict[str, deque] = defaultdict(deque)  # ← fallback kalau Redis down
        self.redis = redis_client                           # ← dari log_monitor start_monitor(redis_client=...)

    def record_attempt(self, ip: str, path: str) -> int:
        """Catat 1 POST login attempt; return jumlah attempt dalam window."""
        now = time.time()
        key = f"bf:{ip}:{path}"  # ← contoh: bf:151.158.106.34:/login

        if self.redis:
            try:
                pipe = self.redis.pipeline()
                pipe.zadd(key, {str(now): now})                          # tambah timestamp attempt
                pipe.zremrangebyscore(key, 0, now - self.window)         # buang attempt di luar window
                pipe.zcard(key)                                          # hitung sisa attempt
                pipe.expire(key, self.window * 2)                        # TTL agar key tidak menumpuk
                results = pipe.execute()
                return results[2]  # ← zcard = jumlah attempt dalam window
            except Exception:
                pass  # ← Redis error → fallback _local di bawah

        # Fallback local (dev tanpa Redis)
        dq = self._local[key]
        dq.append(now)
        while dq and dq[0] < now - self.window:  # buang attempt lama dari deque kiri
            dq.popleft()
        return len(dq)

    def is_brute_force(self, ip: str, path: str) -> bool:
        """True hanya saat attempt == threshold (crossing pertama), bukan setiap attempt setelahnya."""
        return self.record_attempt(ip, path) == self.threshold  # ← True hanya saat count == threshold (1 incident per crossing)

    def clear_ip(self, ip: str):
        """Reset counter untuk IP (dipanggil saat admin unblock di BlockedIPs UI)."""
        prefix = f"bf:{ip}:"
        for key in list(self._local.keys()):
            if key.startswith(prefix):
                del self._local[key]
        if self.redis:
            try:
                for key in self.redis.scan_iter(f"{prefix}*"):
                    self.redis.delete(key)
            except Exception:
                pass


# ─── Global ref engine aktif — dipakai clear_brute_force_state() saat unblock ───
_active_engine: Optional['DetectionEngine'] = None


def register_detection_engine(engine: 'DetectionEngine'):
    """Dipanggil log_monitor start_monitor() sekali — simpan ref untuk API unblock."""
    global _active_engine
    _active_engine = engine


def clear_brute_force_state(ip: str):
    """Dipanggil response_manager / blocked IP API saat admin unblock IP."""
    if _active_engine:
        _active_engine.bf_tracker.clear_ip(ip)


# ═══════════════════════════════════════════════════════════════════════════════
# ③ DetectionEngine — compile patterns + analyze(entry)
#    Dibuat sekali di log_monitor._run() — analyze() dipanggil per baris log
# ═══════════════════════════════════════════════════════════════════════════════

class DetectionEngine:
    def __init__(self, redis_client=None):
        from app.core.settings_reader import get_rate_limit_window, get_brute_force_threshold
        self.redis = redis_client  # ← rules_dirty flag + BruteForceTracker shared Redis
        self.bf_tracker = BruteForceTracker(
            redis_client=redis_client,
            window_seconds=get_rate_limit_window(),       # ← Settings DB
            threshold=get_brute_force_threshold(),        # ← Settings DB (default 10)
        )
        self._compiled = self._compile_patterns()         # ← fallback OWASP-only kalau DB belum load
        self._last_rules_reload = time.time()
        self._rules_reload_interval = 60  # detik — poll reload rule dari DB
        self._lab_mode_cached = None      # ← cache is_lab_mode_ui_only()

    def _compile_patterns(self):
        """Compile regex baseline OWASP saja (startup fallback sebelum _load_rules_from_db)."""
        compiled = {}
        for attack_type, info in DETECTION_PATTERNS.items():
            if not info.get('threshold_based'):  # skip BRUTE_FORCE — tidak punya regex
                compiled[attack_type] = [re.compile(p) for p in info['patterns']]
        return compiled

    def _refresh_runtime_settings(self):
        """Refresh threshold dari Settings setiap analyze() — perubahan UI langsung efektif."""
        from app.core.settings_reader import (
            get_rate_limit_window,
            get_brute_force_threshold,
            is_lab_mode_ui_only,
        )
        self.bf_tracker.window = get_rate_limit_window()
        self.bf_tracker.threshold = get_brute_force_threshold()
        self._lab_mode_cached = is_lab_mode_ui_only()

    def _load_rules_from_db(self):
        """Load rule analyst aktif dari PostgreSQL + merge OWASP baseline (kecuali Lab mode).

        BRUTE_FORCE = threshold only — tidak compile regex.
        Output: self._compiled_db = { patterns, lab_only, brute_force_enabled }
        """
        try:
            from app.core.settings_reader import is_lab_mode_ui_only
            from app.models import DetectionRule
            lab_only = is_lab_mode_ui_only()  # ← Settings: Lab mode = UI rules only
            self._lab_mode_cached = lab_only
            rules = DetectionRule.query.filter_by(is_active=True).all()  # ← tabel detection_rules
            active_bf_rule = any(r.attack_type == 'BRUTE_FORCE' for r in rules)
            compiled = {}
            for rule in rules:
                attack_type = rule.attack_type
                if attack_type == 'BRUTE_FORCE':
                    # BRUTE_FORCE hanya threshold — placeholder list kosong
                    if 'BRUTE_FORCE' not in compiled:
                        compiled['BRUTE_FORCE'] = []
                    continue
                try:
                    if attack_type not in compiled:
                        compiled[attack_type] = []
                    compiled[attack_type].append({
                        'pattern': re.compile(rule.pattern, re.IGNORECASE),  # ← regex dari analyst
                        'severity': rule.severity_level.value,
                        'rule_id': rule.id,  # ← dipakai statistik match_count di log_monitor
                    })
                except re.error as e:
                    logger.warning(f"Invalid regex in rule {rule.id}: {e}")
            # Pastikan entry threshold_based ada meski tidak ada rule DB
            for attack_type, info in DETECTION_PATTERNS.items():
                if info.get('threshold_based') and attack_type not in compiled:
                    compiled[attack_type] = []

            # OWASP baseline (production default). Dilewati kalau Lab mode aktif.
            if not lab_only:
                for attack_type, info in DETECTION_PATTERNS.items():
                    if info.get('threshold_based'):
                        continue
                    if attack_type not in compiled:
                        compiled[attack_type] = []
                    for raw in info['patterns']:
                        compiled[attack_type].append({
                            'pattern': re.compile(raw, re.IGNORECASE),
                            'severity': info['severity'],
                            'rule_id': None,  # ← baseline OWASP — bukan rule DB spesifik
                        })
            else:
                logger.info("Detection lab mode: UI rules only (OWASP baseline disabled)")

            self._compiled_db = {
                'patterns': compiled,
                'lab_only': lab_only,
                'brute_force_enabled': (not lab_only) or active_bf_rule,
            }
            n_patterns = sum(len(v) for v in compiled.values())
            logger.debug(
                "Loaded %s patterns from DB (lab_only=%s, brute_force=%s)",
                n_patterns, lab_only, (not lab_only) or active_bf_rule,
            )
        except Exception as e:
            logger.warning(f"Could not load rules from DB (using defaults): {e}")
            self._compiled_db = None  # ← fallback ke self._compiled (OWASP hardcoded)

    def _maybe_reload_rules(self):
        """Reload rule kalau Redis rules_dirty (analyst edit rule) atau interval 60 detik."""
        now = time.time()
        dirty = False
        if self.redis:
            try:
                dirty = bool(self.redis.get('rules_dirty'))  # ← ditulis rules.py saat create/update/delete rule
                if dirty:
                    self.redis.delete('rules_dirty')
            except Exception:
                pass
        if not dirty and (now - self._last_rules_reload < self._rules_reload_interval):
            return  # belum waktunya reload
        self._last_rules_reload = now
        self._load_rules_from_db()

    def _get_compiled(self):
        """Ambil pattern compiled — prefer DB merge kalau _compiled_db sudah load."""
        if hasattr(self, '_compiled_db') and self._compiled_db is not None:
            return self._compiled_db['patterns']
        return self._compiled  # ← fallback startup sebelum DB query sukses

    def _brute_force_enabled(self) -> bool:
        """Lab mode: brute force hanya aktif kalau analyst punya rule BRUTE_FORCE aktif."""
        if hasattr(self, '_compiled_db') and self._compiled_db is not None:
            return self._compiled_db.get('brute_force_enabled', True)
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # analyze() — ENTRY POINT deteksi (dipanggil log_monitor baris 134)
    # Input:  entry dict dari parse_log_line (ip, method, path, query, user_agent, status_code, raw)
    # Output: threat dict → log_monitor INSERT incident | None → skip (bukan threat)
    # ═══════════════════════════════════════════════════════════════════════════

    def analyze(self, log_entry: dict) -> Optional[dict]:
        """
        Analyze a parsed log entry and return a threat dict or None.
        log_entry keys: ip, method, path, query, user_agent, status_code, raw
        """
        # Step 1–2: refresh Settings + reload rule DB kalau dirty / interval
        self._refresh_runtime_settings()
        self._maybe_reload_rules()

        # Step 3: whitelist check — IP di BlockedIPs is_whitelist=True → skip total
        ip = log_entry.get('ip', '')
        if ip:
            try:
                from app.models import BlockedIP
                if BlockedIP.query.filter_by(ip_address=ip, is_whitelist=True).first():
                    return None  # ← trusted IP — tidak buat incident
            except Exception as e:
                logger.debug(f"whitelist check skipped: {e}")

        # Step 4: ambil field entry — query sudah berisi POST body (log_parser Langkah D)
        path = log_entry.get('path', '')
        query = log_entry.get('query', '')           # ← POST_DATA:username=... sudah di sini
        user_agent = log_entry.get('user_agent', '')
        method = log_entry.get('method', '')
        status_code = log_entry.get('status_code', 200)

        # Step 4b: gabung string untuk regex scan — method penting untuk POST /files + file=...
        searchable = f"{method} {path} {query} {user_agent}"

        threats = []  # ← kumpulkan semua match; nanti pilih score tertinggi
        compiled = self._get_compiled()  # ← DB rules + OWASP baseline (atau fallback _compiled)

        # Step 5: loop regex per attack_type
        for attack_type, patterns in compiled.items():
            if not patterns:  # ← BRUTE_FORCE punya list kosong — skip loop regex
                continue
            for p in patterns:
                # Format lama: list compiled regex | Format baru DB: dict { pattern, severity, rule_id }
                if isinstance(p, dict):
                    pattern = p['pattern']
                    severity = p.get('severity', DETECTION_PATTERNS.get(attack_type, {}).get('severity', 'medium'))
                else:
                    pattern = p
                    severity = DETECTION_PATTERNS.get(attack_type, {}).get('severity', 'medium')
                match = pattern.search(searchable)  # ← regex match di string gabungan
                if match:
                    mitre = DETECTION_PATTERNS.get(attack_type, {}).get('mitre', 'T1190')
                    threats.append({
                        'attack_type': attack_type,
                        'severity': severity,
                        'mitre': mitre,
                        'matched_text': match.group(0)[:200],  # ← potong 200 char untuk DB/UI
                        'score': SEVERITY_WEIGHTS.get(severity, 40),
                    })
                    break  # ← satu attack_type cukup 1 match — lanjut type berikutnya

        # Step 6: brute force — POST ke path login, status 200/401/403, counter >= threshold
        login_paths = ['/login', '/admin', '/wp-login', '/signin', '/auth', '/api/auth/login']
        is_login_path = any(lp in path.lower() for lp in login_paths)
        is_post = method.upper() == 'POST'
        if is_login_path and is_post and status_code in [200, 401, 403] and self._brute_force_enabled():
            if self.bf_tracker.is_brute_force(ip, path):  # ← True saat attempt == threshold
                info = DETECTION_PATTERNS['BRUTE_FORCE']
                threats.append({
                    'attack_type': 'BRUTE_FORCE',
                    'severity': info['severity'],
                    'mitre': info['mitre'],
                    'matched_text': f'Multiple POST requests to {path} (threshold exceeded)',
                    'score': SEVERITY_WEIGHTS[info['severity']],
                })

        # Step 7: edge case — ?file=../../ tanpa php:// → PATH_TRAVERSAL saja, buang LFI_RFI
        if threats:
            types = {t['attack_type'] for t in threats}
            if 'PATH_TRAVERSAL' in types and 'LFI_RFI' in types:
                s = searchable.lower()
                has_remote_include = (
                    'php://' in s or 'expect://' in s or 'data://' in s
                    or re.search(r'https?://', s)
                )
                if not has_remote_include:
                    threats = [t for t in threats if t['attack_type'] != 'LFI_RFI']

        # Step 8: tidak ada match → bukan threat
        if not threats:
            return None  # ← log_monitor baris 135–136: if not threat → return None

        # Step 9–11: pilih severity tertinggi (score max) → bangun threat dict final
        primary = max(threats, key=lambda t: t['score'])  # SEVERITY: pilih match score tertinggi

        return {
            'ip': ip,
            'attack_type': primary['attack_type'],
            'severity': primary['severity'],  # SEVERITY: decide di sini — rule DB atau DETECTION_PATTERNS default
            'mitre_technique': primary['mitre'],
            'raw_payload': log_entry.get('raw', '')[:1000],  # ← baris log mentah (potong)
            'request_path': path[:500],
            'request_method': method,
            'user_agent': user_agent[:500],
            'response_code': status_code,
            'matched_text': primary['matched_text'],       # ← substring yang kena regex
            'recommended_action': RESPONSE_ACTIONS[primary['severity']],  # PIPELINE: log_monitor → respond() baca ini
            'all_threats': threats,  # ← semua match (kalau multi-type); primary = yang dipakai incident
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ④ get_redis_client() — helper standalone (bukan method class)
# ═══════════════════════════════════════════════════════════════════════════════

def get_redis_client():
    """Buat koneksi Redis dari REDIS_URL — return None kalau unreachable."""
    try:
        r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        r.ping()
        return r
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        return None
