# 📊 DevSecOps Lab CIAP Microproject — Submission Gap Report

**Document:** `DEVSECOPS_SUBMISSION_GAP_REPORT.md`
**Date:** October 19, 2026
**Student Name:** Khot Vishwajeet Tanaji
**Roll Number:** 124BTCS1028 (B.Tech Cyber Security)
**Project Title:** IoT-Based Smart Energy Monitoring and Management System
**Repository:** [https://github.com/vishwajeet1210/iot-smart-energy-monitoring](https://github.com/vishwajeet1210/iot-smart-energy-monitoring)
**Local Project Directory:** `C:\Users\Vishwajeet\.gemini\antigravity-ide\scratch\smart-energy-monitor`

---

## 1. Executive Summary & Context

This gap report evaluates the existing project assets, report drafts, presentations, and newly collected submission screenshots against the **official DevSecOps Lab Continuous Internal Assessment Practical (CIAP) Microproject requirements**.

### Baseline Context:
The project is an evolution of the previous Software Engineering Practices (SEP) microproject (`SEP_TYCS_22_MicroProject_Report.pdf`). While the core application logic (IoT simulator, SQLite database, analytics, alerts, and Streamlit dashboard) was built during SEP, the **DevSecOps Lab submission requires a comprehensive shift toward automated security, CI/CD pipeline orchestration, containerization, Infrastructure as Code (IaC), and vulnerability management**.

---

## 2. Inventory of Existing Local Materials

| Material Type | Local File Path / Name | Status | Purpose / Description |
| :--- | :--- | :---: | :--- |
| **Previous SEP Report** | [`REPORT_MATERIALS/SEP_TYCS_22_MicroProject_Report.pdf`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/REPORT_MATERIALS/SEP_TYCS_22_MicroProject_Report.pdf) | **Available** | 29-page final report from SEP course (`CSCOR1PC302`). Contains base problem definition, design, student reflection, and Jira evidence (`ISEM-1`, 43 story points). |
| **DevSecOps Report Draft** | [`REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx) | **Available (Draft)** | Working Word document draft. Needs updating for DevSecOps course headers, CI/CD pipeline, and security audit chapters. |
| **Secondary Report Draft** | [`REPORT_MATERIALS/SEPM_Microproject_Report.docx`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/REPORT_MATERIALS/SEPM_Microproject_Report.docx) | **Available** | Additional academic draft covering software engineering aspects. |
| **Previous SEP Presentation** | `C:\Users\Vishwajeet\Downloads\IoT-Based-Smart-Energy-Monitoring-and-Management-System.pptx` | **Available** | 10-slide PowerPoint from SEP. Needs to be updated with DevSecOps modules (Jenkins, SonarCloud, Trivy, Terraform, AWS). |
| **UML & Architecture Diagrams** | `REPORT_MATERIALS/Evidence/Evidence/*.png` and `REPORT_MATERIALS/files/*.drawio` | **Available** | Use Case, Activity, Sequence, Class, Component, and ER Database diagrams. |
| **Security Assessment Audit** | [`devsecops_evidence/VULNERABILITY_ASSESSMENT_REPORT.md`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/devsecops_evidence/VULNERABILITY_ASSESSMENT_REPORT.md) | **Available** | Comprehensive security assessment report documenting Trivy multi-stage scanning, SBOM, and Residual Risk Register. |
| **Submission Evidence Folder** | `Submission_Evidence/*.png` (**16 screenshots total**) | **Available (Complete)** | Complete evidence captures covering Web UI, Jenkins Build #11, SonarCloud, Trivy reports, GitHub repo, Pytest CLI, Terraform CLI, and Docker runtime. |

---

## 3. Complete Submission Evidence Inventory (`Submission_Evidence/`)

All 16 screenshots located in `C:\Users\Vishwajeet\.gemini\antigravity-ide\scratch\smart-energy-monitor\Submission_Evidence` have been inspected and cataloged:

| Screenshot File | Target Component / URL | What It Demonstrates | Report Section Mapping |
| :--- | :--- | :--- | :--- |
| **`Screenshot 2026-10-19 151413.png`** | Jenkins Job `smart-energy-monitor-ci`<br>`http://localhost:8080/.../11/` | **Jenkins Build #11 Overview:** Status SUCCESS (green checkmark), commit `dc9f84c`, duration 4m 06s, user `Vishwajeet Khot`. Archived artifacts: `coverage.xml`, `results.xml`, `trivy-report.json`. Tests: `no failures`. | **Section 7: Implementation** (Jenkins)<br>**Section 13: Evidence** (CI/CD) |
| **`Screenshot 2026-10-19 151459.png`** | SonarCloud Project Dashboard<br>`https://sonarcloud.io/...` | **SonarCloud Quality Gate:** Status **Passed**, 33 Open Issues, 0.0% Duplications, **48.1% Coverage**, 1.7k LOC. | **Section 8: Security** (SAST Static Analysis)<br>**Section 9: Analysis** |
| **`Screenshot 2026-10-19 151744.png`** | Live App (Sydney EC2)<br>`http://13.210.96.204:8501/` | **Dashboard Overview & KPIs:** Total Power 4.68 kW, Energy 9.651 kWh, Est. Cost ₹77.21, Devices Online 6/6, System Status Alert, Power Over Time, Device Distribution. | **Section 7: Implementation** (Web App)<br>**Section 13: Evidence** (Website) |
| **`Screenshot 2026-10-19 151830.png`** | Live App (Sydney EC2)<br>`http://13.210.96.204:8501/` | **IoT Device Monitoring Table:** All 6 appliances (Water Heater, AC, Washing Machine, PC, Refrigerator, LED Lighting) showing Voltage, Current, Power (kW), and High/Normal status badges. | **Section 7: Implementation** (IoT Devices)<br>**Section 13: Evidence** (Website) |
| **`Screenshot 2026-10-19 151842.png`** | Live App (Sydney EC2)<br>`http://13.210.96.204:8501/` | **Energy Analytics Summary:** 150 readings, 9.651 kWh, ₹77.21, ₹8.0/kWh tariff. Line graph: Total Power Over Time; Area chart: Cumulative Energy Over Time. | **Section 7: Implementation** (Analytics)<br>**Section 13: Evidence** (Website) |
| **`Screenshot 2026-10-19 151853.png`** | Live App (Sydney EC2)<br>`http://13.210.96.204:8501/` | **Energy Consumption Alerts:** Active banner `2 device(s) currently exceed the energy threshold!`. Highlighted alert cards for Water Heater (1.72 kW) and Air Conditioner (1.55 kW) exceeding 1.2 kW. | **Section 7: Implementation** (Alerts Engine)<br>**Section 13: Evidence** (Website) |
| **`Screenshot 2026-10-19 151904.png`** | Live App (Sydney EC2)<br>`http://13.210.96.204:8501/` | **Energy-Saving Recommendations:** Dynamic actionable tips (Reduce Water Heater usage, balance multiple high-power loads, turn off idle lighting, consider solar installation). | **Section 7: Implementation** (Optimization)<br>**Section 13: Evidence** (Website) |
| **`Screenshot 2026-10-19 152012.png`** | Live App (Sydney EC2)<br>`http://13.210.96.204:8501/` | **Analytics Time-Series Deep Dive:** Scrolled view showing explicit X-axis timestamps (`04:30 Oct 18, 2026` to `06:00`) for power and cumulative energy curves. | **Section 7: Implementation** (Analytics)<br>**Section 9: Analysis** |
| **`Screenshot 2026-10-19 152025.png`** | Live App (Sydney EC2)<br>`http://13.210.96.204:8501/` | **Device Energy Share & Comparison:** Interactive donut chart (Water Heater 37.3%, AC, Washing Machine 15.8%, PC 8.79%, Refrigerator 5.64%, Lighting) and horizontal comparison bar chart against 1.2 kW threshold. | **Section 7: Implementation** (Analytics)<br>**Section 13: Evidence** (Website) |
| **`Screenshot 2026-10-19 152750.png`** | Jenkins Build #11 Artifact<br>`.../artifact/trivy-report.json` | **Jenkins CI Trivy Artifact (`smart-energy-monitor:11`):** JSON output from Trivy 0.69.3 scanning image `smart-energy-monitor:11` (ImageID `sha256:25dea133bfb0...`) on Debian 13.7. **Reports 44 HIGH findings.** | **Section 8: Security** (CI Container Scanning)<br>**Section 13: Evidence** (Trivy Scan) |
| **`Screenshot 2026-10-19 153000.png`** | Vulnerability Assessment Report<br>Section 3 Markdown Table | **Dual-Scan Metrics (`smart-energy-monitor:devsecops`):** Table showing Primary Full Scan = **48 findings** (48 HIGH, 0 CRITICAL, 0 Python), Secondary Actionable Scan (`--ignore-unfixed`) = **0 findings**. Explains zero developer debt. | **Section 8: Security** (Vulnerability Assessment)<br>**Section 9: Analysis** |
| **`Screenshot 2026-10-19 153045.png`** | Vulnerability Assessment Report<br>Section 5 Markdown Table | **Debian 13 Base OS Residual Risk Register:** Root-cause analysis of the 48 upstream unpatched OS vulnerabilities (`util-linux`, `curl`, `libacl1`, `ncurses`, `perl`, `systemd`) and container mitigations (`appuser:1001`, namespace isolation). | **Section 8: Security** (Residual Risk Register)<br>**Section 9: Analysis** |
| **`Screenshot 2026-10-19 154841.png`** *(New)* | GitHub Repository Web UI<br>`github.com/vishwajeet1210/...` | **GitHub Repository Overview:** Branch `main`, 14 commits, latest commit `dc9f84c` (`fix: harden SSM deployment polling and payload handling`), full repository file tree. | **Section 7: Implementation** (GitHub Repo)<br>**Section 13: Evidence** (Repository) |
| **`Screenshot 2026-10-19 155043.png`** *(New)* | Terminal CLI Output | **Pytest Automated Unit Test Execution:** CLI output showing `tests/test_system.py` passing across all test suites, ending with `39 passed in 4.26s`. | **Section 7: Implementation** (Testing)<br>**Section 9: Analysis** |
| **`Screenshot 2026-10-19 155217.png`** *(New)* | Terminal CLI Output | **Terraform Formatting & Validation CLI:** `terraform -chdir=terraform fmt -check` (0 errors) and `terraform -chdir=terraform validate` (`Success! The configuration is valid.`). | **Section 7: Implementation** (Terraform IaC)<br>**Section 13: Evidence** (IaC) |
| **`Screenshot 2026-10-19 155301.png`** *(New)* | Terminal CLI Output | **Docker Runtime & Security Context:** `docker ps` showing `smart-energy-monitor` running (healthy, port 8501:8501) and `jenkins-devsecops`. `docker inspect` confirming `running | health=healthy | user=appuser`. | **Section 7: Implementation** (Docker)<br>**Section 13: Evidence** (Container) |

---

## 4. Technical Distinctions Preserved

1. **Trivy Scan Count Separation**:
   * **`smart-energy-monitor:11` (Jenkins Build #11 Artifact)**: Captured in `Screenshot 2026-10-19 152750.png`. Trivy v0.69.3 scanned this image during the CI pipeline, reporting **44 HIGH vulnerabilities** (0 CRITICAL, 0 Python package findings).
   * **Multi-Stage Security Audit (`smart-energy-monitor:devsecops`)**: Captured in `Screenshot 2026-10-19 153000.png` and `153045.png`. Trivy v0.76.0 evaluated this image, reporting **48 HIGH vulnerabilities** (0 CRITICAL, 0 Python findings, and 0 actionable findings with `--ignore-unfixed`).
   * **Rule**: Do not mix these counts or claim they refer to the same image. The 44-finding scan is the automated CI artifact; the 48-finding scan is the standalone multi-stage audit report.
2. **Distinction between AWS Deployments**:
   * **Sydney (`ap-southeast-2`)**: Managed by Terraform (`terraform.tfstate`, 11 resources). This is the instance (`13.210.96.204`) automated via Jenkins Build #11 through AWS Systems Manager (SSM) and shown in the live dashboard screenshots (`Screenshot 2026-10-19 151744.png` to `152025.png`).
   * **Mumbai (`ap-south-1`)**: Standalone, manual deployment on EC2 instance `i-0c06fe2cc3dd7a63a` (`15.252.18.53`) using `scripts/deploy_ec2.sh`. Not managed by Terraform; not triggered by Jenkins.
3. **SonarCloud Metric Accuracy**:
   * Captured in `Screenshot 2026-10-19 151459.png`.
   * Quality Gate status: **Passed**.
   * Exact dashboard values: **33 open issues** and **48.1% coverage** (Overall code). Do not claim 0 issues or 100% coverage.

---

## 5. Section-by-Section Requirement Gap Analysis

| Official DevSecOps Report Section | Requirements & Guidelines | Current Status | What Is Missing / Action Needed |
| :--- | :--- | :---: | :--- |
| **1. Title Page** | Project title, Course name (DevSecOps Lab CIAP Microproject), Student Name (Khot Vishwajeet Tanaji), Roll No (124BTCS1028), Institute & Dept. | **NEEDS UPDATE** | Existing Word draft (`CIAP_Report_IoT_Smart_Energy_Monitor.docx`) has placeholders `[TO BE ADDED - Institute name]` and refers to SEP course code `CSCOR1PC302`. Must update to DevSecOps course details. |
| **2. Certificate Page** | Formal certificate with student name, roll number, course name, faculty guide name (Vishakha Shinde), date, and signature placeholder. | **NEEDS UPDATE** | Existing draft refers to "Software Engineering Practices". Must update to "DevSecOps Lab". |
| **3. Table of Contents** | Auto-generated TOC with dynamic page numbers covering all chapters. | **NEEDS UPDATE** | Existing TOC in draft must be refreshed after assembling new DevSecOps chapters and inserting screenshots. |
| **4. Introduction** | Background of IoT energy monitoring, project overview, and alignment with DevSecOps objectives (shifting security left, CI/CD, automation). | **PARTIALLY COMPLETE** | Base IoT introduction is present from SEP. Must add DevSecOps lifecycle context (SAST, SCA, container security, IaC). |
| **5. Problem Definition & Scope** | Problem statement, objectives, scope boundaries, and security scope (threat model, container escape prevention, supply-chain security). | **PARTIALLY COMPLETE** | Problem definition exists. Need to expand scope to include CI/CD automation and cloud infrastructure boundaries. |
| **6. Design & Methodology** | Application architecture (layers, appliances) AND CI/CD workflow (Jenkins, SonarCloud, Trivy, Docker, Terraform, AWS SSM). | **PARTIALLY COMPLETE** | Application diagrams exist. Need to integrate the DevSecOps workflow diagram (`devsecops_evidence/cicd_workflow_diagram.drawio`) and document the 6-stage pipeline. |
| **7. Implementation & Results** | Comprehensive coverage of Website, GitHub, Docker, Jenkins, Terraform, and AWS EC2. | **ALL SCREENSHOTS READY (16/16)** | All technical components are built and verified with screenshots. Need to assemble the narrative and embed the screenshots into Chapter 7. |
| **8. Security Assessment & Vulnerability Report** | SonarCloud SAST results, Trivy container scans, dual-scan methodology, and the Debian 13 Residual Risk Register. | **READY TO INSERT** | Content is fully drafted in `devsecops_evidence/VULNERABILITY_ASSESSMENT_REPORT.md` and supported by screenshots 2, 10, 11, and 12. Must be compiled into Chapter 8. |
| **9. Analysis & Interpretation** | Automated testing analysis (39/39 tests), pipeline performance (Build #11 metrics), security findings analysis, and implementation challenges. | **DATA READY** | Empirical data is verified. Need to write the analytical narrative connecting tests (`results.xml`), coverage (`coverage.xml`), and build times. |
| **10. Conclusion & Future Scope** | Summary of project outcomes, DevSecOps benefits, and future enhancements (AWS ECS/Fargate, Prometheus/Grafana, automated Slack alerts). | **NEEDS DRAFTING** | Needs expansion beyond the base SEP conclusion to reflect DevSecOps achievements. |
| **11. References** | Citations for DevSecOps, NIST SP 800-190, OWASP, Docker, Terraform, Streamlit, Trivy, and SonarQube. | **NEEDS EXPANSION** | Needs academic and technical citations formatted consistently (IEEE / standard). |
| **12. Project Reflection (400–500 words)** | Individual student reflection based on actual learning across DevSecOps practices, container security, CI/CD, IaC, and security triage. | **NEEDS DRAFTING** | The previous SEP reflection exists (Page 28 of `SEP_TYCS_22_MicroProject_Report.pdf`). A new 400–500 word DevSecOps reflection must be written reflecting actual hands-on learning. |
| **13. Evidence of Completion** | Embedded screenshots, GitHub URL (`https://github.com/vishwajeet1210/iot-smart-energy-monitoring`), demo video link, and presentation. | **SCREENSHOTS COMPLETE** | All 16 screenshots are captured. Remaining: GitHub URL (confirmed), presentation (PPT update), and demo video link placeholder. |

---

## 6. Presentation (PPT) Gap Analysis

The existing PPT (`IoT-Based-Smart-Energy-Monitoring-and-Management-System.pptx`, 10 slides) is dedicated to Software Engineering Practices (SEP).

### Required DevSecOps Slide Modules vs. Current State:
1. **Slide 1: Title & Overview** — *Needs update:* Change course from SEP to DevSecOps Lab, keep student details (Khot Vishwajeet Tanaji, 124BTCS1028).
2. **Slide 2: Problem Statement & Objectives** — *Needs update:* Add DevSecOps objectives (shift-left security, automated quality gates, repeatable cloud deployment).
3. **Slide 3: System Architecture & Data Pipeline** — *Available:* Can reuse the existing application data pipeline slide.
4. **Slide 4: DevSecOps CI/CD Pipeline Workflow** — *MISSING:* Must create a slide illustrating the 6-stage Jenkins workflow (Checkout → Tests → SonarCloud → Docker & Trivy → Terraform → AWS Deploy).
5. **Slide 5: Automated Testing & QA** — *Available:* Update with 39/39 passing tests and JUnit XML/Coverage metrics (`Screenshot 2026-10-19 155043.png`).
6. **Slide 6: Containerization & Least-Privilege Security** — *MISSING:* Must highlight Python 3.12-slim, non-root `appuser:1001`, volume persistence, and native healthchecks (`Screenshot 2026-10-19 155301.png`).
7. **Slide 7: Static Analysis (SonarCloud) & Container Vulnerability Scanning (Trivy)** — *MISSING:* Must showcase SonarCloud Quality Gate Passed (`Screenshot 2026-10-19 151459.png`) and Trivy dual-scan results (`Screenshot 2026-10-19 152750.png` and `153000.png`).
8. **Slide 8: Infrastructure as Code (Terraform) & AWS Deployment** — *MISSING:* Must describe the Sydney VPC, IAM role, security group, and CLI validation (`Screenshot 2026-10-19 155217.png`).
9. **Slide 9: Analysis, Challenges & Project Reflection** — *Needs update:* Replace SEP reflection with DevSecOps reflection highlights.
10. **Slide 10: Conclusion, Future Scope & References** — *Needs update:* Add cloud-native future scope (ECS, Kubernetes, automated security gating).

---

## 7. Remaining Incomplete Mandatory Deliverables

With all 16 evidence screenshots successfully captured and cataloged in `Submission_Evidence/`, the technical and empirical evidence is 100% complete. The remaining work is strictly document compilation and presentation authoring:

1. **Final Word Report Assembly (`.docx`)** — *Mandatory*:
   * Update [`REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx) with DevSecOps Lab headers, student metadata (*Khot Vishwajeet Tanaji, 124BTCS1028*), and faculty guide (*Vishakha Shinde*).
   * Embed all 16 screenshots from `Submission_Evidence/` with descriptive captions into their respective chapters.
   * Integrate the complete Security Assessment and Residual Risk Register from `devsecops_evidence/VULNERABILITY_ASSESSMENT_REPORT.md`.
   * Update the Table of Contents.
2. **Updated Presentation (`.pptx`)** — *Mandatory*:
   * Update the 10-slide PowerPoint to replace the old SEP content with the 8 official DevSecOps modules (Jenkins, SonarCloud, Trivy, Docker, Terraform, and AWS SSM).
3. **Student Personal Reflection (400–500 words)** — *Mandatory*:
   * Must be drafted based on actual learning from the project: shifting security left, multi-stage Docker containerization, solving the Jenkins SSM shell-escaping bug (Build #10 to #11), Trivy vulnerability triage, and Infrastructure as Code.
4. **Demonstration Video Link** — *Mandatory*:
   * A placeholder URL to be added to Chapter 13 of the report (e.g. YouTube unlisted or Google Drive link) for the student to insert after recording their 3–5 minute video demonstration.
5. **JIRA Project Management Evidence**:
   * Reuse the existing completed `ISEM-1` 43 story points sprint board screenshot from the previous SEP report (Page 25/26), or include an updated DevSecOps task board.

---

## 8. Prioritized Execution Plan

### 🎯 Step 1: Draft the 400–500 Word DevSecOps Personal Reflection
Align with the student's actual learning journey:
- Architecture evolution from SEP to DevSecOps.
- Hands-on experience with SonarCloud quality gates and Trivy vulnerability triage.
- Pipeline troubleshooting (resolving the SSM deployment Dash syntax error in Build #11).
- Cloud security best practices (IMDSv2, non-root `appuser:1001`, parameterised SQL).

### 🎯 Step 2: Compile and Format the Final Word Report (`.docx`)
- Programmatically assemble the complete, publication-ready report in `REPORT_MATERIALS/files/` with all 16 screenshots embedded, updated title page, certificate, 13 full chapters, and auto-updated table of contents.

### 🎯 Step 3: Upgrade the PowerPoint Presentation (`.pptx`)
- Generate the updated 10-slide presentation matching the 8 official DevSecOps syllabus topics.
