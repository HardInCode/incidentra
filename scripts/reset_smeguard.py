#!/usr/bin/env python3
"""
SME-Guard Reset Script

Menghapus semua data incidents, blocked IPs, audit logs, dan file terkait sehingga
sistem bisa dimulai dari awal (0 incidents). Tidak menghapus users, detection rules,
atau app settings (konfigurasi API keys, SMTP, Telegram tetap tersimpan).

Usage:
  python scripts/reset_smeguard.py              → Reset DB, Redis, JSON files
  python scripts/reset_smeguard.py --clear-logs → Juga kosongkan access.log
  python scripts/reset_smeguard.py --reset-all  → Reset DB + Redis + JSON + Settings DB

Docker (via reset_smeguard_docker.ps1 — jangan panggil --docker-internal manual):
  .\scripts\reset_smeguard_docker.ps1
  .\scripts\reset_smeguard_docker.ps1 -ClearLogs
  .\scripts\reset_smeguard_docker.ps1 -ResetAll

Run dari root project.
"""
import argparse
import json
import os
import sys

# Project root = parent of scripts/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
VULN_WEB_DIR = os.path.join(PROJECT_ROOT, "vuln-web")

# docker compose run: backend mounted at /app, script at /scripts
if os.path.isfile(os.path.join("/app", "run.py")):
    BACKEND_DIR = "/app"
    PROJECT_ROOT = "/"

# Load .env dari backend
sys.path.insert(0, BACKEND_DIR)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))
except ImportError:
    pass

DOCKER_DATABASE_URL = "postgresql://smeguard:smeguard123@postgres:5432/smeguard_db"
DOCKER_REDIS_URL    = "redis://redis:6379/0"


def configure_docker_urls():
    """Override DATABASE_URL & REDIS_URL ke hostname Compose (postgres, redis)."""
    os.environ["DATABASE_URL"] = DOCKER_DATABASE_URL
    os.environ["REDIS_URL"]    = DOCKER_REDIS_URL


def get_db_url():
    """Return URL for psycopg (postgresql://, no +psycopg)."""
    url = os.getenv("DATABASE_URL", "postgresql://smeguard:smeguard123@localhost:5432/smeguard_db")
    if "postgresql+psycopg://" in url:
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def reset_database():
    """Truncate incidents dan tabel terkait. Tetap pertahankan users, detection_rules, app_settings."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg tidak terpasang. Jalankan: pip install 'psycopg[binary]'")
        return False

    url = get_db_url()
    try:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                # Set lock timeout to 5 seconds to prevent hanging indefinitely
                cur.execute("SET lock_timeout = '5s'")
                
                # Terminate other connections to release locks on tables
                try:
                    cur.execute("""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                          AND pid <> pg_backend_pid()
                    """)
                    conn.commit()
                except Exception as ex:
                    # Rollback transaction in case of lack of permissions
                    conn.rollback()

                # Truncate child tables first (FK order), then parent
                tables = [
                    "incident_notes",
                    "incident_explanations",
                    "incident_logs",
                    "incidents",
                    "blocked_ips",
                    "audit_logs",
                ]
                for t in tables:
                    cur.execute(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE')
                conn.commit()
        print("[OK] Database: incidents, incident_logs, incident_explanations, incident_notes, blocked_ips, audit_logs di-truncate.")
        return True
    except Exception as e:
        print(f"[ERROR] Database: {e}")
        return False


def reset_app_settings():
    """Hapus semua app_settings dari DB (API keys, SMTP, Telegram config). Gunakan --reset-all."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg tidak terpasang.")
        return False

    url = get_db_url()
    try:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                # Set lock timeout to 5 seconds to prevent hanging indefinitely
                cur.execute("SET lock_timeout = '5s'")
                
                # Check if table exists first
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'app_settings'
                    )
                """)
                exists = cur.fetchone()[0]
                if exists:
                    cur.execute('TRUNCATE TABLE "app_settings" RESTART IDENTITY CASCADE')
                    conn.commit()
                    print("[OK] app_settings: semua konfigurasi dihapus (API keys, SMTP, Telegram).")
                else:
                    print("[INFO] app_settings: tabel belum ada, skip.")
        return True
    except Exception as e:
        print(f"[ERROR] app_settings: {e}")
        return False


def reset_redis():
    """Flush semua database Redis."""
    try:
        import redis
    except ImportError:
        print("ERROR: redis tidak terpasang. Jalankan: pip install redis")
        return False

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(url)
        r.flushall()
        print("[OK] Redis: semua data di-flush (blocked IPs, BF counters, dedup cache).")
        return True
    except Exception as e:
        print(f"[ERROR] Redis: {e}")
        return False


def reset_json_files(docker_internal: bool = False):
    """
    Reset blocked_ips.json dan rate_limited.json ke struktur kosong.

    Docker:  PS1 mount vuln-web/logs ke /vuln-web/logs di dalam container.
    Manual:  resolve dari BACKEND_DIR atau env BLOCKED_IPS_JSON_PATH.
    """
    blocked_data = {"blocked": [], "details": {}, "updated_at": ""}
    rate_data = {"rate_limited": [], "updated_at": ""}

    if docker_internal:
        # Path di dalam container (di-mount oleh PS1: -v .../vuln-web/logs:/vuln-web/logs)
        paths_to_reset = [
            ("/vuln-web/logs/blocked_ips.json", blocked_data),
            ("/vuln-web/logs/rate_limited.json", rate_data),
        ]
    else:
        backend_blocked = os.getenv("BLOCKED_IPS_JSON_PATH", "../vuln-web/logs/blocked_ips.json")
        backend_rate = os.getenv("RATE_LIMITED_JSON_PATH", "../vuln-web/logs/rate_limited.json")

        def resolve_backend_path(rel_path):
            return os.path.normpath(os.path.join(BACKEND_DIR, rel_path))

        paths_to_reset = [
            (resolve_backend_path(backend_blocked), blocked_data),
            (resolve_backend_path(backend_rate), rate_data),
            (os.path.join(VULN_WEB_DIR, "logs", "blocked_ips.json"), blocked_data),
            (os.path.join(VULN_WEB_DIR, "logs", "rate_limited.json"), rate_data),
        ]

    # Deduplicate by path (same file may appear twice)
    seen = set()
    unique_paths = []
    for path, data in paths_to_reset:
        path_abs = os.path.abspath(path)
        if path_abs in seen:
            continue
        seen.add(path_abs)
        unique_paths.append((path, data))

    ok = True
    for path, data in unique_paths:
        if not docker_internal and path.startswith("/app/"):
            print(f"[SKIP] {path} adalah Docker path, skip (Docker pakai volume).")
            continue
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[OK] File: {os.path.relpath(path, PROJECT_ROOT)} direset.")
        except Exception as e:
            print(f"[ERROR] {path}: {e}")
            ok = False
    return ok


def clear_access_log(docker_internal: bool = False):
    """Kosongkan access.log vuln-web."""
    if docker_internal:
        log_path = "/vuln-web/logs/access.log"
    else:
        # Default local dev path
        log_path = os.path.join(VULN_WEB_DIR, "logs", "access.log")

        # Support env override
        env_log = os.getenv("VULN_LOG_FILE", "")
        if env_log:
            if os.path.isabs(env_log):
                log_path = env_log
            else:
                log_path = os.path.join(VULN_WEB_DIR, env_log)

        # Skip Docker paths saat mode manual
        if log_path.startswith("/app/"):
            print(f"[SKIP] {log_path} adalah Docker path, skip.")
            return True

    try:
        if os.path.exists(log_path):
            with open(log_path, "w") as f:
                f.write("")
            print(f"[OK] access.log dikosongkan: {log_path}")
        else:
            print(f"[INFO] access.log belum ada: {log_path}")
        return True
    except Exception as e:
        print(f"[ERROR] access.log: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Reset SME-Guard ke state awal (0 incidents)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh:
  python scripts/reset_smeguard.py                  # Reset incidents + Redis + JSON
  python scripts/reset_smeguard.py --clear-logs     # + kosongkan access.log
  python scripts/reset_smeguard.py --reset-all      # + hapus app_settings (API keys hilang!)

Docker (gunakan PS1):
  .\\scripts\\reset_smeguard_docker.ps1
  .\\scripts\\reset_smeguard_docker.ps1 -ClearLogs
  .\\scripts\\reset_smeguard_docker.ps1 -ResetAll
        """
    )
    parser.add_argument(
        "--clear-logs",
        action="store_true",
        help="Juga kosongkan vuln-web/logs/access.log",
    )
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Reset SEMUA termasuk app_settings (API keys, SMTP, Telegram config akan hilang!)",
    )
    parser.add_argument(
        "--docker-internal",
        action="store_true",
        help="Pakai hostname Compose (postgres, redis) — otomatis diset oleh reset_smeguard_docker.ps1",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("SME-Guard Reset Script")
    print("=" * 50)

    if args.docker_internal:
        configure_docker_urls()
        print("Mode: Docker Compose (hostname postgres & redis)")

    if args.reset_all:
        print("⚠️  MODE --reset-all: app_settings (API keys dll) akan dihapus!")
        print()

    r1 = reset_database()
    r2 = reset_redis()
    r3 = reset_json_files(docker_internal=args.docker_internal)
    r4 = True
    r5 = True

    if args.clear_logs:
        r4 = clear_access_log(docker_internal=args.docker_internal)

    if args.reset_all:
        r5 = reset_app_settings()

    print("=" * 50)
    all_ok = r1 and r2 and r3 and r4 and r5
    if all_ok:
        print("✅ Reset selesai. Restart backend untuk mulai dari awal.")
        if args.docker_internal:
            print("   docker compose restart backend")
        if not args.reset_all:
            print("   (app_settings/konfigurasi API keys tetap tersimpan)")
    else:
        print("⚠️  Beberapa langkah gagal. Periksa error di atas.")
        sys.exit(1)


if __name__ == "__main__":
    main()