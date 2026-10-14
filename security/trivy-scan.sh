#!/usr/bin/env bash
# ==============================================================================
# Trivy Security Scanner Runner (Linux / macOS / Jenkins CI)
# Supports native Trivy binary or automatic Docker container fallback
# ==============================================================================

set -euo pipefail

IMAGE_NAME="${1:-smart-energy-monitor:devsecops}"
SEVERITY="${2:-HIGH,CRITICAL}"
OUTPUT_DIR="security"

mkdir -p "${OUTPUT_DIR}"

echo "===================================================================="
echo " 🛡️ [DevSecOps] Trivy Security Audit"
echo " Target Image:      ${IMAGE_NAME}"
echo " Severity Filter:   ${SEVERITY}"
echo " Output Directory:  ${OUTPUT_DIR}"
echo "===================================================================="

# Check if trivy binary is installed, otherwise fallback to containerized trivy
run_trivy() {
    if command -v trivy &> /dev/null; then
        trivy "$@"
    else
        docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v trivy-cache:/root/.cache \
            -v "${PWD}:/workspace" \
            aquasec/trivy:latest "$@"
    fi
}

echo "[1/4] Scanning Filesystem & Dependencies (Primary Full Scan)..."
run_trivy fs --severity "${SEVERITY}" --format json -o "${OUTPUT_DIR}/trivy-fs-report.json" .
run_trivy fs --severity "${SEVERITY}" --format table -o "${OUTPUT_DIR}/trivy-fs-report.txt" .

echo "[2/4] Scanning Terraform Infrastructure as Code (IaC)..."
if [ -d "terraform" ]; then
    run_trivy config --severity "${SEVERITY}" --format json -o "${OUTPUT_DIR}/trivy-iac-report.json" terraform/
    run_trivy config --severity "${SEVERITY}" --format table -o "${OUTPUT_DIR}/trivy-iac-report.txt" terraform/ || true
fi

echo "[3/4] Scanning Docker Container Image (Primary Full Scan - All Findings)..."
run_trivy image --severity "${SEVERITY}" --format json -o "${OUTPUT_DIR}/trivy-image-full-report.json" "${IMAGE_NAME}"
run_trivy image --severity "${SEVERITY}" --format table -o "${OUTPUT_DIR}/trivy-image-full-report.txt" "${IMAGE_NAME}"

echo "[4/4] Scanning Docker Container Image (Secondary View - Actionable Fixed Only)..."
run_trivy image --severity "${SEVERITY}" --ignore-unfixed --format json -o "${OUTPUT_DIR}/trivy-image-actionable-report.json" "${IMAGE_NAME}"
run_trivy image --severity "${SEVERITY}" --ignore-unfixed --format table -o "${OUTPUT_DIR}/trivy-image-actionable-report.txt" "${IMAGE_NAME}"

echo "✅ Trivy dual scan completed successfully."
echo "   - Primary Full Scan Artifacts:       ${OUTPUT_DIR}/trivy-image-full-report.json (.txt)"
echo "   - Secondary Actionable Artifacts:    ${OUTPUT_DIR}/trivy-image-actionable-report.json (.txt)"
