Form1

Capstone Design Proposal

**Incidentra**

“Intelligent Web-SOC Platform with Automated Incident Response”

**GROUP MEMBER:**

| **No.** | **Student Name** | **Student ID** | **Study Program** |
| --- | --- | --- | --- |
| 1. | Hardin Irfan | 001202300066 | Information Technology |
| 2. | Zaidan Mahfudz Azzam Saidi | 001202300144 |  |

Advisor:  Mr. Abdul Ghofir S. Kom., M. Kom.

Submitted for

Capstone Design Project

to Faculty of Computer Science

President University

**TABLE OF CONTENT**

Contents

	STATEMENT OF ORIGINALITY	iii

	Incidentra	iv

	PART 1	1

	PROPOSAL	1

	A. PROBLEM FORMULATION	1

	1. Background of the Problem	1

	2. Problem from a Customer Perspective	2

	3. Problem Statement	3

	4. Objective	4

	4.1 Primary Objectives:	4

	4.2 Extended Features (Secondary Objectives - If Time Permits)	7

	B. PROBLEM ANALYSIS	9

	Aspect 1: Economic (Cost Efficiency)	9

	Aspect 2: Performance (Speed & Efficiency)	10

	Aspect 3: Usability (Interface & Accessibility)	11

	C. SOLUTION SELECTION & SCENARIOS	13

	Alternative Solution 1: Manual Log Analysis	13

	Alternative Solution 2: Commercial SIEM/SOC Platforms (e.g., Splunk, QRadar)	13

	Alternative Solution 3: Intelligent Web-SOC Platform (SELECTED)	14

	Solution Selection	15

	D. DEVELOPMENT EFFORT	17

	1. Manpower Details and Roles	17

	2. Technology Stack (Backend)	18

	3. Technology Stack (Frontend)	19

	4. Technology Stack (AI & Intelligence)	20

	5.  Technology Stack (Development & Testing)	21

	6.  Test Equipment and Validation Strategy	22

	7. Development Phase Cost (14 Weeks - Capstone Project)	23

	8. Timelines	24

	REFERENCES	25

# STATEMENT OF ORIGINALITY

In my capacity as an active student at President University and as the author of the Capstone Design Project stated below:

Name			: 1. Hardin Irfan – 001202300066

			  2. Zaidan Mahfudz Azzam Saidi – 001202300144

Faculty			: Computer Science

I hereby declare that my Capstone Design Project entitled “**Incidentra**” is to the best of my knowledge and belief, an original piece of work based on sound academic principles. If there is any plagiarism detected in this final project, I am willing to be personally responsible for the consequences of these acts of plagiarism and will accept the sanctions against these acts in accordance with the rules and policies of President University.

I also declare that this work, either in whole or in part, has not been submitted to another university to obtain a degree.

Cikarang, Januari 2026

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

## PART 1

## PROPOSAL

## A. PROBLEM FORMULATION

1. Background of the Problem

Small and medium-sized enterprises (SMEs) face critical cybersecurity challenges in today's digital landscape. Web applications serve as the primary business interface for most SMEs, making them attractive targets for various cyberattacks, including SQL injection, cross-site scripting, brute-force authentication attempts, and distributed denial-of-service (DDoS) attacks. Unlike large enterprises, SMEs generally lack the financial resources and technical expertise to implement a comprehensive Security Operations Center (SOC). Traditional enterprise-level security solutions such as SIEM platforms require significant infrastructure investments, specialized expertise, and ongoing operational costs that are beyond the reach of SME budgets.

The latest cybersecurity report shows that small and medium-sized enterprises (SMEs) are more vulnerable to cyberattacks, with many experiencing significant operational disruptions or even closing down after a security breach. However, most SMEs report low confidence in their ability to effectively mitigate cyber risks. The main challenge is the gap between detection time and response time. Manual log analysis cannot keep up with high web traffic volumes, and by the time suspicious activity is identified through periodic log reviews, damage may already have been done.

Current enterprise solutions pose several obstacles for MSMEs. Commercial platforms such as Splunk require significant annual licensing fees, making them financially unattainable for small businesses. Open source alternatives such as ELK Stack, while free in terms of licensing, require substantial infrastructure resources. A typical ELK implementation requires large RAM allocations and dedicated servers to function effectively. Furthermore, these solutions require specialized knowledge for configuration and operation, which SME administrators generally do not possess. 

SMEs require automated, lightweight, and intelligent security solutions that provide real-time threat detection without manual intervention, automated incident response to minimize damage, clear and actionable insights for non-security specialists, and minimal infrastructure requirements with zero licensing costs. This is the gap that Incidentra aims to address through its log-based monitoring proof-of-concept implementation.

### 2. Problem from a Customer Perspective

From the perspective of small and medium-sized Enterprise (SME) owners and IT administrators, several critical challenges arise when attempting to implement effective web security monitoring. First, there is the issue of limited resources. SME owners typically operate their web applications on entry-level servers or lower-end cloud instances due to budget constraints. They cannot afford to implement security monitoring tools that consume significant CPU, memory, and storage resources. Any security solution must operate efficiently within these constraints without impacting application performance or requiring costly hardware upgrades.

Second, there is a significant knowledge gap. Most SME IT administrators are generalists, not cybersecurity specialists. They understand basic server administration and web hosting, but reading raw server logs filled with HTTP status codes, IP addresses, and incomprehensible error messages is not only time-consuming but also requires specialized knowledge that they do not possess. What they need is not just a problem detector, but a system that translates technical security events into clear, business-relevant explanations. They need answers to fundamental questions such as “What happened?”, “Why is this dangerous?”, and “What has been done to address it?”

Third, operational speed is crucial. Manual security monitoring is essentially reactive. An attacker attempting an SQL injection attack at 2:00 a.m. will not be detected until the next business day when the logs are checked. By that time, sensitive customer data may have already been stolen or the database compromised. SMEs need proactive, automated protection that responds to threats in real time, operating 24 hours a day, 7 days a week, without requiring constant human supervision. The system must function as a digital security guard that never sleeps.

Finally, there are compliance and accountability requirements. Even small businesses must maintain security incident logs for compliance purposes, whether for GDPR in Europe or the Personal Data Protection Law in Indonesia. They also need proper documentation for cyber insurance claims. However, maintaining these logs manually is burdensome and prone to error. They need a system that automatically documents all security events, response actions, and investigation results in an auditable format that meets regulatory requirements.

3. Problem Statement

The core technical question addressed by our project is: How can we design and implement a proof-of-concept Web-SOC platform, specifically Incidentra, that demonstrates enterprise-grade threat detection capabilities and automated incident response appropriate for an SME environment? 

**This demonstration platform must showcase: **

- Zero software licensing costs through the use of a 100% open-source stack 

- Minimal hardware requirements allowing deployment on standard development laptops 

- Real-time detection and response capabilities - Human-readable security insights powered by AI explainability 

- Complete incident lifecycle management covering detection through investigation to resolution 

- Professional SOC workflow capabilities including ticketing and basic reporting

The system must be able to detect threats effectively while maintaining reasonable application performance, achieving acceptable accuracy in threat identification, and providing ease of implementation and operation for non-security specialists. This is challenging because traditional approaches tend to sacrifice performance for intelligence or vice versa. Incidentra aims to demonstrate a balanced approach that is suitable for academic evaluation and future development.

4. Objective

Our project aims to develop a **proof-of-concept** Web-SOC platform with specific technical objectives divided into core requirements (must-have for successful capstone completion) and extended features (if time permits).

4.1 Primary Objectives:

These represent the minimum viable functionality required for successful capstone project completion:

4.1.1 Real-Time Threat Detection Engine 

- **Scope:** Implement pattern-based detection for OWASP Top 10 vulnerabilities: 

- SQL Injection (SQLi) detection using regex patterns 

- Cross-Site Scripting (XSS) detection 

- Brute-force authentication attempt detection (simple threshold-based) 

- Suspicious user-agent patterns (known automated scanners)

- **Technical Goals:**

- Demonstrate functional detection of simulated attacks in controlled test environment 

- Process incoming web traffic logs and identify malicious patterns 

- Log detected threats with relevant context (timestamp, source IP, attack type, payload)

- Success Criteria: Successfully detect and log at least 3 different attack types during demonstration using OWASP ZAP or manual attack simulation.

4.1.2 Automated Response System

- **Scope:** Implement graduated response mechanisms: 

- **Level 1 (Low Severity):** Log and monitor 

- **Level 2 (Medium Severity):** Log + Warning flag + Rate limiting 

- **Level 3 (High Severity):** Log + HTTP 403 denial + escalating temporary IP block (default: 1h → 24h → 7d per offense tier)

- **Level 4 (Critical Severity):** Log + escalating temporary IP block (default: 24h → 7d → 30d per offense tier) + Admin notification; Repeat Offender flag when threshold reached; permanent block reserved for manual admin action only

- **Technical Goals:**

- Demonstrate automated decision-making based on threat severity 

- Show IP blocking capability (can be simulated in demo environment) 

- Record all automated actions with justification

- **Success Criteria:** Demonstrate that system can automatically categorize threats and take appropriate actions during live demo.

4.1.3 Incident Management Interface

- **Scope:** Implement PostgreSQL-backed incident tracking workflow:

- Automated incident record creation when threat detected

- Persistent storage of all incident data (attack details, timestamps, source IPs, payloads)

- Priority-based incident queue: Critical → High → Medium → Low

- Status management: New → Investigating → Resolved

- Incident listing with filtering by severity, status, and time range

- Individual incident detail view with complete audit trail

- Search functionality for historical incident analysis

- Response time tracking (time from detection to resolution)

- **Database Schema (Core Tables):**

- `incidents` - Main incident records with priority and timestamps

- `incident_logs` - Automated action logs

- `incident_explanations` - AI-generated explanations

- `blocked_ips` - IP blacklist/whitelist management

- `detection_rules` - Pattern matching rules

- `incident_notes`

- `users` - Admin and analyst accounts

- **Technical Goals:**

- Utilize PostgreSQL's JSON support for flexible payload storage

- Implement proper indexing for fast incident retrieval

- Maintain complete audit trail of all system actions

- Track response times for performance metrics

- Support historical analysis and trend reporting

- Store AI explanations persistently to avoid redundant API calls

- **Success Criteria:**

- All detected incidents successfully persisted to database

- Functional incident query and filtering during demo

- Priority queue displays incidents in correct order

- Database maintains data integrity throughout testing period

- Demonstrate incident history and response time metrics

4.1.4 AI-Powered Explanation Feature

- **Scope:** Integrate Groq Cloud LLM API (Free Tier) for generating human-readable incident explanations:

- Plain-language summary of what attack was detected

- Basic explanation of why it's dangerous

- Simple recommended actions

- Reference to MITRE ATT&CK techniques where applicable

- **Technical Goals:**

- Utilize Groq Cloud free tier (14,400 requests/day - more than sufficient for demo)

- Generate explanations asynchronously (not blocking detection)

- Provide both technical and non-technical explanation modes

- Display AI-generated insights in incident detail view

- Store AI-generated explanations in PostgreSQL database for persistent access

- **Database Integration:**

- Each incident explanation stored in `incident_explanations` table

- Links to parent incident record via foreign key

- Caches explanations to avoid redundant API calls for similar attacks

- **Success Criteria:**

- Successfully integrate Groq API and generate explanations for 100% of detected incidents

- Minimum 70% of explanations should be relevant and understandable to non-technical audience

- Demonstrate API usage during live demo (show real-time explanation generation)

4.1.5 Comprehensive SOC Dashboard

- **Scope:** Web-based monitoring interface displaying:

- List of recent incidents with severity indicators

- Statistics (total incidents, incidents by type, incidents by severity)

- Incident timeline visualization

- System status indicator (operational/detecting/error)

- **Technical Goals:**

- React-based responsive dashboard

- Real-time or near-real-time updates (polling acceptable, WebSocket optional)

- Clean, professional UI suitable for demonstration

- Success Criteria: Functional dashboard that successfully displays incident data and updates when new attacks are simulated during demo.

4.2 Extended Features (Secondary Objectives - If Time Permits)

These features enhance the project but are **NOT required** for successful completion:

4.2.1 Enhanced Threat Intelligence & Additional Features

- **External API Integration (All Free Tier):**

- **AbuseIPDB API Integration **

- IP reputation scoring (15,000 queries/day free)

- Automatic lookup of attacking IP addresses

- Display confidence scores and abuse reports

- Cache results in Redis to minimize API calls

- Enhance incident context with external threat intel

- **Enhanced Alerting:**

- Email notifications for critical incidents

- Telegram bot integration (optional)

- Configurable alert thresholds to prevent notification fatigue

- Alert aggregation for related incidents

- **Advanced Visualizations:**

- Geographic attack source mapping (country-level)

- Attack timeline with trend analysis

- Top attacking IPs and attack types charts

- Threat actor profiling based on behavioral patterns

- **Enhanced Analytics:**

- Historical trend analysis and reporting

- Export incident reports (PDF/CSV)

- Advanced statistical metrics (MTTR - Mean Time to Resolution)

- SLA-style tracking with configurable time thresholds

- Advanced anomaly detection using statistical methods

**Important Note:** These features leverage free-tier APIs and open-source libraries. They will be attempted only if core requirements (4.1.1-4.1.5) are completed ahead of schedule. Their absence will NOT affect project evaluation, but their presence demonstrates advanced integration capabilities.

**SLA Note:** If implemented as extended feature, will use simplified approach with demo-friendly pre-populated data rather than real-time breach alerting system.

## B. PROBLEM ANALYSIS

To ensure the system is feasible for SME environments with limited resources, we analyze three critical technical dimensions that constrain our design choices.

Aspect 1: Economic (Cost Efficiency) 	

The main economic challenge is achieving zero-dollar software licensing costs while operating on low-spec hardware such as entry-level servers, basic VPS instances, or even developer laptops. This challenge is not just about saving money, but also about making this solution accessible to businesses that cannot afford enterprise-grade security infrastructure. Existing enterprise solutions pose significant economic barriers. Commercial platforms such as Splunk require expensive licensing fees, ranging from thousands to tens of thousands of dollars per year depending on data volume. Even open-source alternatives such as the ELK Stack, while free in terms of licensing, require high memory requirements for Elasticsearch to function properly. They also require specialized infrastructure and storage systems, as well as specialized training and certification for system administrators. These costs are too high for most SMEs and are not suitable for academic proof-of-concept projects.

Our solution uses a 100% open-source technology stack that eliminates all licensing costs while maintaining professional-grade capabilities. We chose Flask as our backend framework because it is lightweight, well-documented, and has a minimal resource footprint. For the frontend, we chose React.js because of its modern component-based architecture and superior developer ecosystem. PostgreSQL is used as our database because it is robust, ACID-compliant, and efficient for demo-scale data volumes while remaining completely free. For AI integration, we used Groq Cloud's free developer tier, which provides a large request quota, not only for end-project use but also for potential small-scale deployment in the future. The entire system can be implemented on a standard Linux environment without requiring proprietary infrastructure, making it ideal for academic demonstrations and potential real-world adoption by organizations with limited resources.

In terms of resource requirements for our demonstration environment, the minimum specifications are only 2 CPU cores, 4 GB of RAM, and 20 GB of storage, so it can be implemented on a standard student laptop. The recommended specifications for optimal demonstration performance are 4 CPU cores, 8 GB of RAM, and 50 GB of storage. This lightweight architecture ensures that the project remains accessible for academic evaluation while proving that the concept can operate efficiently within the resource constraints commonly found in small and medium-sized enterprise (SME) environments. The cost-free approach covers not only software licenses, but also all development tools, testing frameworks, and API integrations, demonstrating that effective cybersecurity solutions do not require large financial investments.

Aspect 2: Performance (Speed & Efficiency) 

The performance constraint is particularly important because security systems operate in the critical path of web traffic. Any latency introduced by security checks can potentially impact user experience. For our proof-of-concept demonstration, detection and response should occur efficiently to be viable for practical deployment scenarios.

 The technical challenge arises from the fact that Large Language Models introduce significant latency. API calls to services like GPT or Groq typically require several seconds for response, while local LLM inference can take multiple seconds on CPU. This latency is incompatible with real-time traffic filtering where prompt decisions are necessary. 

To address these challenges, we implemented a hybrid architecture with a two-stage pipeline that separates real-time detection from post-incident analysis. Our architecture splits the workload into two stages. The first handles detection in real-time: as new Nginx/Apache log entries are written to disk, the log monitor parses them immediately and runs them through our rule-based regex patterns to catch known attack signatures. Alongside this, a lightweight threshold-based check flags any unusual request volumes. Once a risk score is calculated, the response manager takes action — whether that's logging the event, throttling the source, or pushing a block rule to the firewall — and stores everything in PostgreSQL with full context (timestamp, IP, attack type, payload).

The second stage runs in the background and has no impact on the monitored application. After an incident is written to the database, a worker process picks it up and sends the relevant context to the Groq Cloud LLM API. A few seconds later, the human-readable explanation comes back and gets saved to the incident record. At this point, if alerting is configured, a notification goes out to the administrator. The explanation is then immediately visible on the dashboard.

The second stage is post-detection analysis, which runs asynchronously and therefore does not affect the performance of the monitored application. Once detected events are stored in the database, a background worker process retrieves incidents that require explanation. The system sends the incident context to the Groq Cloud LLM API, which may take a few seconds to generate a response. This results in a human-readable explanation that covers what happened, why it was dangerous, and what actions should be taken. The explanation is then stored back in the database, updating the incident record. If configured, the system can trigger an alert notification at this stage. Finally, the analysis becomes instantly available on the dashboard for administrator review.

The main design principle here is that AI provides explainability and insight, not real-time detection. Rule-based log parsing and pattern matching provide the speed necessary for near-instant detection. Our demonstration objectives include showing that detection occurs within seconds of an attack being logged during live testing, that AI-generated explanations appear within a reasonable time after detection, that the system can handle simultaneous simulated attacks without performance degradation, and that the observable impact on test application performance is minimal. The focus is on proving that the architectural concept works effectively in a demonstration environment, with the understanding that production implementation will involve additional optimization and adjustments based on actual traffic patterns and infrastructure capabilities.

Aspect 3: Usability (Interface & Accessibility)

The usability constraint recognizes that SME system administrators are typically IT generalists rather than cybersecurity specialists. They may understand basic networking and web hosting concepts, but not advanced security concepts like MITRE ATT&CK techniques, CVE identifiers, or threat intelligence feeds. 

When we analyze the typical SME administrator user persona, we find someone who might be a small business owner, web developer, or general IT support staff. Their skills include basic server administration, web hosting, and database management. However, their security knowledge is limited. They know about firewalls and SSL certificates, but not necessarily about OWASP Top 10 vulnerabilities. Their time availability is constrained because security is only a part-time focus among many other primary duties. What they need are clear answers to fundamental questions: "Am I under attack?", "What should I do?", and "Is it handled?"

Traditional SOC dashboards display raw technical information such as error logs with HTTP status codes, IP addresses, timestamps, and user agent strings. When non-security users see this, they think "What does this mean? Is it bad? What should I do?" This creates confusion and inaction. 

We designed the interface to prioritize clear explanations. Instead of showing raw error messages, Incidentra transforms technical events into human-readable narratives. For example, instead of displaying a cryptic log entry, the dashboard shows a clear incident card with a critical severity indicator. It explains in plain language that an attacker from a specific country attempted to hack the login page using SQL injection, a technique designed to steal database contents. It clearly states what actions were taken, such as the attack being blocked immediately with HTTP 403 Forbidden response and the attacker's IP receiving an escalating temporary block (for example, ~24 hours for a first critical offense). Most importantly, it reassures the administrator that their system is safe and no data was compromised. 

Key usability features include a traffic light status system where green means all systems normal, yellow indicates suspicious activity detected and under monitoring, and red shows an active attack that has been blocked and requires review. We provide plain-language explanations with no jargon in the primary interface, while technical details remain available on-demand through collapsible sections. The AI generates summaries for each incident automatically. 

The interface provides actionable recommendations that clearly answer "What should I do next?" with one-click actions for common tasks like closing tickets, whitelisting IP addresses, or escalating incidents. Visual intelligence features include geographic attack maps showing country flags, timeline visualizations of attack patterns over time, trend graphs indicating decreasing or increasing threat levels, and color-coded severity indicators. 

## C. SOLUTION SELECTION & SCENARIOS

Alternative Solution 1: Manual Log Analysis 

The first alternative we considered is manual log analysis where system administrators manually review web server logs using command-line tools or log viewers. When suspicious activity is identified, administrators manually configure firewall rules or server blocks.

A typical implementation would involve daily manual workflows where an administrator runs commands like tail to follow access logs, grep to search for specific patterns like failed login attempts, and manually executes firewall commands to block suspicious IP addresses. The advantage of this approach is that it has zero development cost, uses existing operating system tools, provides full administrator control, and requires no additional software installation. 

However, the disadvantages are significant. This approach is highly inefficient and time-consuming. It requires constant human monitoring which is not scalable to high traffic volumes. Detection is delayed by hours or days making it reactive rather than proactive. There is no real-time response capability to active attacks. The approach is prone to human error and fatigue. There is no systematic incident documentation or audit trail. Most critically, it cannot operate 24 hours a day, 7 days a week because humans need sleep. We rejected this solution because it does not meet our real-time response requirement.

Alternative Solution 2: Commercial SIEM/SOC Platforms (e.g., Splunk, QRadar)

The second alternative is using enterprise-level SIEM platforms like Splunk Enterprise Security, IBM QRadar, or ArcSight. These are the heavy artillery of cybersecurity. They collect logs from all systems, use machine learning to spot anomalies, and detect sophisticated attack patterns across your entire infrastructure.

The advantages are impressive. These platforms handle millions of security events per second, provide professional dashboards with executive-level reporting, and integrate with virtually any security tool. You get vendor support, regular updates, and battle-tested security strategies refined over decades by Fortune 500 deployments.

However, the costs are prohibitive for SMEs. Annual licensing alone ranges from $50,000 to over $500,000, plus you need powerful servers with terabytes of storage. Implementation takes 3-6 months with certified specialists. Ongoing operation requires dedicated security analysts with salaries in the $80,000-$150,000 range. Most features are overkill for small business needs.

We rejected this solution because the total cost of ownership would consume resources that SMEs need for actually running their business.

Alternative Solution 3: Intelligent Web-SOC Platform (SELECTED) 

The third alternative, which we selected, is a hybrid architecture combining fast rule-based detection for real-time response with AI-powered explainability for human understanding, integrated into a complete SOC workflow platform with incident management, SLA tracking, and professional dashboards.

This solution wins because it resolves the fundamental engineering challenges. It provides real-time detection and response unlike Solution 1. It overcomes the "black box" problem of Solution 2 by using AI for transparency and explainability. The system is designed for low cost by leveraging lightweight open-source frameworks instead of heavy enterprise stacks. It provides SOC-like monitoring capabilities and automated response suitable for SME-scale environments, focusing on both fast rule-based detection and comprehensive explainability. 

When we compare all three solutions across key requirements, we find that manual analysis provides no real-time detection, while Incidentra monitors web server logs in real-time and executes automated responses through firewall commands, rather than acting as an inline proxy. Manual analysis lacks systematic threat intelligence integration, while Incidentra can integrate external threat intelligence sources. For human-readable explanations, only Incidentra provides AI-generated insights. For incident tracking and management, only Incidentra offers comprehensive capabilities. All three solutions can maintain zero cost for software, but only Incidentra is designed for typical SME traffic volumes with efficient handling of concurrent requests on minimal hardware.

### Solution Selection 

After evaluating alternatives, we selected **Alternative Solution 3: Intelligent Web-SOC Platform **as our implementation approach for this **proof-of-concept capstone project**

**Why the Other Solutions Don't Work**

**Manual Log Analysis (Solution 1)** fails the most fundamental requirement: real-time protection. Security threats don't wait for business hours. An attack at 2 AM won't be detected until someone checks the logs the next morning. By then, the damage is done. The approach is inherently reactive, prone to human error, and cannot provide the 24/7 automated response that modern web security demands.

**Commercial SIEM Platforms (Solution 2)** carries a total cost of ownership that is entirely incompatible with small business budgets. Annual licensing alone ranges from $50,000 to over $500,000, and that does not include the cost of dedicated hardware, certified implementation specialists, or ongoing security analyst salaries. The math simply does not work when those resources could instead hire multiple employees or fund core business operations.

**Why Our Solution Works**

Our Intelligent Web-SOC Platform (Solution 3) is ideal for academic demonstration because it showcases integration skills by combining multiple technologies (Flask, React, PostgreSQL, AI APIs) demonstrating full-stack development capability. It demonstrates innovation by applying AI for security explainability in a novel way suitable for SME contexts. The system proves technical competency by implementing core security concepts (pattern matching, threat detection, incident response) from scratch. Core features can be implemented in 14 weeks with proper planning, making it achievable within the timeframe. It uses an entirely open-source stack suitable for student projects, maintaining zero licensing costs. Most importantly, it creates a genuinely useful proof-of-concept that could be extended for real-world use.

**Demonstration Environment:**

The system will be demonstrated in a controlled classroom/lab environment, running on local development laptops via Docker Compose rather than production servers, testing against the intentionally vulnerable vuln-web application (Flask, port 5050), using simulated attacks (OWASP ZAP, manual payloads, or Nikto) to generate log entries that Incidentra monitors in real-time, and showcasing log-based detection functionality rather than production-scale inline filtering.

This approach allows us to prove the concept works while maintaining realistic scope for a 14-week student project.

## D. DEVELOPMENT EFFORT

### 1. Manpower Details and Roles

| Name & ID | Role | Primary Responsibilities | Deliverables |
| --- | --- | --- | --- |
| Hardin Irfan 001202300066 | Project Leader & Full-Stack Developer | Flask API and backend architecture / Log ingestion engine / Detection engine / Response manager (escalating block policy) / Groq LLM integration / React.js SOC Dashboard / Frontend-backend integration | Flask backend API Detection engine Automated response system React.js SOC Dashboard AI explanation system Database models API documentation |
| Zaidan Mahfudz Azzam Saidi 001202300144 | Cybersecurity Specialist & QA Engineer | OWASP Top 10 detection rules development Penetration testing (OWASP ZAP, Burp Suite) Automated testing framework Security validation and performance testing False positive/negative analysis | Detection rule library Testing framework Penetration test reports Performance benchmarks Security documentation |

### 2. Technology Stack (Backend)

| Component | Technology | Version | Justification |
| --- | --- | --- | --- |
| Core Language | Python | 3.11+ | Strong libraries for security pattern matching, extensive community support, team expertise |
| Web Framework | Flask | 3.0+ | Lightweight, flexible, minimal overhead, suitable for API development |
| Database | PostgreSQL | 15+ | ACID compliance, robust performance, excellent JSON support, completely free |
| ORM | SQLAlchemy | 2.0+ | Mature framework, well-documented, prevents SQL injection in application code |
| Task Queue | Celery | 5.3+ | Handles asynchronous AI analysis processing and email sending |
| Cache Layer | Redis | 7.0+ | Fast IP blacklist caching and rate limiting counters |

### 3. Technology Stack (Frontend)

| Component | Technology | Version | Justification |
| --- | --- | --- | --- |
| UI Framework | React.js | 18+ | Component-based architecture, strong ecosystem, team familiarity |
| State Management | React Context API | Latest | Manages global state for dashboard data efficiently |
| HTTP Client | Axios | 1.6+ | Promise-based requests, clean API design, robust error handling |
| Charts/Visualization | Chart.js / Recharts | Latest | Lightweight charting libraries for attack visualizations |
| UI Components | Material-UI / TailwindCSS | Latest | Pre-built components for rapid development |
| Real-time Updates | HTTP polling (3s Live Traffic; 15s Dashboard KPI) | Near-real-time dashboard updates; WebSocket listed as future work |

### 4. Technology Stack (AI & Intelligence)

| Component | Technology | Justification |
| --- | --- | --- |
| LLM Provider | Groq Cloud (Free Tier) | Fast inference, generous free tier, simple API integration |
| Threat Intelligence | AbuseIPDB API (Free) | IP reputation database with 15,000 daily queries free |
| Prompt Management | Custom Templates | Structured prompts for consistent AI explanations |

### 5.  Technology Stack (Development & Testing)

| Component | Technology | Purpose |
| --- | --- | --- |
| Version Control | Git/GitHub | Code collaboration and version tracking |
| API Testing | Postman | Endpoint validation and documentation |
| Security Testing | OWASP ZAP | Automated vulnerability scanning and attack simulation |
| Penetration Testing | Burp Suite Community | Manual security testing and traffic analysis |
| Code Quality | Pylint, Black | Python code formatting and linting |
| Documentation | Markdown, Swagger | API documentation and project guides |

### 6.  Test Equipment and Validation Strategy

**Development Infrastructure:**

- 2x Student laptops for parallel development (one per team member) 

- Each laptop serves as individual development environment during weeks 1-13 

- Version control via Git for code synchronization 

**Integrated Testing ****&**** Demonstration Setup:**

- Single laptop deployment for integrated system testing (weeks 10-14) 

- All components run on localhost via Docker Compose (six services):

- vuln-web Target Application (Port 5050)

- Incidentra Backend (Port 5000)

- React Dashboard via Nginx (Port 3000)

- PostgreSQL Database (Port 5432)

- Redis Cache (Port 6379)

- Celery Worker (optional background tasks) 

- OWASP ZAP and Burp Suite for security testing 

- Apache JMeter for load testing

### 7. Development Phase Cost (14 Weeks - Capstone Project)

| **Item** | **Specification** | **Cost (USD)** | **Notes** |
| --- | --- | --- | --- |
| **Development Hardware** | Student Laptops (2x existing) | $0.00 | Using personal hardware already owned by team members |
| **AI API Access** | Groq Cloud Developer Free Tier | $0.00 | 14,400 requests/day (432K/month) sufficient for development and testing |
| **Threat Intelligence API** | AbuseIPDB Free Tier | $0.00 | 15,000 IP lookups/day included in free tier |
| **Software Stack** | Python, Flask, React, PostgreSQL, Redis | $0.00 | 100% open-source technologies with no licensing fees |
| **Development Tools** | VS Code, Git, Postman, Docker | $0.00 | Free community editions sufficient for development |
| **Testing Tools** | OWASP ZAP, Burp Suite Community, JMeter | $0.00 | Free versions provide all required testing capabilities |
| **Version Control ****&**** Collaboration** | GitHub (Public Repository), Discord | $0.00 | Unlimited public repositories and free team communication |
| **Documentation Tools** | Markdown, Google Docs, Draw.io | $0.00 | Free collaborative documentation and diagramming tools |
| **Test Web Server** | vuln-web + Docker Compose (localhost) | $0.00 | Deliberately vulnerable Flask shop for development and testing |
| **TOTAL DEVELOPMENT COST** | **$0.00** | **Zero-cost implementation** |

### 8. Timelines

| **Phase** | **W1** | **W2** | **W3** | **W4** | **W5** | **W6** | **W7** | **W8** | **W9** | **W10** | **W11** | **W12** | **W13** | **W14** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Research ****&**** Planning** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Backend Development** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Frontend ****&**** Dashboard** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Integration ****&**** Testing** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Documentation ****&**** Presentation** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Milestones** |  | **M1** |  |  |  | **M2** |  |  | **M3** |  |  | **M4** |  | **M5** |

## REFERENCES

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