"""
Runtime settings: AppSetting (PostgreSQL) first, then environment variables.

Sidang / Ctrl+F anchors:
  - Lab mode toggle key: DETECTION_LAB_MODE_UI_ONLY
  - Brute-force threshold: BRUTE_FORCE_THRESHOLD
  - Rate-limit window: RATE_LIMIT_WINDOW
  - Temp block duration (seconds): TEMP_BLOCK_DURATION
"""
import os


def get_setting(key: str, default: str = '') -> str:
    from app.services.notification_service import _get_setting
    return (_get_setting(key) or os.getenv(key, default) or default).strip()


def get_int_setting(key: str, default: int) -> int:
    raw = get_setting(key, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def is_lab_mode_ui_only() -> bool:
    """When True, detection uses only active rules from Detection Rules UI (no OWASP baseline)."""
    return get_setting('DETECTION_LAB_MODE_UI_ONLY', 'false').lower() in ('1', 'true', 'yes', 'on')


def get_brute_force_threshold() -> int:
    return get_int_setting('BRUTE_FORCE_THRESHOLD', 10)


def get_rate_limit_window() -> int:
    return get_int_setting('RATE_LIMIT_WINDOW', 60)


def get_temp_block_duration() -> int:
    return get_int_setting('TEMP_BLOCK_DURATION', 86400)
