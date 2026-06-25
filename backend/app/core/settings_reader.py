"""
Runtime settings: AppSetting (PostgreSQL) first, then environment variables.

Sidang / Ctrl+F anchors:
  - Lab mode toggle key: DETECTION_LAB_MODE_UI_ONLY
  - Brute-force threshold: BRUTE_FORCE_THRESHOLD
  - Rate-limit window: RATE_LIMIT_WINDOW
  - Temp block duration (seconds): TEMP_BLOCK_DURATION
  - Repeat offender threshold: REPEAT_OFFENDER_THRESHOLD
  - Escalating block durations (hours): ESCALATING_HIGH_DURATIONS, ESCALATING_CRITICAL_DURATIONS
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


def get_repeat_offender_threshold() -> int:
    """Number of incidents from an IP before it is flagged as Repeat Offender (default 3)."""
    return get_int_setting('REPEAT_OFFENDER_THRESHOLD', 3)


def _parse_hour_list(raw: str, defaults: list) -> list:
    """Parse comma-separated hours string into a sorted list of ints."""
    try:
        parts = [int(x.strip()) for x in raw.split(',') if x.strip()]
        if parts:
            return sorted(parts)
    except (TypeError, ValueError):
        pass
    return defaults


def get_escalating_high_durations() -> list:
    """
    Block durations (in hours) for HIGH severity, indexed by offense tier.
    Index 0 = 1st offense, 1 = 2nd offense, 2+ = repeat offender.
    Default: [1, 24, 168]  (1h → 24h → 7 days)
    """
    raw = get_setting('ESCALATING_HIGH_DURATIONS', '')
    return _parse_hour_list(raw, [1, 24, 168])


def get_escalating_critical_durations() -> list:
    """
    Block durations (in hours) for CRITICAL severity, indexed by offense tier.
    Index 0 = 1st offense, 1 = 2nd offense, 2+ = repeat offender.
    Default: [24, 168, 720]  (24h → 7 days → 30 days)
    """
    raw = get_setting('ESCALATING_CRITICAL_DURATIONS', '')
    return _parse_hour_list(raw, [24, 168, 720])
