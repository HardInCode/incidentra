# SME-Guard

**Intelligent Web-SOC Platform with Automated Incident Response**

Platform pemantauan log web untuk UKM: deteksi serangan, insiden di PostgreSQL, blokir & rate limit IP, dashboard SOC (React).

> Capstone — President University, Faculty of Computer Science

**Repositori GitHub:** [github.com/HardInCode/sme-guard](https://github.com/HardInCode/sme-guard)

---

## Dokumentasi

| Dokumen | Isi |
|---------|-----|
| **[docs/TUTORIAL.md](docs/TUTORIAL.md)** | Docker + manual Windows, demo serangan, env |
| **[docs/GITHUB.md](docs/GITHUB.md)** | Clone, push, file rahasia, env Docker |
| **[docs/APPLICATION.md](docs/APPLICATION.md)** | Arsitektur, DB vs JSON, API |
| **[docs/LEARNING.md](docs/LEARNING.md)** | Token JWT, konsep capstone Bab 3–4 |
| **[docs/DEPLOY.md](docs/DEPLOY.md)** | Deploy VPS (nilai tambah) |
| **[docs/AUDIT_2026-05-19.md](docs/AUDIT_2026-05-19.md)** | Checklist uji manual, Docker & Burp |

---

## Clone & quick start — Docker

```powershell
git clone https://github.com/HardInCode/sme-guard.git
cd sme-guard
copy backend\.env.docker.example backend\.env.docker
docker compose up --build -d
```

**Prasyarat:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) Running.

| Layanan | URL |
|---------|-----|
| SOC UI | http://localhost:3000 |
| API | http://localhost:5000/api |
| Target lab | http://localhost:5050 |

Login: `admin` / `Admin@SMEGuard2026!`  
Opsional: `notepad backend\.env.docker` → `GROQ_API_KEY` (file lokal, tidak di-commit).

---

## Quick start — Manual

Tiga terminal — detail di [docs/TUTORIAL.md](docs/TUTORIAL.md):

```powershell
cd backend && copy .env.example .env && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt && python run.py
cd frontend && npm install && npm start
cd vuln-web && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt && python app.py
```

---

## Fitur utama (Mei 2026)

- Deteksi: SQLi, XSS, brute force, path traversal, LFI/RFI, scanner, command injection
- **IP Management** (`/blocked-ips`): tab **Blocked** + **Rate Limited** (clear / extend / edit policy)
- Insiden ongoing vs arsip, bulk resolve, export CSV, live traffic, rules, audit
- Docker: 6 service (postgres, redis, vuln-web, backend, celery, frontend)

---

## Skrip

```powershell
python scripts/reset_smeguard.py --clear-logs
python scripts/seed_chart_demo.py
```

Lihat [docs/TUTORIAL.md](docs/TUTORIAL.md).

---

## Struktur

```
backend/     Flask API, log monitor, detection
frontend/    React + MUI
vuln-web/    Target rentan + access.log + JSON enforcement
scripts/     reset, seed, init SQL
docs/        Dokumentasi lengkap
```

---

## Tim

| Nama | NIM | Peran |
|------|-----|-------|
| Hardin Irfan | 001202300066 | Project Lead & Backend |
| Nasywa Kamila | 001202300211 | AI Engineer & Frontend |
| Zaidan Mahfudz Azzam Saidi | 001202300144 | Security & QA |
