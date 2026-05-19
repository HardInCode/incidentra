# SME-Guard — Tutorial

Cara menjalankan proyek: **Docker** (disarankan) atau **manual** (Windows, tiga terminal).

| Dokumen | Isi |
|---------|-----|
| [APPLICATION.md](APPLICATION.md) | Arsitektur, DB vs JSON |
| [GITHUB.md](GITHUB.md) | Clone & push ke GitHub |
| [LEARNING.md](LEARNING.md) | Konsep token, Bab capstone |
| [DEPLOY.md](DEPLOY.md) | VPS / Docker di server |
| [AUDIT_2026-05-19.md](AUDIT_2026-05-19.md) | Checklist uji lengkap |

**Repo:** [github.com/HardInCode/sme-guard](https://github.com/HardInCode/sme-guard)

**Waktu:** ~45 menit · **Hasil:** Dashboard `:3000`, target `:5050`, deteksi & blokir IP.

---

## Yang akan berjalan

```
PostgreSQL + Redis
        │
        ▼
Backend (Flask :5000) ◄── tail access.log vuln-web
        │
        ▼
Frontend (React :3000)     vuln-web (:5050) ──► logs/access.log
                              └── blocked_ips.json, rate_limited.json
```

| Layanan | URL |
|---------|-----|
| SOC Dashboard | http://localhost:3000 |
| Backend API | http://localhost:5000/api |
| Vuln-web | http://localhost:5050 |

**Login:** `admin` / `Admin@SMEGuard2026!`

Token JWT disimpan di `localStorage` (`sme_token`). Mengapa API `:5000` di browser tab kosong bisa error? → [LEARNING.md §1–2](LEARNING.md#1-apa-itu-token-login)

---

## File environment (penting)

| File | Dipakai | Jangan |
|------|---------|--------|
| `backend/.env.example` | Template manual | Commit sebagai `.env` dengan secret |
| `backend/.env` | Manual `python run.py` | Push ke GitHub |
| `backend/.env.docker.example` | Template Docker (di repo) | — |
| `backend/.env.docker` | Docker compose (buat dari example) | Push jika sudah berisi API key |
| `docker-compose.yml` | Override `DATABASE_URL`, `REDIS_URL` untuk container | Edit `localhost` untuk DB di Docker |

**Docker:** URL database **bukan** di `.env.docker` — ada di `docker-compose.yml` (`postgresql+psycopg://...@postgres:5432/...`).

---

## Opsi A — Docker (disarankan)

**Prasyarat:** Docker Desktop **Running** (hijau).

```powershell
git clone https://github.com/HardInCode/sme-guard.git
cd sme-guard
copy backend\.env.docker.example backend\.env.docker
# Opsional: notepad backend\.env.docker
docker compose up --build -d
docker compose ps
```

Tunggu ~2 menit. Semua service harus **running** (backend tidak restart loop).

| Layanan | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API | http://localhost:5000/api |
| Vuln-web | http://localhost:5050 |

**Volume `vuln_logs`:** backend `/app/watched_logs/` = vuln-web `/app/logs/` (log + JSON bersama).

**Cek backend:**

```powershell
docker compose logs backend --tail 30
```

Harus ada: `PostgreSQL ready`, `DB init complete`, `Log monitor started`, gunicorn listening.

**Reset data (host, venv backend):**

```powershell
python scripts/reset_smeguard.py
```

**Stop:** `docker compose down`

### Troubleshooting Docker

| Masalah | Solusi |
|---------|--------|
| `dockerDesktopLinuxEngine` gagal | Jalankan Docker Desktop dulu |
| Port 3000/5000/5050 dipakai | Tutup proses manual atau `docker compose down` |
| Backend restart loop | `docker compose logs backend` — cek `postgresql+psycopg` di compose |
| Build frontend `ajv` error | `docker compose build --no-cache frontend` |
| UI tidak panggil API | Rebuild frontend; `REACT_APP_API_URL` harus `http://localhost:5000/api` |
| Nama container bentrok | `docker compose down` lalu `docker rm -f smeguard_postgres smeguard_redis ...` |

---

## Opsi B — Manual (Windows)

### Prasyarat

Python 3.10–3.13 · Node 18–20 LTS · PostgreSQL 15 · Redis 7.

### PostgreSQL

```powershell
psql -U postgres -f scripts/init_postgres.sql
psql -U smeguard -d smeguard_db -c "SELECT version();"
```

### Redis

```powershell
redis-cli ping
```

Harus `PONG`.

### Backend (Terminal 1)

```powershell
cd backend
copy .env.example .env
notepad .env
```

First run (simulasi):

```env
DATABASE_URL=postgresql+psycopg://smeguard:smeguard123@localhost:5432/smeguard_db
REDIS_URL=redis://localhost:6379/0
USE_SIMULATED_LOGS=true
DEMO_MODE=true
```

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

### Frontend (Terminal 2)

```powershell
cd frontend
npm install
npm start
```

Opsional grafik: `python scripts/seed_chart_demo.py` (venv backend, dari root).

### Vuln-web (Terminal 3)

```powershell
cd vuln-web
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

### Sambungkan log nyata

Edit `backend\.env`:

```env
USE_SIMULATED_LOGS=false
DEMO_MODE=false
WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log
BLOCKED_IPS_JSON_PATH=../vuln-web/logs/blocked_ips.json
RATE_LIMITED_JSON_PATH=../vuln-web/logs/rate_limited.json
```

Restart backend. Log: `Tailing real log: ...`

---

## IP Management (Blocked & Rate Limited)

Menu sidebar: **IP Management** (route `/blocked-ips`).

| Tab | Fungsi |
|-----|--------|
| **Blocked** | Blokir permanen/sementara, edit durasi, unblock (DB + `blocked_ips.json`) |
| **Rate Limited** | Daftar IP rate limit, **Clear**, **Extend** (TTL, max requests, window) |

Setelah serangan **SCANNER** (medium), IP muncul di tab Rate Limited — bukan di Blocked.

Unblock di tab Blocked juga menghapus rate limit untuk IP tersebut.

---

## Demo serangan

| Severity | Respons | Contoh |
|----------|---------|--------|
| low | Monitor | — |
| medium | Rate limit (429) | `curl -A "Nikto/2.1.6" http://localhost:5050/` |
| high | Blokir sementara | Path traversal `?file=../../etc/passwd` |
| critical | Blokir permanen | SQLi di `/login` |

**SQLi:** `admin' OR '1'='1' --` di login → insiden → 403 di `/`.

**Path traversal:** URL `?file=../../etc/passwd` → insiden **PATH_TRAVERSAL** (bukan LFI jika tanpa `php://`).

**Brute force:**

```powershell
for ($i = 1; $i -le 12; $i++) {
  curl -X POST -d "username=admin&password=wrong$i" http://localhost:5050/login -s -o NUL
}
```

**Simulate Attack:** Incidents → Mode B (log injection).

Checklist lengkap + Burp: [AUDIT_2026-05-19.md](AUDIT_2026-05-19.md).

---

## Skrip utilitas

Dari root, venv backend aktif:

| Perintah | Fungsi |
|----------|--------|
| `python scripts/reset_smeguard.py` | Kosongkan insiden, blokir, rate JSON, Redis |
| `python scripts/reset_smeguard.py --clear-logs` | + kosongkan access.log |
| `python scripts/seed_chart_demo.py` | Grafik dashboard 7 hari |

Setelah reset → restart backend (dan vuln-web jika perlu).

---

## Troubleshooting umum

| Masalah | Solusi |
|---------|--------|
| Database error | Cek `DATABASE_URL` + user `smeguard` |
| Redis error | `redis-cli ping` |
| Insiden tidak muncul | `USE_SIMULATED_LOGS` / path log |
| 403 terus | Unblock di IP Management atau reset |
| Grafik kosong | `seed_chart_demo.py` |

---

## Langkah berikutnya

- [APPLICATION.md](APPLICATION.md) — arsitektur & API  
- [GITHUB.md](GITHUB.md) — push tim  
- [LEARNING.md](LEARNING.md) — Bab 3/4 & perasaan “selalu kurang”
