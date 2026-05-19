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
    try:
        from app.models import AppSetting
        s = AppSetting.query.filter_by(key=key).first()
        if s and s.value:
            return s.value
    except Exception:
        pass
    return os.getenv(key, '')


def _do_notify(incident_id: int, severity: str = 'critical'):
    """
    Core notification logic.
    Must be called within an active Flask app context.
    Shared by Celery task and background thread fallback.
    """
    from app.models import Incident
    from datetime import timezone, timedelta
    incident = Incident.query.get(incident_id)
    if not incident:
        return

    wib = timezone(timedelta(hours=7))
    detected_wib = incident.created_at.replace(tzinfo=timezone.utc).astimezone(wib)

    emoji = '🚨' if severity == 'critical' else '⚠️'
    level = severity.upper()
    action_text = ('IP permanently blocked.'
                   if severity == 'critical'
                   else 'IP temporarily blocked for 24 hours.')

    subject = f"[SME-Guard {level}] {incident.attack_type} from {incident.source_ip}"
    body = f"""
SME-Guard Security Alert — {level}
=====================================
Incident ID   : #{incident.id}
Attack Type   : {incident.attack_type}
Severity      : {level}
Source IP     : {incident.source_ip}
Request Path  : {incident.request_path}
Detected At   : {detected_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}
Raw Payload   : {str(incident.raw_payload)[:200]}

Action Taken  : {action_text}

Review: http://localhost:3000/incidents/{incident.id}
"""
    _send_email(subject, body)
    _send_telegram(
        f"{emoji} *SME-Guard {level} ALERT*\n\n"
        f"*Attack:* {incident.attack_type}\n"
        f"*IP:* `{incident.source_ip}`\n"
        f"*Path:* `{incident.request_path}`\n"
        f"*Time:* {detected_wib.strftime('%H:%M WIB')}\n"
        f"*Action:* {action_text}"
    )


@celery.task
def notify_incident(incident_id: int, severity: str = 'critical'):
    """Celery task — delegates to shared core function."""
    _do_notify(incident_id, severity)


# Backward-compatibility alias (used in existing code)
notify_critical_incident = notify_incident


def _send_email(subject: str, body: str):
    smtp_host = _get_setting('SMTP_HOST')
    smtp_port = int(_get_setting('SMTP_PORT') or 587)
    smtp_user = _get_setting('SMTP_USER')
    smtp_pass = _get_setting('SMTP_PASSWORD')
    alert_email = _get_setting('ALERT_EMAIL')

    if not all([smtp_host, smtp_user, smtp_pass, alert_email]):
        logger.info("Email not configured, skipping notification.")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = alert_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, alert_email, msg.as_string())
        logger.info(f"Alert email sent to {alert_email}.")
    except Exception as e:
        logger.error(f"Email send failed: {e}")


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
