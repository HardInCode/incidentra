# Research Methodology — Title, Abstract, and Keywords

**Capstone Design Project:** Incidentra — Intelligent Web-SOC Platform with Automated Incident Response  
**Author:** Hardin Irfan (001202300066) — Project Leader & Full-Stack Developer  
**Institution:** Faculty of Computer Science, President University  
**Target Journal:** IEEE Access *(see [RMAssignment1Hardin.md](RMAssignment1Hardin.md) for journal selection rationale)*  
**Advisor:** Mr. Abdul Ghofir S. Kom., M. Kom.

---

## Title

**Design and Implementation of a Log-Based Web Security Operations Center with OWASP Threat Detection, Escalating Automated Response, and LLM-Assisted Incident Analysis**

### Alternative Titles (for consideration)

| # | Title |
|---|-------|
| A | *Incidentra: An Open-Source Web-SOC Platform Combining Passive Log Monitoring, Regex-Based OWASP Detection, and Groq-Powered Incident Explanation* |
| B | *A Lightweight Security Operations Center for SMEs: Automated Web Attack Detection and Tiered IP Response Using Flask, React, and Large Language Models* |
| C | *Log-Tail-Based Intrusion Detection and Automated Incident Response for Web Applications with AI-Generated Threat Summaries* |

> **Note:** Title A emphasizes the product name; Title B highlights the SME target audience; the primary title above balances technical scope (detection + response + AI analysis) and aligns with IEEE Access scope on practical security system implementations.

---

## Abstract

Small and medium enterprises (SMEs) often lack the budget and expertise to operate commercial Security Information and Event Management (SIEM) or Security Operations Center (SOC) platforms, yet remain exposed to common web application attacks such as SQL injection, cross-site scripting (XSS), and brute-force login attempts. This research presents the design and implementation of **Incidentra**, a web-based SOC platform developed as a capstone project at President University. As project leader and full-stack developer, the author was responsible for the core backend architecture, real-time log ingestion pipeline, OWASP-based detection engine, automated response manager, Groq LLM integration for incident analysis, React.js SOC dashboard, and frontend–backend integration.

The proposed approach adopts a **passive, log-based monitoring architecture** that tails NCSA Combined Format access logs from a monitored web application without requiring code modifications, middleware agents, or direct database connections to the target system. Incoming log lines are parsed into structured HTTP request metadata and analyzed by a **DetectionEngine** that combines built-in OWASP regex patterns with administrator-defined rules stored in PostgreSQL, threshold-based brute-force tracking via Redis, and severity-weighted classification across eight attack categories (SQL Injection, XSS, Brute Force, Path Traversal, File Upload, Command Injection, Scanner, and LFI/RFI). Detected threats trigger a **tiered ResponseManager** that maps severity levels to proportional actions—logging and monitoring for low severity, rate limiting for medium, and escalating temporary IP blocking for high and critical severity—addressing client feedback on the risks of automatic permanent blocking in shared IP environments (NAT, corporate proxies, CGNAT).

For analyst support, the author integrated the **Groq Cloud API (LLaMA models)** to generate per-incident explanations including threat summaries, severity assessments, recommended remediation actions, and MITRE ATT&CK technique mappings, complemented by a four-model fallback chain and static safety-net explanations to ensure availability during API outages. Enforcement policies are synchronized to the monitored application through shared JSON files (`blocked_ips.json`, `rate_limited.json`) on a Docker volume, enabling real-time IP blocking and rate limiting without service restarts. The SOC dashboard—built with React.js—provides incident management, IP management (blocked, rate-limited, whitelist), customizable detection rules, live traffic monitoring, settings configuration, and an AI chatbot assistant.

Evaluation through live attack simulations and client feedback sessions with IT professionals at PT Accelist Lentera Indonesia demonstrated that the system detects simulated OWASP attacks within seconds (mean detection accuracy rating: 4.7/5), presents incidents on the dashboard with AI-generated explanations rated 4.3/5 for usefulness, and implements an escalating block policy accepted at 4.0/5 as a proportionate automated response. The complete platform deploys via Docker Compose across six services (PostgreSQL, Redis, Flask backend, React frontend, vulnerable web target, and Celery worker) with a single command, confirming that a functional SOC capability can be achieved using entirely open-source components. These results indicate that log-based detection combined with severity-proportional automated response and LLM-assisted triage offers a practical, cost-effective security monitoring solution for resource-constrained organizations.

---

## Keywords

**Security Operations Center (SOC)** · **Web Application Security** · **Log-Based Intrusion Detection** · **OWASP Top 10** · **Automated Incident Response** · **Large Language Models (LLM)** · **Flask** · **React.js** · **Docker**

---

## Mapping to Assignment Criteria

| Criterion | Section | Notes |
|-----------|---------|-------|
| Clear and concise title reflecting capstone focus and main objective | [Title](#title) | Primary title covers detection, automated response, and AI analysis—the three pillars of Incidentra |
| Abstract: problem overview | [Abstract](#abstract) | Paragraph 1 — SME security monitoring gap |
| Abstract: individual role and contributions | [Abstract](#abstract) | Paragraph 1 — backend, detection, response, AI, dashboard modules assigned to the author |
| Abstract: methodology / approach | [Abstract](#abstract) | Paragraphs 2–3 — log-tail architecture, DetectionEngine, ResponseManager, Groq integration, Docker deployment |
| Abstract: key results / findings | [Abstract](#abstract) | Paragraph 4 — client evaluation scores, detection latency, open-source feasibility |
| Relevant keywords for search databases | [Keywords](#keywords) | 9 terms covering domain, methods, and technologies |

---

## Author Module Scope Reference

The abstract above is scoped to the author's individual deliverables as defined in Form 1 (Manpower Details and Roles):

| Module / Task | Author Deliverable |
|---------------|-------------------|
| Backend Architecture | Flask REST API, PostgreSQL models, Redis integration, Celery worker |
| Log Ingestion Engine | LogTailer, log line parser, real-time pipeline in `log_monitor.py` |
| Detection Engine | `DetectionEngine` class, OWASP regex patterns, DB-backed custom rules, brute-force tracker |
| Response Manager | Escalating block policy, rate limiting, dual-write to DB + JSON enforcement files |
| AI Integration | Groq LLM incident explanations, four-model fallback chain, SOC chatbot widget |
| Frontend | React.js SOC Dashboard (incidents, IP management, rules, live traffic, settings) |
| Integration | Frontend–backend API wiring, Docker Compose multi-service deployment |

*Detection rule library, penetration testing, and QA validation were contributed by co-author Zaidan Mahfudz Azzam Saidi and are referenced only at the evaluation level, not as primary implementation work in this abstract.*
