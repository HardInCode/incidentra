#!/usr/bin/env python3
"""
Seed demo incidents across the last 7 days so Dashboard charts show a full timeline.

Charts read Incident.created_at from PostgreSQL — NOT the timestamp inside access.log.
For chart testing, use this script instead of only editing access.log.

Usage (from project root, backend venv active):
  cd backend
  ..\\venv\\Scripts\\activate
  python ..\\scripts\\seed_chart_demo.py
  python ..\\scripts\\seed_chart_demo.py --dry-run

Optional: append sample lines to access.log (Live Traffic only):
  python ..\\scripts\\seed_chart_demo.py --append-logs
"""
import argparse
import os
import random
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))
except ImportError:
    pass

# Varied demo rows: (attack_type, severity enum name, path snippet)
DEMO_ROWS = [
    ("SQL_INJECTION", "CRITICAL", "/search", "GET", "q=1' OR 1=1--"),
    ("XSS", "HIGH", "/comment", "POST", "body=<script>alert(1)</script>"),
    ("BRUTE_FORCE", "HIGH", "/login", "POST", "username=admin"),
    ("PATH_TRAVERSAL", "HIGH", "/files", "GET", "file=../../../etc/passwd"),
    ("COMMAND_INJECTION", "CRITICAL", "/cmd", "GET", "cmd=;whoami"),
    ("SCANNER", "MEDIUM", "/", "GET", "ua=sqlmap/1.7"),
    ("LFI_RFI", "CRITICAL", "/index.php", "GET", "page=php://filter"),
]

IPS = [
    "10.0.0.15",
    "172.16.0.88",
    "203.45.12.9",
    "185.192.16.47",
    "192.168.1.200",
]


def resolve_log_path():
    path = os.getenv("WEB_SERVER_LOG_PATH", "../vuln-web/logs/access.log")
    if not os.path.isabs(path):
        path = os.path.normpath(os.path.join(BACKEND_DIR, path))
    return path


def nginx_line(ip, dt, method, path, status, query="", ua="Mozilla/5.0"):
    """Build one Combined Log Format line (UTC timestamp)."""
    t = dt.strftime("%d/%b/%Y:%H:%M:%S +0000")
    if method == "GET" and query:
        full = f"{path}?{query}"
    else:
        full = path
    post = ""
    if method == "POST" and query:
        post = f" POST_DATA:{query}"
    return (
        f'{ip} - - [{t}] "{method} {full} HTTP/1.1" {status} 256 "-" "{ua}"{post}\n'
    )


def append_demo_logs():
    log_path = resolve_log_path()
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    now = datetime.utcnow()
    lines = []
    for day_offset in range(6, -1, -1):
        day = now - timedelta(days=day_offset)
        for hour in (9, 14, 20):
            row = random.choice(DEMO_ROWS)
            attack, _, path, method, payload = row
            dt = day.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            ip = random.choice(IPS)
            lines.append(nginx_line(ip, dt, method, path, 200 if attack != "BRUTE_FORCE" else 401, payload))
    with open(log_path, "a", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[OK] Appended {len(lines)} lines to {log_path}")
    print("     Note: log monitor may create NEW incidents with today's created_at unless paused.")


def seed_incidents(dry_run=False):
    from app import create_app, db
    from app.models import Incident, SeverityLevel, IncidentStatus, DetectionRule

    app = create_app(os.getenv("FLASK_ENV", "development"))
    sev_map = {
        "LOW": SeverityLevel.LOW,
        "MEDIUM": SeverityLevel.MEDIUM,
        "HIGH": SeverityLevel.HIGH,
        "CRITICAL": SeverityLevel.CRITICAL,
    }

    with app.app_context():
        rules_by_type = {
            r.attack_type: r.id for r in DetectionRule.query.filter_by(is_active=True).all()
        }
        now = datetime.utcnow()
        to_add = []

        for day_offset in range(6, -1, -1):
            day_base = (now - timedelta(days=day_offset)).replace(
                hour=12, minute=0, second=0, microsecond=0
            )
            # More incidents on recent days, fewer on older days
            count = random.randint(1, 3) if day_offset > 0 else random.randint(2, 5)
            for i in range(count):
                attack, sev_name, path, method, payload = random.choice(DEMO_ROWS)
                created = day_base + timedelta(
                    hours=random.randint(-6, 6),
                    minutes=random.randint(0, 59),
                )
                ip = random.choice(IPS)
                status = random.choice(
                    [IncidentStatus.NEW, IncidentStatus.NEW, IncidentStatus.RESOLVED]
                )
                resolved_at = None
                if status == IncidentStatus.RESOLVED:
                    resolved_at = created + timedelta(minutes=random.randint(5, 120))

                to_add.append(
                    Incident(
                        source_ip=ip,
                        attack_type=attack,
                        severity=sev_map[sev_name],
                        status=status,
                        raw_payload=payload[:500],
                        request_path=path,
                        request_method=method,
                        user_agent="seed-chart-demo/1.0",
                        response_code=403 if sev_name == "CRITICAL" else 200,
                        rule_id=rules_by_type.get(attack),
                        created_at=created,
                        updated_at=created,
                        resolved_at=resolved_at,
                    )
                )

        if dry_run:
            print(f"[DRY-RUN] Would insert {len(to_add)} incidents across 7 days.")
            by_day = {}
            for inc in to_add:
                d = inc.created_at.date().isoformat()
                by_day[d] = by_day.get(d, 0) + 1
            for d in sorted(by_day):
                print(f"  {d}: {by_day[d]}")
            return True

        db.session.add_all(to_add)
        db.session.commit()
        print(f"[OK] Inserted {len(to_add)} demo incidents (created_at spread over last 7 days).")
        print("     Refresh Dashboard — timeline & severity trend should show multiple days.")
        return True


def main():
    parser = argparse.ArgumentParser(description="Seed SME-Guard dashboard chart demo data")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing DB")
    parser.add_argument(
        "--append-logs",
        action="store_true",
        help="Also append dated lines to access.log (Live Traffic only; may trigger monitor)",
    )
    args = parser.parse_args()

    if not seed_incidents(dry_run=args.dry_run):
        sys.exit(1)
    if args.append_logs and not args.dry_run:
        append_demo_logs()


if __name__ == "__main__":
    main()
