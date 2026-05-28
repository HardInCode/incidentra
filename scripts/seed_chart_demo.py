#!/usr/bin/env python3
"""
Seed demo incidents across the last 7 days so Dashboard charts show a full timeline.

Purpose: fill PostgreSQL with Incident rows whose created_at is spread over 7 days
(timeline + severity donut). This is NOT Mode B "Inject log" in the SOC UI.

Charts use Incident.created_at from the DB — NOT timestamps inside access.log.

Docker (Postgres container exposed on localhost:5432):
  cd E:\\Capstone\\May\\incidentra-May
  $env:DATABASE_URL = "postgresql://incidentra:incidentra123@localhost:5432/incidentra_db"
  $env:REDIS_URL = "redis://localhost:6379/0"
  python scripts/seed_chart_demo.py

Manual (backend/.env already has DATABASE_URL — optional override in shell):
  python scripts/seed_chart_demo.py

Optional --append-logs: writes dated lines to access.log for Live Traffic only;
may also create extra incidents with TODAY's created_at if log monitor is running.
"""
import argparse
import os
import random
import sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
# docker compose run: backend mounted at /app, script at /scripts
if os.path.isfile(os.path.join("/app", "run.py")):
    BACKEND_DIR = "/app"
    PROJECT_ROOT = "/"
sys.path.insert(0, BACKEND_DIR)

# Host localhost:5432 is often Windows PostgreSQL — not the Docker container (see TUTORIAL).
DOCKER_DATABASE_URL_HOST = "postgresql://incidentra:incidentra123@127.0.0.1:5432/incidentra_db"
DOCKER_DATABASE_URL_INTERNAL = "postgresql+psycopg://incidentra:incidentra123@postgres:5432/incidentra_db"


def _mask_db_url(url: str) -> str:
    """Hide password in logs."""
    if "@" not in url:
        return url
    pre, rest = url.split("@", 1)
    if ":" in pre:
        scheme, _, _user = pre.rpartition("://")
        user = pre.split("://", 1)[-1].split(":")[0]
        return f"{scheme}://{user}:***@{rest}"
    return url


def configure_database_url(use_docker_host: bool, use_docker_internal: bool) -> str:
    """
    backend/.env often has MANUAL Postgres (postgres/..., incidentra_db).
    Docker Compose DB is incidentra/incidentra123/incidentra_db — usually NOT on host :5432
    if Windows PostgreSQL already uses that port.
    """
    env_path = os.path.join(BACKEND_DIR, ".env")
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
    except ImportError:
        pass

    if use_docker_internal:
        os.environ["DATABASE_URL"] = DOCKER_DATABASE_URL_INTERNAL
    elif use_docker_host:
        os.environ["DATABASE_URL"] = DOCKER_DATABASE_URL_HOST
    elif not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = DOCKER_DATABASE_URL_HOST

    url = os.environ["DATABASE_URL"]
    print(f"[DB] Using {_mask_db_url(url)}")
    if use_docker_internal:
        print("     (--docker-internal: Compose network, hostname postgres)")
    elif use_docker_host:
        print(
            "     (--docker: host -> 127.0.0.1:5432)\n"
            "     If auth fails, Windows PostgreSQL may own port 5432.\n"
            "     Use:  .\\scripts\\seed_chart_docker.ps1"
        )
    elif os.path.isfile(env_path) and "incidentra_db" not in url:
        print(
            "     [hint] Using backend/.env (manual DB). Dashboard Docker reads incidentra_db.\n"
            "     For Docker charts:  .\\scripts\\seed_chart_docker.ps1"
        )
    return url

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

# Demo-only IPs (RFC 5737 TEST-NET-3) — avoid 10.0.0.x so they are not confused with live simulates.
IPS = [
    "203.0.113.10",
    "203.0.113.20",
    "203.0.113.30",
    "198.51.100.40",
    "192.0.2.50",
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
        day_start = (now - timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        if day_offset == 0:
            day_end = now
        for hour in (9, 14, 20):
            row = random.choice(DEMO_ROWS)
            attack, _, path, method, payload = row
            dt = day_start.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            if dt > day_end:
                dt = day_end - timedelta(minutes=random.randint(1, 30))
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
            day_start = (now - timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)
            if day_offset == 0:
                day_end = now  # never seed "future" times on today (UTC)

            span_seconds = max(60, int((day_end - day_start).total_seconds()))
            count = random.randint(1, 3) if day_offset > 0 else random.randint(2, 5)
            for i in range(count):
                attack, sev_name, path, method, payload = random.choice(DEMO_ROWS)
                created = day_start + timedelta(
                    seconds=random.randint(0, span_seconds - 1),
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
    parser = argparse.ArgumentParser(description="Seed Incidentra dashboard chart demo data")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing DB")
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Host: force incidentra@127.0.0.1:5432 (fails if Windows PG owns port 5432)",
    )
    parser.add_argument(
        "--docker-internal",
        action="store_true",
        help="Inside Compose network (used by seed_chart_docker.ps1)",
    )
    parser.add_argument(
        "--append-logs",
        action="store_true",
        help="Also append dated lines to access.log (Live Traffic only; may trigger monitor)",
    )
    args = parser.parse_args()

    configure_database_url(
        use_docker_host=args.docker,
        use_docker_internal=args.docker_internal,
    )

    try:
        if not seed_incidents(dry_run=args.dry_run):
            sys.exit(1)
    except Exception as e:
        err = str(e).lower()
        if "password authentication failed" in err or "operationalerror" in err:
            print(
                "\n[ERROR] Cannot connect to PostgreSQL.\n"
                "  Docker running?  docker compose up -d\n"
                "  Docker + Windows both on :5432?  Run:  .\\scripts\\seed_chart_docker.ps1\n"
                "  Manual only?  python scripts/seed_chart_demo.py  (uses backend/.env)"
            )
        raise

    if args.append_logs and not args.dry_run:
        append_demo_logs()


if __name__ == "__main__":
    main()
