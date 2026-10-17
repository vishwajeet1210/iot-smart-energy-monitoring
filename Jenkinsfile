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
        // STAGE 3: Security & Code Quality (SAST & SCA)
        // ──────────────────────────────────────────────────────────────────────
        stage('Security & Code Quality') {
            steps {
                echo "🔍 Checking for security tools and running static/dependency scans..."
                script {
                    def hasTrivy = false
                    def hasSonar = false

                    if (isUnix()) {
                        hasTrivy = (sh(script: 'command -v trivy >/dev/null 2>&1', returnStatus: true) == 0)
                        hasSonar = (sh(script: 'command -v sonar-scanner >/dev/null 2>&1', returnStatus: true) == 0)
                    } else {
                        hasTrivy = (bat(script: 'where trivy >nul 2>nul', returnStatus: true) == 0)
                        hasSonar = (bat(script: 'where sonar-scanner >nul 2>nul', returnStatus: true) == 0)
                    }

                    // 1. Dependency Vulnerability Scan (SCA via Trivy)
                    if (hasTrivy) {
                        echo "🛡️ Running Trivy dependency vulnerability scan..."
                        try {
                            if (isUnix()) {
                                sh 'trivy fs --severity HIGH,CRITICAL --format table .'
                            } else {
                                bat 'trivy fs --severity HIGH,CRITICAL --format table .'
                            }
                            env.TRIVY_SCAN_STATUS = 'PASSED'
                        } catch (Exception e) {
                            env.TRIVY_SCAN_STATUS = 'FAILED'
                            throw e
                        }
                    } else {
                        env.TRIVY_SCAN_STATUS = 'NOT_RUN (CLI missing)'
                        if (env.REQUIRE_SECURITY_SCANS == 'true') {
                            error("❌ Security Gate Failure: Trivy CLI is required but not installed on this agent.")
                        } else {
                            echo "[WARNING] Trivy CLI is not installed on this agent."
                            echo "[STATUS] Dependency vulnerability scan (SCA): NOT RUN (Tool missing: trivy)"
                        }
                    }

                    // 2. Static Code Analysis (SAST via SonarQube Scanner)
                    if (hasSonar) {
                        echo "🔍 Running SonarQube Scanner for static analysis..."
                        try {
                            if (isUnix()) {
                                sh 'sonar-scanner -Dproject.settings=sonar-project.properties'
                            } else {
                                bat 'sonar-scanner -Dproject.settings=sonar-project.properties'
                            }
                            env.SONAR_SCAN_STATUS = 'PASSED'
                        } catch (Exception e) {
                            env.SONAR_SCAN_STATUS = 'FAILED'
                            throw e
                        }
                    } else {
                        env.SONAR_SCAN_STATUS = 'NOT_RUN (CLI missing)'
                        if (env.REQUIRE_SECURITY_SCANS == 'true') {
                            error("❌ Security Gate Failure: SonarQube Scanner is required but not installed on this agent.")
                        } else {
                            echo "[WARNING] SonarQube Scanner is not installed or configured on this agent."
                            echo "[STATUS] Static code analysis (SAST): NOT RUN (Tool missing: sonar-scanner)"
                        }
                    }

                    // Determine overall security stage status
                    if (env.TRIVY_SCAN_STATUS == 'PASSED' && env.SONAR_SCAN_STATUS == 'PASSED') {
                        env.STAGE_SECURITY_STATUS = 'PASSED (Both Trivy & SonarQube executed)'
                    } else if (env.TRIVY_SCAN_STATUS == 'PASSED' || env.SONAR_SCAN_STATUS == 'PASSED') {
                        def missing = (env.TRIVY_SCAN_STATUS != 'PASSED') ? 'Trivy missing' : 'SonarQube missing'
                        env.STAGE_SECURITY_STATUS = "PARTIAL (${missing})"
                    } else {
                        env.STAGE_SECURITY_STATUS = 'NOT_RUN (Both scanner tools missing)'
                    }
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
        // STAGE 4: Docker Containerization & Optional Registry Delivery
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
                        def hasTerraform = false

                        if (isUnix()) {
                            hasTerraform = (sh(script: 'command -v terraform >/dev/null 2>&1', returnStatus: true) == 0)
                        } else {
                            hasTerraform = (bat(script: 'where terraform >nul 2>nul', returnStatus: true) == 0)
                        }

                        if (hasTerraform) {
                            echo "🏗️ Running Terraform initialization and validation..."
                            if (isUnix()) {
                                sh 'terraform init -backend=false'
                                sh 'terraform validate'
                            } else {
                                bat 'terraform init -backend=false'
                                bat 'terraform validate'
                            }
                            env.STAGE_IAC_STATUS = 'PASSED'
                            echo "✅ Terraform configuration is valid."
                        } else {
                            env.STAGE_IAC_STATUS = 'NOT_RUN (CLI missing)'
                            if (env.REQUIRE_IAC_VALIDATION == 'true') {
                                error("❌ IaC Gate Failure: Terraform CLI is required but not installed on this agent.")
                            } else {
                                echo "[WARNING] Terraform CLI is not installed on this agent."
                                echo "[STATUS] IaC validation: NOT RUN (Missing prerequisite: terraform)"
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
                echo "    - Trivy (SCA):        ${env.TRIVY_SCAN_STATUS ?: 'NOT_RUN'}"
                echo "    - SonarQube (SAST):   ${env.SONAR_SCAN_STATUS ?: 'NOT_RUN'}"
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
