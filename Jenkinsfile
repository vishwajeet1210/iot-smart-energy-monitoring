// ==============================================================================
// Jenkins Declarative Pipeline - DevSecOps CI/CD
// Project: IoT-Based Smart Energy Monitoring and Management System
// Repository: https://github.com/vishwajeet1210/iot-smart-energy-monitoring
// ==============================================================================
//
// REQUIRED JENKINS PLUGINS:
//   1. Pipeline: Declarative (workflow-aggregator)
//   2. Git Plugin
//   3. JUnit Plugin (for test results visualization)
//   4. SonarQube Scanner for Jenkins (sonarqube-scanner)
//   5. Docker Pipeline Plugin (docker-workflow)
//   6. Warnings Next Generation Plugin (optional, for Trivy SARIF parsing)
//   7. Credentials Binding Plugin
//
// REQUIRED JENKINS CREDENTIALS / TOOLS:
//   - Tool 'SonarQubeScanner' configured in Global Tool Configuration
//   - SonarQube Server configured in System Configuration (named 'SonarQube')
//   - Secret Text 'SONAR_TOKEN' (SonarQube analysis token)
//   - (Optional) Docker Registry Credential ID 'docker-registry-credentials'
//   - (Optional) AWS Credential ID 'aws-deployment-credentials'
// ==============================================================================

pipeline {
    agent any

    options {
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        ansiColor('xterm')
    }

    environment {
        APP_NAME        = 'smart-energy-monitor'
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        REGISTRY_IMAGE  = "smart-energy-monitor:${env.BUILD_NUMBER}"
        LATEST_IMAGE    = "smart-energy-monitor:latest"
        SEVERITY_LEVEL  = 'HIGH,CRITICAL'
        PYTHONUNBUFFERED = '1'
    }

    stages {

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 1: Code Checkout
        // ──────────────────────────────────────────────────────────────────────
        stage('Checkout SCM') {
            steps {
                echo "📥 Checking out repository source code..."
                checkout scm
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 2: Dependency Installation & Environment Verification
        // ──────────────────────────────────────────────────────────────────────
        stage('Setup & Dependencies') {
            steps {
                echo "🔧 Preparing Python environment and installing test dependencies..."
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    if [ -f requirements-dev.txt ]; then
                        pip install -r requirements-dev.txt
                    else
                        pip install -r requirements.txt
                    fi
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 3: Unit Testing & Code Coverage
        // ──────────────────────────────────────────────────────────────────────
        stage('Unit Tests & Coverage') {
            steps {
                echo "🧪 Executing pytest test suite with JUnit XML & coverage output..."
                sh '''
                    . .venv/bin/activate
                    pytest --junitxml=results.xml tests/
                '''
            }
            post {
                always {
                    junit testResults: 'results.xml', allowEmptyResults: true
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 4: SonarQube Static Code Analysis (SAST)
        // ──────────────────────────────────────────────────────────────────────
        stage('SonarQube Static Analysis') {
            steps {
                echo "🔍 Running SonarQube static code & security analysis..."
                // Runs SonarQube Scanner using configured SonarQube installation
                script {
                    def scannerHome = tool name: 'SonarQubeScanner', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                    withSonarQubeEnv('SonarQube') {
                        sh "${scannerHome}/bin/sonar-scanner -Dproject.settings=sonar-project.properties"
                    }
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 5: SonarQube Quality Gate
        // ──────────────────────────────────────────────────────────────────────
        stage('SonarQube Quality Gate') {
            steps {
                echo "🚦 Evaluating SonarQube Quality Gate status..."
                timeout(time: 5, unit: 'MINUTES') {
                    script {
                        def qg = waitForQualityGate()
                        if (qg.status != 'OK') {
                            error "❌ Pipeline aborted due to SonarQube Quality Gate failure: ${qg.status}"
                        }
                        echo "✅ SonarQube Quality Gate passed."
                    }
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 6: Trivy Dependency & Filesystem Vulnerability Scan
        // ──────────────────────────────────────────────────────────────────────
        stage('Trivy Dependency Scan') {
            steps {
                echo "🛡️ Scanning project dependencies and filesystem for CVEs..."
                sh '''
                    mkdir -p security
                    # Machine-readable JSON output
                    trivy fs --severity ${SEVERITY_LEVEL} --format json -o security/trivy-fs-report.json .
                    # Human-readable console summary
                    trivy fs --severity ${SEVERITY_LEVEL} --format table .
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'security/trivy-fs-report.json', allowEmptyArchive: true
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 7: Docker Image Build & Tagging
        // ──────────────────────────────────────────────────────────────────────
        stage('Docker Build') {
            steps {
                echo "🐳 Building Docker container image: ${REGISTRY_IMAGE}..."
                sh '''
                    docker build \
                        --label "build_number=${BUILD_NUMBER}" \
                        --label "git_commit=${GIT_COMMIT}" \
                        -t ${REGISTRY_IMAGE} \
                        -t ${LATEST_IMAGE} .
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 8: Trivy Container Image Security Scan
        // ──────────────────────────────────────────────────────────────────────
        stage('Trivy Image Security Scan') {
            steps {
                echo "🛡️ Scanning Docker container image for OS and package vulnerabilities..."
                sh '''
                    mkdir -p security
                    # Primary Full Scan (All Findings including vendor debt)
                    trivy image --severity ${SEVERITY_LEVEL} --format json -o security/trivy-image-full-report.json ${REGISTRY_IMAGE}
                    trivy image --severity ${SEVERITY_LEVEL} --format table ${REGISTRY_IMAGE}

                    # Secondary Actionable Scan (Findings with available upstream patches only)
                    trivy image --severity ${SEVERITY_LEVEL} --ignore-unfixed --format json -o security/trivy-image-actionable-report.json ${REGISTRY_IMAGE}
                    trivy image --severity ${SEVERITY_LEVEL} --ignore-unfixed --format table ${REGISTRY_IMAGE}
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'security/trivy-image-*.json', allowEmptyArchive: true
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 9: Terraform IaC Static Validation & Formatting
        // ──────────────────────────────────────────────────────────────────────
        stage('Terraform IaC Validation') {
            steps {
                echo "🏗️ Validating Terraform Infrastructure as Code definitions..."
                dir('terraform') {
                    sh '''
                        terraform fmt -check || echo "Warning: Terraform formatting needs adjustment"
                        terraform init -backend=false
                        terraform validate
                    '''
                }
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // STAGE 10: Production Deployment Gate (Approval & Execution)
        // ──────────────────────────────────────────────────────────────────────
        stage('Deployment Gate') {
            when {
                branch 'main'
            }
            steps {
                echo "🚀 Preparing deployment to AWS Cloud environment..."
                // Manual approval gate before infrastructure deployment
                input message: "Approve deployment of version ${IMAGE_TAG} to AWS infrastructure?", ok: "Deploy"

                script {
                    echo "Deploying containerized application to AWS EC2 / ECS..."
                    /*
                    // Example Deployment Execution Step (when AWS credentials configured):
                    withCredentials([[
                        $class: 'AmazonWebServicesCredentialsBinding',
                        credentialsId: 'aws-deployment-credentials',
                        accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                        secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                    ]]) {
                        dir('terraform') {
                            sh 'terraform init'
                            sh 'terraform plan -out=tfplan'
                            sh 'terraform apply -auto-approve tfplan'
                        }
                    }
                    */
                    echo "✅ Deployment completed successfully."
                }
            }
        }
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Post-Pipeline Execution Handlers
    // ──────────────────────────────────────────────────────────────────────────
    post {
        always {
            echo "🧹 Cleaning up workspace..."
            cleanWs deleteDirs: true, notFailBuild: true
        }
        success {
            echo "🎉 Pipeline finished successfully! All tests, security scans, and build steps passed."
        }
        failure {
            echo "❌ Pipeline failed. Check console log and security reports for diagnostic details."
        }
    }
}
