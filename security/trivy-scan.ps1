# ==============================================================================
# Trivy Security Scanner Runner (PowerShell for Windows)
# Supports native Trivy binary or automatic Docker container fallback
# ==============================================================================

param (
    [string]$ImageName = "smart-energy-monitor:devsecops",
    [string]$Severity = "HIGH,CRITICAL",
    [string]$OutputDir = "security"
)

$ErrorActionPreference = "Continue"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " [DevSecOps] Trivy Security Audit" -ForegroundColor Cyan
Write-Host " Target Image: $ImageName"
Write-Host " Severity Filter: $Severity"
Write-Host " Output Directory: $OutputDir"
Write-Host "===================================================================="

# Check if Trivy is available
$trivyCmd = Get-Command trivy -ErrorAction SilentlyContinue

function Invoke-TrivyScan {
    param (
        [string[]]$ScanArgs
    )
    if ($trivyCmd) {
        & trivy $ScanArgs
    } else {
        docker run --rm -v //var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache -v "${PWD}:/workspace" aquasec/trivy:latest $ScanArgs
    }
}

if (-not $trivyCmd) {
    Write-Host "[INFO] Local trivy binary not found. Falling back to containerized 'aquasec/trivy:latest'..." -ForegroundColor Magenta
}

Write-Host "`n[1/4] Scanning Filesystem & Dependencies (Primary Full Scan)..." -ForegroundColor Yellow
Invoke-TrivyScan @("fs", "--severity", $Severity, "--format", "json", "-o", "$OutputDir/trivy-fs-report.json", ".")
Invoke-TrivyScan @("fs", "--severity", $Severity, "--format", "table", "-o", "$OutputDir/trivy-fs-report.txt", ".")

Write-Host "`n[2/4] Scanning Terraform Infrastructure as Code (IaC)..." -ForegroundColor Yellow
if (Test-Path "terraform") {
    Invoke-TrivyScan @("config", "--severity", $Severity, "--format", "json", "-o", "$OutputDir/trivy-iac-report.json", "terraform/")
    Invoke-TrivyScan @("config", "--severity", $Severity, "--format", "table", "-o", "$OutputDir/trivy-iac-report.txt", "terraform/")
}

Write-Host "`n[3/4] Scanning Docker Container Image (Primary Full Scan - All Baseline Findings)..." -ForegroundColor Yellow
Invoke-TrivyScan @("image", "--severity", $Severity, "--format", "json", "-o", "$OutputDir/trivy-image-full-report.json", $ImageName)
Invoke-TrivyScan @("image", "--severity", $Severity, "--format", "table", "-o", "$OutputDir/trivy-image-full-report.txt", $ImageName)

Write-Host "`n[4/4] Scanning Docker Container Image (Secondary View - Actionable Fixed Only)..." -ForegroundColor Yellow
Invoke-TrivyScan @("image", "--severity", $Severity, "--ignore-unfixed", "--format", "json", "-o", "$OutputDir/trivy-image-actionable-report.json", $ImageName)
Invoke-TrivyScan @("image", "--severity", $Severity, "--ignore-unfixed", "--format", "table", "-o", "$OutputDir/trivy-image-actionable-report.txt", $ImageName)

Write-Host "`n[OK] Trivy dual scan process completed successfully." -ForegroundColor Green
Write-Host "     - Primary Full Baseline:    $OutputDir/trivy-image-full-report.json (.txt)" -ForegroundColor Green
Write-Host "     - Secondary Actionable View: $OutputDir/trivy-image-actionable-report.json (.txt)" -ForegroundColor Green
