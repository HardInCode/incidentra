# Video Recording Guide — Form 5 Section C

One video, three parts: **Build · Install · Use**.

**Target:** 12–15 minutes · OBS 1080p · English voiceover · Upload Google Drive → paste URL in [Form5-Conclusion.md](Form5-Conclusion.md)

---

## Recording strategy (read this first)

| | **Docker mode** (primary) | **Manual mode** (alternative) |
|---|---------------------------|-------------------------------|
| **On video** | **Run live** — terminal, VS Code, browser | **PPT slide only** + short narration |
| **Why** | One command, fast demo, no 3-terminal mess | Still satisfies Form 5 "build" requirement (`requirements.txt`, `pip`, `npm`) without recording long installs |

You do **not** run `pip install` or three terminals on camera. Show those steps on a **slide**, explain verbally, then continue with Docker live.

Slides: generate via [GEMINI_SLIDES_PROMPT.md](GEMINI_SLIDES_PROMPT.md) (5–6 cards).

---

## Sir Williem's definitions → Incidentra (read first)

Template order: **Build → Install → Use**. Sir Williem's WhatsApp explanation maps like this:

| Sir Williem says | His example | Incidentra (Docker — what you demo live) |
|------------------|-------------|------------------------------------------|
| **Build** = setup from scratch, install tools + dependencies | `apt install nodejs` → open folder → **`npm install`** | Install **Docker Desktop + Git** → clone repo → copy **`.env.docker`** → show **`requirements.txt`** / **`docker-compose.yml`** (dependencies go inside `docker compose build`) |
| **Install** = run the ready app (like Play Store → open app) | Put source in folder → **`php artisan serve`** | **`docker compose up --build -d`** → **`docker ps`** → open **localhost:3000** |
| **Use** = **User Manual** — login, then click menu | Enter email/password → dashboard → click this, click that | Login SOC → sidebar (**Incidents**, **IP Management**, **Settings**, etc.) — **no attack required** |

**Build ≠ Install:** Build prepares the environment and dependencies. Install **starts** the running application.

**Manual mode** (pip, npm, 3 terminals): show on **PPT + narration only** — satisfies "build" without re-recording.

---

## Before recording

1. `docker compose up --build -d` **before** recording (show `docker ps`, not a 5-min build wait).
2. PPT open on second monitor or alt-tab ready (Docker vs Manual, Manual Build, Manual Install).
3. Optional reset:

```powershell
docker compose exec backend python /app/scripts/reset_incidentra.py --clear-logs
docker compose restart backend vuln_web
```

4. Notifications off · browser zoom 110–125% · terminal font 14+.

---

## Opening (~20 sec)

**Show:** Slide 1 (title) → Slide 2 (Docker vs Manual)

**Narration:**

> "Hello, I'm [name] from the Incidentra team. This Form 5 video has three parts: **build**, **install**, and **use**. We demo **Docker mode** live. **Manual mode** is documented on screen as an alternative for developers who prefer local Python and Node without containers."

---

## PART 1 — How to Build (~3 min)

**Live = Docker only. Manual = PPT + narration.**

### 1.1 Docker vs Manual — PPT (Slide 2)

**Show:** comparison slide (~15 sec). **Do not run manual commands.**

**Narration:**

> "Incidentra supports two modes. **Docker** needs only Docker Desktop and Git — dependencies install inside the container build. **Manual** needs Python, Node, PostgreSQL, and Redis locally, plus `pip install -r requirements.txt` and `npm install`. Same application, different packaging."

### 1.2 Manual build — PPT only (Slide 3)

**Show:** slide with `requirements.txt`, `pip`, `npm`, `.env` commands. **Stay on slide ~20 sec, narrate, do not type in terminal.**

**Narration:**

> "For **manual build**, developers create virtual environments, run **pip install -r requirements.txt** on backend and vuln-web, **npm install** on frontend, and copy **.env.example** to **.env**. Key paths point the backend log monitor at vuln-web's access log. Full steps are in GUIDE.md — we show this on slide because it satisfies the build requirement without repeating a long install on video."

### 1.3 Docker build — LIVE

**Show:** Docker Desktop (Running) → Terminal:

```powershell
git clone https://github.com/HardInCode/incidentra.git
cd incidentra
copy backend\.env.docker.example backend\.env.docker
```

**Show in VS Code (brief peek, ~10 sec):**

| File | Say out loud |
|------|----------------|
| `backend/requirements.txt` | "Manual mode installs these via pip — we use Docker instead." |
| `docker-compose.yml` | "Six services: postgres, redis, backend, celery, frontend, vuln-web." |

**Narration:**

> "For **Docker build**, clone the repo and copy **.env.docker**. Dependencies install during **docker compose build** — no local pip or npm needed. Database URLs are in **docker-compose.yml**."

**Close Part 1:**

> "Build complete — Docker configured. Manual alternative was shown on slide. Next: install and run."

---

## PART 2 — How to Install (~2 min)

### 2.1 Manual install — PPT only (Slide 4)

**Show:** 3-terminal slide (~15 sec). **Do not open three terminals.**

**Narration:**

> "**Manual install** runs three terminals: backend **python run.py** on port 5000, frontend **npm start** on 3000, vuln-web **python app.py** on 5050 — after PostgreSQL and Redis are running. Same URLs as Docker."

### 2.2 Docker install — LIVE

**Show:** Terminal (optional flash Slide 5 with commands, then run live):

```powershell
docker compose up --build -d
docker ps
```

**Narration:**

> "We install with **Docker** — one command starts all six containers. Entrypoint seeds the database and detection rules automatically."

Optional:

```powershell
docker compose logs backend --tail 15
```

### 2.3 Verify — LIVE (browser)

| URL | Expected |
|-----|----------|
| `http://localhost:3000` | SOC login |
| `http://localhost:5050` | vuln-web |

**Narration:**

> "Both URLs load — installation successful."

**Close Part 2:**

> "System is running. Part three is the user manual — live SOC demo."

---

## PART 3 — How to Use (~5–8 min)

**100% live screen. No PPT.**

This part functions as the **User Manual walkthrough** ("klik ini klik itu"). For each step, you will show the page on screen, explain what the menu does (its purpose), and narrate your actions clearly.

### 3.1 Login Page
* **How to Demo:** Load `http://localhost:3000` in the browser. Type the administrative credentials: username `admin` and password `Admin@Incidentra2026!`.
* **Menu Function:** Provides secure, credential-based authentication to control administrative access to the security dashboard. Only authorized users can configure policies, view logs, or clear blocks.
* **Narration (Say):**
  > "We begin the user manual walkthrough on the Incidentra login page. This screen enforces role-based access control, ensuring only authorized security administrators can view sensitive incident logs or adjust mitigation settings. I will enter our admin credentials and log into the system."

### 3.2 Dashboard
* **How to Demo:** Click log in and show the main dashboard. Hover the cursor over the four KPI cards at the top, then scroll down to show each of the visualization charts.
* **Menu Function:** Acts as the central security observability pane. Displays real-time aggregations of incident metrics (Total Incidents, Last 24h, Blocked IPs, MTTR) and trends (Timeline, Severity Breakdown, Severity Trend, Attack Types, Top Attacking IPs) to give security analysts immediate situational awareness.
* **Narration (Say):**
  > "Once logged in, we land on the main Dashboard. At the top, we see real-time KPI metrics, including total incident counts, active blocks, and our Mean Time to Resolution, or MTTR.
  > Scrolling down, we have interactive charts displaying the attack timeline, severity distributions, trend lines over time, attack types, and the top attacking IP addresses. This provides SOC analysts with immediate situational awareness of current threat profiles."

### 3.3 Incidents List (Ongoing vs. All)
* **How to Demo:** Click **Incidents** in the sidebar. Show the list, toggle between the **Ongoing** tab and the **All** tab, and show how the filters or search bar work.
* **Menu Function:** The core log triage interface. The "Ongoing" tab filters active threats requiring mitigation or review, whereas the "All" tab stores a search-friendly historical database of every threat captured.
* **Narration (Say):**
  > "Now, we navigate to the 'Incidents' menu in the sidebar. This is our central triage hub. The screen separates incidents into 'Ongoing' for active threats and 'All' for a complete historical record. From here, analysts can filter by severity, search for specific attacking IPs, and review alerts."

### 3.4 Incident Details & AI Explanation
* **How to Demo:** Click on one incident to load its detail view. Show the HTTP headers and raw log details. Click the **Explain with AI** button, wait for the Groq markdown response, then click the attacker's IP to show the **IP History Drawer**.
* **Menu Function:** Delivers deep forensic evidence for individual incidents, mapping the exact raw log entry and headers. Integrates with the **Groq API** to explain payloads (like SQLi or XSS) in plain terms, while the history drawer aggregates past malicious behaviors from that IP.
* **Narration (Say):**
  > "Clicking on an incident takes us to the 'Incident Details' page. This view shows raw HTTP headers and log payloads. Clicking 'Explain with AI' triggers a Groq AI analysis that translates complex attack payloads into easy-to-understand explanations and recovery steps.
  > Furthermore, clicking on the IP address slides out the IP History Drawer, showing us all past malicious actions associated with this address."

### 3.5 IP Management (Blocked, Rate Limited, Whitelisted)
* **How to Demo:** Click **IP Management** in the sidebar. Show the three tabs: **Blocked IPs**, **Rate Limited IPs**, and **Whitelisted IPs**. Click the **Block IP** button to show the manual configuration modal.
* **Menu Function:** The active firewall controls. Enforces IP blocks triggered by the escalating block policy, lists throttled users in the rate limit tab, and houses whitelisted IPs which are exempt from any auto-blocking rules.
* **Narration (Say):**
  > "Next is the 'IP Management' page, the primary firewall command center. It is split into three lists: 'Blocked IPs' managed by our automatic blocker, 'Rate Limited IPs' which restricts suspicious traffic rates, and 'Whitelisted IPs' which are immune to automated blocking.
  > Administrators can manually add IP blocks or lift bans with a single click."

### 3.6 Detection Rules
* **How to Demo:** Click **Detection Rules** in the sidebar. Show the list of rules (SQL Injection, XSS, etc.) and toggle one rule's switch to show how it is enabled or disabled.
* **Menu Function:** Manages the active detection signatures. Allows real-time adjustments to regex match patterns, risk severity mapping, and automated actions (log/rate-limit/block) without restarting the parsing monitor.
* **Narration (Say):**
  > "Under 'Detection Rules', we manage the regex patterns that detect attacks like SQL Injection or Cross-Site Scripting. We can review matched signatures, assign severity responses, and toggle detection rules on or off dynamically without restarting the server."

### 3.7 Live Traffic
* **How to Demo:** Click **Live Traffic** in the sidebar. Show the real-time requests scrolling on the screen.
* **Menu Function:** A live stream websocket viewer showing raw incoming web server requests as they are processed, helping analysts verify parser ingestion status and debug real-time traffic.
* **Narration (Say):**
  > "The 'Live Traffic' view uses WebSockets to stream incoming Nginx access logs in real-time. This helps us confirm that the log parser is actively reading server logs and shows us immediately when a request is evaluated."

### 3.8 Audit Log
* **How to Demo:** Click **Audit Log** in the sidebar. Scroll through the rows and filter by user or action.
* **Menu Function:** An immutable administrative log. Records all administrative actions—such as manual unblocking, modifying whitelists, or editing rules—for compliance and auditability.
* **Narration (Say):**
  > "The 'Audit Log' page maintains a strict audit trail of administrative actions. Any rule change, manual IP unblocking, or setting updates is recorded here with timestamps and admin user IDs to ensure security compliance and internal accountability."

### 3.9 Settings & Escalating Block Policy
* **How to Demo:** Click **Settings** in the sidebar. Scroll down to the **Escalating Block Policy** section and explain the escalation tiers for High and Critical severities.
* **Menu Function:** System configuration panel. Defines the escalation staircase durations, repeat offender thresholds, Groq AI API keys, and Telegram integration parameters.
* **Narration (Say):**
  > "In the 'Settings' page, we configure our automated response thresholds. The 'Escalating Block Policy' section defines how long IPs are blocked based on severity. Repeat offenders escalate through longer block durations—such as escalating from 1 hour, to 24 hours, and then 7 days.
  > We also manage our Telegram alert integration and Groq AI API keys here."

### 3.10 AI Security Chatbot Widget
* **How to Demo:** Click the floating chatbot button in the bottom-right corner. When the drawer opens, click a **Quick Prompt** or type a query: *"How does the escalating block policy protect against brute force?"*, send it, and wait for the AI's reply.
* **Menu Function:** A global interactive Groq-powered AI Security Assistant. Let analysts ask cybersecurity questions, get regex advice, or query Incidentra configurations on the fly. If opened from an Incident page, it inherits context automatically.
* **Narration (Say):**
  > "Lastly, we feature the floating 'AI Security Assistant' chatbot widget at the bottom right. Powered by the Groq API, this assistant is available on all pages to answer general security questions, write regex, or guide analysts through incident responses.
  > If opened while inspecting an incident, it automatically receives the threat context to provide tailored advice."

---

### Optional — Attack & Automated Response Demo (NOT required for Form 5)

Only include if already recorded or if you want to showcase automated blocking.

1. Open `http://localhost:5050/login` in another browser window/tab.
2. Submit a malicious SQL injection payload (e.g. `' OR '1'='1`).
3. Return to the dashboard at `http://localhost:3000` to show the new **Incident** popup and the IP listed under **Blocked IPs**.
4. Refresh the vuln-web page at `http://localhost:5050` to show it now returns a **403 Forbidden** page.

---

### Closing (voice only)

> "Part three complete — user manual walkthrough of the SOC dashboard. Form 5 video finished. Thank you."

---

## What goes where (cheat sheet)

| Content | PPT slide | Live screen |
|---------|-----------|-------------|
| Docker vs Manual comparison | ✅ Slide 2 | — |
| Manual: requirements.txt, pip, npm, .env | ✅ Slide 3 | — |
| Manual: 3 terminals | ✅ Slide 4 | — |
| Docker: clone, .env.docker | optional Slide 5 | ✅ Terminal |
| Docker: docker compose up | optional Slide 5 | ✅ Terminal |
| Peek requirements.txt in VS Code | — | ✅ 10 sec + narrate |
| Verify :3000 / :5050 | — | ✅ Browser |
| Login, Dashboard, KPI cards | — | ✅ Browser |
| Incidents List, Filters, Tabs | — | ✅ Browser |
| Incident Details, AI Explanation, IP Drawer | — | ✅ Browser |
| IP Management, Block/Whitelist tabs | — | ✅ Browser |
| Detection Rules page & toggle control | — | ✅ Browser |
| Live Traffic websocket stream | — | ✅ Browser |
| Audit Log administrative table | — | ✅ Browser |
| Settings page & Escalating block config | — | ✅ Browser |
| AI Chatbot widget & sample query | — | ✅ Browser |
| Attack demo (optional) | — | optional |

---

## After recording checklist

- [ ] Part 1–3 labeled (title slide or verbal transitions)
- [ ] Manual mode shown on **PPT** (requirements.txt + 3 terminals mentioned)
- [ ] Docker **run live** for install
- [ ] Part 3 is live demo, not slides
- [ ] MP4 1080p · clear audio · Google Drive link in Form 5

---

*Incidentra — Video Recording Guide | Form 5 Section C | June 2026*
