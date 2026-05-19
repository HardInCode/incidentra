import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import redis
import os
import logging

logger = logging.getLogger(__name__)

# ─── OWASP-based Detection Patterns ──────────────────────────────────────────

DETECTION_PATTERNS = {
    'SQL_INJECTION': {
        'patterns': [
            r"(?i)(union\s+select|select\s+(\*|[\w]+\s*,\s*[\w\s,`]*|count\s*\([\w\s,*)]*\))\s+from\s+\w|insert\s+into\s+\w+\s*\(|drop\s+table\s+\w|delete\s+from\s+\w|update\s+\w+\s+set\s+\w)",
            r"(?i)(\bor\b\s+[\'\"]?\d+[\'\"]?\s*=\s*[\'\"]?\d+[\'\"]?)",
            r"(?i)(\'|\")(\s*;\s*|\s+or\s+|\s+and\s+).*?(--|#|/\*)",
            r"(?i)(sleep\s*\(|benchmark\s*\(|waitfor\s+delay)",
            r"(?i)(information_schema|sys\.tables|sysobjects|syscolumns)",
            r"(?i)(char\s*\(\d+\)|concat\s*\(|group_concat\s*\()",
            r"(?i)(\bexec\b|\bexecute\b)\s*(\(|xp_)",
            r"(?i)(load_file\s*\(|into\s+outfile\s+|into\s+dumpfile)",
            r"(?i)(\bcast\s*\(|\bconvert\s*\()\s*.*\s+(as|using)\s+\w+",
            r"(?i)(order\s+by\s+\d+|group\s+by\s+\d+.*having)",
        ],
        'severity': 'critical',
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
        'patterns': [],  # threshold-based, not regex
        'severity': 'high',
        'mitre': 'T1110 - Brute Force',
        'threshold_based': True,
    },
    'PATH_TRAVERSAL': {
        'patterns': [
            r"(?i)(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\/|\.\.%2f|%2e\.\/)",
            r"(?i)(\/etc\/passwd|\/etc\/shadow|\/etc\/hosts|\/windows\/system32)",
            r"(?i)(boot\.ini|win\.ini|system\.ini)",
            r"(?i)(%252e%252e|%c0%ae|%c0%af)",
        ],
        'severity': 'high',
        'mitre': 'T1083 - File and Directory Discovery',
    },
    'COMMAND_INJECTION': {
        'patterns': [
            r"(?i)(;|\||&&|\$\(|`)\s*(ls|cat|whoami|id|uname|wget|curl|bash|sh|nc|netcat|ping|python|perl|ruby)",
            r"(?i)(\bexec\b|\bsystem\b|\bpassthru\b|\bshell_exec\b|\bpopen\b)\s*\(",
            r"(?i)(\/bin\/sh|\/bin\/bash|\/usr\/bin\/perl|\/usr\/bin\/python)",
            r"(?i)(\bchmod\s+\d+|\bchown\s+|\brm\s+-|\bmv\s+|\bcp\s+)\s+\/",
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
        'severity': 'medium',
        'mitre': 'T1595 - Active Scanning',
    },
    'LFI_RFI': {
        'patterns': [
            r"(?i)(php://input|php://filter|php://data|expect://|data://)",
            r"(?i)(file=https?://|page=https?://|url=https?://|path=https?://)",
            r"(?i)(\?file=|\?page=|\?path=|\?template=|\?include=).*\.\.",
        ],
        'severity': 'critical',
        'mitre': 'T1190 - Exploit Public-Facing Application',
    },
    'CSRF': {
        'patterns': [
            r"(?i)(csrf|xsrf).*token.*missing",
        ],
        'severity': 'medium',
        'mitre': 'T1185 - Browser Session Hijacking',
    },
}

# Severity weights for scoring
SEVERITY_WEIGHTS = {
    'critical': 100,
    'high': 70,
    'medium': 40,
    'low': 10,
}

# Response actions per severity
RESPONSE_ACTIONS = {
    'low': 'log_and_monitor',
    'medium': 'rate_limit',
    'high': 'temporary_block',
    'critical': 'permanent_block',
}


class BruteForceTracker:
    """In-memory + Redis brute force tracker"""

    def __init__(self, redis_client=None, window_seconds=60, threshold=10):
        self.window = window_seconds
        self.threshold = threshold
        self._local: Dict[str, deque] = defaultdict(deque)
        self.redis = redis_client

    def record_attempt(self, ip: str, path: str) -> int:
        now = time.time()
        key = f"bf:{ip}:{path}"

        if self.redis:
            try:
                pipe = self.redis.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.zremrangebyscore(key, 0, now - self.window)
                pipe.zcard(key)
                pipe.expire(key, self.window * 2)
                results = pipe.execute()
                return results[2]
            except Exception:
                pass

        # Fallback local
        dq = self._local[key]
        dq.append(now)
        while dq and dq[0] < now - self.window:
            dq.popleft()
        return len(dq)

    def is_brute_force(self, ip: str, path: str) -> bool:
        """Fire only when the threshold is first crossed in the sliding window."""
        return self.record_attempt(ip, path) == self.threshold

    def clear_ip(self, ip: str):
        """Reset counters for an IP (e.g. after manual unblock)."""
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


# Shared engine instance used by the log monitor thread (for unblock resets)
_active_engine: Optional['DetectionEngine'] = None


def register_detection_engine(engine: 'DetectionEngine'):
    global _active_engine
    _active_engine = engine


def clear_brute_force_state(ip: str):
    if _active_engine:
        _active_engine.bf_tracker.clear_ip(ip)


class DetectionEngine:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.bf_tracker = BruteForceTracker(
            redis_client=redis_client,
            window_seconds=int(os.getenv('RATE_LIMIT_WINDOW', 60)),
            threshold=int(os.getenv('BRUTE_FORCE_THRESHOLD', 10))
        )
        self._compiled = self._compile_patterns()
        self._last_rules_reload = time.time()
        self._rules_reload_interval = 60  # seconds

    def _compile_patterns(self):
        compiled = {}
        for attack_type, info in DETECTION_PATTERNS.items():
            if not info.get('threshold_based'):
                compiled[attack_type] = [re.compile(p) for p in info['patterns']]
        return compiled

    def _load_rules_from_db(self):
        """BUG 9 FIX: Load active rules from DB and rebuild compiled patterns.
        BUG 3d: BRUTE_FORCE is always threshold-based — skip regex compilation.
        """
        try:
            from app.models import DetectionRule
            rules = DetectionRule.query.filter_by(is_active=True).all()
            compiled = {}
            for rule in rules:
                attack_type = rule.attack_type
                if attack_type == 'BRUTE_FORCE':
                    # BRUTE_FORCE is threshold-based only, not regex
                    if 'BRUTE_FORCE' not in compiled:
                        compiled['BRUTE_FORCE'] = []
                    continue
                try:
                    if attack_type not in compiled:
                        compiled[attack_type] = []
                    compiled[attack_type].append({
                        'pattern': re.compile(rule.pattern, re.IGNORECASE),
                        'severity': rule.severity_level.value,
                        'rule_id': rule.id,
                    })
                except re.error as e:
                    logger.warning(f"Invalid regex in rule {rule.id}: {e}")
            # Threshold-based types (no regex list)
            for attack_type, info in DETECTION_PATTERNS.items():
                if info.get('threshold_based') and attack_type not in compiled:
                    compiled[attack_type] = []

            # Always append built-in OWASP patterns as fallback (DB rules can be
            # edited incorrectly in the UI, e.g. missing \s* in Command Injection).
            for attack_type, info in DETECTION_PATTERNS.items():
                if info.get('threshold_based'):
                    continue
                if attack_type not in compiled:
                    compiled[attack_type] = []
                for raw in info['patterns']:
                    compiled[attack_type].append({
                        'pattern': re.compile(raw, re.IGNORECASE),
                        'severity': info['severity'],
                        'rule_id': None,
                    })

            self._compiled_db = compiled
            logger.debug(f"Loaded {sum(len(v) for v in compiled.values())} patterns from DB")
        except Exception as e:
            logger.warning(f"Could not load rules from DB (using defaults): {e}")
            self._compiled_db = None

    def _maybe_reload_rules(self):
        """Check Redis 'rules_dirty' flag and reload if needed."""
        now = time.time()
        if now - self._last_rules_reload < self._rules_reload_interval:
            return
        self._last_rules_reload = now
        dirty = False
        if self.redis:
            try:
                dirty = bool(self.redis.get('rules_dirty'))
                if dirty:
                    self.redis.delete('rules_dirty')
            except Exception:
                pass
        # Always try to reload from DB on interval
        self._load_rules_from_db()

    def _get_compiled(self):
        """Get compiled patterns — prefer DB rules if available."""
        if hasattr(self, '_compiled_db') and self._compiled_db is not None:
            return self._compiled_db
        return self._compiled

    def analyze(self, log_entry: dict) -> Optional[dict]:
        """
        Analyze a parsed log entry and return a threat dict or None.
        log_entry keys: ip, method, path, query, user_agent, status_code, raw
        """
        # BUG 9 FIX: Periodically reload rules from DB
        self._maybe_reload_rules()

        ip = log_entry.get('ip', '')
        path = log_entry.get('path', '')
        query = log_entry.get('query', '')
        user_agent = log_entry.get('user_agent', '')
        method = log_entry.get('method', '')
        status_code = log_entry.get('status_code', 200)

        # Combine searchable text
        searchable = f"{path} {query} {user_agent}"

        threats = []
        compiled = self._get_compiled()

        # Pattern-based detection (supports both old list format and new dict format)
        for attack_type, patterns in compiled.items():
            if not patterns:
                continue
            for p in patterns:
                # Support both old format (compiled regex) and new DB format (dict with 'pattern')
                if isinstance(p, dict):
                    pattern = p['pattern']
                    severity = p.get('severity', DETECTION_PATTERNS.get(attack_type, {}).get('severity', 'medium'))
                else:
                    pattern = p
                    severity = DETECTION_PATTERNS.get(attack_type, {}).get('severity', 'medium')
                match = pattern.search(searchable)
                if match:
                    mitre = DETECTION_PATTERNS.get(attack_type, {}).get('mitre', 'T1190')
                    threats.append({
                        'attack_type': attack_type,
                        'severity': severity,
                        'mitre': mitre,
                        'matched_text': match.group(0)[:200],
                        'score': SEVERITY_WEIGHTS.get(severity, 40),
                    })
                    break

        # Brute force check (login paths) — only count POST requests (actual login attempts)
        login_paths = ['/login', '/admin', '/wp-login', '/signin', '/auth', '/api/auth/login']
        is_login_path = any(lp in path.lower() for lp in login_paths)
        is_post = method.upper() == 'POST'
        if is_login_path and is_post and status_code in [200, 401, 403]:
            if self.bf_tracker.is_brute_force(ip, path):
                info = DETECTION_PATTERNS['BRUTE_FORCE']
                threats.append({
                    'attack_type': 'BRUTE_FORCE',
                    'severity': info['severity'],
                    'mitre': info['mitre'],
                    'matched_text': f'Multiple POST requests to {path} (threshold exceeded)',
                    'score': SEVERITY_WEIGHTS[info['severity']],
                })

        # B3: classic path traversal (?file=../../) without php/remote wrappers → PATH_TRAVERSAL
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

        if not threats:
            return None

        # Pick highest severity threat
        primary = max(threats, key=lambda t: t['score'])

        return {
            'ip': ip,
            'attack_type': primary['attack_type'],
            'severity': primary['severity'],
            'mitre_technique': primary['mitre'],
            'raw_payload': log_entry.get('raw', '')[:1000],
            'request_path': path[:500],
            'request_method': method,
            'user_agent': user_agent[:500],
            'response_code': status_code,
            'matched_text': primary['matched_text'],
            'recommended_action': RESPONSE_ACTIONS[primary['severity']],
            'all_threats': threats,
        }


def get_redis_client():
    try:
        r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        r.ping()
        return r
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        return None
