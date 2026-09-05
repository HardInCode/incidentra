# Incidentra

**Intelligent Web-SOC Platform with Automated Incident Response**

Real-time web log monitoring platform for SMEs — attack detection, automated incident management, IP blocking & rate limiting, and a SOC dashboard built with React and Flask.

[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Features

- **Detection Engine** — SQLi, XSS, brute force, path traversal, LFI/RFI, scanner detection, command injection, file upload (malicious extensions)
- **IP Management** — Blocked IPs + Rate Limited tabs with auto-escalation tiers
- **Incident Lifecycle** — Ongoing vs archived incidents, bulk resolve, CSV export
- **Live Traffic Monitor** — Real-time log streaming with attack classification
- **SOC Dashboard** — Charts, severity breakdown, top attackers, threat timeline
- **Automated Response** — IP auto-blocking, rate limiting, configurable thresholds
- **AI Explanations** — Optional Groq AI integration for incident analysis
- **Alert Notifications** — Email (SMTP) and Telegram bot integration
- **Lab Environment** — Built-in vulnerable web app (`/lab`) for testing & demos
- **Detection Rules** — Configurable rules with Lab Mode toggle (UI rules only vs OWASP baseline)
- **Internationalization** — Multi-language support (EN/ID)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    React Frontend (MUI)                       │
│              SOC Dashboard · IP Management · Rules            │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST API (JWT)
┌───────────────────────────▼──────────────────────────────────┐
│                     Flask Backend API                         │
│  Detection Engine · Log Monitor · Response Engine · Seeder    │
├──────────────┬───────────────────────┬───────────────────────┤
│  PostgreSQL  │        Redis          │     Celery Worker     │
│  Incidents   │  Rate limit cache     │  Background tasks     │
│  Users/Rules │  Escalation tiers     │  Scheduled checks     │
│  Blocked IPs │  Block cache          │  Alert dispatch       │
└──────────────┴───────────────────────┴───────────────────────┘
                            │ Shared filesystem (access.log)
┌───────────────────────────▼──────────────────────────────────┐
│                vuln-web (Target Lab)                          │
│  Intentionally vulnerable Flask app for attack simulation     │
│  SQLi · XSS · CSRF · Command Injection · File Upload         │
└──────────────────────────────────────────────────────────────┘
```

---

## Quick Start — Docker

```bash
git clone https://github.com/HardInCode/incidentra.git
cd incidentra
cp backend/.env.docker.example backend/.env.docker
docker compose up --build -d
```

**Prerequisite:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

| Service       | URL                          |
|---------------|------------------------------|
| SOC Dashboard | http://localhost:3000         |
| Backend API   | http://localhost:5000/api     |
| Target Lab    | http://localhost:5050         |

**Login:** Check `backend/.env.docker` for `DEMO_ADMIN_PASSWORD`, or run `docker compose logs backend` and look for the one-time generated admin password (printed once on first seed).

**Optional:** Edit `backend/.env.docker` → `GROQ_API_KEY` for AI-powered incident explanations.

---

## Quick Start — Manual

Three terminals:

```bash
# Terminal 1: Backend
cd backend && cp .env.example .env && pip install -r requirements.txt && python run.py

# Terminal 2: Frontend
cd frontend && npm install && npm start

# Terminal 3: Vulnerable target (optional)
cd vuln-web && pip install -r requirements.txt && python app.py
```

**Reset demo data:** `python scripts/reset_incidentra.py --clear-logs` (from repo root, backend venv active).

---

## Deployment

### Frontend → Vercel (Free)

1. Import repo on [Vercel](https://vercel.com) → set root directory to `frontend`
2. Set environment variable: `REACT_APP_API_URL=https://<your-render-backend>.onrender.com/api`
3. Deploy — Vercel auto-detects React and handles routing via `vercel.json`

### Backend → Render.com (Free Tier)

1. Connect repo on [Render](https://render.com) → New Blueprint Instance
2. Render auto-detects `render.yaml` and provisions:
   - **incidentra-core** — Docker web service (backend + vuln-web + Celery + log monitor)
   - **incidentra-db** — PostgreSQL database
   - **incidentra-redis** — Redis cache
3. Set additional environment variables:
   - `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`
   - `DEMO_ADMIN_PASSWORD=<your-password>` (or leave blank for auto-generated)
   - `GROQ_API_KEY=<key>` (optional, for AI explanations)
4. Deploy

> **Note:** Render free tier spins down after 15 minutes of inactivity. First request after idle has a ~30–60s cold start. Sufficient for portfolio demos.

### Docker Compose (Self-hosted)

For full local or VPS deployment with all 6 services:

```bash
docker compose up --build -d
```

---

## Project Structure

```
backend/     Flask API, detection engine, log monitor, Celery tasks
frontend/    React + Material UI SOC dashboard
vuln-web/    Intentionally vulnerable target app + access.log
scripts/     Database reset and seed utilities
render/      Render.com deployment config (Dockerfile, entrypoint, WSGI)
```

---

## Tech Stack

| Layer     | Technology                                          |
|-----------|-----------------------------------------------------|
| Frontend  | React 18, Material UI 5, Chart.js, React Router 6   |
| Backend   | Flask 3, SQLAlchemy 2, Flask-Migrate, Gunicorn       |
| Database  | PostgreSQL 15, Redis 7                               |
| Workers   | Celery 5 (worker + beat scheduler)                   |
| Auth      | JWT (PyJWT)                                          |
| Container | Docker Compose, multi-stage builds                   |
| AI        | Groq API (optional)                                  |
| Alerts    | SMTP email, Telegram bot                             |

---

## Environment Variables

See [`backend/.env.example`](backend/.env.example) for the full list. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing key |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) |
| `GROQ_API_KEY` | Groq AI API key for incident explanations |
| `ABUSEIPDB_API_KEY` | AbuseIPDB API key for IP reputation |
| `DEMO_ADMIN_PASSWORD` | Admin password (auto-generated if blank) |

---

## Screenshots

> Screenshots coming soon — run locally with Docker to preview the full dashboard.

---

## License

MIT

---

## Author

**Hardin Irfan** — [GitHub](https://github.com/HardInCode)
