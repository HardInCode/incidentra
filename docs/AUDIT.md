# Full Audit — Incidentra (July 2026)

**Version:** Full capstone audit · **July 2026**  
**Product:** Intelligent Web-SOC Platform with Automated Incident Response  
**Scope:** Local demo (manual 3-terminal **or** Docker Compose). VPS deployment is **not** required.

**How to use:** Run section **P** then **A** or **D**, attacks **B**/**E**, optional **C** (Burp), features **F**–**J**, revisions **G**. Check **Pass** if *expected result* is met.

| Field | Value |
|-------|-------|
| **Tester** | _______________ |
| **Test date** | _______________ |
| **Environment** | ☐ Manual  ☐ Docker Desktop |
| **OS** | Windows / Linux / macOS ___ |
| **Commit / tag** | _______________ |

**Guide:** [GUIDE.md](GUIDE.md) · **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) · **Form 4:** [additional/form4/FORM4_IMPLEMENTATION_v2.md](additional/form4/FORM4_IMPLEMENTATION_v2.md)

---

## Table of Contents

| Section | Contents |
|---------|----------|
| [Concepts](#audit-concepts) | Live Traffic vs incidents vs blocking; baseline vs AI vs lab mode |
| [P](#p--general-preparation) | General preparation |
| [A](#a--manual-setup) | Manual setup |
| [B](#b--manual-attacks) | Manual attacks (8 types + unblock + AI) |
| [C](#c--burp-suite) | Burp Suite (optional for defense) |
| [D](#d--docker-setup) | Docker setup |
| [E](#e--docker-attacks) | Docker attacks (repeat B) |
| [F](#f--soc-features) | SOC features (dashboard, traffic, rules, IP, export, …) |
| [G](#g--shop-upload-phase-3) | Shop, upload, absolute path, Phase 3 |
| [H](#h--settings--integrations) | Settings, thresholds, Groq, notifications |
| [I](#i--lab-mode--custom-rules) | Lab mode & custom rules (defense demo) |
| [J](#j--uiux--july-2026) | UI/UX July 2026 (chatbot, toast, rules dialog) |
| [Summary](#scoring-summary) | Pass / fail decision |

---

## Audit Concepts

### Three Layers (must understand)

| Layer | UI | Meaning |
|-------|-----|---------|
| **1. Log** | Live Traffic | Every HTTP → `access.log` |
| **2. Tag** | Live Traffic TAG | Quick heuristic (`traffic.py`) — **not** a SOC decision |
| **3. Incident + block** | Incidents + IP Management | `DetectionEngine` → PostgreSQL → `blocked_ips.json` → vuln-web **403** |

**Attack passes** = correct type & severity in **Incidents** **and** (except rate limit) **403** on the next request from the same IP. **Attack 200** alone = **not sufficient**.

**Blocked IP** = the IP shown in the Live Traffic column (`172.x`, `192.168.x`, etc.). **Unblock** that IP before the next test.

### Three Detection Sources (defense presentation)

| Source | File / UI | When active |
|--------|-----------|-------------|
| **UI Rule** | Detection Rules → PostgreSQL | Rule `is_active=true` |
| **OWASP Baseline** | `detection_engine.py` → `DETECTION_PATTERNS` | Default (Lab mode **OFF**) |
| **AI analyst** | `ai_service.py` (Groq) | Explanation only — **does not** block |

**Lab mode ON** (Settings): only UI rules; baseline off. See [I](#i--lab-mode--custom-rules).

### Severity → Response

| Severity | Response | vuln-web |
|----------|----------|----------|
| low | Log & monitor | 200 |
| medium | Rate limit | **429** if quota exceeded |
| high | Escalating block (default: 1h → 24h → 7d) | **403** |
| critical | Escalating block (default: 24h → 7d → 30d) | **403** |

| Attack type | Default severity | Auto response |
|-------------|------------------|---------------|
| SQL_INJECTION | critical | Escalating (offense #1 ≈ 24 hours) |
| XSS | critical | Escalating |
| COMMAND_INJECTION | critical | Escalating |
| LFI_RFI | critical | Escalating |
| BRUTE_FORCE | high | Escalating |
| PATH_TRAVERSAL | high | Escalating |
| FILE_UPLOAD | high | Escalating |
| SCANNER | medium | Rate limit |

Permanent block **only** via manual action in IP Management. Offense ≥ threshold → badge **Repeat Offender**.

---

## P — General Preparation

| # | Step | Expected result | Pass | Notes |
|---|------|-----------------|------|-------|
| P1 | Redis: `redis-cli ping` **or** `docker compose ps` | `PONG` / 6 services **Up** | | |
| P2 | Reset demo: `python scripts/reset_incidentra.py --clear-logs` (+ unblock all IPs) | Incidents empty; `blocked_ips.json` empty | | Docker: see [GUIDE.md](GUIDE.md) reset |
| P3 | Login SOC `admin` / `Admin@Incidentra2026!` | Dashboard, full sidebar | | |
| P4 | Backend: log `Tailing real log` (not simulated) | Monitor active | | `USE_SIMULATED_LOGS=false` |
| P5 | Search `SIDANG Ctrl+F` in `detection_engine.py`, `traffic.py` | Code map for defense available | | Optional — see [ARCHITECTURE.md](ARCHITECTURE.md) |
| P6 | Burp (if using C): proxy `127.0.0.1:8080`, normal browser UA | No automatic SCANNER | | |

---

## A — Manual SETUP

Prerequisite: [GUIDE.md](GUIDE.md) manual section.

| # | Step | Expected result | Pass | Notes |
|---|------|-----------------|------|-------|
| A1 | `backend`: `.env`, `pip install`, `python run.py` | Seed admin/rules; `Running on :5000` | | |
| A2 | `frontend`: `npm install`, `npm start` | `:3000` login OK | | |
| A3 | `vuln-web`: `python app.py` | Shop Home/Catalog/Cart; CSS loaded | | |
| A4 | Backend `WEB_SERVER_LOG_PATH` → `vuln-web/logs/access.log` | `Tailing real log: ...` | | Restart after changing .env |
| A5 | `http://localhost:5050/search?q=test` | Live Traffic new row; no critical incident | | |
| A6 | API without JWT → `/api/incidents` | `401 Authorization required` | | |
| A7 | Analyst login (if analyst user exists) | Limited access vs admin | | Optional |

---

## B — Manual ATTACKS

**Before testing escalation:** unblock IP in **IP Management → Blocked** (escalation counter remains in Redis after unblock).

| # | Attack | Steps | Expected (≤10 s in Incidents) | Pass | Notes |
|---|--------|-------|-------------------------------|------|-------|
| B1 | SQL Injection | POST `/login` user `admin' OR '1'='1' --` | **SQL_INJECTION** critical → **403** on refresh `/` | | |
| B2 | XSS | `/search?q=<script>alert(1)</script>` | **XSS** critical → **403** | | |
| B3 | Path traversal | `/files?file=../../etc/passwd` | **PATH_TRAVERSAL** high, temp block | | May get LFI first — see C7 |
| B4 | Command injection | `/cmd?cmd=;whoami` or `cmd=whoami` | **COMMAND_INJECTION** critical → **403** | | |
| B5 | Scanner | `curl -A "Nikto/2.1.6" http://localhost:5050/` | **SCANNER** medium; **Rate Limited** tab | | Not permanent block |
| B6 | Brute force | 12× POST `/login` wrong password < 60 s | **BRUTE_FORCE** high | | Default threshold 10 |
| B7 | Unblock UI | IP Management → Unblock | `localhost:5050` **200** shop | | |
| B8 | Simulate Mode B | Incidents → Simulate → LFI_RFI / FILE_UPLOAD | Toast OK; incident ~5 s | | Without vuln-web |
| B9 | Resolve workflow | Mark **resolved** | Gone from ongoing; visible in `/incidents/all` | | |
| B10 | AI explanation | Incident detail → Generate | AI panel; `model_used` badge | | Groq or `fallback-static` |
| B11 | Live Traffic proof | After B4: lines **Attack 200** then **Blocked 403** | Two phases visible | | See GUIDE |
| B12 | 429 rate limit | After B5: refresh vuln-web 10+×/min | Yellow **429** page | | Strong optional |

---

## C — Burp Suite

Target: `http://localhost:5050` · Normal browser UA for non-scanner tests.

### C0 — Setup

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C0.1 | Proxy ON, traffic to vuln-web | History populated | | |
| C0.2 | UA is not default Burp scanner | No auto SCANNER on SQLi/XSS | | |

### C1 — Brute Force (Intruder)

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C1.1 | POST login 1× wrong | History entry | | |
| C1.2 | Intruder password, 15 payloads | ≥10 hits < 60 s | | |
| C1.3 | SOC Incidents | **BRUTE_FORCE** high | | |
| C1.4 | Subsequent request | May return **403** | | |

### C2 — SQLi (Repeater)

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C2.1 | POST body `username=admin' OR '1'='1' --&password=x` | Login reflected | | |
| C2.2 | SOC | **SQL_INJECTION** critical | | |
| C2.3 | GET `/` | **403** Incidentra | | |

### C3 — XSS

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C3.1 | Unblock IP | OK | | |
| C3.2 | `GET /search?q=<script>alert(1)</script>` | Reflected | | |
| C3.3 | SOC | **XSS** critical | | |

### C4 — Path Traversal

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C4.1 | `GET /files?file=../../etc/passwd` | Files page | | |
| C4.2 | SOC | **PATH_TRAVERSAL** high | | |

### C5 — Command Injection

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C5.1 | `GET /cmd?cmd=;whoami` | Output on page | | |
| C5.2 | SOC | **COMMAND_INJECTION** → **403** | | |

### C6 — Scanner & 429

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C6.1 | UA `Nikto/2.1.6` | 200 initially | | |
| C6.2 | SOC | **SCANNER** medium, Rate Limited tab | | |
| C6.3 | Many rapid requests | **429** | | |

### C7 — LFI/RFI

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C7.1 | `GET /files?file=php://filter/convert.base64-encode/resource=index` | Logged | | |
| C7.2 | SOC | **LFI_RFI** critical | | |

### C8 — Evidence

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| C8.1 | Screenshot Incidents + IP Mgmt + Live Traffic | Defense archive | | |
| C8.2 | Export Burp item / Repeater | Request evidence | | |

---

## D — Docker SETUP

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| D1 | Ports 3000/5000/5050/5432 free | No conflict | | |
| D2 | Docker Desktop running | Engine OK | | |
| D3 | `docker compose up --build -d` | 6 services up | | |
| D4 | `docker compose ps` | All **running** | | |
| D5 | `docker compose logs backend` | DB ready, log monitor, gunicorn | | |
| D6 | `http://localhost:3000` login | OK | | |
| D7 | `http://localhost:5050` | Shop 200 | | |
| D8 | `GET /api/dashboard/stats` + Bearer | JSON (not 502) | | |
| D9 | After code change: `docker compose up --build -d` | Latest image | | July 2026 features |

---

## E — Docker ATTACKS

Repeat subset of **B** — expected results are **identical**.

| # | Test | Ref B | Pass | Notes |
|---|------|-------|------|-------|
| E1 | SQLi login | B1 | | |
| E2 | XSS | B2 | | |
| E3 | Brute force | B6 | | |
| E4 | Scanner + 429 | B5, B12 | | |
| E5 | Command injection | B4 | | |
| E6 | Backend logs `[THREAT]` | — | | |
| E7 | Blocked UI = vuln-web 403 | B7 | | |
| E8 | Volume `vuln_logs` synced | — | | `blocked_ips.json` shared |

---

## F — SOC Features

| # | Feature | Steps | Expected | Pass | Notes |
|---|---------|-------|----------|------|-------|
| F1 | Dashboard | `/` | KPI, timeline, severity chart | | |
| F2 | Chart seed | `seed_chart_demo.py` + refresh | 7-day timeline | | |
| F3 | Live Traffic | `/traffic` | Auto-refresh; hide static | | |
| F4 | Detection Rules | `/rules` | CRUD; toggle active; sandbox Test | | |
| F4a | Info icon ⓘ | Hover next to Add Rule | Tooltip baseline / lab mode | | |
| F5 | Bulk resolve | Select incidents → resolved | Status + audit log | | |
| F6 | Export CSV | Incidents export | File downloads | | |
| F7 | Chatbot | Open chat, ask about regex/SQLi | Groq response | | Draggable — [J](#j--uiux--july-2026) |
| F7b | IP Management | Blocked + Rate Limited tabs | Unblock, extend, clear | | |
| F8 | i18n | Settings → EN / ID | Labels change | | |
| F9 | Theme | Dark / light | Theme changes | | |
| F10 | Session timeout | Idle for extended period | Warning logout | | If configured |
| F11 | IP History drawer | Click IP in incident | History + pattern | | |
| F12 | Assign analyst | Admin assign in detail | Saved | | |
| F13 | Investigation notes | Add note | Timestamp + user | | |
| F14 | Audit log | `/audit` (admin) | Login, rule, block recorded | | |
| F15 | Notification bell | Trigger new incident | Brief toast + badge count | | Not email |

---

## G — Shop, Upload, Phase 3

Unblock IP + optional reset before starting.

| # | Feature | Steps | Expected | Pass | Notes |
|---|---------|-------|----------|------|-------|
| G1 | Safe upload | POST `/files` `notes.txt` | Live Traffic normal; **no** FILE_UPLOAD incident | | |
| G2 | Dangerous upload | `shell.php` at `/files` or profile avatar | **FILE_UPLOAD** high | | |
| G3 | Absolute path | `?file=E:/.../blocked_ips.json` or Docker `/app/logs/...` | Read file + **PATH_TRAVERSAL** | | [ARCHITECTURE.md](ARCHITECTURE.md) § Security Lab |
| G4 | Safe file | `?file=readme.txt` | Content shown; no incident | | |
| G5 | Cart | Catalog → Add to cart | Cart page OK | | |
| G6 | Phase 3 CMD | `VULN_UNSAFE_CMD=1` + restart vuln-web | Red banner; real shell; CMD incident | | |
| G6b | Read secret file | `/cmd?cmd=cat lab_secrets/capstone_flag.txt` (CMD rule off, unblock) | Flag text in output; **does not** require `ping` | | Slim Docker: `ping` not found = normal |
| G7 | Phase 3 upload | `VULN_UNSAFE_UPLOAD=1` (optional) | Path escape upload | | Lab only |
| G8 | Seed rules | Restart backend / check `/rules` | FILE_UPLOAD + path rules exist | | |

---

## H — Settings & Integrations

| # | Feature | Steps | Expected | Pass | Notes |
|---|---------|-------|----------|------|-------|
| H1 | Save thresholds | Brute 10 → 15, Save, 15× failed login | BF at hit #15 (±60 s) | | |
| H2 | Temp block hours | Change hours, Save, trigger high attack | Expire matches setting | | |
| H3 | Groq API key | Enter key + model, Save | Configured badge | | |
| H4 | Test Groq | Test Connection | Success + **model name** in message | | Single selected model |
| H5 | AI explanation model | Generate on incident | Badge = model used | | Tooltip on chip |
| H6 | AbuseIPDB | Test API key | Score for 8.8.8.8 | | Optional |
| H7 | Email test | Send test email | Sent or clear error | | Optional |
| H8 | Telegram test | Send test message | OK | | Optional |
| H9 | Alert sound | Toggle + test sound | Sound plays (browser allow) | | Sidebar bell |
| H10 | Lab mode OFF default | Fresh install / reset settings | Detection Rules ⓘ = production text | | |

---

## I — Lab Mode & Custom Rules

Defense demo: **rule operator** vs **baseline**.

| # | Step | Expected | Pass | Notes |
|---|------|----------|------|-------|
| I1 | Settings → Lab mode **ON** → Save | Rules page ⓘ = lab warning | | |
| I2 | Disable **all** COMMAND_INJECTION rules | 0 active CMD rules | | |
| I3 | Unblock IP | vuln-web OK | | |
| I4 | `cmd=;whoami` | **No** incident (lab, no baseline) | | Controlled bypass proof |
| I5 | Create rule: SQLi `(?i)lorem\s+ipsum`, active | Rule in table | | |
| I6 | POST login `username=lorem ipsum` | **SQL_INJECTION**; `match_count++` | | |
| I7 | Lab mode **OFF** → Save | ⓘ = production; baseline active again | | |
| I8 | `cmd=;whoami` again | CMD incident despite CMD rule off | | OWASP baseline |
| I9 | Sandbox Test payload | Match per engine (lab on/off) | | `/api/detection/test` |

---

## J — UI/UX July 2026

| # | Feature | Steps | Expected | Pass | Notes |
|---|---------|-------|----------|------|-------|
| J1 | Create Rule dialog | Add Rule → form | Label **Rule Name** not truncated | | |
| J2 | Chatbot position | Default bottom-right | Does not cover Logout sidebar | | |
| J3 | Chatbot drag | Drag FAB to another corner | Position persists after refresh | | `localStorage` |
| J4 | Incident toast | New incident | Toast top-right ~2.5 s, max 3 | | |
| J5 | Rate limit chip | IP Management → Rate Limited | Tooltip if "JSON only" | | Enforcement still works |

---

## Scoring Summary

| Section | Items (≈) | Pass | Fail | N/A |
|---------|-----------|------|------|-----|
| P — Preparation | 6 | | | |
| A — Manual setup | 7 | | | |
| B — Manual attacks | 12 | | | |
| C — Burp | 20+ | | | |
| D — Docker setup | 9 | | | |
| E — Docker attacks | 8 | | | |
| F — SOC features | 15 | | | |
| G — Shop/lab revisions | 8 | | | |
| H — Settings | 10 | | | |
| I — Lab mode | 9 | | | |
| J — UI/UX | 5 | | | |

**Approximate total:** ~100 scenarios (check per tested row).

### Decision

- ☐ **PASS** — Manual **and** Docker; features F–J OK; ready for defense
- ☐ **CONDITIONAL PASS** — Notes: _______________
- ☐ **NOT YET PASSING** — Blocker: _______________

### Common Blockers

| Symptom | Solution |
|---------|----------|
| Incident not appearing | `USE_SIMULATED_LOGS=false`; correct log path; `docker compose restart backend` |
| Attack 200, no 403 | Check **Incidents**; unblock wrong IP; wait for tailer |
| Rule OFF still detects | Lab mode OFF → baseline active — explain in defense |
| Lab mode ON still detects | Another rule active or brute-force rule active |
| All requests SCANNER (Burp) | Use normal browser UA |
| 403 persists | IP Management unblock or `reset_incidentra.py --clear-logs` |
| Settings thresholds not working | **Save** Settings; wait ≤60 s or restart backend |
| AI model always the same | Normal if Groq primary succeeds; check tooltip `model_used` |
| Docker backend loop | `docker compose logs backend` — check `DATABASE_URL` |
| Frontend build fails | `docker compose build --no-cache frontend` |

### Appendix — Status July 2026

| Item | Status |
|------|--------|
| Core SOC + 8 attack types | Done |
| IP Management Blocked + Rate Limited | Done |
| Lab mode UI-only detection | Done |
| OWASP baseline + rule UI (production) | Done |
| AI Groq + static fallback | Done |
| vuln-web shop + Phase 3 | Done |
| Documentation Form 4 | Team |
| **Full audit July 2026** | This document |

**Deploy / Git:** [additional/DEPLOY.md](additional/DEPLOY.md) · [additional/GITHUB.md](additional/GITHUB.md)

---

*Full Audit — Incidentra, July 2026 · President University Capstone*
