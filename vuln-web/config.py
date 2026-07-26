"""vuln-web configuration from environment."""
import os


def _env_bool(key: str, default: str = '0') -> bool:
    return os.getenv(key, default).strip().lower() in ('1', 'true', 'yes')


DB_PATH = os.getenv('VULN_DB_PATH', 'vuln.db')
BLOCKED_IPS_FILE = os.getenv('BLOCKED_IPS_JSON', 'logs/blocked_ips.json')
RATE_LIMITED_FILE = os.getenv('RATE_LIMITED_JSON', 'logs/rate_limited.json')
RATE_LIMIT_MAX = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', 10))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 60))
LOG_FILE = os.getenv('VULN_LOG_FILE', 'logs/access.log')
# Env override lets deployments that don't run this app with CWD at its own project root
# (e.g. Railway's merged core container, see railway/core/wsgi.py) point at the right dir.
SAFE_FILES_DIR = os.getenv('VULN_SAFE_FILES_DIR', os.path.join(os.getcwd(), 'safe_files'))
VULN_PORT = int(os.getenv('VULN_PORT', 5050))

# Phase 3 — only enable on isolated lab machines (see docs/DETECTION.md)
VULN_UNSAFE_CMD = _env_bool('VULN_UNSAFE_CMD')
VULN_UNSAFE_UPLOAD = _env_bool('VULN_UNSAFE_UPLOAD')
CMD_TIMEOUT_SEC = int(os.getenv('VULN_CMD_TIMEOUT', 5))

# --- Decoupled deployment (vuln-web as its own Railway service/domain) ---
# Unset by default -> logging.py / security.py fall back to the local LOG_FILE /
# BLOCKED_IPS_FILE / RATE_LIMITED_FILE above exactly as before (local Docker Compose,
# and the merged railway/core /lab topology, are both untouched by these).
# See railway/README.md, "Running vuln-web on its own domain".
LOG_INGEST_URL = os.getenv('LOG_INGEST_URL', '')
BLOCKLIST_API_URL = os.getenv('BLOCKLIST_API_URL', '')
INTERNAL_API_TOKEN = os.getenv('INTERNAL_API_TOKEN', '')
INTERNAL_API_TIMEOUT = float(os.getenv('INTERNAL_API_TIMEOUT', '2'))
# How long a fetched blocklist is cached before security.py calls BLOCKLIST_API_URL again
# — avoids one HTTP round-trip to `core` per request on the hot enforcement path.
BLOCKLIST_CACHE_SECONDS = float(os.getenv('BLOCKLIST_CACHE_SECONDS', '3'))
