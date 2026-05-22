# SME-Guard

**Intelligent Web-SOC Platform with Automated Incident Response**

Platform pemantauan log web untuk UKM: deteksi serangan, insiden di PostgreSQL, blokir & rate limit IP, dashboard SOC (React).

> Capstone — President University, Faculty of Computer Science

**Repositori GitHub:** [github.com/HardInCode/sme-guard](https://github.com/HardInCode/sme-guard)

---

## Quick start — Docker

```powershell
git clone https://github.com/HardInCode/sme-guard.git
cd sme-guard
copy backend\.env.docker.example backend\.env.docker
docker compose up --build -d
```

**Prasyarat:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) Running.


| Layanan    | URL                                                    |
| ---------- | ------------------------------------------------------ |
| SOC UI     | [http://localhost:3000](http://localhost:3000)         |
| API        | [http://localhost:5000/api](http://localhost:5000/api) |
| Target lab | [http://localhost:5050](http://localhost:5050)         |


Login: `admin` / `Admin@Incidentra2026!`  
Opsional: `notepad backend\.env.docker` → `GROQ_API_KEY` (file lokal, tidak di-commit).

---

## Quick start — Manual

Tiga terminal (detail lengkap di [docs/GUIDE.md](docs/GUIDE.md)):

```powershell
cd backend && copy .env.example .env && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt && python run.py
cd frontend && npm install && npm start
cd vuln-web && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt && python app.py
```

Reset demo: `python scripts/reset_smeguard.py --clear-logs` (dari root, venv backend aktif).

---

## Port & login


| Layanan        | URL                                                    | Kredensial                       |
| -------------- | ------------------------------------------------------ | -------------------------------- |
| SOC Dashboard  | [http://localhost:3000](http://localhost:3000)         | `admin` / `Admin@Incidentra2026!`  |
| Backend API    | [http://localhost:5000/api](http://localhost:5000/api) | JWT setelah login                |
| vuln-web (lab) | [http://localhost:5050](http://localhost:5050)         | `admin` / `password` (shop demo) |


---

## Dokumentasi

**Peta lengkap:** [docs/README.md](docs/README.md)

| File | Untuk apa |
|------|-----------|
| [docs/GUIDE.md](docs/GUIDE.md) | Jalankan sistem (Docker/manual), demo sidang, troubleshooting |
| [docs/AUDIT.md](docs/AUDIT.md) | **Audit full sidang — Mei 2026** (~100 skenario, A–J) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arsitektur: log → engine → JSON → vuln-web |
| [docs/DETECTION.md](docs/DETECTION.md) | Deteksi, Lab mode, Phase 3, Live Traffic vs insiden |
| [docs/form4/](docs/form4/) | **Form 4** — v2 implementation + cover + screenshot checklist |

Opsional: [docs/additional/](docs/additional/) (deploy, GitHub, learning)

---

## Fitur utama (Mei 2026)

- Deteksi: SQLi, XSS, brute force, path traversal, LFI/RFI, scanner, command injection, file upload (ekstensi berbahaya); **Lab mode** di Settings (hanya rule UI, untuk demo sidang)
- **IP Management** (`/blocked-ips`): tab **Blocked** + **Rate Limited**
- Insiden ongoing vs arsip, bulk resolve, export CSV, live traffic, rules, audit
- Docker: 6 service (postgres, redis, vuln-web, backend, celery, frontend)
- Fase 3 lab (opsional): `vuln-web/.env` → `VULN_UNSAFE_CMD=1` / `VULN_UNSAFE_UPLOAD=1` — restart vuln-web; lihat [docs/GUIDE.md](docs/GUIDE.md)

---

## Struktur

```
backend/     Flask API, log monitor, detection
frontend/    React + MUI
vuln-web/    Target rentan + access.log + JSON enforcement
scripts/     reset, seed, init SQL
docs/        Dokumentasi
```

---

## Tim


| Nama                       | NIM          | Peran                  |
| -------------------------- | ------------ | ---------------------- |
| Hardin Irfan               | 001202300066 | Project Lead & Backend |
| Nasywa Kamila              | 001202300211 | AI Engineer & Frontend |
| Zaidan Mahfudz Azzam Saidi | 001202300144 | Security & QA          |


