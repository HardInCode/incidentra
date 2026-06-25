"""
RESPONSE MANAGER — severity → monitor / rate_limit / escalating_block.
SIDANG Ctrl+F: respond, _escalating_block, _write_blocked_ips_json, _apply_rate_limit

Escalation logic (configurable in Settings):
  HIGH:     1st → 1h, 2nd → 24h, 3rd+ → 7d + Repeat Offender flag
  CRITICAL: 1st → 24h, 2nd → 7d, 3rd+ → 30d + Repeat Offender flag + notify

Writes: blocked_ips.json, rate_limited.json (read by vuln-web middleware.security)
"""
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

BLOCKED_IPS_JSON = os.getenv('BLOCKED_IPS_JSON_PATH', '../vuln-web/logs/blocked_ips.json')
RATE_LIMITED_JSON = os.getenv('RATE_LIMITED_JSON_PATH', '../vuln-web/logs/rate_limited.json')
RATE_LIMIT_REDIS_TTL = int(os.getenv('RATE_LIMIT_REDIS_TTL', 300))


def _write_blocked_ips_json():
    """Write current blocked IPs from DB to shared JSON file for vuln-web enforcement."""
    try:
        from app.models import BlockedIP
        from app import db
        now = datetime.utcnow()
        blocked = BlockedIP.query.filter_by(is_whitelist=False).all()
        active_ips = []
        for b in blocked:
            if b.block_type == 'permanent':
                active_ips.append(b.ip_address)
            elif b.expire_time and b.expire_time > now:
                active_ips.append(b.ip_address)

        data = {"blocked": active_ips, "updated_at": now.isoformat()}
        os.makedirs(os.path.dirname(os.path.abspath(BLOCKED_IPS_JSON)), exist_ok=True)
        with open(BLOCKED_IPS_JSON, 'w') as f:
            json.dump(data, f)
        logger.info(f"Updated blocked_ips.json with {len(active_ips)} IPs")
    except Exception as e:
        logger.error(f"Error writing blocked_ips.json: {e}")


def _default_rate_limit_policy():
    return {
        'max_requests': int(os.getenv('RATE_LIMIT_MAX_REQUESTS', 10)),
        'window_seconds': int(os.getenv('RATE_LIMIT_WINDOW', 60)),
    }


def _read_rate_limited_data():
    """Read rate_limited.json; returns {rate_limited: [], limits: {}, updated_at: ...}."""
    data = {"rate_limited": [], "limits": {}, "updated_at": None}
    try:
        if os.path.exists(RATE_LIMITED_JSON):
            with open(RATE_LIMITED_JSON, 'r') as f:
                data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading rate_limited.json: {e}")
    if not isinstance(data.get('rate_limited'), list):
        data['rate_limited'] = []
    if not isinstance(data.get('limits'), dict):
        data['limits'] = {}
    return data


def get_rate_limit_policy_for_ip(data: dict, ip: str) -> dict:
    """Per-IP policy from JSON limits, else env defaults."""
    policy = _default_rate_limit_policy()
    override = (data.get('limits') or {}).get(ip)
    if isinstance(override, dict):
        if 'max_requests' in override:
            policy['max_requests'] = int(override['max_requests'])
        if 'window_seconds' in override:
            policy['window_seconds'] = int(override['window_seconds'])
    return policy


def _persist_rate_limited_data(data: dict):
    data['updated_at'] = datetime.utcnow().isoformat()
    os.makedirs(os.path.dirname(os.path.abspath(RATE_LIMITED_JSON)), exist_ok=True)
    with open(RATE_LIMITED_JSON, 'w') as f:
        json.dump(data, f)


def _write_rate_limited_json(ip: str, add: bool = True):
    """Add or remove IP from rate_limited.json for vuln-web enforcement."""
    try:
        data = _read_rate_limited_data()
        limited = set(data.get("rate_limited", []))
        limits = dict(data.get("limits") or {})
        if add:
            limited.add(ip)
            entry = limits.get(ip) or {}
            if 'expires_at' not in entry:
                import time
                entry['expires_at'] = time.time() + RATE_LIMIT_REDIS_TTL
            limits[ip] = entry
        else:
            limited.discard(ip)
            limits.pop(ip, None)
        data["rate_limited"] = list(limited)
        data["limits"] = limits
        _persist_rate_limited_data(data)
    except Exception as e:
        logger.error(f"Error writing rate_limited.json: {e}")


def get_rate_limit_redis_ttl(redis_client, ip: str) -> int:
    """Remaining TTL for ratelimit:{ip} in Redis (0 if missing)."""
    if not redis_client:
        return 0
    try:
        ttl = redis_client.ttl(f"ratelimit:{ip}")
        return max(int(ttl), 0) if ttl and ttl > 0 else 0
    except Exception:
        return 0


def clear_rate_limit_entry(ip: str, redis_client=None):
    """Remove IP from rate_limited.json and Redis."""
    _write_rate_limited_json(ip, add=False)
    if redis_client:
        try:
            redis_client.delete(f"ratelimit:{ip}")
        except Exception:
            pass


def update_rate_limit_entry(
    ip: str,
    redis_client=None,
    *,
    seconds: Optional[int] = None,
    max_requests: Optional[int] = None,
    window_seconds: Optional[int] = None,
):
    """Update rate-limit list, per-IP policy in JSON, and optional Redis TTL."""
    if seconds is not None and seconds <= 0:
        raise ValueError('seconds must be positive')
    if max_requests is not None and max_requests <= 0:
        raise ValueError('max_requests must be positive')
    if window_seconds is not None and window_seconds <= 0:
        raise ValueError('window_seconds must be positive')

    data = _read_rate_limited_data()
    limited = set(data.get('rate_limited', []))
    limited.add(ip)
    data['rate_limited'] = list(limited)

    limits = dict(data.get('limits') or {})
    entry = dict(limits.get(ip) or {})
    if max_requests is not None:
        entry['max_requests'] = max_requests
    if window_seconds is not None:
        entry['window_seconds'] = window_seconds

    # Calculate expires_at
    import time
    ttl = seconds if seconds is not None else RATE_LIMIT_REDIS_TTL
    entry['expires_at'] = time.time() + ttl

    limits[ip] = entry
    data['limits'] = limits
    _persist_rate_limited_data(data)

    if redis_client and seconds is not None:
        try:
            redis_client.setex(f"ratelimit:{ip}", seconds, '1')
        except Exception:
            pass


def extend_rate_limit_entry(ip: str, seconds: int, redis_client=None):
    """Keep IP on rate list and refresh Redis enforcement TTL."""
    update_rate_limit_entry(ip, redis_client, seconds=seconds)


def _pick_escalating_duration(durations: list, offense_index: int) -> int:
    """
    Pick the block duration (in hours) for the given offense index.
    offense_index 0 = first offense, 1 = second, etc.
    If offense_index >= len(durations), use the last (highest) value.
    """
    if not durations:
        return 24
    idx = min(offense_index, len(durations) - 1)
    return durations[idx]


class ResponseManager:
    """
    Executes automated responses based on threat severity.
    Level 1 (Low)      → Log & Monitor
    Level 2 (Medium)   → Rate Limit (Redis counter)
    Level 3 (High)     → Escalating temp block: 1h → 24h → 7d + Repeat Offender
    Level 4 (Critical) → Escalating temp block: 24h → 7d → 30d + Repeat Offender + Notify
    """

    def __init__(self, db, redis_client=None, app=None):
        self.db = db
        self.redis = redis_client
        self._app = app
        self.temp_block_duration = int(os.getenv('TEMP_BLOCK_DURATION', 86400))

    def _notify_async(self, incident_id: int, severity: str, block_hours: int = 0, offense_count: int = 0):
        """
        Run notification in a background thread (works without Celery worker).
        Celery .delay() is skipped intentionally: even if broker is reachable,
        tasks queue silently without a running worker. Thread fallback is always reliable.
        """
        import threading
        from app.services.notification_service import _do_notify

        app = self._app
        if app:
            def _notif_thread(app_ref, inc_id, sev, b_hours, o_count):
                try:
                    with app_ref.app_context():
                        _do_notify(inc_id, sev, block_hours=b_hours, offense_count=o_count)
                except Exception as e:
                    logger.error(f"Notification thread error: {e}")
            threading.Thread(
                target=_notif_thread,
                args=(app, incident_id, severity, block_hours, offense_count),
                daemon=True
            ).start()
        else:
            # Called from API endpoint — already in app context, run directly
            try:
                _do_notify(incident_id, severity, block_hours=block_hours, offense_count=offense_count)
            except Exception as e:
                logger.warning(f"Notification failed: {e}")

    def respond(self, threat: dict, incident_id: int) -> dict:
        from app.core.settings_reader import get_temp_block_duration
        self.temp_block_duration = get_temp_block_duration()
        severity = threat.get('severity', 'low')
        ip = threat.get('ip', '')
        action = threat.get('recommended_action', 'log_and_monitor')

        result = {
            'action_taken': action,
            'ip': ip,
            'severity': severity,
            'incident_id': incident_id,
            'details': '',
        }

        if action == 'log_and_monitor':
            result['details'] = f'Threat logged. IP {ip} is being monitored.'
            self._log_to_redis(ip, 'monitor')

        elif action == 'rate_limit':
            self._apply_rate_limit(ip)
            _write_rate_limited_json(ip, add=True)
            result['details'] = f'Rate limiting applied to {ip}. Max 10 req/min enforced.'

        elif action == 'escalating_block':
            self.db.session.expire_all()
            block_result = self._escalating_block(
                ip=ip,
                severity=severity,
                attack_type=threat.get('attack_type', ''),
                incident_id=incident_id,
            )
            result.update(block_result)

        # Legacy actions still supported (e.g. manual API calls)
        elif action == 'temporary_block':
            self.db.session.expire_all()
            ok = self._block_ip(ip, permanent=False, reason=f"Auto-blocked: {threat.get('attack_type')}")
            if ok:
                expire = datetime.utcnow() + timedelta(seconds=self.temp_block_duration)
                _write_blocked_ips_json()
                result['details'] = (
                    f'IP {ip} temporarily blocked until {expire.strftime("%Y-%m-%d %H:%M UTC")}. '
                    f'Next request from this IP should receive HTTP 403.'
                )
                self._notify_async(incident_id, 'high')
            else:
                result['action_taken'] = 'block_failed'
                result['details'] = f'Incident logged but temporary block failed for {ip}. Check server logs.'

        elif action == 'permanent_block':
            self.db.session.expire_all()
            ok = self._block_ip(ip, permanent=True, reason=f"Auto-blocked (CRITICAL): {threat.get('attack_type')}")
            if ok:
                _write_blocked_ips_json()
                result['details'] = (
                    f'IP {ip} permanently blocked. '
                    f'Next request from this IP should receive HTTP 403.'
                )
                self._notify_async(incident_id, 'critical')
            else:
                result['action_taken'] = 'block_failed'
                result['details'] = f'Incident logged but permanent block failed for {ip}. Check server logs.'

        self._save_incident_log(incident_id, result)
        return result

    def _escalating_block(self, ip: str, severity: str, attack_type: str, incident_id: int) -> dict:
        """
        Escalating temporary block logic:
        - Looks up existing BlockedIP.incident_count to determine offense tier
        - Picks block duration from configurable duration list per severity
        - Flags is_repeat_offender=True when count >= threshold
        - Notifies admin for critical repeat offenders
        """
        from app.models import BlockedIP
        from app.core.settings_reader import (
            get_escalating_high_durations,
            get_escalating_critical_durations,
            get_repeat_offender_threshold,
        )

        try:
            repeat_threshold = get_repeat_offender_threshold()

            existing = BlockedIP.query.filter_by(ip_address=ip, is_whitelist=False).first()
            current_count = 0
            previous_max_severity = None
            if existing:
                current_count = existing.incident_count or 0
                # Extract the highest severity previously recorded from the reason field
                if existing.reason:
                    for sev_tag in ['CRITICAL', 'HIGH']:
                        if sev_tag in existing.reason.upper():
                            previous_max_severity = sev_tag.lower()
                            break
            elif self.redis:
                # IP was unblocked — check Redis for preserved escalation count & severity
                try:
                    saved = self.redis.get(f"escalation_count:{ip}")
                    if saved:
                        current_count = int(saved)
                    saved_sev = self.redis.get(f"escalation_severity:{ip}")
                    if saved_sev:
                        previous_max_severity = saved_sev if isinstance(saved_sev, str) else saved_sev.decode()
                except Exception:
                    pass

            # Use the HIGHEST severity between current attack and historical max
            # This ensures escalation always uses the worst-case duration list
            SEVERITY_RANK = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            effective_severity = severity
            if previous_max_severity and SEVERITY_RANK.get(previous_max_severity, 0) > SEVERITY_RANK.get(severity, 0):
                effective_severity = previous_max_severity

            durations = (
                get_escalating_critical_durations()
                if effective_severity == 'critical'
                else get_escalating_high_durations()
            )

            offense_index = current_count  # 0-based: 0=first block, 1=second, ...

            hours = _pick_escalating_duration(durations, offense_index)
            expire_time = datetime.utcnow() + timedelta(hours=hours)
            new_count = current_count + 1
            is_repeat = new_count >= repeat_threshold

            reason_parts = [f"Auto-blocked ({effective_severity.upper()}): {attack_type}"]
            reason_parts.append(f"Offense #{new_count}")
            if is_repeat:
                reason_parts.append("⚠ Repeat Offender")
            reason = " | ".join(reason_parts)

            if existing:
                existing.is_whitelist = False
                existing.reason = reason
                existing.block_type = 'temporary'
                existing.expire_time = expire_time
                existing.block_time = datetime.utcnow()
                existing.incident_count = new_count
                existing.is_repeat_offender = is_repeat
            else:
                new_block = BlockedIP(
                    ip_address=ip,
                    reason=reason,
                    block_type='temporary',
                    expire_time=expire_time,
                    is_whitelist=False,
                    incident_count=new_count,
                    is_repeat_offender=is_repeat,
                )
                self.db.session.add(new_block)

            self.db.session.commit()

            # Persist escalation count and max severity in Redis (survives future unblock)
            if self.redis:
                try:
                    self.redis.setex(f"escalation_count:{ip}", 30 * 24 * 3600, str(new_count))
                    self.redis.setex(f"escalation_severity:{ip}", 30 * 24 * 3600, effective_severity)
                except Exception:
                    pass

            # Redis TTL for fast enforcement check
            if self.redis:
                ttl_seconds = int(hours * 3600)
                try:
                    self.redis.setex(f"blocked:{ip}", ttl_seconds, '1')
                except Exception:
                    pass

            _write_blocked_ips_json()

            # Human-readable duration
            if hours >= 720:
                duration_str = f"{hours // 720} month(s)"
            elif hours >= 168:
                duration_str = f"{hours // 168} week(s)"
            elif hours >= 24:
                duration_str = f"{hours // 24} day(s)"
            else:
                duration_str = f"{hours} hour(s)"

            details = (
                f'IP {ip} blocked for {duration_str} (offense #{new_count}, {severity}). '
                f'Expires: {expire_time.strftime("%Y-%m-%d %H:%M UTC")}.'
            )
            if is_repeat:
                details += f' ⚠ Repeat Offender (≥{repeat_threshold} offenses) — review in IP Management.'

            # Notify on critical repeat offenders, or any severity repeat offender
            if is_repeat and severity == 'critical':
                self._notify_async(incident_id, 'critical', block_hours=hours, offense_count=new_count)
            elif is_repeat:
                self._notify_async(incident_id, 'high', block_hours=hours, offense_count=new_count)
            elif severity == 'critical' and new_count == 1:
                # Notify on first critical offense too
                self._notify_async(incident_id, 'critical', block_hours=hours, offense_count=new_count)

            return {
                'action_taken': 'escalating_block',
                'details': details,
                'block_hours': hours,
                'offense_count': new_count,
                'is_repeat_offender': is_repeat,
            }

        except Exception as e:
            logger.error(f"Error in escalating block for {ip}: {e}", exc_info=True)
            self.db.session.rollback()
            return {
                'action_taken': 'block_failed',
                'details': f'Incident logged but escalating block failed for {ip}. Check server logs.',
            }

    def _log_to_redis(self, ip: str, action: str):
        if self.redis:
            try:
                self.redis.setex(f"action:{ip}", 3600, action)
            except Exception:
                pass

    def _apply_rate_limit(self, ip: str):
        if self.redis:
            try:
                key = f"ratelimit:{ip}"
                self.redis.setex(key, RATE_LIMIT_REDIS_TTL, '1')
            except Exception:
                pass

    def _block_ip(self, ip: str, permanent: bool, reason: str) -> bool:
        """Legacy helper used by the manual permanent/temporary_block action paths."""
        from app.models import BlockedIP
        try:
            expire_time = None if permanent else (
                datetime.utcnow() + timedelta(seconds=self.temp_block_duration)
            )
            existing = BlockedIP.query.filter_by(ip_address=ip).first()
            if existing:
                existing.is_whitelist = False
                existing.reason = reason
                existing.incident_count = (existing.incident_count or 0) + 1
                existing.block_type = 'permanent' if permanent else 'temporary'
                existing.expire_time = expire_time
                existing.block_time = datetime.utcnow()
            else:
                blocked = BlockedIP(
                    ip_address=ip,
                    reason=reason,
                    block_type='permanent' if permanent else 'temporary',
                    expire_time=expire_time,
                    is_whitelist=False,
                )
                self.db.session.add(blocked)
            self.db.session.commit()

            if self.redis:
                ttl = -1 if permanent else self.temp_block_duration
                if ttl > 0:
                    self.redis.setex(f"blocked:{ip}", ttl, '1')
                else:
                    self.redis.set(f"blocked:{ip}", '1')
            return True
        except Exception as e:
            logger.error(f"Error blocking IP {ip}: {e}", exc_info=True)
            self.db.session.rollback()
            return False

    def _save_incident_log(self, incident_id: int, result: dict):
        from app.models import IncidentLog
        try:
            log = IncidentLog(
                incident_id=incident_id,
                action_taken=result['action_taken'],
                action_detail=result['details'],
                performed_by='system',
            )
            self.db.session.add(log)
            self.db.session.commit()
        except Exception as e:
            logger.error(f"Error saving incident log: {e}")
            self.db.session.rollback()

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is blocked (Redis fast path)."""
        if self.redis:
            try:
                return bool(self.redis.exists(f"blocked:{ip}"))
            except Exception:
                pass
        # Fallback to DB
        from app.models import BlockedIP
        blocked = BlockedIP.query.filter_by(ip_address=ip, is_whitelist=False).first()
        if blocked:
            if blocked.block_type == 'permanent':
                return True
            if blocked.expire_time and blocked.expire_time > datetime.utcnow():
                return True
        return False
