# Form 5

## Conclusion

**Intelligent Web-SOC Platform with Automated Incident Response**

**Incidentra SOC**

---

**GROUP MEMBER:**

| No. | Student Name                     | Student ID    |
|-----|----------------------------------|---------------|
| 1.  | Hardin Irfan (Leader)            | 001202300066  |
| 2.  | Nasywa Kamila                    | 001202300211  |
| 3.  | Zaidan Mahfudz Azzam Saidi       | 001202300144  |

---

Submitted for

**Capstone Design Project**

to Faculty of Computer Science

President University

---

## TABLE OF CONTENT

- [Statement of Originality](#statement-of-originality)
- [Part 5 — Conclusion](#part-5--conclusion)
  - [A. Conclusion and Future Works](#a-conclusion-and-future-works)
  - [B. Client Feedback](#b-client-feedback)
  - [C. Video Demonstration](#c-video-demonstration)
- [Reference](#reference)

---

## STATEMENT OF ORIGINALITY

In my capacity as an active student at President University and as the author of the Capstone Design Project stated below:

**Name** :
1. Hardin Irfan — 001202300066
2. Nasywa Kamila — 001202300211
3. Zaidan Mahfudz Azzam Saidi — 001202300144

**Faculty** : Computer Science

I hereby declare that my Capstone Design Project entitled **"Intelligent Web-SOC Platform with Automated Incident Response"** is to the best of my knowledge and belief, an original piece of work based on sound academic principles. If there is any plagiarism detected in this final project, I am willing to be personally responsible for the consequences of these acts of plagiarism and will accept the sanctions against these acts in accordance with the rules and policies of President University.

I also declare that this work, either in whole or in part, has not been submitted to another university to obtain a degree.

Cikarang, June 2026

| Hardin Irfan — 001202300066 | Nasywa Kamila — 001202300211 | Zaidan Mahfudz Azzam Saidi — 001202300144 |
|-----------------------------|------------------------------|-------------------------------------------|
|                             |                              |                                           |

---

**Intelligent Web-SOC Platform with Automated Incident Response**

Approved:

| Mr. Abdul Ghofir S. Kom., M. Kom. — Capstone Advisor | {Your head of study program name} — Program Head of Informatics |
|-------------------------------------------------------|------------------------------------------------------------------|

**Prof. Dr. Ir. Wiranto Herry Utomo, M.Kom.**

Dean of Faculty of Computer Science

---

## PART 5 — CONCLUSION

**Consists of:**

- CONCLUSION AND FUTURE WORKS
- CLIENT FEEDBACK
- VIDEO DEMONSTRATION

---

### A. CONCLUSION AND FUTURE WORKS

#### Conclusion

1. **Automated threat detection and incident response is achievable with open-source tools.** Incidentra demonstrates that a fully functional Security Operations Center (SOC) platform can be built entirely from open-source components — Flask, React, PostgreSQL, Redis, and Docker — without requiring any commercial SIEM or WAF license. The system successfully detects eight categories of OWASP web attacks (SQL Injection, XSS, Brute Force, Path Traversal, File Upload, Command Injection, Scanner, and LFI/RFI) through a combination of regex pattern matching and threshold-based analysis, and automatically responds with severity-proportional actions ranging from logging and monitoring to escalating temporary IP blocking. Detection rules can be customized from the SOC Dashboard without restarting services.

2. **A log-based detection architecture provides effective security monitoring without modifying the monitored application.** By tailing the web server access log (NCSA Combined Log Format with a POST_DATA suffix), Incidentra operates as a passive observer that does not require any code changes, middleware injection, or agent installation on the monitored web application. Enforcement is achieved through shared JSON files on a Docker named volume, keeping the detection backend and the monitored application completely decoupled.

3. **AI-powered incident analysis enhances analyst productivity.** The integration with Groq Cloud API (LLaMA models) provides automated incident explanations covering threat summaries, danger assessments, recommended actions, and MITRE ATT&CK technique mappings. The four-model fallback chain with a static explanation safety net ensures that every incident always has a human-readable analysis, even when API connectivity fails. This reduces the cognitive load on SOC analysts during triage.

4. **A tiered automated response system with escalating block policy balances security with operational continuity.** During the client feedback phase, a concern was raised by a senior IT Application Support professional regarding the risk of permanent automated IP blocking in shared IP environments (NAT, corporate proxy, CGNAT), where multiple users may share the same public IP address. In response to this feedback, the automated response system was revised from a permanent auto-blocking approach to an escalating block policy. The severity-to-action mapping (Low → log & monitor, Medium → rate limit, High → escalating temporary block starting at 1 hour, Critical → escalating temporary block starting at 24 hours) ensures that low-severity threats are observed without disruption while critical attacks receive immediate but proportional enforcement. Repeated offenses from the same IP address receive progressively longer block durations (e.g., 1h → 24h → 168h for high severity; 24h → 168h → 720h for critical severity). IPs that exceed a configurable offense threshold are automatically flagged as Repeat Offenders, alerting the administrator to decide whether permanent blocking is warranted. All block durations and the Repeat Offender threshold are configurable via the Settings page. The administrator retains full override capability through the SOC Dashboard to unblock IPs, whitelist trusted sources, and modify block durations, providing a safety net against false positives.

5. **Containerized deployment reduces operational complexity.** The Docker Compose deployment provisions all six services (PostgreSQL, Redis, backend, frontend, vuln-web, Celery worker) with a single `docker compose up --build -d` command. No manual database setup, virtual environment configuration, or service registration is required, making the system immediately deployable on any machine with Docker installed.

#### Future Works

1. **Enhanced shared IP address awareness.** While the current escalating block policy already mitigates the risk of permanent blocking for shared IP addresses by using progressively longer temporary blocks instead of immediate permanent blocks, further improvements could include combining IP-based detection with session-level fingerprinting (cookie, User-Agent, request patterns) to distinguish between malicious and legitimate users on the same IP. Additionally, integration with known NAT/CGNAT IP range databases could enable the system to automatically apply more lenient block policies for IPs identified as shared.

2. **CIDR range and subnet-based blocking.** Extend the IP management module to support CIDR notation (e.g., `192.168.1.0/24`) for blocking or whitelisting entire subnets, reducing the manual effort of managing individual IP addresses from coordinated attack sources.

3. **Multi-user role-based access control (RBAC) enhancement.** Expand the current Admin/Analyst role system with more granular permissions, such as separating rule management, IP management, and settings access into distinct privilege levels. Add support for LDAP/Active Directory integration for enterprise environments.

4. **Real-time WebSocket-based event streaming.** Replace the current HTTP polling mechanism (3-second interval for Live Traffic, 15-second default interval for Dashboard KPI refresh) with WebSocket or Server-Sent Events (SSE) for truly real-time incident notifications and live traffic updates, reducing latency and server load.

5. **Enhanced reporting and compliance.** Add scheduled report generation (daily/weekly PDF/Excel summaries), compliance dashboards aligned with regulatory frameworks (ISO 27001, PCI DSS), and incident response timeline visualization for post-incident reviews.

6. **Machine learning-based anomaly detection.** Complement the current regex and threshold-based detection with statistical anomaly detection models that learn normal traffic patterns and identify deviations, reducing dependency on predefined patterns and improving zero-day attack detection capability.

7. **Multi-application monitoring.** Extend the log ingestion layer to support simultaneous monitoring of multiple web applications from different log sources, with per-application dashboards and rule sets.

8. **Web Application Firewall (WAF) integration.** Integrate with established WAF solutions such as ModSecurity or AWS WAF to combine Incidentra's log-based detection intelligence with real-time request filtering at the network edge. This would enable the system to push dynamically generated blocking rules to the WAF based on detected threats, providing defense-in-depth where the WAF handles immediate request-level enforcement while Incidentra continues to serve as the centralized SOC platform for monitoring, analysis, and incident management.

---

### B. CLIENT FEEDBACK

<!-- ================================================================
     GUIDE FOR SECTION B — CLIENT FEEDBACK
     ================================================================

     Questionnaire categories (as per lecturer guidelines):
     1. Easy of use
     2. Display and performance
     3. Feature and functionality
     4. Satisfaction level
     5. Respondent suggestions
     6. Conclusion

     STEPS:
     1. Create a Google Form with the questions below
     2. Distribute to client stakeholder(s) — follow lecturer minimum respondent count if required
     3. Collect responses and fill the table
     4. Attach blank questionnaire screenshot

     ================================================================ -->

To evaluate the effectiveness, usability, and features of the Incidentra SOC system, a feedback session was conducted with **three client representatives** from PT Accelist Lentera Indonesia (IT Manager, Apps Support, and IT Support). Each representative completed the same evaluation questionnaire after a live demonstration and hands-on testing. The table below presents an **aggregate summary**: numeric ratings are the **arithmetic mean** of all three responses; remarks **synthesize** recurring themes and notable comments from the combined feedback (not attributed individually unless essential for context).

#### Client Feedback Summary

| No. | Category | Question / Evaluation Criteria | Rating (1-5) / Response | Client's Remarks / Elaborations |
|-----|----------|-------------------------------|-------------------------|---------------------------------|
| 1   | Ease of Use | Is the SOC Dashboard easy to navigate and intuitive for daily security monitoring tasks? (1-5) | **4.7 / 5** *(mean, n=3)* | Respondents consistently rated navigation positively. The sidebar structure and incident workflow were considered intuitive for routine security monitoring after a brief walkthrough. |
| 2   | Ease of Use | Is the system easy to deploy and set up using Docker Compose? (1-5) | **4.0 / 5** *(mean, n=3)* | Docker Compose deployment was generally viewed as practical for demo and staging environments. Documentation clarity for first-time setup was noted as an area that could be improved. |
| 3   | Display and Performance | Is the dashboard layout (charts, tables, KPI cards) clear and visually informative? (1-5) | **4.0 / 5** *(mean, n=3)* | KPI cards, charts, and tables were uniformly rated as clear and informative across all three evaluations. |
| 4   | Display and Performance | Does the system respond quickly when detecting attacks and displaying incidents? (1-5) | **4.3 / 5** *(mean, n=3)* | Live testing showed incidents appearing on the dashboard within seconds of attack simulation. Response speed was rated positively overall. |
| 5   | Feature and Functionality | Does the system accurately detect web attacks (SQL Injection, XSS, Command Injection, etc.)? (1-5) | **4.7 / 5** *(mean, n=3)* | Demonstrated attack scenarios (e.g., SQL injection, XSS) were detected with appropriate severity labels during the evaluation session. |
| 6   | Feature and Functionality | Is the escalating block policy (progressively longer blocks instead of permanent auto-block) an appropriate automated response? (1-5) | **4.0 / 5** *(mean, n=3)* | The escalating temporary block policy was generally accepted. During discussion, **concern was raised collectively** that strict **IP-only blocking** may penalize legitimate users on shared public IPs (NAT/corporate proxy). Respondents suggested **session-based blocking** as a future improvement. The tiered policy (no automatic permanent block, admin unblock/whitelist) was considered a reasonable mitigation for a capstone prototype. |
| 7   | Feature and Functionality | Is the AI-powered incident explanation feature useful for understanding threats? (1-5) | **4.3 / 5** *(mean, n=3)* | AI-generated explanations were rated useful for understanding threat impact and recommended actions during incident triage. |
| 8   | Satisfaction Level | Overall, how satisfied are you with the Incidentra system? (1 = Very Poor, 5 = Excellent) | **4.7 / 5** *(mean, n=3)* | Overall satisfaction was high across all three respondents. The system was regarded as a capable capstone SOC prototype suitable for further evaluation. |
| 9   | Respondent Suggestions | What improvements would you suggest for the system? | [Open Response] | **Aggregated suggestions:** (1) integrate a **WAF** for real-time edge filtering as defense-in-depth; (2) evolve from IP-only toward **session-based blocking** to reduce shared-IP false positives; (3) improve **end-user and deployment documentation**. |
| 10  | Conclusion | Would you recommend this system for use in a real SOC environment (with further development)? Why or why not? | [Open Response] | **Aggregated conclusion:** All three respondents would **recommend** the system for further use in a controlled or staging environment, **pending refinement** (documentation, bug fixes, and production-hardening). Core detection and automated response—including the tiered blocking policy—were assessed as effective and promising for real SOC workflows with continued development. |

*Rating notation: **X.X / 5 (mean, n=3)** = average of three independent client questionnaire responses. Scores are rounded to one decimal place (e.g., a total sum of 14 divided by 3 is 4.66, rounding up to 4.7; a total sum of 13 divided by 3 is 4.33, rounding down to 4.3). Remarks = synthesized summary; full raw responses are attached.*

#### Questionnaire Form

[Attach evaluation questionnaire responses — e.g. **Incidentra Security System Evaluation (Jawaban).xlsx** or exported PDF showing all three completed entries.]

---

### C. VIDEO DEMONSTRATION

> Recording script and step-by-step narrative: see [VIDEO_RECORDING_GUIDE.md](VIDEO_RECORDING_GUIDE.md).

The video demonstration of the Incidentra system is available at the following Google Drive link:

**Video URL:** [INSERT YOUR GOOGLE DRIVE VIDEO LINK HERE]

<!-- Replace the line above with your actual link, for example:
**Video URL:** https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXXXXX/view?usp=sharing
-->

The video covers the following sections:

1. **How to Build the System** — **Docker mode (demoed live):** Docker Desktop, Git, clone repo, `.env.docker`, `docker-compose.yml`. **Manual mode (on-screen reference):** prerequisites, `backend/requirements.txt`, `vuln-web/requirements.txt`, `pip install -r`, `npm install`, `.env` configuration.
2. **How to Install the System** — **Docker mode (demoed live):** `docker compose up --build -d`, verify six containers, access :3000 / :5050. **Manual mode (on-screen reference):** three-terminal startup (`python run.py`, `npm start`, `python app.py`).
3. **How to Use the System** — User Manual-style walkthrough: login, dashboard navigation, Settings (escalating block policy), live Scanner attack demo (Nikto scan) triggering automated IP rate limiting, AI explanation, IP history, whitelist, detection rules, and live traffic.

---

## REFERENCE

1. OWASP Top 10 (2021) — A03 Injection, A04 Insecure Design. https://owasp.org/Top10/
2. MITRE ATT&CK — Enterprise matrix. https://attack.mitre.org/
3. NCSA Combined Log Format — web server logging conventions.
4. Flask Documentation — https://flask.palletsprojects.com/
5. React 18 Documentation — https://react.dev/
6. PostgreSQL 15 Documentation — https://www.postgresql.org/docs/
7. Redis Documentation — https://redis.io/docs/
8. Docker Compose Specification — https://docs.docker.com/compose/
9. Groq API Documentation — https://console.groq.com/docs
10. AbuseIPDB API v2 — https://www.abuseipdb.com/api-documentation
11. Material UI (MUI) — https://mui.com/
12. Chart.js — https://www.chartjs.org/

---

*Form 5 Conclusion | Incidentra "Intelligent Web-SOC Platform with Automated Incident Response" | President University Capstone 2026 | Hardin Irfan (001202300066) · Nasywa Kamila (001202300211) · Zaidan Mahfudz Azzam Saidi (001202300144)*
