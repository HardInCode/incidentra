"""Seed the database with default detection rules and demo users."""
import os
import secrets
from werkzeug.security import generate_password_hash
from app import db
from app.models import DetectionRule, User, SeverityLevel, AppSetting

# Demo credentials (PostgreSQL users table — hashed, not stored in JSON).
# No hardcoded default password: set DEMO_ADMIN_PASSWORD / DEMO_ANALYST_PASSWORD manually
# (see .env / .env.docker), otherwise a random password is generated on first seed and
# printed ONCE to the startup log — it is never persisted in plaintext anywhere.
# SYNC_DEMO_CREDENTIALS=0 skips password refresh on existing users.
DEMO_ADMIN_USER = os.getenv('DEMO_ADMIN_USER', 'admin')
DEMO_ADMIN_EMAIL = os.getenv('DEMO_ADMIN_EMAIL', 'admin@incidentra.local')
DEMO_ADMIN_PASSWORD = os.getenv('DEMO_ADMIN_PASSWORD', '')
DEMO_ANALYST_USER = os.getenv('DEMO_ANALYST_USER', 'analyst')
DEMO_ANALYST_EMAIL = os.getenv('DEMO_ANALYST_EMAIL', 'analyst@incidentra.local')
DEMO_ANALYST_PASSWORD = os.getenv('DEMO_ANALYST_PASSWORD', '')
SYNC_DEMO_CREDENTIALS = os.getenv('SYNC_DEMO_CREDENTIALS', '1').lower() in ('1', 'true', 'yes')


EXTRA_RULES = [
    {
        'rule_name': 'File Upload - dangerous extension',
        'attack_type': 'FILE_UPLOAD',
        'pattern': r'(?i)(?:POST_DATA:)?file=[^&\s"]*\.(php\d*|phtml|phar|jsp|asp|aspx|exe|dll|sh|bat|cmd|ps1|htaccess|cgi)\b',
        'severity_level': SeverityLevel.HIGH,
        'description': 'Upload with executable/script extension in POST_DATA (vuln-web has no filter)',
    },
    {
        'rule_name': 'File Upload - double extension',
        'attack_type': 'FILE_UPLOAD',
        'pattern': r'(?i)(?:POST_DATA:)?file=[^&\s"]*\.(php|jsp|asp|aspx)[^&\s"]*\.(jpg|jpeg|png|gif|txt|pdf)\b',
        'severity_level': SeverityLevel.HIGH,
        'description': 'Upload disguised as image (e.g. shell.php.jpg)',
    },
    {
        'rule_name': 'Path Traversal - Incidentra JSON',
        'attack_type': 'PATH_TRAVERSAL',
        'pattern': r'(?i)(blocked_ips\.json|rate_limited\.json)',
        'severity_level': SeverityLevel.HIGH,
        'description': 'Detects reads of Incidentra enforcement JSON via LFI/path abuse',
    },
    {
        'rule_name': 'Path Traversal - logs folder',
        'attack_type': 'PATH_TRAVERSAL',
        'pattern': r'(?i)([/\\]logs[/\\])',
        'severity_level': SeverityLevel.MEDIUM,
        'description': 'Detects access to logs directory in request path or query',
    },
    {
        'rule_name': 'Path Traversal - Windows absolute file',
        'attack_type': 'PATH_TRAVERSAL',
        'pattern': r'(?i)(?:\?file=|[&;\s]file=|file=)[a-zA-Z]:[/\\]',
        'severity_level': SeverityLevel.HIGH,
        'description': 'Detects Windows drive-letter paths in file= parameter (lab gap)',
    },
    {
        'rule_name': 'Path Traversal - file param parent dirs',
        'attack_type': 'PATH_TRAVERSAL',
        'pattern': r'(?i)(?:\?file=|[&;\s]file=|file=)[^&\s"]*\.\.',
        'severity_level': SeverityLevel.HIGH,
        'description': 'Detects ../ in file= query (e.g. GET /files?file=../../etc/passwd)',
    },
    {
        'rule_name': 'Command Injection - vuln-web cmd param',
        'attack_type': 'COMMAND_INJECTION',
        'pattern': r'(?i)\bcmd=\s*[^&\s"]*\b(whoami|id|uname|ls|pwd|cat|ping)\b',
        'severity_level': SeverityLevel.CRITICAL,
        'description': 'Detects shell commands in GET /cmd?cmd=... (vuln-web lab)',
    },
]


def _deactivate_legacy_upload_rules():
    """Turn off broad lab rules that flagged every upload as FILE_UPLOAD."""
    legacy_names = [
        'File Upload - vuln-web POST_DATA',
        'File Upload - POST /files',
    ]
    changed = 0
    for name in legacy_names:
        rule = DetectionRule.query.filter_by(rule_name=name).first()
        if rule and rule.is_active:
            rule.is_active = False
            changed += 1
    if changed:
        db.session.commit()
        print(f"Deactivated {changed} legacy FILE_UPLOAD rule(s).")


def seed_missing_rules():
    """Insert new rules on existing DBs without wiping custom rules."""
    _deactivate_legacy_upload_rules()
    added = 0
    for r in EXTRA_RULES:
        exists = DetectionRule.query.filter_by(rule_name=r['rule_name']).first()
        if exists:
            continue
        db.session.add(DetectionRule(**r))
        added += 1
    if added:
        db.session.commit()
        print(f"Added {added} new detection rule(s).")
    return added


def seed_rules():
    if DetectionRule.query.count() > 0:
        seed_missing_rules()
        print("Rules already seeded.")
        return

    rules = [
        {
            'rule_name': 'SQL Injection - UNION SELECT',
            'attack_type': 'SQL_INJECTION',
            'pattern': r'(?i)(union\s+select|select\s+(\*|[\w]+\s*,\s*[\w\s,`]*|count\s*\([\w\s,*)]*\))\s+from\s+\w|insert\s+into\s+\w+\s*\(|drop\s+table\s+\w|delete\s+from\s+\w|update\s+\w+\s+set\s+\w)',
            'severity_level': SeverityLevel.CRITICAL,
            'description': 'Detects UNION-based SQL injection attempts',
        },
        {
            'rule_name': 'SQL Injection - OR 1=1',
            'attack_type': 'SQL_INJECTION',
            'pattern': r"(?i)(\bor\b\s+[\'\"]?\d+[\'\"]?\s*=\s*[\'\"]?\d+[\'\"]?)",
            'severity_level': SeverityLevel.CRITICAL,
            'description': 'Detects tautology-based SQL injection',
        },
        {
            'rule_name': 'SQL Injection - Blind (Sleep)',
            'attack_type': 'SQL_INJECTION',
            'pattern': r'(?i)(sleep\s*\(|benchmark\s*\(|waitfor\s+delay)',
            'severity_level': SeverityLevel.CRITICAL,
            'description': 'Detects time-based blind SQL injection',
        },
        {
            'rule_name': 'XSS - Script Tag',
            'attack_type': 'XSS',
            'pattern': r'(?i)(<script[\s>]|</script>)',
            'severity_level': SeverityLevel.HIGH,
            'description': 'Detects script tag injection',
        },
        {
            'rule_name': 'XSS - Event Handler',
            'attack_type': 'XSS',
            'pattern': r'(?i)(onerror\s*=|onload\s*=|onclick\s*=|onmouseover\s*=)',
            'severity_level': SeverityLevel.HIGH,
            'description': 'Detects HTML event handler injection',
        },
        {
            'rule_name': 'XSS - JavaScript Protocol',
            'attack_type': 'XSS',
            'pattern': r'(?i)(javascript\s*:|vbscript\s*:)',
            'severity_level': SeverityLevel.HIGH,
            'description': 'Detects javascript: protocol injection',
        },
        {
            'rule_name': 'Path Traversal',
            'attack_type': 'PATH_TRAVERSAL',
            'pattern': r'(?i)(\.\.\/|\.\.\\|%2e%2e%2f)',
            'severity_level': SeverityLevel.HIGH,
            'description': 'Detects directory traversal attempts',
        },
        {
            'rule_name': 'Command Injection',
            'attack_type': 'COMMAND_INJECTION',
            'pattern': r'(?i)(;|\||&&|\$\(|`)\s*(ls|cat|whoami|id|uname|wget|curl|bash|sh|nc|netcat|ping|python|perl|ruby)',
            'severity_level': SeverityLevel.CRITICAL,
            'description': 'Detects OS command injection attempts',
        },
        {
            'rule_name': 'Security Scanner Detection',
            'attack_type': 'SCANNER',
            'pattern': r'(?i)(nikto|sqlmap|nmap|acunetix|nessus|burpsuite|zaproxy|dirbuster)',
            'severity_level': SeverityLevel.MEDIUM,
            'description': 'Detects known security scanning tools',
        },
        {
            'rule_name': 'LFI/RFI - PHP Wrapper',
            'attack_type': 'LFI_RFI',
            'pattern': r'(?i)(php://input|php://filter|php://data|expect://)',
            'severity_level': SeverityLevel.CRITICAL,
            'description': 'Detects PHP wrapper-based LFI/RFI attempts',
        },
        {
            'rule_name': 'Brute Force - Login',
            'attack_type': 'BRUTE_FORCE',
            'pattern': r'threshold-based: 10+ requests to /login within 60s',
            'severity_level': SeverityLevel.HIGH,
            'description': 'Detects brute force login attempts (threshold-based)',
        },
        *EXTRA_RULES,
    ]

    for r in rules:
        rule = DetectionRule(**r)
        db.session.add(rule)

    db.session.commit()
    print(f"Seeded {len(rules)} detection rules.")


def _ensure_demo_user(username, email, password, role):
    """Create or optionally refresh demo user in PostgreSQL (password stored as hash).

    - password came from DEMO_*_PASSWORD env var: sync it on every start (explicit operator choice).
    - password not set: generate a random one on FIRST creation only (printed once, never
      persisted in plaintext); existing users are left untouched on later restarts so their
      credentials do not silently change.
    """
    user = User.query.filter_by(username=username).first()
    if user:
        if password and SYNC_DEMO_CREDENTIALS:
            user.email = email
            user.password_hash = generate_password_hash(password)
            user.role = role
            user.is_active = True
            db.session.commit()
            print(f"Demo user synced: {username} (password set from env var)")
        else:
            print(f"Demo user exists (sync skipped): {username}")
        return

    generated = not password
    if generated:
        password = secrets.token_urlsafe(12)

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        status='active',
    )
    db.session.add(user)
    db.session.commit()

    if generated:
        print("=" * 64)
        print(f"[SECURITY] Generated first-time password for '{username}':")
        print(f"  {username} / {password}")
        print("  Save this now — it will not be shown again. Change it after logging in,")
        print(f"  or set DEMO_{role.upper()}_PASSWORD in .env / .env.docker to control it.")
        print("=" * 64)
    else:
        print(f"Demo user created: {username} (password set from env var)")


def seed_admin():
    _ensure_demo_user(DEMO_ADMIN_USER, DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD, 'admin')


def seed_analyst():
    _ensure_demo_user(DEMO_ANALYST_USER, DEMO_ANALYST_EMAIL, DEMO_ANALYST_PASSWORD, 'analyst')


def seed_settings_from_env():
    """Copy non-empty env vars into app_settings (Docker .env.docker → AI/notifications)."""
    keys = [
        'GROQ_API_KEY', 'GROQ_MODEL', 'ABUSEIPDB_API_KEY',
        'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'ALERT_EMAIL',
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
    ]
    for key in keys:
        val = os.getenv(key, '').strip()
        if not val:
            continue
        existing = AppSetting.query.filter_by(key=key).first()
        if existing and existing.value:
            continue
        if existing:
            existing.value = val
        else:
            db.session.add(AppSetting(key=key, value=val))
    db.session.commit()


def seed_all():
    seed_admin()
    seed_analyst()
    seed_rules()
    seed_settings_from_env()
