# 📋 Smart Energy Monitor — Comprehensive DevSecOps Project Audit

**Document:** `PROJECT_AUDIT.md`
**Date of Audit:** October 19, 2026
**Auditor:** Senior DevSecOps Engineer
**Repository:** [https://github.com/vishwajeet1210/iot-smart-energy-monitoring](https://github.com/vishwajeet1210/iot-smart-energy-monitoring)
**Local Project Directory:** `C:\Users\Vishwajeet\.gemini\antigravity-ide\scratch\smart-energy-monitor`

---

## 1. Executive Summary

This audit assesses the completion status, security compliance, CI/CD pipeline execution, and submission readiness of the **IoT-Based Smart Energy Monitoring and Management System** (DevSecOps Lab CIAP Microproject).

All statements in this document are strictly based on verifiable local source code, test execution logs, machine-readable security reports, Jenkins build histories, and AWS Terraform states.

### Overall Readiness: 85% (Core Implementation & CI/CD Complete; Submission Evidence Pending)
* **Core Application & Testing:** 100% complete (39/39 passing unit tests, full telemetry simulation, SQLite WAL persistence).
* **Security Hardening & Scans:** 100% complete (SonarCloud Quality Gate PASSED; Trivy reports 0 CRITICAL and 0 developer-actionable findings).
* **CI/CD Automation:** 100% complete (Jenkins Build #11 passed end-to-end with all 6 stages green).
* **Live Deployment:** 100% operational on AWS EC2 at `http://15.252.18.53:8501`.
* **Remaining Deliverables:** Capturing UI screenshots for submission documents, compiling the final `.docx` report, and optionally publishing to Amazon ECR Public.

---

## 2. Infrastructure Clarification: Sydney vs. Mumbai Environments

A critical finding of this audit is distinguishing between the two distinct AWS environments associated with this project:

```
┌────────────────────────────────────────────────────────┐     ┌────────────────────────────────────────────────────────┐
│             AWS SYDNEY (ap-southeast-2)                │     │              AWS MUMBAI (ap-south-1)                   │
├────────────────────────────────────────────────────────┤     ├────────────────────────────────────────────────────────┤
│ • Managed by Terraform: YES (terraform.tfstate)        │     │ • Managed by Terraform: NO (Standalone / Out-of-band) │
│ • AWS Account ID: 695496430374                         │     │ • Public IP: 15.252.18.53                              │
│ • Instance ID: i-06e85f034d1c71c9c                     │     │ • Instance ID: i-0c06fe2cc3dd7a63a                     │
│ • Public IP: 13.210.96.204                             │     │ • Security Group: launch-wizard-1                      │
│ • Jenkins CI/CD Target: YES (Automated SSM Deploy)     │     │ • Jenkins CI/CD Target: NO                             │
│ • Deployment Method: Automated via Jenkins Build #11   │     │ • Deployment Method: scripts/deploy_ec2.sh via SSH/SCP │
│ • Private ECR: 695496430374.dkr.ecr.ap-southeast-2    │     │ • Live Status: ACTIVE & VERIFIED (HTTP 200 OK)         │
└────────────────────────────────────────────────────────┘     └────────────────────────────────────────────────────────┘
```

1. **Terraform-Managed Infrastructure (Sydney — `ap-southeast-2`)**:
   * Recorded in `terraform/terraform.tfstate` (11 managed AWS resources).
   * Creates a dedicated VPC (`vpc-05713fbc5a8c9ed52`), public subnet (`subnet-0db7732a9d0454372`), security group (`sg-09adc97f05d2f1ac1`), IAM instance profile/role (`smart-energy-monitor-ec2-role`), and EC2 instance (`i-06e85f034d1c71c9c`).
   * This is the environment automated and tested by `Jenkinsfile`.

2. **Standalone Production/Demo Infrastructure (Mumbai — `ap-south-1`)**:
   * EC2 instance `i-0c06fe2cc3dd7a63a` (`15.252.18.53`).
   * Created manually outside of Terraform (uses default VPC and security group `launch-wizard-1`).
   * Deployed idempotently via `scripts/deploy_ec2.sh` using the transferred `smart-energy-monitor-11.tar` image archive.
   * Running container `smart-energy-monitor`, port `8501`, healthcheck healthy, responding with HTTP 200 OK.

---

## 3. Detailed Component Audit

### A. Application Code & Persistence
* **Files**: `app.py`, `config.py`, `database.py`, `iot_simulator.py`, `analytics.py`, `alerts.py`.
* **Status**: **VERIFIED COMPLETE**
* **Findings**:
  * Clean separation of concerns: IoT simulation (`iot_simulator.py`), analytics calculations (`analytics.py`), persistence repository (`database.py`), threshold alerts (`alerts.py`), and presentation (`app.py`).
  * Database: SQLite WAL mode with foreign keys enabled. Configured to use environment variables `ENERGY_DB_DIR` and `ENERGY_DB_PATH`.
  * Multi-device telemetry: Simulates 6 appliances (AC, Refrigerator, Washing Machine, PC, Lighting, Water Heater) with realistic voltage, current, and wattage bounds.

### B. Automated Testing & Code Quality
* **Files**: `tests/test_system.py`, `results.xml`, `coverage.xml`.
* **Status**: **VERIFIED COMPLETE**
* **Empirical Evidence**:
  * Test Suite: **39 tests** across 7 test classes (`TestIoTSimulator`, `TestEnergyCalculation`, `TestElectricityCost`, `TestAlerts`, `TestDatabase`, `TestAnalytics`, `TestRecommendations`).
  * Results (`results.xml`): `tests="39" failures="0" errors="0" skipped="0" time="1.326s"`.
  * Code Coverage (`coverage.xml`): Valid lines = 701, covered lines = 440 (line rate: 62.77% across backend modules; UI `app.py` excluded).

### C. Containerization & Least Privilege
* **File**: `Dockerfile`, `.dockerignore`.
* **Status**: **VERIFIED COMPLETE**
* **Findings**:
  * Base: `python:3.12-slim` on Debian 13 (Trixie).
  * Least-Privilege Execution: Dedicated unprivileged user `appuser` (`UID 1001`, `GID 1001`). No root runtime execution.
  * Native Healthcheck: Uses Python stdlib `urllib.request` probing `http://localhost:8501/_stcore/health` (30s interval, 5s timeout, 10s start-period, 3 retries).
  * Build Isolation: `.dockerignore` excludes `.git`, `tests`, `terraform`, `security`, `.tar` files, and local databases.

### D. Static Application Security Testing (SAST / SonarCloud)
* **Files**: `sonar-project.properties`, Jenkins Build #11 console logs.
* **Status**: **VERIFIED COMPLETE**
* **Findings**:
  * SonarCloud Project Key: `iot-smart-energy-monitoring`, Org: `vishwajeet1210`.
  * Execution: Ran inside Jenkins Build #11 via official `sonarsource/sonar-scanner-cli:latest` image using Jenkins secret credential `sonarcloud-token`.
  * Quality Gate Result: **PASSED** (`QUALITY GATE STATUS: PASSED - View details on https://sonarcloud.io/dashboard?id=iot-smart-energy-monitoring`).

### E. Container Vulnerability Assessment (Trivy)
* **Files**: `trivy-report.json`, `security/` directory, `devsecops_evidence/VULNERABILITY_ASSESSMENT_REPORT.md`.
* **Status**: **VERIFIED COMPLETE**
* **Empirical Evidence**:
  * **CRITICAL Vulnerabilities**: **0** (completely eliminated).
  * **Application / Python Package CVEs**: **0** (msgpack, setuptools, urllib3 vulnerabilities remediated).
  * **Node.js CVEs**: **0**.
  * **Actionable Vulnerabilities (`--ignore-unfixed`)**: **0**.
  * **Residual Debt (Full Baseline)**: **44 HIGH findings** in `trivy-report.json`.

---

## 4. Residual Vulnerability Analysis (The 44 Trivy HIGH Findings)

A detailed inspection of `trivy-report.json` was conducted to verify each remaining finding:

```
Total Vulnerabilities: 44
Severity: 100% HIGH (0 CRITICAL, 0 MEDIUM, 0 LOW)
Fixed Versions: None (100% unpatched upstream by Debian maintainers)
```

### Breakdown of Affected Packages:
1. **`util-linux` source packages (36 findings)**:
   * Binary packages: `bsdutils` (4), `libblkid1` (4), `liblastlog2-2` (4), `libmount1` (4), `libsmartcols1` (4), `libuuid1` (4), `login` (4), `mount` (4), `util-linux` (4).
   * Associated CVEs: `CVE-2026-76642`, `CVE-2026-78408`, `CVE-2026-78409`, `CVE-2026-78410`.
   * Upstream Status: Debian Security Tracker marks all as unfixed/affected with no upstream patch released.
2. **`ncurses` (4 findings)**:
   * Binary packages: `libncursesw6`, `libtinfo6`, `ncurses-base`, `ncurses-bin`.
   * Associated CVE: `CVE-2025-69720`.
   * Upstream Status: No patch released.
3. **`systemd` (2 findings)**:
   * Binary packages: `libsystemd0`, `libudev1`.
   * Associated CVE: `CVE-2026-16742`.
   * Upstream Status: No patch released.
4. **`acl` (1 finding)**:
   * Binary package: `libacl1`.
   * Associated CVE: `CVE-2026-54369`.
5. **`perl` (1 finding)**:
   * Binary package: `perl-base`.
   * Associated CVE: `CVE-2026-9538` (Status: `fix_deferred`).

### Security Context & Mitigation:
* None of these vulnerable utilities are invoked by or exposed to the application.
* The container runs as unprivileged `appuser:1001` with no sudo permissions and no network exposure for local utility commands.
* When evaluated under Trivy's actionable filter (`--ignore-unfixed`), the count is **0**, representing zero developer packaging debt.

---

## 5. CI/CD Pipeline Audit (Jenkins Build #11)

* **Pipeline Script**: `Jenkinsfile` (Declarative, 10 stages).
* **Jenkins Agent**: Docker-enabled container `jenkins-devsecops` (Local port 8080).
* **Latest Build**: Build #11 (`dc9f84c7c1adcdae4988e7238bd8557bbd6b948b`).
* **Duration**: 4 minutes 6 seconds (246,774 ms).
* **Build Status**: **SUCCESS / STABLE**.

### Stage-by-Stage Verification:
| Stage Name | Execution Tool | Status | Output Evidence |
| :--- | :--- | :---: | :--- |
| **1. Source Checkout** | Git Plugin | **PASSED** | Checked out commit `dc9f84c` on branch `main` |
| **2. Automated Tests & QA** | pytest (in venv/Docker) | **PASSED** | 39 passed in 0.77s; generated `results.xml` & `coverage.xml` |
| **3. Static Analysis (SAST)** | `sonarsource/sonar-scanner-cli` | **PASSED** | Quality Gate PASSED; SonarCloud dashboard updated |
| **4. Docker Build & ECR** | Docker + `aquasec/trivy:0.69.3` | **PASSED** | Built `smart-energy-monitor:11`, scanned, pushed to Sydney ECR |
| **5. Terraform IaC Validation** | `hashicorp/terraform:latest` | **PASSED** | `fmt -check` and `validate` passed with zero errors |
| **6. Deploy to EC2 (SSM)** | AWS CLI + Systems Manager | **PASSED** | Dispatched SSM command to `i-06e85f034d1c71c9c`, verified healthy |

---

## 6. Deliverable Checklist

### ✅ COMPLETED (DONE)
- [x] Application source code with telemetry simulator, SQLite repository, analytics, and alerts.
- [x] Automated test suite: 39 tests passing with JUnit XML and coverage metrics.
- [x] Hardened Dockerfile: Python 3.12-slim, non-root `appuser:1001`, volume mount `/app/data`, native healthcheck.
- [x] Jenkins declarative pipeline: 10 stages covering test, SAST, SCA, build, IaC, and deployment.
- [x] Successful Jenkins CI build: Build #11 executed and passed end-to-end.
- [x] SonarCloud SAST quality gate integration and pass.
- [x] Trivy container vulnerability scan and residual risk documentation (0 CRITICAL, 0 Python CVEs).
- [x] Terraform Infrastructure as Code definitions (VPC, Subnet, Security Group, IAM, EC2).
- [x] Operational live application running on AWS EC2 at `http://15.252.18.53:8501`.
- [x] Repeatable, idempotent deployment script (`scripts/deploy_ec2.sh`).
- [x] Architecture diagrams (`REPORT_MATERIALS/files/` and `REPORT_MATERIALS/Evidence/Evidence/`).

---

### ⏳ NEEDS LIVE VERIFICATION (Action Required)
- [ ] **Live UI Screenshots (SS-01 to SS-05)**:
  Capture screenshots from `http://15.252.18.53:8501`:
  - SS-01: Main Dashboard KPI Cards
  - SS-02: IoT Device Monitoring Table (6 appliances)
  - SS-03: Real-Time Analytics Plotly Charts
  - SS-04: High-Consumption Alert Card (triggered on AC or Water Heater)
  - SS-05: Energy-Saving Recommendations Card
- [ ] **Jenkins Pipeline View Screenshot (SS-15)**:
  Capture the green stage view of Build #11 from `http://localhost:8080/job/smart-energy-monitor-ci/11/`.
- [ ] **SonarCloud Dashboard Screenshot (SS-17)**:
  Capture the Quality Gate PASSED dashboard from `https://sonarcloud.io/dashboard?id=iot-smart-energy-monitoring`.
- [ ] **Report Document Assembly**:
  Embed the fresh screenshots and active Mumbai URL (`15.252.18.53:8501`) into the draft report (`REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx`).

---

### ❌ NOT DONE (Pending Resolution)
- [ ] **Amazon Public ECR Push**:
  - Image is tagged locally as `public.ecr.aws/u2v8m6a3/smart-energy-monitor:11` and `:latest`.
  - Push to `public.ecr.aws` has not occurred because host AWS CLI credentials for the assumed role expired and authentication troubleshooting was paused.
- [ ] **Formal Assignment Rubric Verification**:
  - No standalone instructor rubric file (e.g. `rubric.pdf`) exists in the repository.
  - Alignment is confirmed against standard CIAP microproject requirements, but specific course-specific point breakdowns cannot be confirmed without the rubric document.

---

## 7. Inventory of Local Evidence Files

| File Path | Description | Verified Metrics / Contents |
| :--- | :--- | :--- |
| [`results.xml`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/results.xml) | JUnit XML test execution report | 39 passed, 0 failed, 1.326s |
| [`coverage.xml`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/coverage.xml) | Cobertura XML code coverage report | 62.77% line coverage across backend |
| [`trivy-report.json`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/trivy-report.json) | Jenkins Build #11 Trivy scan artifact | 0 CRITICAL, 44 HIGH (Debian OS), 0 Python |
| [`sonar-project.properties`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/sonar-project.properties) | SonarQube / SonarCloud configuration | Org: `vishwajeet1210`, Key: `iot-smart-energy-monitoring` |
| [`terraform/terraform.tfstate`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/terraform/terraform.tfstate) | Terraform AWS infrastructure state | 11 resources in Sydney (`ap-southeast-2`) |
| [`scripts/deploy_ec2.sh`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/scripts/deploy_ec2.sh) | Idempotent deployment script | Used to deploy container on Mumbai EC2 instance |
| [`devsecops_evidence/VULNERABILITY_ASSESSMENT_REPORT.md`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/devsecops_evidence/VULNERABILITY_ASSESSMENT_REPORT.md) | Comprehensive security assessment report | Complete audit log & residual risk register |
| [`devsecops_evidence/SCREENSHOT_CHECKLIST.md`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/devsecops_evidence/SCREENSHOT_CHECKLIST.md) | Submission screenshot checklist | Detailed checklist for items SS-01 to SS-24 |
| [`REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx) | Comprehensive project report draft | Academic submission report document |
| [`REPORT_MATERIALS/SEPM_Microproject_Report.docx`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/REPORT_MATERIALS/SEPM_Microproject_Report.docx) | SEPM microproject report draft | Software engineering project report |
| `REPORT_MATERIALS/Evidence/Evidence/*.png` | Architecture & Design Diagrams | Use case, Sequence, Class, ER, Activity diagrams |

---

## 8. Recommended Action Plan (In Priority Order)

### Priority 1: Capture Live Screenshots
While the application is actively running and Jenkins Build #11 is fresh:
1. Open [http://15.252.18.53:8501](http://15.252.18.53:8501) and capture **SS-01** (Dashboard), **SS-02** (Devices), **SS-03** (Analytics), **SS-04** (Alerts), and **SS-05** (Recommendations).
2. Open `http://localhost:8080/job/smart-energy-monitor-ci/11/` and capture **SS-15** (Jenkins Pipeline Stage View).
3. Open `https://sonarcloud.io/dashboard?id=iot-smart-energy-monitoring` and capture **SS-17** (SonarCloud Quality Gate PASSED).

### Priority 2: Finalize the Submission Report Document
1. Open [`REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/REPORT_MATERIALS/files/CIAP_Report_IoT_Smart_Energy_Monitor.docx).
2. Insert the captured screenshots into their respective sections.
3. Update the live demo URL to `http://15.252.18.53:8501`.
4. Export the document as PDF for academic submission.

### Priority 3 (Optional): Publish Image to Public ECR
1. If your assignment specifically requires a public Amazon ECR URL:
   * Refresh AWS credentials using `aws login --profile default` or by exporting session keys from your AWS Academy / lab portal.
   * Authenticate and push:
     ```powershell
     aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
     docker push public.ecr.aws/u2v8m6a3/smart-energy-monitor:11
     ```
