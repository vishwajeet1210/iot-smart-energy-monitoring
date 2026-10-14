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
- Annotate or highlight key security controls (e.g., non-root user, IMDSv2, test counts).
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
| **SS-08** | **Testing & QA** | Automated Test Execution | Terminal: `pytest tests/test_system.py -v` | Terminal showing all 39 tests passing (`39 passed in 0.XXs`) across IoT simulator, energy calculations, tariffs, alerts, and DB CRUD | 🔲 To Capture |
| **SS-09** | **Testing & QA** | Test Suite with JUnit XML | Terminal: `pytest --junitxml=results.xml` | Generated `results.xml` file demonstrating test reporting integration for CI | 🔲 To Capture |
| **SS-10** | **Dockerization** | Hardened Dockerfile | VS Code / Editor: `Dockerfile` | Highlight: `python:3.12-slim`, unprivileged `appuser:1001`, volume `/app/data`, `HEALTHCHECK` command, and Streamlit entrypoint | 🔲 To Capture |
| **SS-11** | **Dockerization** | Docker Build Context Exclusions | VS Code / Editor: `.dockerignore` | Highlight exclusion of `.git`, `.pytest_cache`, `terraform`, `security`, and local database files | 🔲 To Capture |
| **SS-12** | **Dockerization** | Container Build & Run *(When Docker active)* | Terminal: `docker build -t smart-energy-monitor .` & `docker ps` | Terminal showing successful image build, running container, healthy status, and port binding `8501:8501` | 🔲 To Capture |
| **SS-13** | **CI/CD Pipeline** | Declarative Jenkinsfile | VS Code / Editor: `Jenkinsfile` | Show the 10 declarative stages: SCM Checkout, Setup, Unit Tests, SonarQube, Quality Gate, Trivy SCA, Docker Build, Trivy Image, Terraform, Deploy Gate | 🔲 To Capture |
| **SS-14** | **CI/CD Pipeline** | Jenkins Pipeline Execution View *(When Jenkins active)* | Jenkins UI: `http://localhost:8080/job/smart-energy-monitor` | Blue Ocean or Stage View showing green stages passing end-to-end | 🔲 To Capture |
| **SS-15** | **Static Analysis** | SonarQube Project Config | VS Code / Editor: `sonar-project.properties` | Project key, exclusions, python coverage integration, and quality gate wait settings | 🔲 To Capture |
| **SS-16** | **Static Analysis** | SonarQube Dashboard *(When server active)* | SonarQube UI: `http://localhost:9000/dashboard?id=iot-smart-energy-monitoring` | Quality Gate PASSED status, Bugs: 0, Vulnerabilities: 0, Security Hotspots reviewed | 🔲 To Capture |
| **SS-17** | **Security Scanning** | Trivy Dependency / FS Scan | Terminal: `trivy fs --severity HIGH,CRITICAL .` | Console table output scanning filesystem dependencies (`requirements.txt`) | 🔲 To Capture |
| **SS-18** | **Security Scanning** | Trivy Container Image Scan | Terminal: `trivy image smart-energy-monitor:latest` | Console output showing container image vulnerability scan summary | 🔲 To Capture |
| **SS-19** | **Security Scanning** | Machine-Readable Scan Reports | VS Code / Explorer: `security/` directory | Show generated files `trivy-fs-report.json`, `trivy-image-report.json`, and `vulnerability-report-template.md` | 🔲 To Capture |
| **SS-20** | **Infrastructure as Code** | Terraform Core Architecture | VS Code / Editor: `terraform/main.tf` | Highlight VPC, public subnet, security group restricting port 8501, IAM SSM instance profile, IMDSv2, and user data Docker automation | 🔲 To Capture |
| **SS-21** | **Infrastructure as Code** | Terraform Variables & Outputs | VS Code / Editor: `terraform/variables.tf` & `outputs.tf` | Highlight configurable parameters, security comments, and output variables | 🔲 To Capture |
| **SS-22** | **Infrastructure as Code** | Terraform Validation CLI | Terminal: `terraform fmt -check` & `terraform validate` | Terminal showing clean formatting and `Success! The configuration is valid.` | 🔲 To Capture |

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
- Capture the full terminal showing `39 passed in 0.XXs` (**SS-08**).
- Open `results.xml` in VS Code split view alongside the terminal (**SS-09**).

### Category 3: Source Code & Configuration (SS-10, SS-11, SS-13, SS-15, SS-20, SS-21)
Open VS Code in `smart-energy-monitor`:
- Open `Dockerfile` (**SS-10**).
- Open `.dockerignore` (**SS-11**).
- Open `Jenkinsfile` (**SS-13**).
- Open `sonar-project.properties` (**SS-15**).
- Open `terraform/main.tf` and `terraform/variables.tf` side by side (**SS-20**, **SS-21**).

### Category 4: GitHub Repository (SS-06, SS-07)
- Push code to `https://github.com/vishwajeet1210/iot-smart-energy-monitoring` after review.
- Open repository in browser and capture root directory and commit log.

### Category 5: Security & Live Scans (SS-12, SS-14, SS-16, SS-17, SS-18, SS-22)
- Execute once Docker Desktop / Jenkins / SonarQube / Trivy tools are running or in CI environment.
