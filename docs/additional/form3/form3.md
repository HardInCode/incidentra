Form3

Design

Title:

**Incidentra**

“Intelligent Web-SOC Platform with Automated Incident Response”

GROUP MEMBER:

| No. | Student Name | Student ID |
| --- | --- | --- |
| 1. | Hardin Irfan | 001202300066 |
| 2. | Zaidan Mahfudz Azzam Saidi | 001202300144 |

Advisor: Mr. Abdul Ghofir S. Kom., M. Kom.

Submitted for

Capstone Design Project

to Faculty of Computer Science

President University

**TABLE OF CONTENT**

Contents

A.	SYSTEM DESIGN	1

		**1.**	**High-Level System Architecture**	**1**

		a.	Core Threat Detection & Mitigation Flow	2

		b.	Asynchronous Processing & Integrations	2

		c.	SOC Management & User Interface	3

		**2.**	**Technology Stack**	**3**

		**3.**	**Interface Mock-up Design**	**5**

		a.	Login Page	5

		b.	SOC Dashboard	5

		c.	Incidents List	6

		d.	Incident Detail - Before AI Analysis	7

		e.	Incident Detail – After AI Analysis (Groq LLM)	7

		f.	IP Management (Blocked IPs)	8

		g.	Detection Rules	9

		h.	Create Detection Rule	10

		i.	Live Traffic Monitor	10

		j.	Settings	11

B.	HIERARCHICAL/ITERATIVE DESIGN	12

		**1.**	**Block Diagrams and Package Structure**	**12**

		a.	Block Diagram — Level 0 (Highest Level)	12

		b.	Block Diagram — Level 1 (Subsystem Level)	13

		c.	Block Diagram — Level 2 (Primitive Software Functions)	14

		a)	Log Monitoring Module	14

		b)	Detection Engine	14

		c)	Response Manager	15

		**2.**	**Interface Between Block Diagrams**	**16**

		**3.**	**Software Engineering Design Steps**	**17**

		a.	Use Case Diagram	18

		b.	Entity Relationship Diagram (ERD)	19

		c.	Class Diagram	20

		d.	Activity Diagram	21

		e.	Sequence Diagram	21

		**4.**	**Component References and Libraries**	**22**

		**5.**	**Modelling Standards**	**23**

C.	STANDARDS USED	24

D.	IMPLEMENTATION AND TESTING SCENARIO	26

		1.	Implementation Approach	26

		2.	Functional Testing Scenarios	27

		3.	Success Metrics	31

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

**SCREENSHOT OF ZEROGPT**

PART 3

**DESIGN**

 SYSTEM DESIGN

Incidentra is designed as a three-tier web application that functions as a log-based passive security monitoring layer. Instead of being placed inline between the client and the target application—which would introduce latency and create a single point of failure—the system monitors web server access logs in real time using a tail-based mechanism. This architectural decision, described in Form 2, means that the detection and response cycle begins after the web server has written the request to disk, ensuring that there is no impact on the application’s response time.

High-Level System Architecture

The platform is composed of four distinct subsystems that communicate through a shared PostgreSQL database and a Redis message broker. Each subsystem has a clearly defined responsibility boundary:

- Log Ingestion Layer (log_monitor.py + log_parser.py): A Python background process that continuously polls the vuln-web access.log file every second and forwards parsed log entries to the Detection Engine.

- Detection & Response Engine (detection_engine.py + response_manager.py): The core analytical component that classifies traffic using OWASP-based regex patterns and executes automated defensive responses — ranging from rate-limiting to escalating temporary IP blocks — by writing to shared JSON enforcement files. Automatic responses never apply permanent blocks; permanent blocking is reserved for manual admin action.

- Backend API Layer (Flask + Celery): A RESTful API server exposing all platform functionality to the frontend, with Celery managing asynchronous tasks such as AI explanation generation and notification dispatch.

- SOC Dashboard (React.js): A browser-based management interface through which IT administrators review incidents, manage detection rules, monitor live traffic, and configure integrations.

The architecture is presented as three focused diagrams below, each covering a distinct flow within the system.

- Core Threat Detection & Mitigation Flow

This diagram illustrates the main detection workflow: it begins with an attacker’s HTTP request to the vuln-web application, followed by LogMonitor reading access logs in real time, DetectionEngine classifying threats, and finally ResponseManager implementing blocking by updating the shared JSON file that vuln-web reads with every request.

Figure 1. Core Threat Detection & Mitigation Flow

- Asynchronous Processing & Integrations

After an incident is saved, ResponseManager dispatches notifications via a daemon thread (primary path, reliable without a running Celery worker) or optionally via Celery workers through Redis. Background tasks call ai_service (Groq Cloud LLM API for human-readable explanations stored in PostgreSQL), notification_service (SMTP email or Telegram alerts), and threat_intel_service (AbuseIPDB IP reputation scoring).

Figure 2. Asynchronous Processing & External Integrations

- SOC Management & User Interface

The SOC Dashboard (React.js, port 3000) communicates with the Flask REST API backend (port 5000) exclusively over REST/JSON. The API layer handles all CRUD operations against PostgreSQL and queues background tasks via Redis. This separation ensures the UI layer is fully decoupled from the processing engine.

Figure 3. SOC Management & User Interface Flow

Technology Stack

The complete technology stack used by Incidentra is summarised in the following table. All components are open-source and incur zero licensing costs, directly addressing the cost-barrier constraint identified in Form 2.

| **Layer** | **Technology** | **Version / Details** | **Role** |
| --- | --- | --- | --- |
| Frontend | React.js | 18.x (Create React App) | SOC Dashboard UI |
| Frontend | Axios | 1.x | HTTP client for REST API calls |
| Frontend | Chart.js | 4.x | Incident timeline & severity charts |
| Backend | Python | 3.11+ | Primary runtime environment |
| Backend | Flask | 3.x | REST API web framework |
| Backend | SQLAlchemy | 2.x (ORM) | Database abstraction layer |
| Backend | Celery | 5.x | Asynchronous task queue |
| Backend | PyJWT | 2.x | JWT token encoding / verification |
| AI / External | Groq Cloud API | llama-3.3-70b-versatile (primary) | AI-powered incident explanation |
| AI / External | AbuseIPDB API | v2 | IP reputation scoring |
| Data Layer | PostgreSQL | 15+ | Primary relational database |
| Data Layer | Redis | 7.x | Celery broker, result backend, rules_dirty flag |
| DevOps | Docker + Compose | 24.x / 2.x | Container orchestration |
| DevOps | Nginx | 1.25 | Reverse proxy for React frontend |
| Target (demo) | vuln-web (Flask) | internal | Deliberately vulnerable test application |

Table 1. Incidentra Technology Stack

Interface Mock-up Design

The following screenshots represent the actual implemented interface of the Incidentra SOC Dashboard. The frontend is built with React.js and features a dark-themed design optimised for security operations centre environments, where operators may work for extended periods.

- Login Page

The login page authenticates IT administrators using a username and password combination. Upon successful login, the server issues a JWT (JSON Web Token) with a 24-hour expiry. The token is stored in the browser and attached to all subsequent API requests via the Authorization: Bearer header.

Figure 4. Incidentra Login Page — JWT-based Authentication

- SOC Dashboard

The main dashboard provides a real-time operational overview through four metric cards: Total Incidents, Detections in the Last 24 Hours, Blocked IP Addresses, and MTTR (Mean Time to Resolution). A system status banner dynamically displays the current threat status. The Incident Timeline chart (7-day view) and the “By Severity” donut chart use Chart.js.

Figure 5. SOC Dashboard — Real-Time Threat Overview

- Incidents List

The Incidents page is available in two scopes: Ongoing (/incidents) shows new and investigating incidents only; All Incidents (/incidents/all) includes resolved and false-positive records. Each scope presents a filterable, paginated table of detected threats. Each row displays the detection timestamp, source IP address (clickable to open the IP History drawer), attack type badge, severity badge, current status, affected request path, and the automated response action taken (indicated by an icon). Administrators can filter by severity and status using dropdown selectors, and search across IP, attack type, and path fields. A "Simulate Attack" button triggers a test detection for demonstration purposes, and "Export CSV" generates a scoped downloadable report (incidents-ongoing.csv or incidents-all.csv).

 Figure 6. Incidents List — Filterable, Paginated Threat Table

- Incident Detail - Before AI Analysis

When an administrator opens an incident record, the left panel displays full technical details: Source IP with AbuseIPDB reputation score, Attack Type, Severity, HTTP method and path, response code, geolocation country, and both detection and resolution timestamps. The right panel initially shows the "AI Explanation Not Generated" state with a "Generate AI Explanation" call-to-action button. Below it, the Automated Actions log shows what the system did automatically — for example, an escalating temporary block (Offense #1) executed at detection time. An Investigation Notes section allows the analyst to append timestamped manual notes to the incident record.

 Figure 7. Incident Detail — Technical Details and Automated Actions Panel

- Incident Detail – After AI Analysis (Groq LLM)

After the administrator clicks “Generate AI Explanation,” the backend system synchronously calls the Groq Cloud API using the build_prompt() function, which constructs a structured prompt containing the incident’s technical attributes. The Groq LLM returns a JSON object containing four fields displayed in color-coded panels: a plain-language summary (blue-green frame), a “Why It’s Dangerous” explanation (orange frame), numbered Recommended Actions (purple frame), and a MITRE ATT&CK technical mapping. The model name badge (e.g., “llama-3.3-70b-versatile”) is displayed in the panel header for transparency.

If the primary model is unavailable, the system automatically cycles through a chain of four models in the following order:

- llama-3.3-70b-versatile (primary)

- llama-3.1-8b-instant

- meta-llama/llama-4-scout-17b-16e-instruct

- meta-llama/llama-guard-4-12b

If all four models are exhausted, the system falls back to a curated static explanation, ensuring that every incident always receives an explanation regardless of external API availability. The `model_used` field in the database records which model or fallback source generated the explanation, thereby maintaining full auditability.

 Figure 8. Incident Detail — AI-Powered Analysis via Groq Cloud LLM

- IP Management (Blocked IPs)

The IP Management page (/blocked-ips) maintains enforcement state across three tabs. The Blocked tab lists active BlockedIP records with block type (permanent or temporary escalating), expiry time, incident count, Repeat Offender badge when the configurable threshold is reached, and unblock actions; filters support block type and repeat-offender-only views. The Rate Limited tab lists IPs from rate_limited.json with per-IP policy and TTL. The Whitelisted tab lists trusted IPs (GET /api/blocked-ips/?whitelist=true) with add and remove actions. When the Response Manager adds an IP to blocked_ips.json, vuln-web reads this file on every incoming request and returns HTTP 403 Forbidden — enforcing the block in real time without a server restart. Permanent blocks are applied only through manual admin action; automatic high/critical responses use escalating temporary blocks (revised after client feedback on shared-IP environments, documented in Form 5).

 Figure 9. IP Management — Blocked, Rate Limited, and Whitelisted Tabs

- Detection Rules

The Detection Rules page exposes the database-stored rule set that drives the DetectionEngine. Each rule has a name, attack type category, severity level, regex pattern excerpt, match count (total historical detections by this rule), and an active/inactive toggle. The detection engine reloads rules from the database every 60 seconds via a Redis "rules_dirty" flag mechanism, ensuring that newly created or modified rules are picked up without restarting the backend. The default rule set covers **18** active patterns (11 core OWASP-aligned rules plus 7 lab-specific EXTRA_RULES) across SQL Injection, XSS, Path Traversal, Command Injection, Brute Force, Scanner, File Upload, and LFI/RFI categories.

 Figure 10. Detection Rules — Database-Driven Rule Set with Match Counters

- Create Detection Rule

A modal form allows administrators to define new detection rules directly from the dashboard. The form captures a Rule Name, Attack Type (selected from a fixed enum of supported categories), Severity Level (low / medium / high / critical), the Regex Pattern to match against the log payload, and an optional Description. Upon submission, the rule is saved to the detection_rules table in PostgreSQL and the Redis rules_dirty flag is set, triggering the detection engine to reload its compiled pattern set on its next interval check.

Figure 11. Create Detection Rule — Custom OWASP Pattern Entry

- Live Traffic Monitor

The Live Traffic page displays the most recent web requests parsed from the access log, auto-refreshing every 3 seconds via HTTP polling. Each row shows the request timestamp, source IP, HTTP method, request path, query string or payload excerpt, HTTP status code, and a classification tag (attack / suspicious / blocked / normal). The summary counter cards at the top provide an at-a-glance count of each traffic category in the current view window. Filter tabs allow the analyst to isolate specific traffic categories. This page enables real-time situational awareness during active attack scenarios without requiring direct server access.

 Figure 12. Live Traffic Monitor — Real-Time Log Stream with Classification Tags

- Settings

The Settings page allows the IT administrator to configure all external integrations and detection parameters without modifying environment files directly. Configurable sections include: AI Assistant (Groq API key and model selection with a test connection button), Threat Intelligence (AbuseIPDB API key with test function), Email Notifications (SMTP host, port, credentials, and recipient address), Telegram Bot (bot token and chat ID), Detection Thresholds (brute force attempt threshold, rate limit window), Detection Lab Mode toggle, and **Escalating Block Policy** (repeat-offender threshold, high-severity duration tiers default 1h→24h→168h, critical-severity tiers default 24h→168h→720h). All API keys are stored masked in the UI and persisted to the app_settings table in PostgreSQL.

 Figure 13. Settings Page — External Integration and Threshold Configuration

 HIERARCHICAL/ITERATIVE DESIGN

## Block Diagrams and Package Structure

The backend follows a layered package structure that separates concerns across four levels: API endpoints (app/api/), core processing engines (app/core/), service integrations (app/services/), and shared utilities (app/utils/). The API layer includes blueprints for authentication (auth.py), incident management (incidents.py), detection rules (rules.py), blocked IPs (blocked_ips.py), dashboard statistics (dashboard.py), live traffic (traffic.py), settings (settings.py), and the AI chatbot assistant (chatbot.py). This separation ensures that the detection logic remains decoupled from both the transport layer and the external service integrations.

Figure 14. Backend Module Hierarchy and Package Structure

- Block Diagram — Level 0 (Highest Level)

At the highest level, Incidentra consists of three main layers: the User Interface layer (SOC Dashboard), the Application Backend layer (Flask API), and the Security Monitoring Engine (Incidentra Core Engine). The Core Engine drives the three primary subsystems: Log Monitor, Detection Engine, and Response Manager, all backed by PostgreSQL and the AI Explanation Service.

Figure 15. Block Diagram Level 0 — System Hierarchy

- Block Diagram — Level 1 (Subsystem Level)

The Incidentra Core Engine is divided into three primary subsystems with their primitive functions. The Monitoring subsystem contains the Log Parser. The Analysis subsystem contains the Attack Pattern Analyzer and Severity Scoring modules. The Response subsystem contains IP Blocking, Rate Limiting, and Firewall Rules enforcement.

Figure 16. Block Diagram Level 1 — Core Engine Subsystems

- Block Diagram — Level 2 (Primitive Software Functions)

- Log Monitoring Module

The Log Monitor is triggered continuously via a tail-f mechanism. It reads the access log file, buffers the data, parses each log entry into a structured JSON object, and streams the parsed data asynchronously to the Detection Engine.

Figure 17. Level 2 — Log Monitoring Module Flowchart

- Detection Engine

The Detection Engine receives parsed log data and applies OWASP-based regex pattern matching across 8 attack categories: SQL Injection, XSS, Path Traversal, Command Injection, Brute Force (threshold-based), File Upload, Security Scanner (User-Agent detection), and LFI/RFI. Each matched pattern is assigned a severity score (low/medium/high/critical). The highest-scoring threat is forwarded to the Response Manager.

Figure 18. Level 2 — Detection Engine with 8 Attack Categories

- Response Manager

The Response Manager executes automated mitigation based on threat severity: low → log and monitor; medium → rate limit; high → escalating temporary block; critical → escalating temporary block. All automatic high/critical blocks use progressive durations per offense tier; permanent blocks are never applied automatically. All actions are written to the shared JSON enforcement files and logged to the PostgreSQL database as IncidentLog records.

The Response Manager applies the following severity-to-action mapping, consistent with the RESPONSE_ACTIONS dictionary in detection_engine.py:

| **Severity** | **Action** | **Enforcement Method** | **Duration** |
| --- | --- | --- | --- |
| Low | Log & Monitor | Saved to incident_logs | Permanent record |
| Medium | Rate Limit | Write to rate_limited.json | Per rate limit window |
| High | Escalating Block | Write to blocked_ips.json; BlockedIP with block_type=temporary | Default: 1h → 24h → 168h per offense tier |
| Critical | Escalating Block | Write to blocked_ips.json; BlockedIP with block_type=temporary | Default: 24h → 168h → 720h per offense tier |

Table 2. Response Manager Severity-to-Action Mapping

Automatic responses never apply permanent blocks. When an IP reaches the Repeat Offender threshold (default: 3 offenses, configurable via Settings), `is_repeat_offender=True` is set on the BlockedIP record for admin review. Escalation tier counters (`escalation_count:{ip}`, `escalation_severity:{ip}`) persist in Redis across admin unblock so repeat offenders resume at the correct offense tier. This phased policy replaces the earlier permanent auto-block design, reflecting client feedback on shared-IP environments (NAT, corporate proxies) documented in Form 5.

Interface Between Block Diagrams

Communication between system components follows predefined interface contracts to ensure loose coupling and the ability to deploy each subsystem independently.

The internal engine components—Log Monitor, Detection Engine, and Response Manager—communicate via direct Python function calls by passing structured dictionaries, thereby keeping the core detection workflow in sync and ensuring low latency. Enforcement is decoupled from the detection cycle using shared JSON files (blocked_ips.json, rate_limited.json), which are read by the vuln-web application on every incoming request. This design ensures that blocking takes effect immediately without requiring inter-process communication or server restarts, while also ensuring that the enforcement layer can operate independently of the backend API.

All external communication uses standard REST/JSON over HTTP, with Bearer JWT token authentication applied to every protected endpoint. Asynchronous workloads—AI explanation generation, IP reputation checks, and alert notifications—are offloaded via daemon threads (primary) or Celery workers via Redis, preventing them from blocking the main detection cycle.

The complete interface definitions between each component pair are summarized in the table below.

| **Component Pair** | **Interface Type** | **Data Format** | **Description** |
| --- | --- | --- | --- |
| Log Monitor → DetectionEngine | Function call | Python dict (parsed log entry) | Parsed log entries passed as structured JSON objects per line |
| DetectionEngine → ResponseManager | Function call | Python dict (threat data) | Attack detection results including ip, attack_type, severity, score |
| ResponseManager → PostgreSQL | SQLAlchemy ORM | SQL INSERT | Incident and IncidentLog records written via ORM session |
| ResponseManager → vuln-web | Shared file (JSON) | blocked_ips.json / rate_limited.json | Enforcement files read by vuln-web on every incoming HTTP request |
| Flask REST API → Frontend | REST / HTTP | JSON response body | All dashboard operations via RESTful endpoints with JWT auth |
| Flask API → Redis | Redis publish | Task ID + payload | Background tasks queued for Celery worker consumption |
| Celery → Groq Cloud API | HTTPS / REST | JSON (OpenAI-compatible) | Chat completion request with structured incident prompt |
| Celery → AbuseIPDB | HTTPS / REST | JSON | IP reputation check returning abuse confidence score |
| Celery → SMTP / Telegram | SMTP / HTTPS | Text / JSON | Alert notifications dispatched to SOC administrator |

Table 3. Component Interface Definitions

## Software Engineering Design Steps

Incidentra was developed following the Waterfall software engineering methodology over a 14-week period. The following table documents each phase of the development process from requirements analysis through to testing and validation.

| **Phase** | **Description / Implementation in Incidentra** |
| --- | --- |
| **Requirements Analysis** | Functional and non-functional requirements were defined based on the security needs of SME web applications. Key requirements included real-time log-based threat detection, automated IP blocking, AI-powered incident explanation, and a centralized SOC dashboard accessible to non-expert administrators. |
| **System Design** | High-level architecture was designed as a three-tier log-based passive monitoring system. The system was decomposed into four subsystems: Log Ingestion Layer, Detection and Response Engine, Backend API Layer, and SOC Dashboard. External dependencies (Groq Cloud, AbuseIPDB) and component boundaries were documented through architecture diagrams and UML models. |
| **Component Design** | Each component was decomposed into smaller modules with clearly defined inputs and outputs. The backend is structured into four layers: app/api/ (REST endpoints), app/core/ (detection and monitoring engine), app/services/ (external integrations), and app/models/ (ORM models). Each module has a single, well-defined responsibility. |
| **Interface Design** | All interfaces were designed following RESTful principles with resource-based URLs, standard HTTP verbs, and JSON response bodies. Parameter mappings between frontend (React/Axios) and backend (Flask REST API) were explicitly defined. JWT Bearer token authentication is enforced on all protected endpoints via before_request middleware. |
| **Database Design** | PostgreSQL was used with SQLAlchemy ORM. The schema supports a relational structure centered on the Incidents table, with foreign key relationships to Users, DetectionRules, IncidentLogs, IncidentExplanations, IncidentNotes, and BlockedIPs. The ERD is provided in the following section. |
| **Implementation** | Modular structure using React.js (frontend) and Flask (backend). The backend separates responsibilities into API blueprints, core engine modules, service integrations, and ORM models. Asynchronous tasks are handled by Celery workers via Redis. The codebase is version-controlled using Git on GitHub. |
| **Testing ****&**** Validation** | Functional testing covered 23 test cases (TC-01 to TC-23) including authentication, detection for all 8 OWASP attack categories, escalating automated IP blocking, Repeat Offender flagging, AI explanation generation, and system resilience under Redis failure. API endpoint testing was conducted using Postman. Attack simulation used the built-in Simulate Attack feature and manual payload injection via the vuln-web application. |

*Table 5. Software Engineering Design Phases — Incidentra Implementation*

- Use Case Diagram

The Use Case Diagram illustrates the interactions between the IT Administrator and the Incidentra platform, including all primary use cases: Login, Monitor Dashboard Statistics, Manage System Incidents, View AI Explanation, Manage Detection Rules, Manage Blocked IP Addresses, Receive Alerts, and Export Security Reports. External actors include the Groq Cloud LLM API (triggered by View AI Explanation) and the AbuseIPDB API (extended by Assess IP Reputation when a threat is detected).

*Figure 19. Use Case Diagram — Incidentra Platform Interactions*

- Entity Relationship Diagram (ERD)

The Entity Relationship Diagram shows the data model underlying the Incidentra platform. The central entity is Incidents, which is managed by Users, triggered by DetectionRules, generates IncidentLogs, has one IncidentExplanation, contains IncidentNotes, and may result in a BlockedIP record (including is_repeat_offender and is_whitelist flags). All relationships and cardinalities are defined to ensure data integrity and support the full incident lifecycle from detection to resolution.

Figure 20. Entity Relationship Diagram — Incidentra Data Model

- Class Diagram

The class diagram shows the principal domain entities and their relationships. User manages zero or many Incidents. Each Incident is triggered by a DetectionRule, generates zero or many IncidentLog records, has exactly one IncidentExplanation, contains zero or many IncidentNote records, and may result in zero or one BlockedIP entry.

Figure 21. Class Diagram — Domain Entities and Relationships

- Activity Diagram

The activity diagram illustrates the end-to-end system workflow from startup. The LogMonitor continuously reads and parses each log entry. If no threat is detected (normal traffic), the system returns to monitoring. When a threat is found, it triggers the Response Manager, stores the incident, generates an AI explanation, and displays the result in the SOC Dashboard.

Figure 22. Activity Diagram — System Workflow from Log to Dashboard

- Sequence Diagram

The sequence diagram documents the full interaction flow from the moment an attacker sends a malicious HTTP request to the point where the IT administrator reviews the AI-generated explanation on the SOC Dashboard. Key interactions include the tail-f log reading mechanism, regex-based threat detection, escalating automated IP blocking via shared JSON files, thread-based (or Celery) asynchronous AI explanation generation, and the REST API query from the React frontend.

Figure 23. Sequence Diagram — Full Threat Detection and Response Flow

Component References and Libraries

| **Package** | **Version** | **Purpose** | **Source** |
| --- | --- | --- | --- |
| Flask | 3.x | REST API web framework | flask.palletsprojects.com |
| SQLAlchemy | 2.x | ORM database abstraction | sqlalchemy.org |
| Celery | 5.x | Async task queue | docs.celeryq.dev |
| PyJWT | 2.x | JWT token auth | pyjwt.readthedocs.io |
| redis-py | 5.x | Redis client | redis-py.readthedocs.io |
| requests | 2.x | HTTP client (Groq/AbuseIPDB) | requests.readthedocs.io |
| psycopg | 3.x | PostgreSQL driver | psycopg.org |
| python-dotenv | 1.x | Environment config loading | pypi.org/project/python-dotenv |
| React | 18.x | Frontend UI framework | react.dev |
| Axios | 1.x | HTTP client (frontend) | axios-http.com |
| Chart.js | 4.x | Canvas-based charts | chartjs.org |

Table 4. External Library References

## Modelling Standards

All system design diagrams in this document follow established modelling standards to ensure clarity and consistency. The UML 2.5 standard is applied to all structural and behavioral diagrams including the Class Diagram, Use Case Diagram, Activity Diagram, and Sequence Diagram. Flowcharts follow standard ISO 5807 notation for process flow representation. The Entity Relationship Diagram follows Chen notation for data modelling. A complete list of technical standards applied in this project, including data formats, API standards, and security standards, is provided in Section C (Standards Used).

 STANDARDS USED 

Incidentra adheres to the following industry-recognised technical standards across API design, security implementation, data formats, and detection methodology:

| **No.** | **Standard** | **Category** | **Application in Incidentra** |
| --- | --- | --- | --- |
| 1 | REST (RESTful API) | API Design | All backend endpoints follow REST conventions: resource-based URLs (/api/incidents/{id}), HTTP verbs for CRUD, JSON bodies, standard HTTP status codes (200, 201, 400, 401, 403, 404). |
| 2 | JSON (RFC 8259) | Data Format | All inter-service communication uses UTF-8 encoded JSON. Enforcement files (blocked_ips.json, rate_limited.json) use a flat JSON schema with a blocked or rate_limited array and updated_at timestamp. |
| 3 | JWT — RFC 7519 | Authentication | JSON Web Tokens issued on login with 24-hour expiry. Payload contains user_id, username, role. Signed with HS256. All protected routes call verify_token() via before_request. |
| 4 | PBKDF2-SHA256 | Security | User passwords hashed using Werkzeug generate_password_hash() with PBKDF2-SHA256 and a random salt. Plain-text passwords are never stored. |
| 5 | HTTP/1.1 (RFC 2616) | Communication | All internal and external HTTP communication uses HTTP/1.1 over TCP/IP. |
| 6 | OWASP Top 10 (2021) | Detection Methodology | Detection patterns cover OWASP Top 10 categories: A03 Injection (SQLi, Command Injection), A07 XSS, A01 Path Traversal, LFI/RFI, and Brute Force. Each mapped to MITRE ATT&CK. |
| 7 | MITRE ATT&CK v14 | Threat Intelligence | Each attack type is mapped to a MITRE technique ID (e.g., T1190, T1059.007, T1110). Stored per incident and included in AI explanations. |
| 8 | Combined Log Format | Log Parsing | Web server access logs follow NCSA Combined Log Format used by Nginx/Apache. Extended in vuln-web to append POST_DATA for login endpoint detection. |
| 9 | ISO 8601 | Timestamps | All timestamps stored and returned in ISO 8601 UTC format (e.g., 2026-03-17T10:06:52+0000). |
| 10 | Docker Compose v3.8 | Deployment | Multi-container deployment defined using Compose file format v3.8 with named volumes, health checks, and service dependencies. |
| 11 | PEP 8 | Code Style | Python code follows PEP 8: 4-space indentation, snake_case variables, PascalCase classes. |
| 12 | UML 2.5 | Modelling | System design diagrams follow UML 2.5 notation for Class, Activity, and Sequence diagrams. |
| 13 | RegEx (PCRE) | Pattern Matching | Perl-Compatible Regular Expressions used by DetectionEngine for high-speed, real-time attack signature matching. |

Table 5. Standards Used in Incidentra

IMPLEMENTATION AND TESTING SCENARIO

## Implementation Approach

The target deployment environment uses Docker Compose to co-locate all six services on a single host. For development and demonstration purposes during this project phase, the system was also validated through a manual local setup as an alternative. The Docker Compose deployment described below represents the production-target configuration.

- Configure environment by copying backend/.env.docker.example to backend/.env.docker and filling in API keys (Groq, AbuseIPDB, SMTP, Telegram). Core detection operates without any external API keys.

- Run docker compose up --build -d to start all six services: PostgreSQL (port 5432), Redis (port 6379), vuln-web (port 5050), Incidentra backend (port 5000), React frontend via Nginx (port 3000), and celery_worker.

- The backend docker_entrypoint.sh runs database migrations, seeds default admin and analyst users and **18** default detection rules, then launches Flask via Gunicorn. The log monitor starts automatically as a background thread, tailing the shared access.log volume mount from vuln-web.

- Access the SOC Dashboard at http://localhost:3000. The vuln-web test application is at [http://localhost:5050](http://localhost:5050).

Default detection and response thresholds applied in the implementation:

| **Parameter** | **Default Value** | **Configurable Via** | **Effect** |
| --- | --- | --- | --- |
| BRUTE_FORCE_THRESHOLD | 10 requests | Settings page / .env | Triggers brute force incident after N POST requests to login path within window |
| RATE_LIMIT_WINDOW | 60 seconds | Settings page / .env | Sliding window for brute force and rate-limiting counters |
| RATE_LIMIT_MAX_REQUESTS | 100 requests | Settings page / .env | Max requests per IP before rate limiting |
| REPEAT_OFFENDER_THRESHOLD | 3 offenses | Settings page | Flags BlockedIP.is_repeat_offender when incident_count ≥ threshold |
| ESCALATING_HIGH_DURATIONS | 1, 24, 168 (hours) | Settings page | Block duration tiers for high severity (1h → 24h → 7d) |
| ESCALATING_CRITICAL_DURATIONS | 24, 168, 720 (hours) | Settings page | Block duration tiers for critical severity (24h → 7d → 30d) |
| Rules Reload Interval | 60 seconds | detection_engine.py | Frequency engine re-reads active rules from PostgreSQL via Redis flag |

Table 6. Default Detection and Response Thresholds

Functional Testing Scenarios

The following test scenarios cover all primary use cases. Each scenario specifies the test description, steps and input, expected result, and status. Testing is designed to be executed against the Docker Compose deployment environment. Initial validation was conducted during development using the manual local setup as an alternative setup.

| **TC#** | **Test Description** | **Steps ****&**** Input** | **Expected Result** |
| --- | --- | --- | --- |
| **TC-01** | Authentication — Successful login | Navigate to http://localhost:3000. Enter username: admin, password: Admin@Incidentra2026!. Click Sign In. | JWT token issued. Redirect to SOC Dashboard. All navigation items visible. |
| **TC-02** | Authentication — Wrong credentials | Enter username: admin, password: wrongpass. Click Sign In. | HTTP 401 "Invalid credentials" shown. No token issued. User stays on login page. |
| **TC-03** | Authentication — No token | Navigate to http://localhost:5000/api/incidents without Authorization header. | HTTP 401 "Authorization required". Endpoint returns no data. |
| **TC-04** | SQL Injection Detection | Navigate to http://localhost:5050/search. Enter: ' OR 1=1 UNION SELECT username,password FROM users--. Submit. Wait 3 seconds. | Incident created: attack_type=SQL_INJECTION, severity=critical. Source IP in blocked_ips.json with escalating block (Offense #1, ~24h). Incident visible in dashboard. |
| **TC-05** | Automated IP Block — HTTP 403 | After TC-04, navigate to http://localhost:5050 from the same IP. | HTTP 403 Forbidden rendered by vuln-web. "IP has been blocked by Incidentra" shown. |
| **TC-06** | XSS Detection | Navigate to http://localhost:5050/profile?name=<script>alert(document.cookie)</script>. Wait 3 seconds. | Incident: attack_type=XSS, severity=critical. Escalating block (Offense #1, ~24h). Tagged "attack" in Live Traffic. |
| **TC-07** | Path Traversal Detection | Navigate to http://localhost:5050/files?file=../../etc/passwd. Wait 3 seconds. | Incident: attack_type=PATH_TRAVERSAL, severity=high. Escalating block (Offense #1, ~1h). |
| **TC-08** | Brute Force Detection | Send 11+ POST requests to http://localhost:5050/login with varying passwords within 60 seconds. | BRUTE_FORCE incident created (severity=high). Escalating block (Offense #1, ~1h); subsequent requests receive HTTP 403. |
| **TC-09** | Command Injection Detection | Navigate to http://localhost:5050/cmd?cmd=;+cat+/etc/passwd. Wait 3 seconds. | Incident: attack_type=COMMAND_INJECTION, severity=critical. Escalating block (Offense #1, ~24h). MITRE T1059 recorded. |
| **TC-10** | Scanner Detection | Send GET to vuln-web with User-Agent: sqlmap/1.7. Wait 3 seconds. | Incident: attack_type=SCANNER, severity=medium. IP rate-limited (not permanently blocked). |
| **TC-11** | AI Explanation — Groq configured | Open incident from TC-04. Click "Generate AI Explanation". Wait 30 seconds. | AI panel shows Summary, Why It's Dangerous, Recommended Actions, MITRE ATT&CK. Model badge visible. |
| **TC-12** | AI Fallback — No API key | Remove GROQ_API_KEY from .env, restart backend. Simulate attack. Click generate. | Static explanation generated. model_used = "fallback-static" in DB. |
| **TC-13** | Detection Rules — Create | Go to Detection Rules. Click "+ Add Rule". Enter name, type, severity, regex pattern. Click Create. | Rule saved to DB. Appears in table with match_count=0. Redis rules_dirty flag set. |
| **TC-14** | Detection Rules — Toggle Off | Click active toggle on any rule to deactivate. | Rule is_active=false in DB. Engine skips rule on next 60s reload. |
| **TC-15** | Incident Status Update | Open incident. Change: new → investigating → resolved. | Status persisted to DB. resolved_at timestamp set. Badge colour updates. |
| **TC-16** | Investigation Notes | Open incident. Type a note. Click "+ Add". | Note saved to incident_notes with created_by from JWT token and current timestamp. |
| **TC-17** | Blocked IPs — Manual Block | Go to Blocked IPs. Click "+ Block IP". Enter IP: 10.0.0.99. Submit. | IP added to blocked_ips.json. Requests from that IP return HTTP 403. |
| **TC-18** | Blocked IPs — Unblock | Click delete (unblock) icon for any blocked IP. | IP removed from DB and blocked_ips.json. Subsequent requests processed normally. |
| **TC-19** | Export CSV | Go to Incidents. Click "Export CSV". | Browser downloads CSV with columns: ID, Date, Source IP, Attack Type, Severity, Status, Path, Country. |
| **TC-20** | Live Traffic Refresh | Open Live Traffic. Browse http://localhost:5050 in another tab. | New entries appear within 3-6 seconds. Normal requests tagged "normal". |
| **TC-21** | Settings — Groq Test | Go to Settings. Enter valid Groq API key. Click "Test Connection". | Success message shown. If key invalid, error message shown. |
| **TC-22** | Redis Down — Graceful Degradation | Stop Redis container. Trigger a detection event. | LogMonitor continues. DetectionEngine uses in-memory BruteForceTracker fallback. Incidents still saved to PostgreSQL. |
| **TC-23** | Escalating Block / Repeat Offender | Trigger ≥3 offenses from same IP (or lower threshold in Settings). | BlockedIP.is_repeat_offender=True; Repeat Offender badge visible in IP Management Blocked tab; block duration uses highest offense tier. |

Table 7. Functional Test Scenarios (TC-01 to TC-23)

Success Metrics

The success of the project is evaluated against the following performance parameters:

		- **Detection Latency:** Average time from an attack being logged to block action execution must not exceed 2 seconds under normal operating conditions.

		- **Detection Accuracy:** 100% detection rate for all signature-based attack categories defined within the active OWASP-aligned rule set (SQL Injection, XSS, Path Traversal, Command Injection, LFI/RFI, and Scanner), as validated against the vuln-web test application in the Docker Compose deployment environment. Detection accuracy for traffic patterns outside the defined rule set is not in scope for this evaluation.

		- **Data Persistence:** 100% data integrity — every detected incident must be successfully persisted in PostgreSQL for audit and compliance with Indonesia's PDP Law No. 27/2022.

		- **AI Explanation Availability:** An explanation must be generated for every incident, either via the Groq Cloud API four-model chain (primary) or the curated static fallback (secondary), resulting in a 0% explanation generation failure rate.

		- **System Stability:** No service crashes under normal operating conditions. Redis failure must be handled gracefully via the in-memory fallback without interrupting log monitoring or incident persistence.

# REFERENCES

- OWASP Foundation. (2021). OWASP Top Ten. Retrieved from [https://owasp.org/Top10/](https://owasp.org/Top10/)

- MITRE Corporation. (2024). MITRE ATT&CK Framework v14. Retrieved from [https://attack.mitre.org/](https://attack.mitre.org/)

- National Institute of Standards and Technology. (2018). NIST Cybersecurity Framework v1.1. Retrieved from [https://www.nist.gov/cyberframework](https://www.nist.gov/cyberframework)

- Flask Project. (2024). Flask Documentation (3.x). Retrieved from [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)

- PostgreSQL Global Development Group. (2024). PostgreSQL 15 Documentation. Retrieved from [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)

- React. (2024). React Documentation. Retrieved from [https://react.dev/](https://react.dev/)

- Groq Cloud. (2024). Groq API Documentation. Retrieved from [https://console.groq.com/docs](https://console.groq.com/docs)

- AbuseIPDB. (2024). AbuseIPDB API v2 Documentation. Retrieved from [https://www.abuseipdb.com/api](https://www.abuseipdb.com/api)

- IBM Security & Ponemon Institute. (2023). Cost of a Data Breach Report 2023. Retrieved from [https://www.ibm.com/security/data-breach](https://www.ibm.com/security/data-breach)

- Verizon. (2023). Data Breach Investigations Report. Retrieved from [https://www.verizon.com/business/resources/reports/dbir/](https://www.verizon.com/business/resources/reports/dbir/)

- Internet Engineering Task Force. (2015). JSON Web Token (JWT) — RFC 7519. Retrieved from [https://tools.ietf.org/html/rfc7519](https://tools.ietf.org/html/rfc7519)

- Jones, M., Bradley, J., & Sakimura, N. (2015). JSON Data Interchange Format — RFC 8259. Retrieved from [https://tools.ietf.org/html/rfc8259](https://tools.ietf.org/html/rfc8259)

2

2