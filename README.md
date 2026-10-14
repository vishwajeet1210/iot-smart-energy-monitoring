# ⚡ IoT-Based Smart Energy Monitoring and Management System

> **DevSecOps Lab & SEP CIAP Micro Project**
> **Topic:** Requirements Analysis, Security Hardening, and Automated CI/CD for an IoT-Based Smart Energy Monitoring System
> **Repository:** [https://github.com/vishwajeet1210/iot-smart-energy-monitoring](https://github.com/vishwajeet1210/iot-smart-energy-monitoring)

A web-based Smart Energy Monitoring and Management System simulating an IoT-enabled telemetry environment. Demonstrates the complete pipeline: sensor simulation → SQLite persistence → analytics engine → real-time Streamlit dashboard, fully hardened with a complete **DevSecOps lifecycle** (SAST, SCA, Container Security, CI/CD with Jenkins, and Infrastructure as Code with Terraform on AWS).

---

## 🏗️ System & DevSecOps Architecture

### 1. Application Data Pipeline
```
┌─────────────────────────────┐
│   IoT Sensor Simulation     │  ← iot_simulator.py (6 Smart Appliances)
└─────────────┬───────────────┘
              │ Voltage / Current / Power Telemetry
              ▼
┌─────────────────────────────┐
│   Data Processing Layer     │  ← analytics.py (Pandas Aggregation)
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Database Layer (SQLite)   │  ← database.py (Repository pattern, WAL mode)
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Alert & Analytics Engine  │  ← alerts.py + analytics.py (Threshold Logic)
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Presentation Layer        │  ← app.py (Streamlit Web Dashboard)
└─────────────────────────────┘
```

### 2. DevSecOps CI/CD & Cloud Pipeline
```
[ Developer / Git Push ]
           │
           ▼
[ Jenkins Declarative Pipeline ]
   ├─ Stage 1: Checkout SCM
   ├─ Stage 2: Unit Testing (pytest + JUnit XML)
   ├─ Stage 3: SAST Code Quality & Security (SonarQube Scanner & Quality Gate)
   ├─ Stage 4: SCA Dependency Vulnerability Audit (Trivy fs -> JSON/SARIF)
   ├─ Stage 5: Hardened Docker Container Build (python:3.12-slim, non-root appuser)
   ├─ Stage 6: Container Image Security Scan (Trivy image -> JSON/SARIF)
   ├─ Stage 7: Terraform IaC Linting & Validation (fmt check, validate)
   └─ Stage 8: Production Deployment Gate (AWS EC2 / ECS with SSM & IMDSv2)
```

---

## 📁 Project Structure

```
smart-energy-monitor/
├── app.py                         # Streamlit web dashboard (Presentation Layer)
├── config.py                      # Centralized configuration & environment variable overrides
├── database.py                    # SQLite persistence layer (Repository pattern)
├── iot_simulator.py               # IoT sensor simulation engine
├── analytics.py                   # Energy calculations and time-series aggregation
├── alerts.py                      # Dynamic threshold alerting & energy tips
├── requirements.txt               # Production runtime Python dependencies
├── requirements-dev.txt           # Development & testing dependencies (includes pytest)
├── Dockerfile                     # Hardened container definition (non-root, health check, volume)
├── .dockerignore                  # Docker build context exclusions
├── Jenkinsfile                    # 10-stage declarative CI/CD pipeline
├── sonar-project.properties       # SonarQube project analysis configuration
├── .gitignore                     # Git tracking exclusions
├── README.md                      # Comprehensive project & DevSecOps documentation
│
├── data/                          # SQLite persistent volume mount point
│   └── energy.db                  # Local SQLite database (auto-generated at runtime)
│
├── security/                      # DevSecOps security audit resources
│   ├── vulnerability-report-template.md  # Standardized vulnerability & remediation report
│   ├── trivy-scan.sh              # Trivy scanning automation for Linux/CI
│   └── trivy-scan.ps1             # Trivy scanning automation for Windows PowerShell
│
├── terraform/                     # Infrastructure as Code (AWS deployment)
│   ├── main.tf                    # VPC, Subnet, Security Group, IAM SSM role, EC2 instance
│   ├── variables.tf               # Configurable infrastructure parameters
│   ├── outputs.tf                 # Deployed instance IP, URL, and security IDs
│   └── terraform.tfvars.example   # Sample input variable values
│
└── tests/
    └── test_system.py             # 39 passing automated pytest unit tests
```

---

## 🚀 1. Local Run & Testing

### Prerequisites
- Python 3.9 – 3.13
- Git

### Installation & Run
```bash
# Clone repository
git clone https://github.com/vishwajeet1210/iot-smart-energy-monitoring.git
cd iot-smart-energy-monitoring

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install production dependencies (or requirements-dev.txt for development & testing)
pip install -r requirements-dev.txt

# Launch Streamlit dashboard
streamlit run app.py
```
Access the dashboard in your browser at: **`http://localhost:8501`**

### Running Automated Test Suite
```bash
# Ensure test dependencies are installed
pip install -r requirements-dev.txt

# Run test suite
pytest -v
# Run with JUnit XML output for CI reporting
pytest -v --junitxml=results.xml tests/
```
*Current test suite status: **39/39 PASS**.*

---

## 🐳 2. Docker Containerization & Security Hardening

The application is packaged with a security-hardened container specification:
- **Base Image:** `python:3.12-slim` (Official minimal Debian 13 Trixie base)
- **Least Privilege:** Executes as unprivileged user `appuser` (UID `1001:1001`) with `/sbin/nologin`
- **Persistence:** Declared volume at `/app/data` ensuring SQLite readings persist across container restarts
- **Health Check:** Periodic polling of Streamlit's native health endpoint `http://localhost:8501/_stcore/health`
- **Network:** Streamlit bound to `0.0.0.0:8501`

### Build and Run Docker Container

```bash
# Build the production image
docker build -t smart-energy-monitor:latest .

# Run container with SQLite data volume mounted to local host
# Linux / macOS:
docker run -d \
  --name smart-energy-monitor \
  --restart unless-stopped \
  -p 8501:8501 \
  -v "$(pwd)/data:/app/data" \
  smart-energy-monitor:latest

# Windows PowerShell:
docker run -d `
  --name smart-energy-monitor `
  --restart unless-stopped `
  -p 8501:8501 `
  -v "${PWD}/data:/app/data" `
  smart-energy-monitor:latest
```

### Inspect Container Health & Logs
```bash
# Verify container is running and healthy
docker ps --filter "name=smart-energy-monitor"

# View logs
docker logs -f smart-energy-monitor
```

---

## 🛡️ 3. Security Vulnerability Scanning (Trivy)

Trivy audits software dependencies, system packages, and Docker image layers.

### Run Filesystem & Dependency Audit (SCA)
```bash
# Generate machine-readable JSON output
trivy fs --severity HIGH,CRITICAL --format json -o security/trivy-fs-report.json .

# Generate human-readable console table
trivy fs --severity HIGH,CRITICAL --format table .
```

### Run Container Image Security Audit
```bash
# Scan local container image and output JSON
trivy image --severity HIGH,CRITICAL --format json -o security/trivy-image-report.json smart-energy-monitor:latest

# Scan container image with console table
trivy image --severity HIGH,CRITICAL --format table smart-energy-monitor:latest
```

### Automated Scripts
- **Linux/CI:** `./security/trivy-scan.sh [image_name] [severity]`
- **Windows:** `.\security\trivy-scan.ps1 -ImageName smart-energy-monitor:latest`

### Vulnerability Report Template
Document and track all audit findings using the standardized template:
📄 **[`security/vulnerability-report-template.md`](file:///C:/Users/Vishwajeet/.gemini/antigravity-ide/scratch/smart-energy-monitor/security/vulnerability-report-template.md)**

---

## 🔍 4. Static Code Analysis (SonarQube)

Code quality, maintainability, and security smells are configured via `sonar-project.properties`.

### Server & Authentication Setup
1. Launch SonarQube locally or via Docker:
   ```bash
   docker run -d --name sonarqube -p 9000:9000 sonarqube:lts-community
   ```
2. Log in to SonarQube at `http://localhost:9000` (default credentials: `admin` / `admin`).
3. Generate an analysis token: **My Account** → **Security** → **Generate Token** (`SONAR_TOKEN`).
4. Set the environment variable:
   ```bash
   # Linux/macOS
   export SONAR_TOKEN="<your_generated_token>"
   export SONAR_HOST_URL="http://localhost:9000"

   # Windows PowerShell
   $env:SONAR_TOKEN="<your_generated_token>"
   $env:SONAR_HOST_URL="http://localhost:9000"
   ```

### Execute Scanner
```bash
# Run SonarScanner CLI
sonar-scanner \
  -Dsonar.host.url="${SONAR_HOST_URL}" \
  -Dsonar.token="${SONAR_TOKEN}"
```

---

## ⚙️ 5. Jenkins Declarative CI/CD Pipeline

The included `Jenkinsfile` provides an enterprise-ready pipeline executing on commit.

### Required Jenkins Plugins
1. **Pipeline** (Workflow Aggregator)
2. **Git Plugin**
3. **JUnit Plugin** (visualizes `results.xml`)
4. **SonarQube Scanner Plugin**
5. **Docker Pipeline Plugin**
6. **Credentials Binding Plugin**

### Pipeline Stages
1. **Checkout SCM:** Pulls source code from GitHub repository.
2. **Setup & Dependencies:** Installs Python virtual environment and dependencies.
3. **Unit Tests & Coverage:** Runs 39 pytest tests and publishes JUnit test reports.
4. **SonarQube Static Analysis:** Runs SAST scans using SonarScanner.
5. **SonarQube Quality Gate:** Blocks pipeline if code smells or security gates fail.
6. **Trivy Dependency Scan:** Audits dependencies and stores `trivy-fs-report.json`.
7. **Docker Build:** Builds hardened container image with build number tags.
8. **Trivy Image Scan:** Audits container image layers for CVEs before push.
9. **Terraform IaC Validation:** Runs `terraform fmt` and `terraform validate`.
10. **Deployment Gate:** Interactive approval gate for deployment to AWS Cloud.

---

## ☁️ 6. Infrastructure as Code (Terraform on AWS)

The `terraform/` directory provides complete Infrastructure as Code for deploying the containerized monitoring application on AWS.

### Architecture Highlights
- **VPC & Subnet:** Isolated VPC (`10.0.0.0/16`) with public subnet and Internet Gateway.
- **Security Group:** Ingress restricted to application port `8501` (`allowed_ingress_cidrs`). Optional SSH port 22 disabled by default.
- **IAM Instance Profile:** Attaches `AmazonSSMManagedInstanceCore` allowing zero-open-port management via AWS Systems Manager.
- **Storage Encryption:** Root EBS volume encrypted with KMS (`encrypted = true`).
- **Metadata Protection:** Enforces IMDSv2 (`http_tokens = "required"`) to prevent SSRF credential exfiltration.
- **EC2 Compute & User Data:** Automatically installs Docker, creates persistent host storage `/var/data/energy`, and starts container.

### Terraform Validation Commands (Without AWS Account)
```bash
cd terraform

# Format check
terraform fmt -check

# Initialize providers without cloud backend
terraform init -backend=false

# Validate syntax and configuration integrity
terraform validate
```

### Terraform Deployment Commands (When AWS Account Available)
```bash
# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars

# Initialize and plan
terraform init
terraform plan -out=tfplan

# Apply deployment
terraform apply tfplan

# Access output URL:
terraform output application_url
```

---

## 🔒 7. DevSecOps Security Controls Summary

| Security Layer | Implementation Details | Validation Standard |
| :--- | :--- | :--- |
| **Code Quality (SAST)** | SonarQube with `sonar-project.properties` | SonarQube Quality Gate |
| **Dependency Security (SCA)**| Trivy filesystem scanning | Zero CRITICAL / HIGH CVEs |
| **Container Hardening** | Non-root `appuser:1001`, `python:3.12-slim`, healthcheck | CIS Docker Benchmark |
| **Image Vulnerability** | Trivy container image scan before deployment | JSON & SARIF reports |
| **Data Persistence** | Volume isolation at `/app/data` for SQLite | Writable by UID 1001 only |
| **Cloud Network Security** | AWS Security Group with configurable ingress CIDR | Least Privilege Ingress |
| **Cloud IAM & Access** | AWS Systems Manager (SSM) instead of open SSH | Zero open management ports |
| **Instance Hardening** | Encrypted EBS storage + IMDSv2 strictly enforced | AWS Well-Architected Security |

---

## 👥 Contributors & License

- **Author:** Vishwajeet ([@vishwajeet1210](https://github.com/vishwajeet1210))
- **Course:** DevSecOps Lab CIAP Micro Project
- **License:** MIT License
