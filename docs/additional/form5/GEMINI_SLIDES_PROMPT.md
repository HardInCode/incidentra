# Gemini Prompt — Form 5 Video Slides (Docker live + Manual on PPT)

**Strategy:** Video records **Docker mode live**. **Manual mode** appears **only on slides** + narration (requirements.txt, pip, 3 terminals) — tidak di-run di terminal.

Copy block below → paste ke Gemini:

```
Buat 6 slide (16:9, dark cybersecurity theme, font besar 24pt+) untuk screen recording Form 5. BUKAN presentasi sidang — kartu referensi singkat.

Proyek: Incidentra SOC — Intelligent Web-SOC Platform with Automated Incident Response
President University Capstone 2026
Tim: Hardin Irfan, Zaidan Mahfudz Azzam Saidi

Aturan:
- Slide manual = ditampilkan sambil narasi, TIDAK di-run di video
- Slide Docker = bisa flash 5 detik sebelum presenter ketik di terminal
- Part 3 (Use) = live demo di browser, slide 6 cuma cheat sheet 5 detik

---

SLIDE 1 — Title
Incidentra SOC — Form 5 Video Demonstration
Part 1: Build · Part 2: Install · Part 3: Use (live demo)
Primary: Docker mode | Alternative: Manual mode (slides 3–4)

---

SLIDE 2 — Docker vs Manual (PERBANDINGAN — penting)
Buat tabel 2 kolom jelas:

| | Docker Mode (demo live) | Manual Mode (alternative) |
| Prerequisites | Docker Desktop + Git | Python 3.10–3.13, Node 18–20, PostgreSQL 15, Redis 7, Git |
| Dependencies | Built inside container (`docker compose build`) | pip install -r requirements.txt + npm install |
| Env config | .env.docker (from .env.docker.example) | .env (from .env.example) per folder |
| Install / Run | docker compose up --build -d | 3 terminals: run.py · npm start · app.py |
| Best for | Quick demo, capstone, consistent environment | Local development without Docker |
| URLs (same) | :3000 SOC · :5050 vuln-web · :5000 API | Same ports |

Footer note: "Video demos Docker live; manual steps shown for completeness."

---

SLIDE 3 — Part 1 BUILD: Manual Mode (Alternative — PPT only, do not run on video)
Judul: How to Build — Manual Mode (Alternative)

backend/requirements.txt  →  pip install -r requirements.txt
vuln-web/requirements.txt →  pip install -r requirements.txt
frontend/package.json       →  npm install
copy .env.example → .env (backend + vuln-web)

Key backend/.env:
USE_SIMULATED_LOGS=false
WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log
BLOCKED_IPS_JSON_PATH=../vuln-web/logs/blocked_ips.json

---

SLIDE 4 — Part 2 INSTALL: Manual Mode (Alternative — PPT only)
Judul: How to Install — Manual Mode (Alternative)

Requires PostgreSQL + Redis running first.

T1  backend/   →  python run.py      →  :5000
T2  frontend/  →  npm start          →  :3000
T3  vuln-web/  →  python app.py      →  :5050

Same result as Docker — different startup process.

---

SLIDE 5 — Part 1–2 BUILD & INSTALL: Docker Mode (demo live on video)
Judul: How to Build & Install — Docker Mode (Primary)

git clone https://github.com/HardInCode/incidentra.git
cd incidentra
copy backend\.env.docker.example backend\.env.docker
docker compose up --build -d
docker ps

6 containers: postgres · redis · backend · celery_worker · frontend · vuln_web

Verify: http://localhost:3000 · http://localhost:5050

---

SLIDE 6 — Part 3 USE: Quick reference (5 sec then LIVE DEMO)
Judul: How to Use — User Manual (live screen)

Login: admin / Admin@Incidentra2026!
1. Dashboard → Incidents
2. Settings → Escalating Block Policy
3. SQLi demo: vuln-web/login → Incidents → IP Management
4. Optional: AI Explanation · Whitelist · Rules · Export CSV

---

Output: full text per slide + 1 speaker note (English) per slide.
Design: minimal, high contrast, monospace for commands.
```

---

## Urutan saat rekam

```
Slide 1 Title (5s)
Slide 2 Docker vs Manual — narasi bedanya (15s)
Slide 3 Manual BUILD — narasi requirements.txt (20s) ← tidak ketik pip
Slide 4 Manual INSTALL — narasi 3 terminal (15s) ← tidak buka 3 terminal
[LIVE] git clone, .env.docker, peek VS Code requirements.txt (10s)
[LIVE] docker compose up, docker ps
[LIVE] browser :3000 & :5050
Slide 6 Use cheat (5s) → [LIVE] demo SOC 6–8 min
```

Narasi lengkap: [VIDEO_RECORDING_GUIDE.md](VIDEO_RECORDING_GUIDE.md)
