Form2

Capstone Design System Analysis

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

	Incidentra	iv

PART 2	1

		**A.**	**EXISTING AND PROPOSED SYSTEM**	**1**

		1.	Existing Business Process	1

		2.	Proposed Business Process	3

		**B.**	**GLOBAL DESCRIPTION OF THE PRODUCT**	**5**

		1.	Main Functionality	5

		2.	User Characteristics	5

		3.	Constraints	6

		4.	Product Development Environment	7

		5.	Product Operational Environment	8

		**C.**	**REQUIREMENT ANALYSIS**	**10**

		1.	Interface	10

		2.	Functional Description	11

		3.	Data Requirement from user’s perspective	13

		4.	Functional Requirement	14

	**D. ALTERNATIVE SOLUTION**	**19**

	REFERENCES	23

**STATEMENT OF ORIGINALITY**

In my capacity as an active student at President University and as the author of the Capstone Design Project stated below:

Name			: 1. Hardin Irfan – 001202300066

			  2. Zaidan Mahfudz Azzam Saidi – 001202300144

Faculty			: Computer Science

I hereby declare that my Capstone Design Project entitled “**Incidentra**” is to the best of my knowledge and belief, an original piece of work based on sound academic principles. If there is any plagiarism detected in this final project, I am willing to be personally responsible for the consequences of these acts of plagiarism and will accept the sanctions against these acts in accordance with the rules and policies of President University.

I also declare that this work, either in whole or in part, has not been submitted to another university to obtain a degree.

Cikarang, February 2026

| Signer 1 | Signer 2 |
| --- | --- |
|  |  |
| Hardin Irfan – 001202300066 | Zaidan Mahfudz Azzam Saidi – 001202300144 |

### Incidentra

Approved:

| Abdul Ghofir S. Kom., M. Kom. | Rosalina, S. Kom., M. Kom. Program Head of Computer Science |
| --- | --- |

Prof. Dr. Ir. Wiranto Herry Utomo, M. Kom.

Dean of Faculty of Computer Science

## PART 2

**SYSTEM ANALYSIS**

-  EXISTING AND PROPOSED SYSTEM

### Existing Business Process

Currently, the process of monitoring and mitigating web application security for most SME clients is reactive and manual. When a web application is implemented, there is usually no active, real-time security monitoring layer in place.

If an attacker attempts a malicious action (such as SQL injection or brute force), the malicious payload is sent directly to the application server. The IT support team or system administrator usually only becomes aware of the attack after a significant event occurs, such as application failure, database leakage, or customer complaints. To investigate the incident, the IT administrator must manually log into the server, extract the raw Nginx/Apache log files, and read the complex HTTP status codes and payloads. Once the malicious IP address has been manually identified, administrators must manually configure firewall rules to block the attacker. This process is time-consuming, prone to human error, and requires specialized technical skills that SME owners generally do not possess.

**Existing Business Process Flow Diagram:**

### Proposed Business Process

The proposed business process introduces Incidentra, an intelligent Web-SOC platform that actively monitors and analyzes SME web application server logs in real-time, operating as a log-based security monitoring layer. This system shifts the security paradigm from reactive to proactive, operating 24/7 without requiring manual human intervention.

When a new log entry is written by the web server, the Incidentra Real-Time Log Monitor instantly parses and analyzes the entry using pattern matching and anomaly detection. If the traffic is identified as legitimate, no action is taken and the web application continues to serve the request normally. If malicious activity (such as XSS or SQLi) is detected in the log, the Response Manager immediately records the incident and executes automated defensive actions based on severity—ranging from flagging/rate limiting to escalating temporary IP blocks (never automatic permanent blocks; permanent blocks require manual admin action).

At the same time, the event is securely logged into the PostgreSQL database. A background task then sends this raw data to the AI platform (Groq Cloud LLM), which translates complex technical attack data into explanations that are easy for humans to understand. IT administrators or small and medium-sized business (SMB) owners will receive notifications and can open the SOC Dashboard to view a clear and actionable summary of the incident—including what happened, why it was dangerous, and the automatic steps the system took to secure the application.

**Proposed Business Process Flow Diagram:**

-  GLOBAL DESCRIPTION OF THE PRODUCT

### Main Functionality

The main functionality of the Incidentra product is to provide an Intelligent Web-SOC (Security Operations Center) Platform specifically designed for SME web applications. The core functionalities include:

- Real-Time Threat Detection: Automatically monitoring web server access logs in real-time to detect OWASP Top 10 attack patterns across eight categories: SQL Injection, XSS, Path Traversal, Command Injection, Brute Force, File Upload, Security Scanner, and LFI/RFI.

- Automated Response System: Executing immediate defensive actions based on threat severity—log and monitor (low), rate limiting (medium), escalating temporary IP blocks (high/critical)—with Repeat Offender flagging and configurable duration tiers via Settings.

- AI-Powered Incident Explanation: Utilizing the Groq Cloud LLM API to translate complex, raw technical attack logs into human-readable incident summaries and actionable recommendations.

- SOC Dashboard: Providing a centralized, user-friendly interface for IT administrators to manage incidents, view statistics, and track system status without needing advanced cybersecurity expertise.

- Threat Intelligence & Alerting **(Extended)**: Enhancing incident data with IP reputation scoring from AbuseIPDB and sending automated alerts via Email or Telegram.

### User Characteristics 

The primary users of this system are the IT Support/System Administrators who are responsible for managing and maintaining various SME client web applications.

| Users | Responsibility | Access rights | Education Levels | Skill Levels | Type of Training |
| --- | --- | --- | --- | --- | --- |
| IT Administrator / IT Support | Monitoring client web application security, reviewing incident logs, taking preventative actions, and ensuring system uptime. | Full Access (Admin Dashboard) | Diploma or Bachelor’s Degree in IT / Computer Science | Intermediate IT/Networking skills. Familiar with web hosting, but not necessarily an advanced cybersecurity expert. | Basic system walkthrough and dashboard user manual. |

### Constraints 

- **Internet Dependency:** The Incidentra platform requires a stable and continuous internet connection to function optimally. Two critical external services depend on this connection: the Groq Cloud LLM API, which is used to generate AI-powered incident explanations, and the AbuseIPDB API, which is used for real-time IP reputation assessment. Internet disruptions will not affect the core threat detection and blocking engine, as it operates entirely on local servers. However, the AI explanation generation and external threat intelligence features will be temporarily disabled until the connection is restored.

- **API Usage Limits:** The AI explanation and threat intelligence features are limited by the daily usage quotas set by their respective free APIs. The Groq Cloud API provides 14,400 requests per day at the free developer tier, and the AbuseIPDB API allows up to 15,000 IP lookups per day. For proof-of-concept demonstration environments, these quotas are more than sufficient. However, in production environments with high traffic volumes and frequent attack attempts, these limitations may require upgrading to a paid tier or implementing an aggressive local caching strategy using Redis to minimize repetitive API calls.

- **Hardware Resources:** Although Incidentra is specifically designed to be lightweight, the log monitor layer that continuously reads and parses web server access logs must be highly efficient to avoid consuming excessive system resources. At the minimum hardware specifications (2 CPU cores, 4GB RAM), the system is expected to function well for demonstration purposes and small-scale implementations. However, in a production SME environment generating high-volume log entries from concurrent requests, additional CPU and memory resources may be required to maintain real-time detection performance without impacting the overall server experience.

- **Detection Coverage:** In the current proof-of-concept implementation, the detection engine covers OWASP Top 10 vulnerabilities using rule-based pattern matching (regex). This approach is highly effective against known signature-based attacks, but may not detect new or zero-day attack techniques that do not match existing patterns. This limitation is acceptable within the academic scope of this project but represents an area for future improvement through machine learning-based anomaly detection methods.

- **Single-Tenant Architecture:** The current proof-of-concept implementation is designed to protect one SME web application per deployment instance. Multi-tenant support—managing multiple client web applications from a single Incidentra installation—is outside the scope of the current project and represents a potential direction for future development and commercialization.

### Product Development Environment

- **Hardware:** The system will be developed on two student development laptops, one per team member, operating in parallel during the 14-week development period. Each laptop must meet the minimum specifications of 2 CPU cores, 4GB of RAM, and 20GB of available storage space. The recommended specifications for optimal development performance are 4 CPU cores, 8GB RAM, and 50GB of available storage space. Code synchronization between team members will be handled entirely through the Git version control system hosted on GitHub, eliminating the need for shared physical hardware during the development phase.

- **Software:** The development environment uses a fully open-source software stack with zero licensing costs. The backend runtime environment requires Python 3.11 or above, with Flask as the web framework and SQLAlchemy as the ORM layer. Asynchronous task queues use Celery powered by Redis. The frontend is developed using Node.js as the JavaScript runtime with React.js as the user interface framework and Axios for HTTP communication. The database layer uses PostgreSQL. Development tools include Visual Studio Code as the primary IDE, Postman for API endpoint testing, OWASP ZAP and Burp Suite Community Edition for security and penetration testing, and Apache JMeter for load testing. All components can be containerized using Docker for consistency across all team members' machines.

- **Connectivity:** A standard broadband internet connection (minimum 10 Mbps) is required on each development machine for the following purposes: GitHub repository synchronization and collaborative pull request workflow; integration testing with external APIs including Groq Cloud LLM and AbuseIPDB; downloading open-source dependencies via pip for Python packages and npm for Node.js packages; and accessing cloud-based documentation and development resources throughout the project duration.

### Product Operational Environment

- **Hardware:** For the proof-of-concept demonstration, the system runs via Docker Compose on a single consolidated laptop. All six services run on localhost: vuln-web (port 5050), Incidentra backend (port 5000), React dashboard via Nginx (port 3000), PostgreSQL (port 5432), Redis (port 6379), and celery_worker. The deliberately vulnerable vuln-web Flask application serves as the monitored target, writing NCSA Combined Log Format access logs (with POST_DATA suffix) to a shared Docker volume. Simulated attack traffic is generated using OWASP ZAP, Nikto, manual payloads, or the built-in Simulate Attack feature, producing real access log entries that Incidentra monitors in real-time. This approach showcases log-based detection in a controlled environment rather than production-scale inline filtering.

- **Software:** The production operating environment runs on a Linux-based operating system, preferably Ubuntu or Debian, chosen for their stability, frequency of security updates, and extensive community support. The web server layer uses Nginx as a reverse proxy in front of the Flask application, which is served through Gunicorn as a WSGI server for handling production-level requests. The Python runtime environment requires Python 3.11 or above with all dependencies managed through a virtual environment. PostgreSQL serves as the primary database server, while Redis handles caching and task queue brokering. Celery worker processes run as background services managed by systemd to ensure automatic restart upon failure, guaranteeing 24/7 automatic system availability.

- **Connectivity:**  The production environment requires a high-speed, stable server internet connection for two distinct traffic flows: incoming web traffic from end users and potential attackers targeting the SME web application, and outgoing API requests from Incidentra to external services such as Groq Cloud and AbuseIPDB. A minimum dedicated bandwidth of 100 Mbps is recommended for the server connection. The system must be configured behind a firewall with only ports 80 (HTTP) and 443 (HTTPS) open to the public internet, while all internal service ports (5432 for PostgreSQL, 6379 for Redis, and 5000 for the Flask backend) are only accessible via localhost to prevent unauthorized external access.

-  REQUIREMENT ANALYSIS

### Interface

**Interface between the product and the user:**

**Hardware Interface:** The primary hardware interface for IT administrators is a standard personal computer (PC) or laptop. The SOC dashboard is designed with a responsive layout that adapts to various screen sizes, including tablets, so administrators can review and manage security incidents on mobile devices while away from their primary workstations. No special or proprietary hardware is required other than standard computing devices equipped with an internet connection and a modern web browser.

**Software Interface:** The SOC dashboard is a web-based application built with React.js, accessible through any modern web browser—including Google Chrome, Mozilla Firefox, Microsoft Edge, or Safari—without requiring browser plugins or local software installation. The dashboard communicates with the Flask backend API via RESTful HTTP/HTTPS requests formatted as JSON data. Near-real-time dashboard updates are achieved through configurable HTTP polling (3-second Live Traffic, 15-second Dashboard KPI refresh); WebSocket is listed as future work. The Flask backend API exposes fully documented RESTful endpoints for all dashboard operations, including incident retrieval and filtering (Ongoing vs All scope), incident status updates, IP Management (blocked, rate-limited, whitelisted), system statistics queries, and AI explanation retrieval.

**Communication Interface:** The system uses HTTP/HTTPS over TCP/IP as the primary communication protocol for all client-server interactions. The Incidentra log monitor layer reads and parses web server log entries in real-time, analyzing the logged request path, URL parameters, and user-agent content to detect attack patterns. Note: Incidentra operates post-request by reading log files written by the web server; it does not sit inline between the client and the web application. All external API communications—including Groq Cloud LLM and AbuseIPDB—use HTTPS with API key-based authentication to ensure secure data transmission. Internal service communications between Flask, PostgreSQL, and Redis use standard database connection protocols restricted to localhost only, ensuring that no internal service ports are exposed to the external network.

### Functional Description

Use-Case Diagram: 

Use-case Scenario 1: Managing Incidents and Viewing AI Explanations

- **Actor:** IT Administrator

- **Prerequisites:** The system has detected a critical threat, applied an escalating temporary block to the source IP, and logged the incident.

- **Key Success Scenario: **

- The administrator logs into the Incidentra SOC dashboard.

- The system displays a dashboard with a new “Critical” incident notification.

- The administrator clicks on the incident from the queue based on priority to view the details.

- The system displays the incident details (Date/Time, Source IP Address, Payload).

- The administrator clicks “View AI Explanation”.

- The system displays a human-readable summary generated by Groq Cloud AI, explaining the type of attack, why it is dangerous, and the automatic actions that have been taken.

- The administrator marks the incident status as “Resolved”.

- **Postcondition:** The incident is archived as resolved, and the admin is confident that the threat has been successfully mitigated.

**Use-case Scenario ****2****: Real-Time Threat Detection ****&**** Automated Response**

- **Actors**: Attacker / Internet Traffic (Driven by the System)

- **Prerequisites:*** *Incidentra Log Monitor is active and tailing the web server access log of the SME Web Application.

- **Key Success Scenario: **

- The attacker sends an HTTP request containing malicious payload (e.g., SQL injection script).

- The Incidentra Log Monitor reads the new log entry generated by the web server after processing the request. The Detection Engine scans the logged payload against active detection rules.

- The system identifies a match with an OWASP vulnerability (Critical Severity).

- The system applies an escalating temporary block to the source IP (writes to blocked_ips.json), so subsequent requests from that IP are rejected (HTTP 403 Forbidden) by vuln-web.

- The system logs incident details (IP, payload, timestamp) into the database.

- A background or click ‘generate’ button task triggers AI to generate a human-readable explanation based on the logged payload.

- **Post-Condition:** The incident is securely logged and the source IP is temporarily blocked with an escalating duration tier; the incident is ready for review by Admin. Permanent blocking remains a manual admin decision (e.g., after Repeat Offender review).

### Data Requirement from user’s perspective

- ERD (Entity Relationship Diagram)

- Data Dictionary. 

| Entity Table | Description | Relationships & Cardinality |
| --- | --- | --- |
| users | Stores IT Administrator credentials and role information for dashboard access. | 1 users manages 0 or Many (0..N) incidents. |
| detection_rules | Stores the pattern matching rules (e.g., Regex for SQLi, XSS) used by the detection engine. | 1 detection_rules triggers 0 or Many (0..N) incidents. |
| incidents | The core table storing all detected threats, their severity, and current status (New, Investigating, Resolved). | 1 incidents generates 0 or Many (0..N) incident_logs. 1 incidents has exactly 1 (1..1) incident_explanations. 1 incidents contains 0 or Many (0..N) incident_notes. 1 or Many (1..N) incidents results in 0 or 1 (0..1) blocked_ips. |
| incident_logs | Tracks the automated actions taken by the system (e.g., rate limiting, IP dropping) for a specific incident. | Many (0..N) incident_logs belong to 1 incidents. |
| incident_explanations | Stores the human-readable summary generated by the Groq Cloud AI to avoid redundant API calls. | 1 incident_explanations belongs to 1 incidents. |
| incident_notes | Stores manual notes or findings added by the IT Administrator during the investigation process. | Many (0..N) incident_notes belong to 1 incidents. |
| blocked_ips | Maintains blocked, rate-limited enforcement state and whitelist of trusted IP addresses (includes is_repeat_offender, is_whitelist). | 1 or Many (1..N) incidents results in 0 or 1 (0..1) blocked_ips. |

### Functional Requirement

- Context Diagram

The Context Diagram (Level 0 DFD) shows the Incidentra system as a single central process interacting with external entities.

- Activity Diagram and Data Flow Diagram

**Activity Diagram: **

This project involves two main Activity Diagrams representing the system-driven process and the user-driven process.

**1. Activity Diagram: Real-Time Threat Detection ****&**** Automated Response** *(Shows the system workflow when processing incoming traffic and mitigating threats)*

**2. Activity Diagram: Manage Incident ****&**** View AI Explanation** *(Shows the workflow when the IT Administrator interacts with the SOC Dashboard)*

- **Data Flow Diagram (Level 1 DFD): **

This diagram breaks down the main system into specific sub-processes and shows how data moves between them and the data stores.

- **Description**** of the Process inside the Activity Diagram and Data Flow Diagram:**

- Threat Detection & Response Process (System-driven)

- **Log Ingestion ****&**** Detection (P1):**** **New log entries from Nginx/Apache are continuously read by the Incidentra log monitor using a real-time tail mechanism. The system parses each log entry and matches the request payload against stored detection rules looking for SQLi, XSS, or Brute-force patterns.

- **Automated Response (P2):** If the log entry is identified as safe traffic, no automated action is triggered and the web application continues to serve requests normally. If the entry matches an OWASP threat pattern, the system executes a severity-appropriate automated response: rate limiting (medium) or escalating temporary IP block (high/critical), writing enforcement data to shared JSON files so subsequent requests from that IP are rejected by vuln-web (HTTP 403) or rate-limited (HTTP 429).

- **Logging ****&**** AI Processing (P3 ****&**** P4):** Blocked threats are securely logged into the database. A background task can immediately send this raw data to the Groq Cloud API, which returns a human-readable summary that is saved back to the incident record in the database. This update subsequently triggers an alert notification to the admin.

- Incident Management Process (User-driven) 

- **Dashboard Review (P5):** The IT Administrator accesses the React-based SOC dashboard. The dashboard queries the database to display system metrics and the priority-based incident queue. 

- **Investigation ****&**** Resolution:** The Admin selects a specific incident to view its technical details (Source IP, raw payload). The Admin then views the AI-generated explanation to easily understand the threat context without needing advanced security expertise. Finally, the Admin updates the incident status to "Resolved" to close the investigation loop.

D. ALTERNATIVE SOLUTION

- **Alternative Solution 1: Manual Log Analysis** This approach relies entirely on IT administrators manually reviewing raw Nginx or Apache web server logs using command line tools and manually configuring firewall rules. While there are no software licensing costs, this method is highly inefficient, reactive, and unable to provide real-time protection.

**Advantages:** Zero cost, no software installation required, full administrator control.

**Disadvantages:** Cannot operate 24/7 because it requires constant human monitoring. Detection is delayed by hours or even days, making it reactive rather than proactive. Prone to human error and fatigue. No systematic incident documentation or audit trail. We rejected this solution because it fundamentally did not meet the real-time response requirements.

- **Alternative Solution 2: Commercial SIEM/SOC Platforms (e.g., Splunk, QRadar)** This is an enterprise-level security information and event management platform that uses machine learning and big data processing to detect advanced threats across infrastructure. While highly effective, this platform is completely incompatible with the budgets and resource constraints of small and medium-sized enterprises (SMEs).

**Advantages:** Enterprise-level detection capabilities, able to handle millions of events per second, professional dashboards, vendor support, and security strategies that are proven in practice.

**Disadvantages:** Annual licensing fees alone range from $50,000 to over $500,000. Requires a powerful dedicated server with terabyte storage. Implementation takes 3–6 months with certified specialists. Ongoing operations require dedicated security analysts. The total cost of ownership is completely out of line with SME budgets. We rejected this solution because the financial barriers make it unaffordable for the target users of this project.

- **Alternative Solution 3: Intelligent Web-SOC Platform (Incidentra) - Proposed Solution** This hybrid architecture combines fast log-based rule detection for near-real-time automated responses with AI-powered explainability for human understanding, integrated into a complete SOC workflow platform with incident management and professional dashboards — all without license fees.

**Strengths:** Provides real-time automated detection and response unlike Solution 1. Overcomes the prohibitive cost barrier of Solution 2 by using a 100% open-source stack. Designed specifically for low-spec hardware and SME-scale environments. Uses AI for transparency and explainability, translating technical events into plain-language summaries accessible to non-security-specialist administrators.

**Why This Solution Was Selected:** Incidentra is the only solution that satisfies all critical requirements simultaneously: zero software licensing cost, real-time automated threat response, AI-powered human-readable explanations, complete incident lifecycle management, and operation on minimal hardware. It is the only option that bridges the gap between the inadequacy of manual analysis and the inaccessibility of commercial platforms.

REFERENCES

**Detection Methodology**

Our detection methodology is grounded in established industry standards. We use the OWASP Foundation's Top 10 ([https://owasp.org/Top10/](https://owasp.org/Top10/)) and the MITRE ATT&CK framework ([https://attack.mitre.org/](https://attack.mitre.org/)) as a baseline for identifying CVEs and mapping detected attacks to real-world adversary techniques. Our pattern-matching approach draws from Clarke's influential work on SQL injection protection and the comprehensive web application security manual by Stuttard and Pinto. For incident response procedures, we adhere to the National Institute of Standards and Technology's Cybersecurity Framework ([https://www.nist.gov/cyberframework](https://www.nist.gov/cyberframework)).

**Regulatory Compliance and Data Protection**

The platform is compliant with Indonesia's Personal Data Protection Law No. 27 of 2022 ([https://peraturan.go.id/id/uu-no-27-tahun-2022](https://peraturan.go.id/id/uu-no-27-tahun-2022)) through automated logging and audit trails. This simplifies the process for teams to file the required documentation for security controls and breach reporting, eliminating the need to maintain such records manually.

**Technology and Development Framework**

Our stack is built on well-documented, open-source software. The backend is written in Python 3.11+ ([https://docs.python.org/3/](https://docs.python.org/3/)) using the Flask web framework ([https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)). Data persistence is managed by PostgreSQL 15.0 ([https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)), and the frontend is built with React ([https://react.dev/](https://react.dev/)). All components are open-source with no associated licensing costs.

**Artificial Intelligence and Natural Language Processing**

We integrate Groq Cloud ([https://console.groq.com/docs](https://console.groq.com/docs)) for fast LLM inference, enabling real-time, human-readable incident summaries without the latency typically associated with AI processing. Our approach is informed by Vaswani et al.'s foundational work on attention mechanisms and Lewis et al.'s research on retrieval-augmented generation, which together guide how we generate threat intelligence explanations through efficient asynchronous workflows.

**Security and Threat Intelligence Research**

We leverage the AbuseIPDB IP reputation database ([https://www.abuseipdb.com/](https://www.abuseipdb.com/)) for real-time threat intelligence. Our hybrid detection approach — combining rule-based pattern matching with statistical anomaly detection — is supported by research from Sharafaldin et al. on intrusion detection datasets and Sommer & Paxson's study on the application of machine learning to network security.

**SME Cybersecurity Statistics and Industry Research**

The economic rationale behind our platform is supported by several industry sources. The IBM Security and Ponemon Institute's 2023 Cost of a Data Breach Report ([https://www.ibm.com/security/data-breach](https://www.ibm.com/security/data-breach)) quantifies the financial impact of breaches on resource-constrained businesses. Cybersecurity Ventures reports that 60% of small companies cease operations within six months of a cyberattack ([https://cybersecurityventures.com/60-percent-of-small-companies-close-within-6-months-of-being-hacked/](https://cybersecurityventures.com/60-percent-of-small-companies-close-within-6-months-of-being-hacked/)). The European Union Agency for Cybersecurity (ENISA) report on "Cybersecurity for SMEs" ([https://www.enisa.europa.eu/sites/default/files/publications/ENISA%20Report%20-%20Cybersecurity%20for%20SMES%20Challenges%20and%20Recommendations.pdf](https://www.enisa.europa.eu/sites/default/files/publications/ENISA%20Report%20-%20Cybersecurity%20for%20SMES%20Challenges%20and%20Recommendations.pdf)) highlights the limited effectiveness of most SMEs in mitigating cyber threats. Additionally, the Verizon 2023 Data Breach Investigations Report ([https://www.verizon.com/business/resources/reports/dbir/](https://www.verizon.com/business/resources/reports/dbir/)) documents the attack vectors that informed our detection rule design.

**Enterprise Security Solutions Market Analysis**

Commercial security solutions remain financially out of reach for most SMEs. Splunk, for example, is priced between $5,000 and $50,000 per year ([https://www.splunk.com/en_us/products/pricing.html](https://www.splunk.com/en_us/products/pricing.html)). The European Commission's 2023 Digital Economy and Society Index ([https://digital-strategy.ec.europa.eu/en/policies/desi](https://digital-strategy.ec.europa.eu/en/policies/desi)) and McKinsey's AI research further highlight the resource constraints and skills shortages that our automated, user-friendly platform is designed to address.

**Testing and Quality Assurance**

We validate our detection rules and response mechanisms using OWASP Zed Attack Proxy ([https://www.zaproxy.org/](https://www.zaproxy.org/)) and PortSwigger's Burp Suite ([https://portswigger.net/burp/documentation](https://portswigger.net/burp/documentation)). These tools simulate real-world attack scenarios to ensure all functionality is thoroughly tested before deployment to production.

2

2