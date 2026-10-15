# 📸 DevSecOps Microproject Submission Evidence — Screenshot Checklist

**Project Title:** IoT-Based Smart Energy Monitoring and Management System<br>
**Repository:** [https://github.com/vishwajeet1210/iot-smart-energy-monitoring](https://github.com/vishwajeet1210/iot-smart-energy-monitoring)<br>
**Author:** Vishwajeet<br>
**Course:** DevSecOps Lab CIAP Microproject

---

## 📌 Instructions for Evidence Collection

This checklist lists all screenshots required for your CIAP project report and presentation.
For each item:
- Capture at full resolution (avoid cropped or blurry screenshots).
- Ensure terminal commands, file paths, and dates/times are clearly readable.
- Annotate or highlight key security controls (e.g., multi-stage build, non-root user 1001, IMDSv2, test counts, 0 actionable findings).
- Save captures in `devsecops_evidence/screenshots/` (or your submission folder).

---

## 📑 Complete Screenshot Checklist

| ID | Category | Target Component | File / URL / Command | What to Capture & Highlight | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **SS-01** | **Web Application** | Dashboard Overview & KPIs | `http://localhost:8501` | Active KPI metric cards (Total Power kW, Total Energy kWh, Estimated Cost ₹, Connected Devices, System Status) | 🔲 To Capture |
| **SS-02** | **Web Application** | IoT Device Monitoring Table | `http://localhost:8501` (Devices Tab) | Status cards/table of all 6 appliances (AC, Refrigerator, Washing Machine, PC, Lighting, Water Heater) with voltage, current, power | 🔲 To Capture |
| **SS-03** | **Web Application** | Real-Time Energy Analytics | `http://localhost:8501` (Analytics Tab) | Plotly charts (Power over time, cumulative energy area chart, device breakdown donut chart) | 🔲 To Capture |
| **SS-04** | **Web Application** | High-Consumption Alert Trigger | `http://localhost:8501` (Alerts Tab) | Dynamic alert card triggered when appliance exceeds 1.20 kW threshold (e.g. AC or Water Heater in RED/AMBER) | 🔲 To Capture |
| **SS-05** | **Web Application** | Energy-Saving Recommendations | `http://localhost:8501` (Recommendations Tab) | Dynamic tips tailored to highest power consumer + solar recommendation | 🔲 To Capture |
| **SS-06** | **GitHub Repository** | Repository Overview & Tree | `https://github.com/vishwajeet1210/iot-smart-energy-monitoring` | Repository home page showing repo name, branch `main`, latest commit, and file tree containing `Dockerfile`, `Jenkinsfile`, `terraform/`, `security/` | 🔲 To Capture |
| **SS-07** | **GitHub Repository** | Git Commit History | `https://github.com/vishwajeet1210/iot-smart-energy-monitoring/commits/main` | Clean commit log with descriptive DevSecOps conventional commits | 🔲 To Capture |
| **SS-08** | **Testing & QA** | Automated Test Execution | Terminal: `pytest tests/test_system.py -v` | Terminal showing all 39 tests passing (`39 passed in 0.77s`) across IoT simulator, energy calculations, tariffs, alerts, and DB CRUD | 🔲 To Capture |
| **SS-09** | **Testing & QA** | Test Suite with JUnit XML | Terminal: `pytest --junitxml=results.xml` | Generated `results.xml` file demonstrating test reporting integration for CI | 🔲 To Capture |
| **SS-10** | **Dockerization** | Hardened Multi-Stage Dockerfile | VS Code / Editor: `Dockerfile` | Highlight multi-stage architecture: builder stage (`python -m venv`, dependency install, pip strip) and runtime stage (`python:3.12-slim`, purge base pip, `appuser:1001`, `/app/data` volume, `HEALTHCHECK`) | 🔲 To Capture |
| **SS-11** | **Dockerization** | Docker Build Context Exclusions | VS Code / Editor: `.dockerignore` | Highlight exclusion of `*.tar`, `.git`, `.pytest_cache`, `terraform`, `security`, and local database files | 🔲 To Capture |
| **SS-12** | **Dockerization** | Multi-Stage Container Build & Run | Terminal: `docker build -t smart-energy-monitor:devsecops .` & `docker ps` | Successful multi-stage build, running container, status `healthy`, non-root execution (`appuser:1001`), and port binding `8501:8501` | 🔲 To Capture |
| **SS-13** | **Dockerization** | Runtime Isolation & Health Verification | Terminal: `curl.exe http://localhost:8501/_stcore/health` & `which pip` | HTTP 200 OK healthcheck response and terminal confirmation that `pip` is absent from runtime image | 🔲 To Capture |
| **SS-14** | **CI/CD Pipeline** | Declarative Jenkinsfile | VS Code / Editor: `Jenkinsfile` | Show the 10 declarative stages: SCM Checkout, Setup, Unit Tests, SonarQube, Quality Gate, Trivy SCA, Docker Build, Trivy Image, Terraform, Deploy Gate | 🔲 To Capture |
| **SS-15** | **CI/CD Pipeline** | Jenkins Pipeline Execution View *(When Jenkins active)* | Jenkins UI: `http://localhost:8080/job/smart-energy-monitor` | Blue Ocean or Stage View showing green stages passing end-to-end | 🔲 To Capture |
| **SS-16** | **Static Analysis** | SonarQube Project Config | VS Code / Editor: `sonar-project.properties` | Project key, exclusions, python coverage integration, and quality gate wait settings | 🔲 To Capture |
| **SS-17** | **Static Analysis** | SonarQube Dashboard *(When server active)* | SonarQube UI: `http://localhost:9000/dashboard?id=iot-smart-energy-monitoring` | Quality Gate PASSED status, Bugs: 0, Vulnerabilities: 0, Security Hotspots reviewed | 🔲 To Capture |
| **SS-18** | **Security Scanning** | Trivy Filesystem Dependency Scan | Terminal: `trivy fs --severity HIGH,CRITICAL .` | Console table output scanning filesystem dependencies (`requirements.txt`) | 🔲 To Capture |
| **SS-19** | **Security Scanning** | Trivy Multi-Stage Image Scan (Actionable) | Terminal: `trivy image --severity HIGH,CRITICAL --ignore-unfixed ...` | Console output showing **0 actionable findings** (zero developer backlog; all 4 Python CVEs remediated) | 🔲 To Capture |
| **SS-20** | **Security Scanning** | Trivy Full Image Scan & Residual Debt | Terminal: `trivy image --severity HIGH,CRITICAL ...` | Console output showing full scan: 48 Debian OS distribution debt findings (0 CRITICAL, 0 Python findings) | 🔲 To Capture |
| **SS-21** | **Security Scanning** | Machine-Readable Multi-Stage Reports | VS Code / Explorer: `security/` directory | Show generated files `trivy-multistage-full-report.json`, `trivy-multistage-actionable-report.json`, and `.txt` tables | 🔲 To Capture |
| **SS-22** | **Infrastructure as Code** | Terraform Core Architecture | VS Code / Editor: `terraform/main.tf` | Highlight VPC, public subnet, security group restricting port 8501, IAM SSM instance profile, IMDSv2, and user data Docker automation | 🔲 To Capture |
| **SS-23** | **Infrastructure as Code** | Terraform Variables & Outputs | VS Code / Editor: `terraform/variables.tf` & `outputs.tf` | Highlight configurable parameters, security comments, and output variables | 🔲 To Capture |
| **SS-24** | **Infrastructure as Code** | Terraform Validation CLI | Terminal: `terraform fmt -check` & `terraform validate` | Terminal showing clean formatting and `Success! The configuration is valid.` | 🔲 To Capture |

---

## 🛠️ Step-by-Step Instructions to Capture Each Item

### Category 1: Web Application (SS-01 to SS-05)
```bash
# In smart-energy-monitor directory:
streamlit run app.py
```
1. Open `http://localhost:8501` in your browser.
2. Maximize the browser window.
3. Use Windows Snipping Tool (`Win + Shift + S`) to capture:
   - **Main Dashboard tab:** Capture KPI metric cards and charts (**SS-01**).
   - **Device Monitoring:** Show the 6 smart appliances (**SS-02**).
   - **Analytics:** Show the interactive Plotly graphs (**SS-03**).
   - **Alerts tab:** Click "Generate New IoT Reading" until Water Heater or AC triggers high consumption (**SS-04**).
   - **Recommendations tab:** Show dynamic tips (**SS-05**).

### Category 2: Automated Unit Testing (SS-08, SS-09)
```bash
# Run pytest with verbose output
pytest -v

# Run with JUnit XML generation
pytest -v --junitxml=results.xml
```
- Capture the full terminal showing `39 passed in 0.77s` (**SS-08**).
- Open `results.xml` in VS Code split view alongside the terminal (**SS-09**).

### Category 3: Multi-Stage Docker Build & Runtime Verification (SS-10, SS-11, SS-12, SS-13)
```bash
# Build multi-stage image
docker build -t smart-energy-monitor:devsecops .

# Run container in background
docker run -d --name smart-energy-monitor-app -p 8501:8501 smart-energy-monitor:devsecops

# Verify health status and running container
docker ps --filter "name=smart-energy-monitor-app"

# Verify non-root execution (UID/GID 1001)
docker exec smart-energy-monitor-app id

# Verify pip is absent from runtime image
docker exec smart-energy-monitor-app which pip

# Verify health endpoint returns HTTP 200 OK
curl.exe -i http://localhost:8501/_stcore/health
```
- Capture VS Code showing `Dockerfile` multi-stage structure (**SS-10**).
- Capture VS Code showing `.dockerignore` (**SS-11**).
- Capture terminal showing build and `docker ps` with `(healthy)` status (**SS-12**).
- Capture terminal showing `curl` HTTP 200 OK and `which pip` failure (**SS-13**).

### Category 4: Security & Live Scans (SS-18, SS-19, SS-20, SS-21)
```bash
# Actionable scan: reports 0 findings
docker run --rm -v //var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache -v "${PWD}:/workspace" -w /workspace aquasec/trivy:0.76.0 image --severity HIGH,CRITICAL --ignore-unfixed smart-energy-monitor:devsecops

# Full scan: reports 48 Debian OS findings (0 CRITICAL, 0 Python)
docker run --rm -v //var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache -v "${PWD}:/workspace" -w /workspace aquasec/trivy:0.76.0 image --severity HIGH,CRITICAL smart-energy-monitor:devsecops
```
- Capture terminal showing actionable scan with **0 findings** (**SS-19**).
- Capture terminal showing full scan with 48 Debian OS distribution debt findings (**SS-20**).
- Capture VS Code file explorer displaying `security/trivy-multistage-full-report.json` and `security/trivy-multistage-actionable-report.json` (**SS-21**).

### Category 5: Source Code, CI/CD & Cloud Infrastructure (SS-06, SS-07, SS-14 to SS-17, SS-22 to SS-24)
- Open VS Code to capture `Jenkinsfile` (**SS-14**), `sonar-project.properties` (**SS-16**), `terraform/main.tf` (**SS-22**), and `terraform/variables.tf` (**SS-23**).
- Run `terraform fmt -check` and `terraform validate` in `terraform/` directory (**SS-24**).
- Push to GitHub after final review and capture repository root and commit history (**SS-06**, **SS-07**).
