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
SAFE_FILES_DIR = os.path.join(os.getcwd(), 'safe_files')
VULN_PORT = int(os.getenv('VULN_PORT', 5050))

# Phase 3 — only enable on isolated lab machines (see docs/DETECTION.md)
VULN_UNSAFE_CMD = _env_bool('VULN_UNSAFE_CMD')
VULN_UNSAFE_UPLOAD = _env_bool('VULN_UNSAFE_UPLOAD')
CMD_TIMEOUT_SEC = int(os.getenv('VULN_CMD_TIMEOUT', 5))
