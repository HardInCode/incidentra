# Incidentra

**Intelligent Web-SOC Platform with Automated Incident Response**

Web log monitoring platform for SMEs: attack detection, incident management in PostgreSQL, IP blocking & rate limiting, SOC dashboard (React).

> Capstone — President University, Faculty of Computer Science

**GitHub Repository:** [github.com/HardInCode/incidentra](https://github.com/HardInCode/incidentra)

---

## Quick start — Docker

```powershell
git clone https://github.com/HardInCode/incidentra.git
cd incidentra
copy backend\.env.docker.example backend\.env.docker
docker compose up --build -d
```

**Prerequisite:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.


| Service    | URL                                                    |
| ---------- | ------------------------------------------------------ |
| SOC UI     | [http://localhost:3000](http://localhost:3000)         |
| API        | [http://localhost:5000/api](http://localhost:5000/api) |
| Target lab | [http://localhost:5050](http://localhost:5050)         |


Login: `admin` / `Admin@Incidentra2026!`  
Optional: edit `backend\.env.docker` → `GROQ_API_KEY` (local file, do not commit).

---

## Quick start — Manual

Three terminals (full details in [docs/GUIDE.md](docs/GUIDE.md)):

```powershell
cd backend && copy .env.example .env && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt && python run.py
cd frontend && npm install && npm start
cd vuln-web && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt && python app.py
```

Reset demo: `python scripts/reset_smeguard.py --clear-logs` (from repo root, backend venv active).

---

## Ports & login


| Service        | URL                                                    | Credentials                      |
| -------------- | ------------------------------------------------------ | -------------------------------- |
| SOC Dashboard  | [http://localhost:3000](http://localhost:3000)         | `admin` / `Admin@Incidentra2026!` |
| Backend API    | [http://localhost:5000/api](http://localhost:5000/api) | JWT after login                  |
| vuln-web (lab) | [http://localhost:5050](http://localhost:5050)         | `admin` / `password` (shop demo) |


---

## Documentation

**Full map:** [docs/README.md](docs/README.md)

| File | Purpose |
|------|---------|
| [docs/GUIDE.md](docs/GUIDE.md) | Run the system (Docker/manual), defense demo, troubleshooting |
| [docs/AUDIT.md](docs/AUDIT.md) | **Full defense audit — May 2026** (~100 scenarios, A–J) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture: log → engine → JSON → vuln-web |
| [docs/DETECTION.md](docs/DETECTION.md) | Detection, Lab mode, Phase 3, Live Traffic vs incidents |
| [docs/form4/](docs/form4/) | **Form 4** — v2 implementation + cover + screenshot checklist |

Optional: [docs/additional/](docs/additional/) (deploy, GitHub, learning)

---

## Key features (May 2026)

- Detection: SQLi, XSS, brute force, path traversal, LFI/RFI, scanner, command injection, file upload (malicious extensions); **Lab mode** in Settings (UI rules only, for defense demo)
- **IP Management** (`/blocked-ips`): **Blocked** + **Rate Limited** tabs
- Ongoing vs archived incidents, bulk resolve, CSV export, live traffic, rules, audit
- Docker: 6 services (postgres, redis, vuln-web, backend, celery, frontend)
- Optional Phase 3 lab: set `vuln-web/.env` → `VULN_UNSAFE_CMD=1` / `VULN_UNSAFE_UPLOAD=1` — restart vuln-web; see [docs/GUIDE.md](docs/GUIDE.md)

---

## Structure

```
backend/     Flask API, log monitor, detection
frontend/    React + MUI
vuln-web/    Vulnerable target + access.log + JSON enforcement
scripts/     reset, seed, init SQL
docs/        Documentation
```

---

## Team


| Name                       | NIM          | Role                     |
| -------------------------- | ------------ | ------------------------ |
| Hardin Irfan               | 001202300066 | Project Lead & Backend   |
| Zaidan Mahfudz Azzam Saidi | 001202300144 | Security & QA            |


