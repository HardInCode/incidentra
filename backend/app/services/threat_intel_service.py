import os
import requests
import logging
from app import celery, db

logger = logging.getLogger(__name__)
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"


def _do_reputation_check(incident_id: int, ip_address: str):
    """
    Core logic — must be called within an active Flask app context.
    Shared by Celery task and background thread fallback.
    """
    import ipaddress

    # Skip private, loopback, and reserved IPs — AbuseIPDB rejects these
    try:
        addr = ipaddress.ip_address(ip_address)
        if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_multicast:
            logger.info(f"Skipping AbuseIPDB for non-public IP: {ip_address}")
            return
    except ValueError:
        logger.warning(f"Invalid IP address format: {ip_address}")
        return

    from app.models import Incident
    from app.services.notification_service import _get_setting
    api_key = _get_setting('ABUSEIPDB_API_KEY')
    if not api_key:
        return
    try:
        headers = {'Key': api_key, 'Accept': 'application/json'}
        params = {'ipAddress': ip_address, 'maxAgeInDays': 90}
        response = requests.get(ABUSEIPDB_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json().get('data', {})
        confidence = data.get('abuseConfidenceScore', 0)
        country = data.get('countryCode', '')
        incident = Incident.query.get(incident_id)
        if incident:
            incident.abuse_confidence_score = confidence
            incident.country_code = country
            db.session.commit()
            logger.info(f"IP {ip_address}: {confidence}% abuse score, country: {country}")
    except Exception as e:
        logger.error(f"AbuseIPDB error for {ip_address}: {e}")


@celery.task(bind=True, max_retries=2)
def check_ip_reputation(self, incident_id: int, ip_address: str):
    """Celery task — delegates to shared core function."""
    _do_reputation_check(incident_id, ip_address)
