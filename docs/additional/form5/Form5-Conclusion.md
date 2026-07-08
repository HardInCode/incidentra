Form4

Capstone Design Implementation

Title :

**Incidentra**

“Intelligent Web-SOC Platform with Automated Incident Response”

GROUP MEMBER:

| No. | Student Name | Student ID |
| --- | --- | --- |
| 1. | Hardin Irfan | 001202300066 |
| 2. | Zaidan Mahfudz Azzam Saidi | 001202300144 |

Advisor:  Mr. Abdul Ghofir S. Kom., M. Kom.

Submitted for

Capstone Design Project

to Faculty of Computer Science

President University

**TABLE OF CONTENT**

Contents

	A. CONCLUSION AND FUTURE WORKS	1

	Conclusion	1

	Future Works	3

	B. CLIENT FEEDBACK	5

	Client Feedback Summary	5

	C. VIDEO DEMONSTRATION	11

	The video covers	11

	REFERENCE	12

		

**STATEMENT OF ORIGINALITY**

In my capacity as an active student at President University and as the author of the Capstone Design Project stated below:

Name			: 1. Hardin Irfan – 001202300066

			  2. Zaidan Mahfudz Azzam Saidi – 001202300144

Faculty			: Computer Science

I hereby declare that my Capstone Design Project entitled “**Incidentra**” is to the best of my knowledge and belief, an original piece of work based on sound academic principles. If there is any plagiarism detected in this final project, I am willing to be personally responsible for the consequences of these acts of plagiarism and will accept the sanctions against these acts in accordance with the rules and policies of President University.

I also declare that this work, either in whole or in part, has not been submitted to another university to obtain a degree.

Cikarang, June 2026

| Signer 1 | Signer 2 |
| --- | --- |
|  |  |
| Hardin Irfan – 001202300066 | Zaidan Mahfudz Azzam Saidi – 001202300144 |

**Incidentra**

Approved:

| Abdul Ghofir S. Kom., M. Kom. | Rosalina, S. Kom., M. Kom. Program Head of Computer Science |
| --- | --- |

Prof. Dr. Ir. Wiranto Herry Utomo, M. Kom.

Dean of Faculty of Computer Science

**PART 5**

**CONCLUSION**

**Consists of: **

- **CONCLUSION AND FUTURE WORKS**

- **CLIENT FEEDBACK**

- **VIDEO DEMONSTRATION**

A. CONCLUSION AND FUTURE WORKS

Conclusion

- **Automated threat detection and incident response is achievable with open-source tools.** Incidentra has demonstrated that a fully functional Security Operations Center (SOC) platform can be built entirely from open-source components—Flask, React, PostgreSQL, Redis, and Docker—without requiring any commercial SIEM or WAF licenses. The system successfully detects the eight OWASP web attack categories (SQL Injection, XSS, Brute Force, Path Traversal, File Upload, Command Injection, Scanner, and LFI/RFI) through a combination of regex pattern matching and threshold-based analysis, and automatically responds with actions proportional to the severity level, ranging from logging and monitoring to escalating to temporary IP blocking. Detection rules can be customized from the SOC Dashboard without the need to restart the service.

- **A log-based detection architecture provides effective security monitoring without modifying the monitored application.** By tailing the web server access logs (NCSA Combined Log Format with the POST_DATA suffix), Incidentra acts as a passive observer that requires no code changes, middleware insertion, or agent installation on the monitored web applications. Deployment is performed via a shared JSON file on a named Docker volume, ensuring that the detection backend and the monitored applications remain completely separate.

- **AI-powered incident analysis enhances analyst productivity.** Integration with the Groq Cloud API (LLaMA models) provides automated incident explanations that include threat summaries, severity assessments, recommended actions, and MITRE ATT&CK mapping. A four-model fallback chain with a safety net of static explanations ensures that every incident is always accompanied by human-readable analysis, even when API connectivity is lost. This reduces the cognitive load on SOC analysts during the triage process.

- **A tiered automated response system with escalating block policy balances security with operational continuity.** During the client feedback phase, a senior professional in the field of IT Application Support raised concerns regarding the risk of permanent automatic IP blocking in shared IP environments (NAT, corporate proxies, CGNAT), where multiple users may share the same public IP address. In response to this feedback, the automated response system has been revised from an automatic permanent blocking approach to a phased blocking policy. Mapping severity levels to actions (Low → logging & monitoring, Medium → rate limiting, High → escalated temporary blocking starting at 1 hour, Critical → escalated temporary blocking starting at 24 hours) ensures that low-severity threats are monitored without disruption, while critical attacks are addressed with immediate yet proportionate measures. Repeated violations from the same IP address will result in progressively longer blocking periods (for example, 1 hour → 24 hours → 168 hours for high severity; 24 hours → 168 hours → 720 hours for critical severity). IP addresses that exceed the configurable violation threshold are automatically flagged as “Repeat Offenders,” alerting administrators to decide whether a permanent block is necessary. All blocking durations and “Repeat Offender” thresholds can be configured via the Settings page. Administrators retain full ability to override these settings through the SOC Dashboard to unblock IP addresses, add trusted sources to the whitelist, and modify blocking durations, thereby providing a safety net against false positives.

- **Containerized deployment reduces operational complexity.** Using Docker Compose sets up all six services (PostgreSQL, Redis, backend, frontend, vuln-web, and Celery worker) with just a single command: `docker-compose up --build -d`. No manual database setup, virtual environment configuration, or service registration is required, so this system can be deployed immediately on any machine that has Docker installed.

Future Works

- **Enhanced shared IP address awareness.** Although the current blocking policy—which is being further refined—has reduced the risk of permanent IP address blocking by using temporary blocks of increasingly longer durations instead of immediate permanent blocks, further improvements could include combining IP-based detection with session-level fingerprinting (cookies, User -Agent, request patterns) to distinguish between malicious users and legitimate users sharing the same IP address. Additionally, integration with a database of known NAT/CGNAT IP ranges could enable the system to automatically apply more lenient blocking policies to IP addresses identified as shared IP addresses.

- **CIDR range and subnet-based blocking.** Expand the IP management module to support CIDR notation (e.g., 192.168.1.0/24) for blocking or whitelisting entire subnets, thereby reducing the manual effort required to manage IP addresses one by one against coordinated attacks.

- **Multi-user role-based access control (RBAC) enhancement.** Expand the current Admin/Analyst role system with more granular permissions, such as separating rule management, IP management, and configuration access into different access levels. Add support for LDAP/Active Directory integration for enterprise environments.

- **Real-time WebSocket-based event streaming.** Replace the current HTTP polling mechanism (3-second interval for Live Traffic, default 15-second interval for Dashboard KPI refreshes) with WebSocket or Server-Sent Events (SSE) to receive truly real-time incident notifications and live traffic updates, thereby reducing latency and server load.

- **Enhanced reporting and compliance.** Add scheduled reporting features (daily/weekly summaries in PDF/Excel format), a compliance dashboard aligned with regulatory frameworks (ISO 27001, PCI DSS), and a visualization of incident response timelines for post-incident reviews.

- **Machine learning-based anomaly detection.** Supplement the current regex- and threshold-based detection system with a statistical anomaly detection model that learns normal traffic patterns and identifies deviations, thereby reducing reliance on predefined patterns and improving the ability to detect zero-day attacks.

- **Multi-application monitoring.** Expand the log collection layer to support simultaneous monitoring of multiple web applications from various log sources, with dashboards and custom rule sets for each application.

- **Web Application Firewall (WAF) integration.** Integrate with established WAF solutions such as ModSecurity or AWS WAF to combine Incidentra’s log-based detection intelligence with real-time request filtering at the network edge. This will enable the system to send dynamically generated blocking rules to the WAF based on detected threats, providing a layered defense where the WAF handles rule enforcement directly at the request level, while Incidentra continues to serve as a centralized SOC platform for monitoring, analysis, and incident management.

B. CLIENT FEEDBACK

To evaluate the effectiveness, ease of use, and features of the Incidentra SOC system, a feedback session was held with **three client representatives** from PT Accelist Lentera Indonesia (an IT Manager and two Senior IT Application Support Staff members). Each representative completed the same evaluation questionnaire after participating in a live demonstration and hands-on trial. The table below presents an **aggregated summary**: the numerical values represent the **arithmetic mean** of the three responses; the notes summarize recurring themes and key comments from the combined feedback (individual sources are not cited unless relevant to the context).

Client Feedback Summary

| **No.** | **Category** | **Question / Evaluation Criteria** | **Rating (1-5) / Response** | **Client's Remarks / Elaborations** |
| --- | --- | --- | --- | --- |
| 1 | Easy of Use | Is the SOC Dashboard easy to navigate and intuitive for daily security monitoring tasks? | **4.7 / 5** | The sidebar structure and incident workflow are considered intuitive for routine security monitoring after a brief explanation. |
| 2 | Easy of Use | Is the system easy to deploy and set up using Docker Compose? | **4.0 / 5** | The use of Docker Compose is generally considered practical for demo and staging environments. The clarity of the documentation for initial setup is cited as an area for improvement. |
| 3 | Display and Performance | Is the dashboard layout (charts, tables, KPI cards) clear and visually informative? | **4.0 / 5** | The KPI cards, charts, and tables were consistently rated as clear and informative in all three evaluations. |
| 4 | Display and Performance | Does the system respond quickly when detecting attacks and displaying incidents? | **4.3 / 5** | Live testing showed that incidents appeared on the dashboard within seconds of the attack simulation being carried out. Overall, the response speed was rated positively. |
| 5 | Feature and Functionality | Does the system accurately detect web attacks (SQL Injection, XSS, Command Injection, etc.)? | **4.7 / 5** | The simulated attack scenarios (e.g., SQL injection, XSS) were detected with the appropriate severity labels during the evaluation session. |
| 6 | Feature and Functionality | Is the escalating block policy (progressively longer blocks instead of permanent auto-block) an appropriate automated response? | **4.0 / 5** | The escalating temporary block policy s generally accepted. During discussion, **a shared concern was raised **that strict blocking based solely on IP addresses could harm legitimate users who use shared public IP addresses (NAT/corporate proxies).** **Respondents suggested **session-based blocking** as a future improvement. The tiered policy was considered a reasonable mitigation for a capstone project. |
| 7 | Feature and Functionality | Is the AI-powered incident explanation feature useful for understanding threats? | **4.3 / 5** | AI-generated explanations are considered useful for understanding the impact of threats and the recommended actions during the incident triage process. |
| 8 | Satisfaction Level | Overall, how satisfied are you with the Incidentra system? | **4.7 / 5** | Overall satisfaction levels were quite high among the three respondents. The system was assessed as a top-tier SOC project that is capable and worthy of further evaluation. |
| 9 | Respondent Suggestions | What improvements would you suggest for the system? | [Open Response] | **Aggregated suggestions:** (1) integrate a WAF for real-time edge filtering as part of a layered defense strategy; (2) transition from IP-based blocking alone to **session-based blocking** to reduce false positives on shared IP addresses; (3) improve **end-user and deployment documentation**. |
| 10 | Conclusion | Would you recommend this system for use in a real SOC environment (with further development)? Why or why not? | [Open Response] | All three respondents would **recommend** the system for further use in a controlled or staging environment, **pending refinement** (documentation, bug fixes, and production-hardening). Core detection and automated response—including the tiered blocking policy—were assessed as effective and promising for real SOC workflows with continued development. |

Table 1. Client Feedback Summary

*Rating notation: ****X.X / 5 (mean, n=3)**** = average of three independent client questionnaire responses. Scores are rounded to one decimal place.*

The Google Form and the responses to the Google Form are available at the following URL:

**Questionnaire Form**** URL: **[**FORM**](https://forms.gle/2R4B16hLJsaNomre6)** ****&**** **[**CLIENT FEEDBACK**](https://drive.google.com/drive/folders/1-RjSUXoiCVxqGSyiu8QiTCUy-9VME1oi?usp=sharing)

Figure 1. Form Respondent Screenshot

C. VIDEO DEMONSTRATION

The video demonstration of the Incidentra system is available at the following Google Drive link:

Video URL: [ **VIDEO DEMONSTRATION**](https://drive.google.com/drive/folders/1qCRW2EdbnSv1P_Ij7dFamKaw44YoW37d?usp=sharing)

The video covers

- **How to Build the System** — **Docker mode (demoed live):** Docker Desktop, Git, clone repo, .env.docker, docker-compose.yml. **Manual mode (on-screen reference):** prerequisites, backend/requirements.txt, vuln-web/requirements.txt, pip install -r, npm install, .env configuration.

- **How to Install the System** — **Docker mode (demoed live):** docker compose up --build -d, verify six containers, access :3000 / :5050. **Manual mode (on-screen reference):** three-terminal startup (python run.py, npm start, python app.py).

- **How to Use the System** — User Manual-style walkthrough: login, dashboard navigation, Settings (escalating block policy), live Scanner attack demo (Nikto scan) triggering automated IP rate limiting, AI explanation, IP history, whitelist, detection rules, and live traffic.

REFERENCE

- OWASP Top 10 (2021) — A03 Injection, A04 Insecure Design. [https://owasp.org/Top10/](https://owasp.org/Top10/)

- MITRE ATT&CK — Enterprise matrix. [https://attack.mitre.org/](https://attack.mitre.org/)

- NCSA Combined Log Format — web server logging conventions.

- Flask Documentation — [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)

- React 18 Documentation — [https://react.dev/](https://react.dev/)

- PostgreSQL 15 Documentation — [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)

- Redis Documentation — [https://redis.io/docs/](https://redis.io/docs/)

- Docker Compose Specification — [https://docs.docker.com/compose/](https://docs.docker.com/compose/)

- Groq API Documentation — [https://console.groq.com/docs](https://console.groq.com/docs)

- AbuseIPDB API v2 — [https://www.abuseipdb.com/api-documentation](https://www.abuseipdb.com/api-documentation)

- Material UI (MUI) — [https://mui.com/](https://mui.com/)

- Chart.js — [https://www.chartjs.org/](https://www.chartjs.org/)

2

2