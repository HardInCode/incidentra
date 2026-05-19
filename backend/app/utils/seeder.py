"""Seed the database with default detection rules and admin user."""
from werkzeug.security import generate_password_hash
from app import db
from app.models import DetectionRule, User, SeverityLevel


def seed_rules():
    if DetectionRule.query.count() > 0:
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
    ]

    for r in rules:
        rule = DetectionRule(**r)
        db.session.add(rule)

    db.session.commit()
    print(f"Seeded {len(rules)} detection rules.")


def seed_admin():
    if User.query.filter_by(username='admin').first():
        print("Admin user already exists.")
        return

    admin = User(
        username='admin',
        email='admin@smeguard.local',
        password_hash=generate_password_hash('Admin@SMEGuard2026!'),
        role='admin',
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin user created: admin / Admin@SMEGuard2026!")


def seed_analyst():
    # Demo analyst: analyst / Analyst@SMEGuard2026! (read-mostly; admin-only actions hidden in UI)
    if User.query.filter_by(username='analyst').first():
        print("Analyst user already exists.")
        return

    analyst = User(
        username='analyst',
        email='analyst@smeguard.local',
        password_hash=generate_password_hash('Analyst@SMEGuard2026!'),
        role='analyst',
    )
    db.session.add(analyst)
    db.session.commit()
    print("Analyst user created: analyst / Analyst@SMEGuard2026!")


def seed_all():
    seed_admin()
    seed_analyst()
    seed_rules()
