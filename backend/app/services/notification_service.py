import os
import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app import celery, db

logger = logging.getLogger(__name__)


def _get_setting(key: str) -> str:
    """Read from AppSetting DB first, fall back to environment variable."""
    env_val = (os.getenv(key, '') or '').strip()
    try:
        from app.models import AppSetting
        s = AppSetting.query.filter_by(key=key).first()
        if s and s.value:
            db_val = s.value.strip()
            # Ignore corrupted masked placeholders saved by mistake
            if '••••' in db_val:
                return env_val
            return db_val
    except Exception:
        pass
    return env_val


def _frontend_base_url() -> str:
    """Public UI base URL for links in alert emails (Railway: set FRONTEND_URL or CORS_ORIGINS)."""
    explicit = (os.getenv('FRONTEND_URL') or '').strip().rstrip('/')
    if explicit:
        return explicit
    cors = (os.getenv('CORS_ORIGINS') or '').strip()
    if cors:
        first = cors.split(',')[0].strip().rstrip('/')
        if first:
            return first
    return 'http://localhost:3000'


def _do_notify(incident_id: int, severity: str = 'critical', block_hours: int = 0, offense_count: int = 0):
    """
    Core notification logic.
    Must be called within an active Flask app context.
    Shared by Celery task and background thread fallback.
    """
    from app.models import Incident, BlockedIP
    from datetime import timezone, timedelta
    incident = Incident.query.get(incident_id)
    if not incident:
        return

    wib = timezone(timedelta(hours=7))
    detected_wib = incident.created_at.replace(tzinfo=timezone.utc).astimezone(wib)

    emoji = '🚨' if severity == 'critical' else '⚠️'
    level = severity.upper()

    # Build accurate action_text based on actual block info
    if block_hours > 0 and offense_count > 0:
        # Called from escalating_block — show actual duration
        if block_hours >= 720:
            duration_str = f"{block_hours // 720} month(s)"
        elif block_hours >= 168:
            duration_str = f"{block_hours // 168} week(s)"
        elif block_hours >= 24:
            duration_str = f"{block_hours // 24} day(s)"
        else:
            duration_str = f"{block_hours} hour(s)"
        action_text = f'IP escalation-blocked for {duration_str} (offense #{offense_count}).'
    else:
        # Fallback: look up the actual block status from DB
        blocked = BlockedIP.query.filter_by(ip_address=incident.source_ip, is_whitelist=False).first()
        if blocked and blocked.block_type == 'permanent':
            action_text = 'IP permanently blocked by admin.'
        elif blocked and blocked.expire_time:
            remaining = blocked.expire_time - incident.created_at
            hours = int(remaining.total_seconds() / 3600)
            if hours >= 720:
                action_text = f'IP escalation-blocked for {hours // 720} month(s).'
            elif hours >= 168:
                action_text = f'IP escalation-blocked for {hours // 168} week(s).'
            elif hours >= 24:
                action_text = f'IP escalation-blocked for {hours // 24} day(s).'
            else:
                action_text = f'IP escalation-blocked for {hours} hour(s).'
        else:
            action_text = 'IP blocked (escalation policy).'

    subject = f"[Incidentra SOC {level}] {incident.attack_type} from {incident.source_ip}"
    body = f"""
Incidentra SOC Security Alert — {level}
=====================================
Incident ID   : #{incident.id}
Attack Type   : {incident.attack_type}
Severity      : {level}
Source IP     : {incident.source_ip}
Request Path  : {incident.request_path}
Detected At   : {detected_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}
Raw Payload   : {str(incident.raw_payload)[:200]}

Action Taken  : {action_text}

Review: {_frontend_base_url()}/incidents/{incident.id}
"""
    ok, err = _send_email(subject, body)
    if not ok:
        logger.warning(f"Incident email not sent (incident #{incident.id}): {err}")
    _send_telegram(
        f"{emoji} *Incidentra SOC {level} ALERT*\n\n"
        f"*Attack:* {incident.attack_type}\n"
        f"*IP:* `{incident.source_ip}`\n"
        f"*Path:* `{incident.request_path}`\n"
        f"*Time:* {detected_wib.strftime('%H:%M WIB')}\n"
        f"*Action:* {action_text}"
    )


@celery.task
def notify_incident(incident_id: int, severity: str = 'critical', block_hours: int = 0, offense_count: int = 0):
    """Celery task — delegates to shared core function."""
    _do_notify(incident_id, severity, block_hours=block_hours, offense_count=offense_count)


# Backward-compatibility alias (used in existing code)
notify_critical_incident = notify_incident


def _send_email(subject: str, body: str) -> tuple:
    """Send alert email. Returns (success: bool, error_message: str | None)."""
    smtp_host = _get_setting('SMTP_HOST')
    smtp_port = int(_get_setting('SMTP_PORT') or 587)
    smtp_user = _get_setting('SMTP_USER')
    smtp_pass = _get_setting('SMTP_PASSWORD')
    alert_email = _get_setting('ALERT_EMAIL')

    missing = [
        name for name, val in (
            ('SMTP_HOST', smtp_host),
            ('SMTP_USER', smtp_user),
            ('SMTP_PASSWORD', smtp_pass),
            ('ALERT_EMAIL', alert_email),
        ) if not val
    ]
    if missing:
        msg = f"Email not configured — missing: {', '.join(missing)}"
        logger.warning(msg)
        return False, msg

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = alert_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        timeout = 30
        if smtp_port == 465:
            # Gmail / providers that require implicit TLS
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [alert_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [alert_email], msg.as_string())

        logger.info(f"Alert email sent to {alert_email}.")
        return True, None
    except smtplib.SMTPAuthenticationError as e:
        hint = (
            f"SMTP authentication failed ({e}). "
            "For Gmail use an App Password (not your normal password) and 2-Step Verification."
        )
        logger.error(hint)
        return False, hint
    except Exception as e:
        err = f"Email send failed: {e}"
        logger.error(err)
        return False, err


def _send_telegram(message: str):
    bot_token = _get_setting('TELEGRAM_BOT_TOKEN')
    chat_id = _get_setting('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id:
        return
    import time
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    plain = message.replace('*', '').replace('`', '').replace('_', ' ')
    for attempt in range(3):
        try:
            resp = requests.post(url, json={
                'chat_id': chat_id,
                'text': plain,
            }, timeout=10)
            if resp.ok:
                logger.info("Telegram notification sent.")
                return
            if resp.status_code == 429:
                retry_after = resp.json().get('parameters', {}).get('retry_after', 5)
                logger.warning(f"Telegram flood control, retrying after {retry_after}s")
                time.sleep(retry_after + 1)
                continue
            logger.error(f"Telegram API error: {resp.status_code} {resp.text}")
            return
        except Exception as e:
            logger.error(f"Telegram send failed (attempt {attempt + 1}): {e}")
            time.sleep(2)
