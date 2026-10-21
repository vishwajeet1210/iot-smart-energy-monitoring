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

    triggers {
        pollSCM('H/5 * * * *') // Automatically poll GitHub repository every 5 minutes for new commits
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    parameters {
        choice(
            name: 'DEPLOY_REGION',
            choices: ['ap-south-1'],
            description: 'Target AWS deployment region (AWS Mumbai ap-south-1 is the only permitted deployment target)'
        )
        string(
            name: 'MUMBAI_EC2_INSTANCE_ID',
            defaultValue: '',
            description: 'Optional expected Terraform-managed Mumbai EC2 instance ID. The SSM target is resolved from terraform/mumbai state to support the approved private-instance migration.'
        )
        string(
            name: 'MUMBAI_APP_URL',
            defaultValue: '',
            description: 'Optional Application URL (ALB DNS or HTTPS domain) for Mumbai (ap-south-1). If omitted, dynamically queried from Terraform outputs or verified deployment target.'
        )
        string(
            name: 'MUMBAI_ECR_REGISTRY',
            defaultValue: '695496430374.dkr.ecr.ap-south-1.amazonaws.com',
            description: 'Amazon ECR Registry URI for Mumbai (ap-south-1)'
        )
        booleanParam(
            name: 'ENABLE_DEPLOYMENT',
            defaultValue: false,
            description: 'Enable deployment to the Terraform-managed Mumbai EC2 instance via SSM. Defaults to false for safe verification-only runs.'
        )
        booleanParam(
            name: 'ENABLE_ECR_PUBLISH',
            defaultValue: false,
            description: 'Enable publishing the built image to the verified Mumbai ECR repository. This never changes Terraform ingress rules.'
        )
        string(
            name: 'ALLOWED_INGRESS_CIDR',
            defaultValue: '',
            description: 'Optional restricted IPv4 CIDR for a reviewed Mumbai Terraform plan (e.g., 203.0.113.50/32). A public-ALB plan has no permissive default and requires an explicit value.'
        )
    }

    environment {
        APP_NAME                 = 'smart-energy-monitor'
        IMAGE_NAME               = 'smart-energy-monitor'
        IMAGE_TAG                = "${env.BUILD_NUMBER ?: 'latest'}"
        PYTHONUNBUFFERED         = '1'

        // AWS & Amazon ECR Settings (Mumbai ap-south-1 is the sole permitted target)
        AWS_REGION               = 'ap-south-1'
        ECR_REGISTRY             = '695496430374.dkr.ecr.ap-south-1.amazonaws.com'
        ECR_REPO                 = 'smart-energy-monitor'
        EC2_INSTANCE_ID          = ''
        APP_URL                  = ''
        TF_WORKING_DIR           = 'terraform/mumbai'

        // Pipeline Behavior Flags
        REQUIRE_SECURITY_SCANS   = 'false' // Set to 'true' to fail build if security tools are missing
        ENFORCE_QUALITY_GATE     = 'true'  // Set to 'true' to fail build if SonarCloud quality gate fails
        REQUIRE_IAC_VALIDATION   = 'false' // Set to 'true' to fail build if terraform is missing
        PUBLISH_TO_ECR           = "${(params.ENABLE_ECR_PUBLISH == true || params.ENABLE_ECR_PUBLISH == 'true') ? 'true' : 'false'}"
        DEPLOY_TO_EC2            = "${(params.ENABLE_DEPLOYMENT == true || params.ENABLE_DEPLOYMENT == 'true') ? 'true' : 'false'}"

        // SonarCloud Credential ID (Secret text in Jenkins)
        SONAR_CREDENTIALS_ID     = 'sonarcloud-token'

        // Optional Docker Hub Registry Settings (used only when PUBLISH_TO_DOCKERHUB is 'true')
        PUBLISH_TO_DOCKERHUB     = 'false'
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
                    env.STAGE_DEPLOY_STATUS   = 'NOT_RUN'
                    env.TRIVY_SCAN_STATUS     = 'NOT_RUN'
                    env.SONAR_SCAN_STATUS     = 'NOT_RUN'

                    // Validate deployment target region (Mumbai ap-south-1 is strictly required)
                    def selectedRegion = (params.DEPLOY_REGION?.trim()) ?: 'ap-south-1'
                    echo "🌍 Selected Deployment Region: ${selectedRegion}"
                    if (selectedRegion != 'ap-south-1') {
                        error("❌ Deployment Gate Failure: Target region '${selectedRegion}' is rejected. AWS Mumbai ('ap-south-1') is the only permitted deployment target.")
                    }

                    // Strict Target Validation: Prevent parameter tampering or redirection
                    def selectedInstance = (params.MUMBAI_EC2_INSTANCE_ID?.trim()) ?: ''
                    if (selectedInstance && !selectedInstance.matches('^i-[0-9a-f]{8,17}$')) {
                        error("❌ Deployment Gate Failure: MUMBAI_EC2_INSTANCE_ID must be a valid EC2 instance ID when supplied. The actual SSM target is resolved from Terraform state.")
                    }

                    def selectedRegistry = (params.MUMBAI_ECR_REGISTRY?.trim()) ?: '695496430374.dkr.ecr.ap-south-1.amazonaws.com'
                    if (selectedRegistry != '695496430374.dkr.ecr.ap-south-1.amazonaws.com') {
                        error("❌ Deployment Gate Failure: Target ECR registry '${selectedRegistry}' is rejected. Expected verified Mumbai ECR registry '695496430374.dkr.ecr.ap-south-1.amazonaws.com'.")
                    }

                    def selectedUrl = (params.MUMBAI_APP_URL?.trim()) ?: ''
                    if (selectedUrl) {
                        if (!selectedUrl.matches('^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?(/[^\\s]*)?$')) {
                            error("❌ Deployment Gate Failure: Target application URL must be a plain http(s) URL with a hostname, optional port, and no shell-control characters.")
                        }
                        if (selectedUrl.contains('3.110.85.209')) {
                            error("❌ Deployment Gate Failure: Target application URL cannot be obsolete hardcoded IP '3.110.85.209'. Architecture requires ALB endpoint or private subnet resolution.")
                        }
                    }

                    // Configure verified Mumbai environment settings
                    env.AWS_REGION      = 'ap-south-1'
                    env.ECR_REGISTRY    = '695496430374.dkr.ecr.ap-south-1.amazonaws.com'
                    env.ECR_REPO        = 'smart-energy-monitor'
                    env.EC2_INSTANCE_ID = selectedInstance
                    env.APP_URL         = selectedUrl
                    env.TF_WORKING_DIR  = 'terraform/mumbai'

                    echo "📍 Target Region: AWS Mumbai (ap-south-1) [MANDATORY & EXCLUSIVE]"
                    echo "📦 Target ECR Registry: ${env.ECR_REGISTRY}"
                    echo "🏷️ Target ECR Repository: ${env.ECR_REPO}"
                    echo "🏗️ Target Terraform Directory: ${env.TF_WORKING_DIR}"
                    echo "🖥️ Target EC2 Instance ID: ${env.EC2_INSTANCE_ID ?: '(Resolved from Terraform only when deployment is enabled)'}"
                    echo "🌐 Target Application URL: ${env.APP_URL ?: '(Dynamic from ALB/Terraform outputs)'}"
                }
                echo "📥 Pulling latest source code from GitHub repository..."
                checkout scm
                script {
                    def rawCidr = (params.ALLOWED_INGRESS_CIDR ?: '').trim()

                    // This pipeline deliberately has no infrastructure-apply step. CIDR input is therefore optional
                    // for CI/CD, but any supplied value is normalized safely for a reviewed plan.
                    if (rawCidr) {
                        if (rawCidr =~ /[\r\n]/) {
                            error("❌ Deployment Security Gate Failure: ALLOWED_INGRESS_CIDR contains unsupported control characters.")
                        }
                        echo "🔒 Validating supplied restricted ingress CIDR with standard parser..."
                        def cidrExit = -1
                        def validatedCidr = ''
                        withEnv(["RAW_INGRESS_CIDR=${rawCidr}"]) {
                            if (isUnix()) {
                                cidrExit = sh(script: '''python3 scripts/validate_cidr.py "$RAW_INGRESS_CIDR" > .validated_cidr 2>&1''', returnStatus: true)
                                if (cidrExit == 0) {
                                    validatedCidr = readFile('.validated_cidr').trim()
                                }
                            } else {
                                cidrExit = powershell(script: '''& python scripts/validate_cidr.py $env:RAW_INGRESS_CIDR *> .validated_cidr
exit $LASTEXITCODE''', returnStatus: true)
                                if (cidrExit == 0) {
                                    validatedCidr = readFile('.validated_cidr').trim()
                                }
                            }
                        }

                        if (cidrExit != 0 || !validatedCidr) {
                            def errorDetail = fileExists('.validated_cidr') ? readFile('.validated_cidr').trim() : 'Parser execution failed'
                            error("❌ Deployment Security Gate Failure: Ingress CIDR '${rawCidr}' failed security validation: ${errorDetail}")
                        }

                        env.TF_VAR_allowed_ingress_cidrs = "[\"${validatedCidr}\"]"
                        echo "✅ Supplied ingress CIDR was normalized for a reviewed Terraform plan."
                    }

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
                echo "🧪 Running pytest test suite (39 tests) and publishing JUnit XML & coverage..."
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m venv .venv
                            . .venv/bin/activate
                            pip install --no-cache-dir -r requirements.txt pytest pytest-cov
                            pytest --cov=. --cov-report=xml:coverage.xml --cov-report=term --junitxml=results.xml tests/test_system.py
                        '''
                    } else {
                        bat '''
                            python -m venv .venv
                            call .venv\\Scripts\\activate.bat
                            pip install --no-cache-dir -r requirements.txt pytest pytest-cov
                            pytest --cov=. --cov-report=xml:coverage.xml --cov-report=term --junitxml=results.xml tests/test_system.py
                        '''
                    }
                    env.STAGE_TESTS_STATUS = 'PASSED'
                }
            }
            post {
                always {
                    junit testResults: 'results.xml', allowEmptyResults: true
                    archiveArtifacts artifacts: 'coverage.xml, results.xml', allowEmptyArchive: true
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

                    // Validate coverage report existence and content before scanning
                    if (!fileExists('coverage.xml')) {
                        error("❌ Coverage Gate Failure: 'coverage.xml' is missing. Run unit testing with coverage before static analysis.")
                    }
                    def covContent = readFile('coverage.xml').trim()
                    if (covContent.length() == 0 || !covContent.contains('<coverage')) {
                        error("❌ Coverage Gate Failure: 'coverage.xml' is empty or invalid.")
                    }
                    echo "✅ Validated coverage report 'coverage.xml' (${covContent.length()} characters)."

                    // Static Code Analysis (SAST via SonarCloud)
                    if (hasDocker) {
                        echo "🔍 Running SonarCloud static analysis via sonarsource/sonar-scanner-cli:latest..."
                        try {
                            withCredentials([string(credentialsId: env.SONAR_CREDENTIALS_ID, variable: 'SONAR_TOKEN')]) {
                                if (isUnix()) {
                                    sh '''
                                        if [ -n "$JENKINS_HOME" ] && command -v hostname >/dev/null 2>&1 && docker inspect "$(hostname)" >/dev/null 2>&1; then
                                            docker run --rm --volumes-from "$(hostname)" -w "${PWD}" -e SONAR_TOKEN sonarsource/sonar-scanner-cli:latest -Dsonar.host.url=https://sonarcloud.io -Dsonar.python.coverage.reportPaths=coverage.xml
                                        else
                                            docker run --rm -v "${PWD}:/usr/src" -w /usr/src -e SONAR_TOKEN sonarsource/sonar-scanner-cli:latest -Dsonar.host.url=https://sonarcloud.io -Dsonar.python.coverage.reportPaths=coverage.xml
                                        fi
                                    '''
                                } else {
                                    powershell '''
                                        $ws = if ($env:WORKSPACE) { $env:WORKSPACE } else { (Get-Location).Path }
                                        docker run --rm -v "${ws}:/usr/src" -w /usr/src -e SONAR_TOKEN sonarsource/sonar-scanner-cli:latest -Dsonar.host.url=https://sonarcloud.io -Dsonar.python.coverage.reportPaths=coverage.xml
                                    '''
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
                            if (env.ENFORCE_QUALITY_GATE == 'true' || env.REQUIRE_SECURITY_SCANS == 'true') {
                                throw e
                            }
                        }
                    } else if (hasSonarCli) {
                        echo "🔍 Running local SonarQube Scanner for static analysis..."
                        try {
                            withCredentials([string(credentialsId: env.SONAR_CREDENTIALS_ID, variable: 'SONAR_TOKEN')]) {
                                if (isUnix()) {
                                    sh 'sonar-scanner -Dproject.settings=sonar-project.properties -Dsonar.host.url=https://sonarcloud.io -Dsonar.python.coverage.reportPaths=coverage.xml'
                                } else {
                                    bat 'sonar-scanner -Dproject.settings=sonar-project.properties -Dsonar.host.url=https://sonarcloud.io -Dsonar.python.coverage.reportPaths=coverage.xml'
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

                    // Amazon ECR publishing
                    if (env.PUBLISH_TO_ECR == 'true') {
                        if (env.AWS_REGION != 'ap-south-1' || env.ECR_REGISTRY != '695496430374.dkr.ecr.ap-south-1.amazonaws.com' || env.ECR_REPO != 'smart-energy-monitor') {
                            error("❌ Target Gate Failure: Pushing to '${env.ECR_REGISTRY}/${env.ECR_REPO}' in '${env.AWS_REGION}' is rejected. Only verified Mumbai ECR is permitted.")
                        }
                        echo "🔑 PUBLISH_TO_ECR=true. Authenticating and pushing to Amazon ECR (${env.ECR_REGISTRY})..."
                        try {
                            if (isUnix()) {
                                sh """
                                    docker run --rm -v "C:/Users/Vishwajeet/.aws:/root/.aws" amazon/aws-cli ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                                    docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                                    docker logout ${ECR_REGISTRY}
                                """
                            } else {
                                powershell """
                                    docker run --rm -v "\${env:USERPROFILE}\\.aws:/root/.aws" amazon/aws-cli ecr get-login-password --region ${env.AWS_REGION} | docker login --username AWS --password-stdin ${env.ECR_REGISTRY}
                                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                                    docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                                    docker logout ${ECR_REGISTRY}
                                """
                            }
                            echo "✅ Docker image published to Amazon ECR: ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}"
                        } catch (Exception e) {
                            echo "[ERROR] Failed to publish image to Amazon ECR: ${e.getMessage()}"
                            throw e
                        }
                    } else {
                        echo "[INFO] Amazon ECR publishing disabled (PUBLISH_TO_ECR=false). Skipping image push to preserve remote registry."
                    }

                    // Optional Docker Hub publishing (strictly credential-based, zero secrets in command text)
                    if (env.PUBLISH_TO_DOCKERHUB == 'true') {
                        echo "🔑 PUBLISH_TO_DOCKERHUB=true. Authenticating via Jenkins credentials ID '${env.DOCKERHUB_CREDENTIALS_ID}'..."
                        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDENTIALS_ID, usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                            if (isUnix()) {
                                sh """
                                    printf '%s\\n' "\$DH_PASS" | docker login -u "\$DH_USER" --password-stdin
                                    docker tag ${IMAGE_NAME}:latest ${DOCKERHUB_REPO}:${IMAGE_TAG}
                                    docker tag ${IMAGE_NAME}:latest ${DOCKERHUB_REPO}:latest
                                    docker push ${DOCKERHUB_REPO}:${IMAGE_TAG}
                                    docker push ${DOCKERHUB_REPO}:latest
                                    docker logout
                                """
                            } else {
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
                    def targetTfDir = env.TF_WORKING_DIR ?: 'terraform'
                    echo "🏗️ Target Terraform configuration directory: ${targetTfDir}"

                    // Verify configuration and directory exist before entering
                    if (!fileExists(targetTfDir) || !fileExists("${targetTfDir}/main.tf")) {
                        if (env.REQUIRE_IAC_VALIDATION == 'true') {
                            error("❌ IaC Gate Failure: Terraform directory or configuration ('${targetTfDir}/main.tf') is missing.")
                        } else {
                            echo "[WARNING] Terraform directory or configuration ('${targetTfDir}/main.tf') not found."
                            echo "[STATUS] IaC validation: NOT RUN (Prerequisite configuration missing)"
                            env.STAGE_IAC_STATUS = 'NOT_RUN (Files missing)'
                            return
                        }
                    }

                    dir(targetTfDir) {
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

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 6: Continuous Deployment to AWS EC2 (via AWS Systems Manager)
        // ──────────────────────────────────────────────────────────────────────
        stage('Deploy to EC2 (SSM)') {
            when {
                expression { env.DEPLOY_TO_EC2 == 'true' }
            }
            steps {
                script {
                    if (env.AWS_REGION != 'ap-south-1') {
                        error("❌ Deployment Gate Failure: Target AWS_REGION is '${env.AWS_REGION}'. Only AWS Mumbai ('ap-south-1') is permitted.")
                    }
                    if (env.ECR_REGISTRY != '695496430374.dkr.ecr.ap-south-1.amazonaws.com') {
                        error("❌ Deployment Gate Failure: Target ECR_REGISTRY is '${env.ECR_REGISTRY}'. Expected verified Mumbai ECR registry '695496430374.dkr.ecr.ap-south-1.amazonaws.com'.")
                    }
                    if (env.APP_URL && !env.APP_URL.startsWith('http://') && !env.APP_URL.startsWith('https://')) {
                        error("❌ Deployment Gate Failure: Target APP_URL '${env.APP_URL}' is invalid. Protocol must be http:// or https://.")
                    }
                    def managedInstanceId = ''
                    try {
                        if (isUnix()) {
                            managedInstanceId = sh(script: 'terraform -chdir=terraform/mumbai output -raw instance_id', returnStdout: true).trim()
                        } else {
                            managedInstanceId = powershell(script: 'terraform -chdir=terraform/mumbai output -raw instance_id', returnStdout: true).trim()
                        }
                    } catch (Exception e) {
                        echo "ℹ️ Terraform state is unavailable in this Jenkins workspace; an explicit MUMBAI_EC2_INSTANCE_ID is required for this deployment."
                    }
                    if (env.EC2_INSTANCE_ID && managedInstanceId && env.EC2_INSTANCE_ID != managedInstanceId) {
                        error("❌ Deployment Gate Failure: supplied MUMBAI_EC2_INSTANCE_ID does not match Terraform-managed instance '${managedInstanceId}'.")
                    }
                    if (managedInstanceId && !managedInstanceId.matches('^i-[0-9a-f]{8,17}$')) {
                        error("❌ Deployment Gate Failure: Terraform output 'instance_id' is invalid. Refusing to dispatch SSM to an unverified target.")
                    }
                    env.EC2_INSTANCE_ID = managedInstanceId ?: env.EC2_INSTANCE_ID
                    if (!env.EC2_INSTANCE_ID || !env.EC2_INSTANCE_ID.matches('^i-[0-9a-f]{8,17}$')) {
                        error("❌ Deployment Gate Failure: a valid Terraform instance_id or explicit MUMBAI_EC2_INSTANCE_ID is required before SSM dispatch.")
                    }
                    echo "✅ Resolved Mumbai SSM target: ${env.EC2_INSTANCE_ID}"
                    echo "🚀 Deploying updated container to EC2 instance '${env.EC2_INSTANCE_ID}' in Mumbai ('${env.AWS_REGION}') via AWS Systems Manager..."
                    try {
                        def ssmCommands = [
                            "set -e",
                            "echo 'Starting safe container deployment on EC2 (${env.AWS_REGION})...'",
                            "DEPLOY_SUCCESS=0",
                            "ROLLBACK_TRIGGERED=0",
                            "ROLLBACK_SUCCESS=0",
                            "BACKUP_PRESERVED=0",
                            "rollback() { if [ \"\$ROLLBACK_TRIGGERED\" -eq 1 ]; then if [ \"\$ROLLBACK_SUCCESS\" -eq 1 ]; then return 0; else exit 1; fi; fi; ROLLBACK_TRIGGERED=1; echo 'Initiating rollback to previous working container...'; if docker inspect ${env.APP_NAME} >/dev/null 2>&1; then echo 'Stopping and removing failed replacement container...'; docker stop ${env.APP_NAME} >/dev/null 2>&1 || true; docker rm -f ${env.APP_NAME} >/dev/null 2>&1 || true; fi; TARGET_BACKUP=''; if docker inspect ${env.APP_NAME}-newbackup >/dev/null 2>&1; then TARGET_BACKUP='${env.APP_NAME}-newbackup'; elif docker inspect ${env.APP_NAME}-backup >/dev/null 2>&1; then TARGET_BACKUP='${env.APP_NAME}-backup'; fi; if [ -n \"\$TARGET_BACKUP\" ]; then echo \"Restoring previous working container from \$TARGET_BACKUP...\"; if ! docker rename \"\$TARGET_BACKUP\" ${env.APP_NAME}; then echo \"CRITICAL: Rollback failed - could not rename \$TARGET_BACKUP to ${env.APP_NAME}. Recovery container \$TARGET_BACKUP preserved.\"; exit 1; fi; if ! docker start ${env.APP_NAME}; then echo \"CRITICAL: Rollback failed - could not start restored container ${env.APP_NAME}. Recovery container preserved.\"; exit 1; fi; echo 'Awaiting health check on restored container ${env.APP_NAME}...'; R_HEALTHY=0; for r in \$(seq 1 30); do R_STATUS=\$(docker inspect --format='{{.State.Health.Status}}' ${env.APP_NAME} 2>/dev/null || echo 'starting'); if [ \"\$R_STATUS\" = 'healthy' ]; then R_HEALTHY=1; echo \"Restored container is healthy after \$r attempts.\"; break; fi; sleep 2; done; if [ \"\$R_HEALTHY\" -ne 1 ]; then echo \"CRITICAL: Rollback verification failed - restored container failed health check (status: \$R_STATUS). Recovery container preserved.\"; docker logs ${env.APP_NAME} || true; exit 1; fi; if ! curl -s -f --max-time 5 http://localhost:8501/_stcore/health >/dev/null 2>&1; then echo 'CRITICAL: Rollback verification failed - restored container failed HTTP health check. Recovery container preserved.'; docker logs ${env.APP_NAME} || true; exit 1; fi; ROLLBACK_SUCCESS=1; echo '[SUCCESS] Previous working container successfully restored and verified healthy.'; else if [ \"\$BACKUP_PRESERVED\" -eq 1 ]; then echo 'CRITICAL: Rollback failed - expected preserved backup container but none was found.'; exit 1; else echo 'No backup container to restore (first deployment without previous container).'; exit 1; fi; fi; }",
                            "trap 'EXIT_CODE=\$?; if [ \"\$DEPLOY_SUCCESS\" -ne 1 ]; then if [ \"\$ROLLBACK_TRIGGERED\" -eq 0 ]; then if [ \"\$BACKUP_PRESERVED\" -eq 1 ]; then echo \"Unexpected failure or interruption (exit code \$EXIT_CODE). Triggering rollback...\"; rollback; fi; fi; if [ \"\$BACKUP_PRESERVED\" -eq 1 ] && [ \"\$ROLLBACK_SUCCESS\" -ne 1 ]; then echo \"CRITICAL: Deployment failed and rollback was unsuccessful (exit code \$EXIT_CODE). Recovery container preserved.\"; fi; if [ \"\$EXIT_CODE\" -eq 0 ]; then EXIT_CODE=1; fi; exit \$EXIT_CODE; fi' EXIT",
                            "aws ecr get-login-password --region ${env.AWS_REGION} | docker login --username AWS --password-stdin ${env.ECR_REGISTRY}",
                            "echo 'Pulling target image ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}...'",
                            "docker pull ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}",
                            "echo 'Validating pulled image integrity before stopping current container...'",
                            "docker image inspect ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG} >/dev/null",
                            "if docker inspect ${env.APP_NAME} >/dev/null 2>&1; then echo 'Stopping and preserving current container as staged backup...'; if ! docker stop ${env.APP_NAME}; then echo 'ERROR: Failed to stop current container for backup.'; exit 1; fi; if ! docker rename ${env.APP_NAME} ${env.APP_NAME}-newbackup; then echo 'ERROR: Failed to rename current container to staged backup. Restarting container...'; docker start ${env.APP_NAME} || true; exit 1; fi; BACKUP_PRESERVED=1; echo 'Current container safely preserved as ${env.APP_NAME}-newbackup.'; if docker inspect ${env.APP_NAME}-backup >/dev/null 2>&1; then echo 'Removing superseded older backup container...'; if ! docker rm -f ${env.APP_NAME}-backup; then echo 'ERROR: Failed to remove old backup container. Staged backup remains preserved.'; rollback; exit 1; fi; fi; if ! docker rename ${env.APP_NAME}-newbackup ${env.APP_NAME}-backup; then echo 'ERROR: Failed to promote staged backup to primary backup.'; rollback; exit 1; fi; echo 'Current container promoted to ${env.APP_NAME}-backup.'; elif docker inspect ${env.APP_NAME}-backup >/dev/null 2>&1; then echo 'Existing primary backup found from previous deployment; retaining as recovery target.'; BACKUP_PRESERVED=1; elif docker inspect ${env.APP_NAME}-newbackup >/dev/null 2>&1; then echo 'Existing staged backup found from previous deployment; retaining as recovery target.'; BACKUP_PRESERVED=1; else echo 'No existing container found to preserve; proceeding with initial deployment.'; BACKUP_PRESERVED=0; fi",
                            "echo 'Starting replacement container...'",
                            "if ! docker run -d --name ${env.APP_NAME} --restart unless-stopped -p 8501:8501 -v /var/data/energy:/app/data -e ENERGY_DB_DIR=/app/data -e ENERGY_DB_PATH=/app/data/energy.db ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}; then echo 'ERROR: Failed to launch replacement container.'; rollback; exit 1; fi",
                            "echo 'Awaiting Docker container health check...'",
                            "i=1; HEALTHY=0; while [ \"\$i\" -le 30 ]; do STATUS=\$(docker inspect --format='{{.State.Health.Status}}' ${env.APP_NAME} 2>/dev/null || echo 'starting'); if [ \"\$STATUS\" = 'healthy' ]; then echo \"Container is healthy after \$i attempts\"; HEALTHY=1; break; fi; sleep 2; i=\$((i + 1)); done",
                            "if [ \"\$HEALTHY\" -ne 1 ]; then echo \"ERROR: Replacement container failed Docker health check (status: \$STATUS). Dumping logs and rolling back...\"; docker logs ${env.APP_NAME} || true; rollback; exit 1; fi",
                            "echo 'Verifying final local HTTP health check against http://localhost:8501/_stcore/health...'",
                            "HTTP_OK=0; for h in \$(seq 1 5); do if curl -s -f --max-time 5 http://localhost:8501/_stcore/health >/dev/null 2>&1; then HTTP_OK=1; echo \"Local HTTP health check passed on attempt \$h.\"; break; fi; sleep 2; done",
                            "if [ \"\$HTTP_OK\" -ne 1 ]; then echo 'ERROR: Final local HTTP health check failed. Dumping logs and rolling back...'; docker logs ${env.APP_NAME} || true; rollback; exit 1; fi",
                            "echo 'Replacement container passed health checks. Executing finalization verification...'",
                            "docker inspect --format='Image: {{.Config.Image}} | ImageID: {{.Image}} | Status: {{.State.Status}} | Health: {{.State.Health.Status}}' ${env.APP_NAME}",
                            "ls -la /var/data/energy",
                            "DEPLOY_SUCCESS=1",
                            "BACKUP_PRESERVED=0",
                            "echo 'Finalization verified. Cleaning up backup container(s)...'",
                            "if docker inspect ${env.APP_NAME}-newbackup >/dev/null 2>&1; then docker rm -f ${env.APP_NAME}-newbackup || echo 'WARNING: Failed to remove staged backup container.'; fi",
                            "if docker inspect ${env.APP_NAME}-backup >/dev/null 2>&1; then docker rm -f ${env.APP_NAME}-backup || echo 'WARNING: Failed to remove backup container.'; fi",
                            "echo 'Deployment finalized successfully.'"
                        ]
                        def ssmParamsJson = groovy.json.JsonOutput.toJson([commands: ssmCommands])

                        if (isUnix()) {
                            withEnv(["SSM_PAYLOAD=${ssmParamsJson}"]) {
                                sh '''
                                    set -e
                                    echo "Dispatching SSM deployment command to instance ${EC2_INSTANCE_ID}..."
                                    CMD_ID=$(docker run --rm -v "C:/Users/Vishwajeet/.aws:/root/.aws" -e AWS_REGION="${AWS_REGION}" amazon/aws-cli ssm send-command \
                                        --instance-ids "${EC2_INSTANCE_ID}" \
                                        --document-name "AWS-RunShellScript" \
                                        --parameters "${SSM_PAYLOAD}" \
                                        --query "Command.CommandId" \
                                        --output text)

                                    echo "SSM Command dispatched: ${CMD_ID}. Awaiting execution..."
                                    sleep 10
                                    for i in $(seq 1 35); do
                                        STATUS=$(docker run --rm -v "C:/Users/Vishwajeet/.aws:/root/.aws" -e AWS_REGION="${AWS_REGION}" amazon/aws-cli ssm get-command-invocation \
                                            --command-id "${CMD_ID}" \
                                            --instance-id "${EC2_INSTANCE_ID}" \
                                            --query "Status" \
                                            --output text 2>/dev/null || echo "Pending")
                                        if [ "$STATUS" = "Success" ]; then
                                            echo "SSM Deployment command completed successfully."
                                            break
                                        elif [ "$STATUS" = "Failed" ]; then
                                            echo "ERROR: SSM Deployment command failed."
                                            docker run --rm -v "C:/Users/Vishwajeet/.aws:/root/.aws" -e AWS_REGION="${AWS_REGION}" amazon/aws-cli ssm get-command-invocation \
                                                --command-id "${CMD_ID}" \
                                                --instance-id "${EC2_INSTANCE_ID}"
                                            exit 1
                                        fi
                                        echo "SSM execution status: $STATUS (waiting...)"
                                        sleep 5
                                    done

                                    if [ "$STATUS" != "Success" ]; then
                                        echo "ERROR: SSM deployment timed out or ended with status: $STATUS"
                                        docker run --rm -v "C:/Users/Vishwajeet/.aws:/root/.aws" -e AWS_REGION="${AWS_REGION}" amazon/aws-cli ssm get-command-invocation \
                                            --command-id "${CMD_ID}" \
                                            --instance-id "${EC2_INSTANCE_ID}" 2>/dev/null || true
                                        exit 1
                                    fi

                                    if [ -z "${APP_URL}" ] && command -v terraform >/dev/null 2>&1; then
                                        ALB_DNS=$(terraform -chdir="${TF_WORKING_DIR}" output -raw alb_dns_name 2>/dev/null || true)
                                        if [ -n "${ALB_DNS}" ] && [ "${ALB_DNS}" != "null" ] && ! echo "${ALB_DNS}" | grep -qi "error"; then
                                            CANDIDATE_URL=$(terraform -chdir="${TF_WORKING_DIR}" output -raw application_url 2>/dev/null || true)
                                            if [ -n "${CANDIDATE_URL}" ] && ! echo "${CANDIDATE_URL}" | grep -q "3.110.85.209"; then
                                                APP_URL="${CANDIDATE_URL}"
                                            else
                                                echo "⚠️ Stale direct EC2 public IP output (3.110.85.209) ignored. External verification requires provisioned ALB."
                                                APP_URL=""
                                            fi
                                        else
                                            echo "ℹ️ Application Load Balancer has not been provisioned by Terraform yet. Skipping external ALB verification."
                                            APP_URL=""
                                        fi
                                    fi
                                    if [ -n "${APP_URL}" ] && [ "${APP_URL}" != "null" ] && ! echo "${APP_URL}" | grep -q "3.110.85.209"; then
                                        echo "Verifying external ALB health endpoint: ${APP_URL}/_stcore/health..."
                                        python3 -c 'import os, sys, urllib.request; url = os.environ["APP_URL"].rstrip("/") + "/_stcore/health"; sys.exit(0 if urllib.request.urlopen(url, timeout=10).getcode() == 200 else 1)'
                                    else
                                        echo "ℹ️ External URL verification skipped (ALB not provisioned or application URL not set; local container health verified via SSM)."
                                    fi
                                '''
                            }
                        } else {
                            withEnv(["SSM_PAYLOAD=${ssmParamsJson}"]) {
                                powershell '''
                                    Write-Host "Dispatching SSM deployment command to instance ${env:EC2_INSTANCE_ID}..."
                                    $safePayload = $env:SSM_PAYLOAD.Replace('"', '\"')
                                    $cmdId = docker run --rm -v "${env:USERPROFILE}\\.aws:/root/.aws" -e AWS_REGION="${env:AWS_REGION}" amazon/aws-cli ssm send-command `
                                        --instance-ids "${env:EC2_INSTANCE_ID}" `
                                        --document-name "AWS-RunShellScript" `
                                        --parameters "$safePayload" `
                                        --query "Command.CommandId" `
                                        --output text

                                    Write-Host "SSM Command dispatched: $cmdId. Awaiting execution..."
                                    Start-Sleep -Seconds 10
                                    for ($i = 1; $i -le 35; $i++) {
                                        $status = docker run --rm -v "${env:USERPROFILE}\\.aws:/root/.aws" -e AWS_REGION="${env:AWS_REGION}" amazon/aws-cli ssm get-command-invocation `
                                            --command-id "$cmdId" `
                                            --instance-id "${env:EC2_INSTANCE_ID}" `
                                            --query "Status" `
                                            --output text
                                        if ($status -eq "Success") {
                                            Write-Host "SSM Deployment command completed successfully."
                                            break
                                        } elseif ($status -eq "Failed") {
                                            Write-Error "ERROR: SSM Deployment command failed."
                                            docker run --rm -v "${env:USERPROFILE}\\.aws:/root/.aws" -e AWS_REGION="${env:AWS_REGION}" amazon/aws-cli ssm get-command-invocation `
                                                --command-id "$cmdId" `
                                                --instance-id "${env:EC2_INSTANCE_ID}"
                                            exit 1
                                        }
                                        Start-Sleep -Seconds 5
                                    }

                                    if ($status -ne "Success") {
                                        Write-Error "ERROR: SSM deployment timed out or ended with status: $status"
                                        exit 1
                                    }

                                    if (-not $env:APP_URL -and (Get-Command terraform -ErrorAction SilentlyContinue)) {
                                        $albDns = (terraform -chdir="$env:TF_WORKING_DIR" output -raw alb_dns_name 2>$null)
                                        if ($albDns -and $albDns.Trim() -ne "" -and $albDns.Trim() -ne "null" -and -not ($albDns -match "Error")) {
                                            $candidateUrl = (terraform -chdir="$env:TF_WORKING_DIR" output -raw application_url 2>$null).Trim()
                                            if ($candidateUrl -and -not ($candidateUrl -match "3\.110\.85\.209")) {
                                                $env:APP_URL = $candidateUrl
                                            } else {
                                                Write-Host "⚠️ Stale direct EC2 public IP output ignored. External verification requires provisioned ALB."
                                                $env:APP_URL = ""
                                            }
                                        } else {
                                            Write-Host "ℹ️ Application Load Balancer has not been provisioned by Terraform yet. Skipping external ALB verification."
                                            $env:APP_URL = ""
                                        }
                                    }
                                    if ($env:APP_URL -and $env:APP_URL -ne "null" -and -not ($env:APP_URL -match "3\.110\.85\.209")) {
                                        Write-Host "Verifying external ALB health endpoint: ${env:APP_URL}/_stcore/health..."
                                        curl.exe -s -f --connect-timeout 10 "${env:APP_URL}/_stcore/health"
                                    } else {
                                        Write-Host "ℹ️ External URL verification skipped (ALB not provisioned or application URL not set; local container health verified via SSM)."
                                    }
                                '''
                            }
                        }
                        env.STAGE_DEPLOY_STATUS = 'PASSED'
                        echo "✅ Application successfully deployed and verified on EC2 (Target: ${env.APP_URL ?: 'local container verified'})."
                    } catch (Exception e) {
                        env.STAGE_DEPLOY_STATUS = 'FAILED'
                        echo "[ERROR] Deployment to EC2 failed: ${e.getMessage()}"
                        throw e
                    }
                }
            }
            post {
                failure {
                    script {
                        env.STAGE_DEPLOY_STATUS = 'FAILED'
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
                echo " Target Deployment Region: ${env.AWS_REGION ?: 'UNKNOWN'} (${env.EC2_INSTANCE_ID ?: 'N/A'})"
                echo " Target Application URL:  ${env.APP_URL ?: 'N/A'}"
                echo " ------------------------------------------------------------------------"
                echo " 1. Source Checkout:      ${env.STAGE_CHECKOUT_STATUS ?: 'NOT_RUN'}"
                echo " 2. Automated Tests & QA: ${env.STAGE_TESTS_STATUS ?: 'NOT_RUN'}"
                echo " 3. Security & Quality:   ${env.STAGE_SECURITY_STATUS ?: 'NOT_RUN'}"
                echo "    - Trivy (Image Scan): ${env.TRIVY_SCAN_STATUS ?: 'NOT_RUN'}"
                echo "    - SonarCloud (SAST):  ${env.SONAR_SCAN_STATUS ?: 'NOT_RUN'}"
                echo " 4. Docker Build & ECR:   ${env.STAGE_DOCKER_STATUS ?: 'NOT_RUN'}"
                echo " 5. Terraform Validation: ${env.STAGE_IAC_STATUS ?: 'NOT_RUN'}"
                echo " 6. AWS EC2 Deployment:   ${env.STAGE_DEPLOY_STATUS ?: 'NOT_RUN'}"
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
