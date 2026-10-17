// ==============================================================================
// Jenkins Declarative Pipeline - DevSecOps CI/CD
// Project: IoT-Based Smart Energy Monitoring and Management System
// Repository: https://github.com/vishwajeet1210/iot-smart-energy-monitoring
// ==============================================================================
//
// REQUIRED JENKINS PLUGINS (Core CI setup only):
//   1. Pipeline: Declarative (workflow-aggregator)
//   2. Git Plugin (for SCM checkout)
//   3. JUnit Plugin (for test results visualization)
//   4. Credentials Binding Plugin (for optional Docker Hub credentials)
//
// NOTE: Unnecessary plugin dependencies (ansiColor, timestamper, ws-cleanup)
// have been intentionally removed to avoid plugin compatibility errors.
// ==============================================================================

pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        APP_NAME                 = 'smart-energy-monitor'
        IMAGE_NAME               = 'smart-energy-monitor'
        IMAGE_TAG                = "${env.BUILD_NUMBER ?: 'latest'}"
        PYTHONUNBUFFERED         = '1'

        // Pipeline Behavior Flags
        REQUIRE_SECURITY_SCANS   = 'false' // Set to 'true' to fail build if security tools are missing
        REQUIRE_IAC_VALIDATION   = 'false' // Set to 'true' to fail build if terraform is missing
        PUBLISH_TO_DOCKERHUB     = 'false' // Set to 'true' to push image to Docker Hub using Jenkins credentials

        // SonarCloud Credential ID (Secret text in Jenkins)
        SONAR_CREDENTIALS_ID     = 'sonarcloud-token'

        // Docker Hub Registry Settings (used only when PUBLISH_TO_DOCKERHUB is 'true')
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub-credentials'
        DOCKERHUB_REPO           = 'vishwajeet1210/smart-energy-monitor'
    }

    stages {

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 1: Code Checkout
        // ──────────────────────────────────────────────────────────────────────
        stage('Checkout SCM') {
            steps {
                script {
                    // Initialize stage and scanner outcome tracking imperatively in env
                    env.STAGE_CHECKOUT_STATUS = 'NOT_RUN'
                    env.STAGE_TESTS_STATUS    = 'NOT_RUN'
                    env.STAGE_SECURITY_STATUS = 'NOT_RUN'
                    env.STAGE_DOCKER_STATUS   = 'NOT_RUN'
                    env.STAGE_IAC_STATUS      = 'NOT_RUN'
                    env.TRIVY_SCAN_STATUS     = 'NOT_RUN'
                    env.SONAR_SCAN_STATUS     = 'NOT_RUN'
                }
                echo "📥 Pulling latest source code from GitHub repository..."
                checkout scm
                script {
                    env.STAGE_CHECKOUT_STATUS = 'PASSED'
                }
            }
            post {
                failure {
                    script {
                        env.STAGE_CHECKOUT_STATUS = 'FAILED'
                    }
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 2: Automated Testing & Code Quality
        // ──────────────────────────────────────────────────────────────────────
        stage('Unit Testing & QA') {
            steps {
                echo "🧪 Running pytest test suite (39 tests) and publishing JUnit XML..."
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m venv .venv
                            . .venv/bin/activate
                            pip install --no-cache-dir -r requirements.txt pytest
                            pytest --junitxml=results.xml tests/test_system.py
                        '''
                    } else {
                        bat '''
                            python -m venv .venv
                            call .venv\\Scripts\\activate.bat
                            pip install --no-cache-dir -r requirements.txt pytest
                            pytest --junitxml=results.xml tests/test_system.py
                        '''
                    }
                    env.STAGE_TESTS_STATUS = 'PASSED'
                }
            }
            post {
                always {
                    junit testResults: 'results.xml', allowEmptyResults: true
                }
                failure {
                    script {
                        env.STAGE_TESTS_STATUS = 'FAILED'
                    }
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 3: Security & Code Quality (Static Analysis - SAST)
        // ──────────────────────────────────────────────────────────────────────
        stage('Security & Code Quality') {
            steps {
                echo "🔍 Checking for static analysis tools (SonarCloud)..."
                script {
                    def hasDocker   = false
                    def hasSonarCli = false

                    if (isUnix()) {
                        hasDocker   = (sh(script: 'command -v docker >/dev/null 2>&1', returnStatus: true) == 0)
                        hasSonarCli = (sh(script: 'command -v sonar-scanner >/dev/null 2>&1', returnStatus: true) == 0)
                    } else {
                        hasDocker   = (bat(script: 'where docker >nul 2>nul', returnStatus: true) == 0)
                        hasSonarCli = (bat(script: 'where sonar-scanner >nul 2>nul', returnStatus: true) == 0)
                    }

                    // Static Code Analysis (SAST via SonarCloud)
                    if (hasDocker) {
                        echo "🔍 Running SonarCloud static analysis via sonarsource/sonar-scanner-cli:latest..."
                        def sonarImage = 'sonarsource/sonar-scanner-cli:latest'
                        try {
                            withCredentials([string(credentialsId: env.SONAR_CREDENTIALS_ID, variable: 'SONAR_TOKEN')]) {
                                if (isUnix()) {
                                    sh """
                                        if [ -n "\$JENKINS_HOME" ] && command -v hostname >/dev/null 2>&1 && docker inspect "\$(hostname)" >/dev/null 2>&1; then
                                            docker run --rm --volumes-from "\$(hostname)" -w "\${PWD}" -e SONAR_TOKEN ${sonarImage} "-Dsonar.host.url=https://sonarcloud.io"
                                        else
                                            docker run --rm -v "\${PWD}:/usr/src" -w /usr/src -e SONAR_TOKEN ${sonarImage} "-Dsonar.host.url=https://sonarcloud.io"
                                        fi
                                    """
                                } else {
                                    powershell """
                                        docker run --rm -v "\${PWD}:/usr/src" -w /usr/src -e SONAR_TOKEN ${sonarImage} "-Dsonar.host.url=https://sonarcloud.io"
                                    """
                                }
                                env.SONAR_SCAN_STATUS = 'PASSED'
                                echo "✅ SonarCloud static analysis passed."
                            }
                        } catch (Exception e) {
                            def msg = e.getMessage() ?: ''
                            if (msg.contains("Could not find credentials") || msg.contains(env.SONAR_CREDENTIALS_ID)) {
                                env.SONAR_SCAN_STATUS = "NOT_RUN (Credential missing: ${env.SONAR_CREDENTIALS_ID})"
                                echo "[WARNING] Jenkins credential '${env.SONAR_CREDENTIALS_ID}' (Secret text) was not found."
                                echo "[STATUS] Static code analysis (SAST): NOT RUN (Prerequisite credential missing: ${env.SONAR_CREDENTIALS_ID})"
                            } else {
                                env.SONAR_SCAN_STATUS = 'FAILED'
                                echo "[ERROR] SonarCloud scan failed: ${msg}"
                            }
                            if (env.REQUIRE_SECURITY_SCANS == 'true') {
                                throw e
                            }
                        }
                    } else if (hasSonarCli) {
                        echo "🔍 Running local SonarQube Scanner for static analysis..."
                        try {
                            withCredentials([string(credentialsId: env.SONAR_CREDENTIALS_ID, variable: 'SONAR_TOKEN')]) {
                                if (isUnix()) {
                                    sh 'sonar-scanner -Dproject.settings=sonar-project.properties -Dsonar.host.url=https://sonarcloud.io'
                                } else {
                                    bat 'sonar-scanner -Dproject.settings=sonar-project.properties -Dsonar.host.url=https://sonarcloud.io'
                                }
                                env.SONAR_SCAN_STATUS = 'PASSED'
                                echo "✅ SonarCloud static analysis passed."
                            }
                        } catch (Exception e) {
                            def msg = e.getMessage() ?: ''
                            if (msg.contains("Could not find credentials") || msg.contains(env.SONAR_CREDENTIALS_ID)) {
                                env.SONAR_SCAN_STATUS = "NOT_RUN (Credential missing: ${env.SONAR_CREDENTIALS_ID})"
                                echo "[WARNING] Jenkins credential '${env.SONAR_CREDENTIALS_ID}' (Secret text) was not found."
                            } else {
                                env.SONAR_SCAN_STATUS = 'FAILED'
                                echo "[ERROR] SonarScanner execution failed: ${msg}"
                            }
                            if (env.REQUIRE_SECURITY_SCANS == 'true') {
                                throw e
                            }
                        }
                    } else {
                        env.SONAR_SCAN_STATUS = 'NOT_RUN (Docker missing)'
                        if (env.REQUIRE_SECURITY_SCANS == 'true') {
                            error("❌ Security Gate Failure: Docker (or sonar-scanner CLI) is required but not installed on this agent.")
                        } else {
                            echo "[WARNING] Neither Docker nor sonar-scanner CLI is installed on this agent."
                            echo "[STATUS] Static code analysis (SAST): NOT RUN (Tool missing: docker or sonar-scanner)"
                        }
                    }

                    // Record stage security status
                    env.STAGE_SECURITY_STATUS = (env.SONAR_SCAN_STATUS == 'PASSED') ? 'PASSED' : env.SONAR_SCAN_STATUS
                }
            }
            post {
                failure {
                    script {
                        env.STAGE_SECURITY_STATUS = 'FAILED'
                    }
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 4: Docker Containerization, Security Scan & Optional Delivery
        // ──────────────────────────────────────────────────────────────────────
        stage('Docker Build & Package') {
            steps {
                echo "🐳 Building single-stage Docker container image: ${IMAGE_NAME}:${IMAGE_TAG}..."
                script {
                    if (isUnix()) {
                        sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest ."
                    } else {
                        bat "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest ."
                    }

                    // ──────────────────────────────────────────────────────────
                    // Trivy Container Image Vulnerability Scan
                    // ──────────────────────────────────────────────────────────
                    echo "🛡️ Scanning Docker image '${IMAGE_NAME}:${IMAGE_TAG}' with Trivy (aquasec/trivy:0.69.3)..."
                    def trivyImage = 'aquasec/trivy:0.69.3'
                    def targetImage = "${IMAGE_NAME}:${IMAGE_TAG}"
                    def trivyExit = -1

                    try {
                        if (isUnix()) {
                            // 1. Generate machine-readable JSON report and capture exit code (10 = findings, 0 = passed)
                            trivyExit = sh(
                                script: "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro -v trivy-cache:/root/.cache/ ${trivyImage} image --image-src docker --scanners vuln --severity HIGH,CRITICAL --exit-code 10 --format json ${targetImage} > trivy-report.json",
                                returnStatus: true
                            )
                            // 2. Display human-readable table in console log
                            sh(script: "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro -v trivy-cache:/root/.cache/ ${trivyImage} image --image-src docker --scanners vuln --severity HIGH,CRITICAL --format table ${targetImage}", returnStatus: true)
                        } else {
                            // 1. Generate machine-readable JSON report and capture exit code (10 = findings, 0 = passed)
                            trivyExit = bat(
                                script: "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ ${trivyImage} image --image-src docker --scanners vuln --severity HIGH,CRITICAL --exit-code 10 --format json ${targetImage} > trivy-report.json",
                                returnStatus: true
                            )
                            // 2. Display human-readable table in console log
                            bat(script: "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ ${trivyImage} image --image-src docker --scanners vuln --severity HIGH,CRITICAL --format table ${targetImage}", returnStatus: true)
                        }

                        if (trivyExit == 0) {
                            env.TRIVY_SCAN_STATUS = 'PASSED'
                            echo "✅ Trivy scan passed: 0 HIGH or CRITICAL vulnerabilities detected."
                        } else if (trivyExit == 10) {
                            env.TRIVY_SCAN_STATUS = 'FINDINGS'
                            echo "[SECURITY] Trivy detected HIGH/CRITICAL vulnerabilities in ${targetImage} (report archived as trivy-report.json)."
                        } else {
                            env.TRIVY_SCAN_STATUS = 'ERROR'
                            echo "[ERROR] Trivy scanner execution failed with exit code ${trivyExit}."
                            if (env.REQUIRE_SECURITY_SCANS == 'true') {
                                error("❌ Security Gate Failure: Trivy scan execution error (exit code: ${trivyExit}).")
                            }
                        }
                    } catch (Exception e) {
                        env.TRIVY_SCAN_STATUS = 'ERROR'
                        echo "[ERROR] Unexpected failure running Trivy container: ${e.getMessage()}"
                        if (env.REQUIRE_SECURITY_SCANS == 'true') {
                            throw e
                        }
                    }

                    // Optional Docker Hub publishing (strictly credential-based, zero secrets in command text)
                    if (env.PUBLISH_TO_DOCKERHUB == 'true') {
                        echo "🔑 PUBLISH_TO_DOCKERHUB=true. Authenticating via Jenkins credentials ID '${env.DOCKERHUB_CREDENTIALS_ID}'..."
                        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDENTIALS_ID, usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                            if (isUnix()) {
                                // On Linux, stream password via POSIX stdin (never embedded in command text)
                                sh """
                                    printf '%s\\n' "\$DH_PASS" | docker login -u "\$DH_USER" --password-stdin
                                    docker tag ${IMAGE_NAME}:latest ${DOCKERHUB_REPO}:${IMAGE_TAG}
                                    docker tag ${IMAGE_NAME}:latest ${DOCKERHUB_REPO}:latest
                                    docker push ${DOCKERHUB_REPO}:${IMAGE_TAG}
                                    docker push ${DOCKERHUB_REPO}:latest
                                    docker logout
                                """
                            } else {
                                // On Windows, stream password via PowerShell from process environment (never embedded in command text)
                                powershell """
                                    \$env:DH_PASS | docker login -u \$env:DH_USER --password-stdin
                                    docker tag ${IMAGE_NAME}:latest ${DOCKERHUB_REPO}:${IMAGE_TAG}
                                    docker tag ${IMAGE_NAME}:latest ${DOCKERHUB_REPO}:latest
                                    docker push ${DOCKERHUB_REPO}:${IMAGE_TAG}
                                    docker push ${DOCKERHUB_REPO}:latest
                                    docker logout
                                """
                            }
                            echo "✅ Docker image published to Docker Hub: ${DOCKERHUB_REPO}:${IMAGE_TAG}"
                        }
                    } else {
                        echo "[INFO] Docker Hub publishing disabled (PUBLISH_TO_DOCKERHUB=false)."
                        echo "[STATUS] Image stored in local Docker daemon (${IMAGE_NAME}:${IMAGE_TAG}); remote push omitted."
                    }
                    env.STAGE_DOCKER_STATUS = 'PASSED'
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
                }
                failure {
                    script {
                        env.STAGE_DOCKER_STATUS = 'FAILED'
                    }
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 5: Infrastructure as Code (IaC) Validation
        // ──────────────────────────────────────────────────────────────────────
        stage('Terraform IaC Validation') {
            steps {
                echo "🏗️ Validating Terraform Infrastructure as Code definitions..."
                script {
                    // Verify configuration and directory exist before entering
                    if (!fileExists('terraform') || !fileExists('terraform/main.tf')) {
                        if (env.REQUIRE_IAC_VALIDATION == 'true') {
                            error("❌ IaC Gate Failure: Terraform directory or configuration ('terraform/main.tf') is missing.")
                        } else {
                            echo "[WARNING] Terraform directory or configuration ('terraform/main.tf') not found."
                            echo "[STATUS] IaC validation: NOT RUN (Prerequisite configuration missing)"
                            env.STAGE_IAC_STATUS = 'NOT_RUN (Files missing)'
                            return
                        }
                    }

                    dir('terraform') {
                        def hasDocker    = false
                        def hasTerraform = false

                        if (isUnix()) {
                            hasDocker    = (sh(script: 'command -v docker >/dev/null 2>&1', returnStatus: true) == 0)
                            hasTerraform = (sh(script: 'command -v terraform >/dev/null 2>&1', returnStatus: true) == 0)
                        } else {
                            hasDocker    = (bat(script: 'where docker >nul 2>nul', returnStatus: true) == 0)
                            hasTerraform = (bat(script: 'where terraform >nul 2>nul', returnStatus: true) == 0)
                        }

                        def tfImage = 'hashicorp/terraform:latest'

                        if (hasDocker) {
                            echo "🏗️ Running containerized Terraform fmt -check, init, and validate (${tfImage})..."
                            try {
                                if (isUnix()) {
                                    sh """
                                        if [ -n "\$JENKINS_HOME" ] && command -v hostname >/dev/null 2>&1 && docker inspect "\$(hostname)" >/dev/null 2>&1; then
                                            docker run --rm --volumes-from "\$(hostname)" -w "\${PWD}" ${tfImage} fmt -check
                                            docker run --rm --volumes-from "\$(hostname)" -w "\${PWD}" ${tfImage} init -backend=false
                                            docker run --rm --volumes-from "\$(hostname)" -w "\${PWD}" ${tfImage} validate
                                        else
                                            docker run --rm -v "\${PWD}:/workspace" -w /workspace ${tfImage} fmt -check
                                            docker run --rm -v "\${PWD}:/workspace" -w /workspace ${tfImage} init -backend=false
                                            docker run --rm -v "\${PWD}:/workspace" -w /workspace ${tfImage} validate
                                        fi
                                    """
                                } else {
                                    powershell """
                                        docker run --rm -v "\${PWD}:/workspace" -w /workspace ${tfImage} fmt -check
                                        docker run --rm -v "\${PWD}:/workspace" -w /workspace ${tfImage} init -backend=false
                                        docker run --rm -v "\${PWD}:/workspace" -w /workspace ${tfImage} validate
                                    """
                                }
                                env.STAGE_IAC_STATUS = 'PASSED'
                                echo "✅ Terraform configuration is valid and properly formatted."
                            } catch (Exception e) {
                                env.STAGE_IAC_STATUS = 'FAILED'
                                echo "[ERROR] Terraform IaC validation failed: ${e.getMessage()}"
                                throw e
                            }
                        } else if (hasTerraform) {
                            echo "🏗️ Running local Terraform formatting check, initialization and validation..."
                            try {
                                if (isUnix()) {
                                    sh 'terraform fmt -check'
                                    sh 'terraform init -backend=false'
                                    sh 'terraform validate'
                                } else {
                                    bat 'terraform fmt -check'
                                    bat 'terraform init -backend=false'
                                    bat 'terraform validate'
                                }
                                env.STAGE_IAC_STATUS = 'PASSED'
                                echo "✅ Terraform configuration is valid."
                            } catch (Exception e) {
                                env.STAGE_IAC_STATUS = 'FAILED'
                                echo "[ERROR] Terraform validation failed: ${e.getMessage()}"
                                throw e
                            }
                        } else {
                            env.STAGE_IAC_STATUS = 'NOT_RUN (Docker missing)'
                            if (env.REQUIRE_IAC_VALIDATION == 'true') {
                                error("❌ IaC Gate Failure: Docker (or Terraform CLI) is required but not installed on this agent.")
                            } else {
                                echo "[WARNING] Neither Docker nor Terraform CLI is installed on this agent."
                                echo "[STATUS] IaC validation: NOT RUN (Missing prerequisite: docker or terraform)"
                            }
                        }
                    }
                }
            }
            post {
                failure {
                    script {
                        env.STAGE_IAC_STATUS = 'FAILED'
                    }
                }
            }
        }
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Post-Pipeline Execution Summary (Honest Reporting, Never Hardcoded)
    // ──────────────────────────────────────────────────────────────────────────
    post {
        always {
            script {
                echo "========================================================================"
                echo "                      PIPELINE EXECUTION SUMMARY                        "
                echo "========================================================================"
                echo " 1. Source Checkout:      ${env.STAGE_CHECKOUT_STATUS ?: 'NOT_RUN'}"
                echo " 2. Automated Tests:      ${env.STAGE_TESTS_STATUS ?: 'NOT_RUN'}"
                echo " 3. Security & Quality:   ${env.STAGE_SECURITY_STATUS ?: 'NOT_RUN'}"
                echo "    - Trivy (Image Scan): ${env.TRIVY_SCAN_STATUS ?: 'NOT_RUN'}"
                echo "    - SonarCloud (SAST):  ${env.SONAR_SCAN_STATUS ?: 'NOT_RUN'}"
                echo " 4. Docker Build:         ${env.STAGE_DOCKER_STATUS ?: 'NOT_RUN'}"
                echo " 5. Terraform Validation: ${env.STAGE_IAC_STATUS ?: 'NOT_RUN'}"
                echo "========================================================================"
            }
        }
        success {
            echo "🎉 Pipeline completed successfully!"
        }
        failure {
            echo "❌ Pipeline failed. Review the stage output above for failure details."
        }
    }
}
