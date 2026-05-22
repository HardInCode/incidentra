"""
AI ANALYST ONLY — Groq explanations for incidents (does NOT detect attacks).
SIDANG Ctrl+F: _call_groq_with_fallback, generate_explanation_task, _save_fallback_explanation
Detection regex: detection_engine.DETECTION_PATTERNS (separate)
"""
import os
import logging
import json
import requests
from app import celery, db

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# BUG 8 FIX: 4 fallback models from the Groq console screenshot
# Tries primary model first, then falls through this list automatically
GROQ_FALLBACK_MODELS = [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'meta-llama/llama-guard-4-12b',
]


def _call_groq_with_fallback(prompt: str, max_tokens: int = 600):
    """
    Try the configured primary model first, then fall back through
    GROQ_FALLBACK_MODELS until one succeeds.
    Returns (content_string, model_name_used).
    Raises RuntimeError if all models fail.
    """
    from app.services.notification_service import _get_setting
    api_key = _get_setting('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not configured")

    primary = _get_setting('GROQ_MODEL') or os.getenv('GROQ_MODEL', GROQ_FALLBACK_MODELS[0])
    models_to_try = [primary] + [m for m in GROQ_FALLBACK_MODELS if m != primary]

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    last_error = None
    for model in models_to_try:
        try:
            payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': max_tokens,
                'temperature': 0.3,
            }
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            logger.info(f"Groq responded successfully with model: {model}")
            return content, model
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (400, 404, 422):
                logger.warning(f"Model {model} unavailable (HTTP {status}), trying next...")
                last_error = e
                continue
            raise  # re-raise auth errors, rate limits etc.
        except requests.exceptions.RequestException as e:
            logger.warning(f"Model {model} request failed: {e}, trying next...")
            last_error = e
            continue

    raise RuntimeError(f"All Groq models failed. Last error: {last_error}")


def build_prompt(incident_data: dict, language: str = 'en') -> str:
    lang = 'id' if language and str(language).lower().startswith('id') else 'en'
    lang_instruction = (
        'Respond in Indonesian (Bahasa Indonesia).'
        if lang == 'id'
        else 'Respond in English.'
    )
    return f"""You are a cybersecurity expert helping an SME IT administrator understand a security incident.
{lang_instruction}

Incident Details:
- Attack Type: {incident_data.get('attack_type', 'Unknown')}
- Severity: {incident_data.get('severity', 'Unknown').upper()}
- Source IP: {incident_data.get('source_ip', 'Unknown')}
- Request Path: {incident_data.get('request_path', '/')}
- Request Method: {incident_data.get('request_method', 'GET')}
- Raw Payload (excerpt): {str(incident_data.get('raw_payload', ''))[:300]}
- User Agent: {incident_data.get('user_agent', 'Unknown')[:100]}
- Detected At: {incident_data.get('created_at', 'Unknown')}

Please provide a JSON response with EXACTLY these fields:
{{
  "ai_summary": "2-3 sentence plain-language summary of what happened, suitable for a non-technical SME owner",
  "threat_explanation": "Explanation of why this attack is dangerous and what damage it could cause (2-3 sentences)",
  "recommended_actions": "3-5 specific action steps the IT admin should take now, numbered list",
  "mitre_technique": "MITRE ATT&CK technique ID and name (e.g., T1190 - Exploit Public-Facing Application)"
}}

Respond ONLY with the JSON object, no markdown, no extra text."""


@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def generate_explanation_task(self, incident_id: int):
    from app.models import Incident, IncidentExplanation

    try:
        incident = Incident.query.get(incident_id)
        if not incident:
            logger.warning(f"Incident {incident_id} not found for AI explanation.")
            return

        if incident.explanation:
            return

        from app.services.notification_service import _get_setting
        api_key = _get_setting('GROQ_API_KEY')
        if not api_key:
            # No API key at all — use static fallback immediately
            _save_fallback_explanation(incident_id)
            return

        prompt = build_prompt(incident.to_dict())

        # BUG 8 FIX: Use fallback model chain instead of single hardcoded model
        try:
            content, model_used = _call_groq_with_fallback(prompt, max_tokens=600)
        except ValueError:
            # No API key
            _save_fallback_explanation(incident_id)
            return
        except RuntimeError as exc:
            # All models failed — fall back to static
            logger.error(f"All Groq models failed for incident {incident_id}: {exc}")
            _save_fallback_explanation(incident_id)
            return

        # Parse JSON response
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            data = json.loads(match.group(0)) if match else {}

        explanation = IncidentExplanation(
            incident_id=incident_id,
            ai_summary=data.get('ai_summary', 'AI explanation unavailable.'),
            threat_explanation=data.get('threat_explanation', ''),
            recommended_actions=data.get('recommended_actions', ''),
            mitre_technique=data.get('mitre_technique', ''),
            model_used=model_used,
        )
        db.session.add(explanation)
        db.session.commit()
        logger.info(f"AI explanation generated for incident {incident_id} using {model_used}.")

    except requests.exceptions.RequestException as exc:
        logger.error(f"Groq API error for incident {incident_id}: {exc}")
        # BUG 8 FIX: retry via Celery, but if Celery itself is unavailable this
        # block is never reached — the sync fallback in incidents.py handles that case
        try:
            self.retry(exc=exc)
        except Exception:
            _save_fallback_explanation(incident_id)
    except Exception as exc:
        logger.error(f"AI task error for incident {incident_id}: {exc}", exc_info=True)
        _save_fallback_explanation(incident_id)


def _save_fallback_explanation(incident_id: int):
    from app.models import Incident, IncidentExplanation
    try:
        incident = Incident.query.get(incident_id)
        if not incident or incident.explanation:
            return

        attack_summaries = {
            'SQL_INJECTION': {
                'summary': 'An attacker attempted to manipulate your database by injecting malicious SQL code into a web request. This is one of the most common and dangerous web attacks.',
                'explanation': 'SQL injection can allow attackers to read, modify, or delete your entire database, including customer data, passwords, and financial records. If successful, the attacker could gain complete control over your database.',
                'actions': '1. Ensure all database queries use parameterized statements.\n2. Review and sanitize all user inputs.\n3. Check database logs for any unauthorized access.\n4. Consider using a Web Application Firewall (WAF).\n5. Update your database credentials immediately if breach is suspected.',
                'mitre': 'T1190 - Exploit Public-Facing Application',
            },
            'XSS': {
                'summary': 'An attacker attempted to inject malicious JavaScript code into your web application. This could be used to steal user sessions or redirect users to malicious sites.',
                'explanation': 'Cross-Site Scripting (XSS) allows attackers to run malicious scripts in the browsers of your legitimate users, potentially stealing their cookies, session tokens, or credentials.',
                'actions': '1. Implement output encoding for all user-supplied data.\n2. Enable Content Security Policy (CSP) headers.\n3. Sanitize all HTML inputs using a trusted library.\n4. Review affected pages for data leakage.\n5. Notify users if their session data may be compromised.',
                'mitre': 'T1059.007 - JavaScript',
            },
            'BRUTE_FORCE': {
                'summary': 'An attacker is repeatedly trying different passwords to gain unauthorized access to your system. This is an automated attack targeting your login page.',
                'explanation': 'Brute force attacks can eventually guess weak passwords, giving attackers full access to compromised accounts. This can lead to data theft, unauthorized transactions, or complete account takeover.',
                'actions': '1. Enable multi-factor authentication (MFA) immediately.\n2. Implement account lockout after 5 failed attempts.\n3. Add CAPTCHA to your login form.\n4. Review accounts for any successful unauthorized logins.\n5. Force password reset for all admin accounts.',
                'mitre': 'T1110 - Brute Force',
            },
            'PATH_TRAVERSAL': {
                'summary': 'An attacker attempted to access files outside the web root directory, potentially trying to read system configuration files or sensitive data.',
                'explanation': 'Path traversal attacks can expose sensitive system files like password files, configuration files, or application source code, giving attackers critical information to plan further attacks.',
                'actions': '1. Validate and sanitize all file path inputs.\n2. Use chroot jails or similar isolation for web applications.\n3. Review web server configuration for directory listing.\n4. Check if any sensitive files were accessed in server logs.\n5. Apply principle of least privilege to web server file permissions.',
                'mitre': 'T1083 - File and Directory Discovery',
            },
            'COMMAND_INJECTION': {
                'summary': 'An attacker attempted to execute system commands through your web application. This is a critical vulnerability that could lead to complete server compromise.',
                'explanation': 'Command injection allows attackers to run arbitrary operating system commands on your server, potentially installing malware, creating backdoors, or exfiltrating all data.',
                'actions': '1. CRITICAL: Take the affected application offline immediately.\n2. Audit all server processes for unauthorized activity.\n3. Check for new user accounts or scheduled tasks.\n4. Review all files modified in the last 24 hours.\n5. Consider a complete server audit before bringing the service back online.',
                'mitre': 'T1059 - Command and Scripting Interpreter',
            },
            'LFI_RFI': {
                'summary': 'An attacker attempted to include malicious files into your web application using PHP file inclusion vulnerabilities.',
                'explanation': 'LFI/RFI attacks can allow attackers to read sensitive local files or execute remote malicious code, potentially leading to full server compromise.',
                'actions': '1. Disable PHP allow_url_include if not needed.\n2. Validate and whitelist all file path inputs.\n3. Apply open_basedir restrictions in PHP config.\n4. Review application logs for accessed file paths.\n5. Consider moving to parameterized file access.',
                'mitre': 'T1190 - Exploit Public-Facing Application',
            },
            'SCANNER': {
                'summary': 'An automated vulnerability scanner was detected probing your web application for weaknesses.',
                'explanation': 'Security scanners map your attack surface and identify exploitable vulnerabilities. This is often a precursor to a more targeted attack.',
                'actions': '1. Review what the scanner found in the request path.\n2. Check for any follow-up attacks from the same IP.\n3. Ensure your application is patched and up to date.\n4. Consider geo-blocking or rate-limiting suspicious user agents.\n5. Review your public attack surface for unnecessary exposed endpoints.',
                'mitre': 'T1595 - Active Scanning',
            },
        }

        attack_type = incident.attack_type
        info = attack_summaries.get(attack_type, {
            'summary': f'A {attack_type.replace("_", " ").title()} attack was detected and blocked by Incidentra SOC.',
            'explanation': 'This type of attack targets web application vulnerabilities to gain unauthorized access or steal data.',
            'actions': '1. Review the incident details.\n2. Check server logs for related activity.\n3. Update all software and apply security patches.\n4. Contact your security team if you need assistance.',
            'mitre': 'T1190 - Exploit Public-Facing Application',
        })

        explanation = IncidentExplanation(
            incident_id=incident_id,
            ai_summary=info['summary'],
            threat_explanation=info['explanation'],
            recommended_actions=info['actions'],
            mitre_technique=info['mitre'],
            model_used='fallback-static',
        )
        db.session.add(explanation)
        db.session.commit()
        logger.info(f"Fallback explanation saved for incident {incident_id}.")
    except Exception as e:
        logger.error(f"Fallback explanation error: {e}")
        db.session.rollback()
