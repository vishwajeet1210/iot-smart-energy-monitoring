# 🚀 AWS Sydney to Mumbai Migration Runbook

**Document:** `MUMBAI_MIGRATION_RUNBOOK.md`
**Date:** October 19, 2026
**Project:** IoT-Based Smart Energy Monitoring and Management System
**Repository:** [https://github.com/vishwajeet1210/iot-smart-energy-monitoring](https://github.com/vishwajeet1210/iot-smart-energy-monitoring)
**Target AWS Account:** `695496430374`
**Source Region:** AWS Sydney (`ap-southeast-2`)
**Target Region:** AWS Mumbai (`ap-south-1`)
**Application Port:** `8501` (Streamlit Web Dashboard)

---

## 1. Safety Principles & Prerequisites

1. **Dual-Region Operation (Zero Downtime):**
   The Sydney deployment (`i-06e85f034d1c71c9c` / `http://13.210.96.204:8501`) remains active and serving traffic until the Mumbai deployment is independently provisioned, populated with container images, and verified healthy.
2. **State Isolation:**
   The Sydney Terraform configuration resides in `terraform/` with its state in `terraform/terraform.tfstate`.
   The Mumbai Terraform configuration resides exclusively in `terraform/mumbai/` with its own separate state file `terraform/mumbai/terraform.tfstate`. **Never run Terraform commands across the wrong directory.**
3. **Disambiguation of Existing Mumbai Host:**
   The existing host at `15.252.18.53` (`i-0c06fe2cc3dd7a63a`) was a manual out-of-band host in a separate account. This runbook provisions fresh, managed infrastructure within your official project account (`695496430374`).
4. **AWS Organizations Access:**
   Because access to `ap-south-1` was recently modified at the AWS Organizations policy level, follow Step 2 carefully to verify that permissions are unblocked before provisioning resources.

---

## 2. Step 1: Verify Active AWS Identity and Region Access

Run the following commands in PowerShell or Bash on your operator workstation to confirm that your AWS session is authenticated to account `695496430374`:

```bash
# 1. Verify caller identity and account number
aws sts get-caller-identity
```

**Expected Output:**
```json
{
    "UserId": "AROA...",
    "Account": "695496430374",
    "Arn": "arn:aws:sts::695496430374:assumed-role/..."
}
```

> ⚠️ **If you receive `Error loading login session token`:**
> Run `aws login` or refresh your AWS profile credentials with:
> ```bash
> aws sso login
> ```
> Do not proceed until `aws sts get-caller-identity` returns account `695496430374`.

```bash
# 2. Verify Mumbai (ap-south-1) region access at the AWS Organizations / account level
aws ec2 describe-regions --region-names ap-south-1 --query "Regions[0].OptInStatus" --output text
```

**Expected Output:**
```
opt-in-not-required
```
*(or `opted-in`)*

```bash
# 3. Test basic EC2 and ECR authorization in ap-south-1
aws ec2 describe-availability-zones --region ap-south-1 --query "AvailabilityZones[].ZoneName" --output text
aws ecr get-login-password --region ap-south-1 > /dev/null && echo "✅ ECR authentication authorized in ap-south-1"
```

---

## 3. Step 2: Initialize and Validate Mumbai Terraform Configuration

Navigate to the dedicated Mumbai directory:

```bash
cd C:\Users\Vishwajeet\.gemini\antigravity-ide\scratch\smart-energy-monitor\terraform\mumbai
```

```bash
# 1. Verify formatting
terraform fmt -check

# 2. Initialize provider plugins (local state)
terraform init

# 3. Validate syntax and argument references
terraform validate
```

**Expected Output:**
```
Success! The configuration is valid.
```

---

## 4. Step 3: Review the Terraform Execution Plan

Generate an explicit execution plan to confirm that **only** Mumbai (`ap-south-1`) resources will be created, with zero changes to Sydney:

```bash
terraform plan -out=mumbai.tfplan
```

### Plan Checklist: Verify Before Applying
* [ ] **Provider Region:** `ap-south-1`
* [ ] **VPC to create:** `smart-energy-monitor-mumbai-vpc` (CIDR `10.1.0.0/16`)
* [ ] **Subnet to create:** `smart-energy-monitor-mumbai-public-subnet` (CIDR `10.1.1.0/24`)
* [ ] **Security Group:** `smart-energy-monitor-mumbai-app-sg` (port 8501 ingress, port 22 disabled)
* [ ] **IAM Role:** `smart-energy-monitor-mumbai-ec2-role` (region-differentiated name)
* [ ] **ECR Repository:** `smart-energy-monitor` in `ap-south-1`
* [ ] **EC2 Server:** `smart-energy-monitor-mumbai-server` with IMDSv2 required
* [ ] **Plan Summary:** Expected `Plan: 12 to add, 0 to change, 0 to destroy.` (or 11 if ECR repository already exists).
* [ ] **Confirm Sydney State Untouched:** Confirm no resources in `ap-southeast-2` or `i-06e85f034d1c71c9c` are referenced.

---

## 5. Step 4: Apply the Mumbai Plan (Requires Human Approval)

Once the plan is confirmed safe, execute the apply:

```bash
terraform apply mumbai.tfplan
```

Capture the outputs displayed in the terminal:
```bash
terraform output
```

**Example Outputs:**
```text
aws_region          = "ap-south-1"
vpc_id              = "vpc-0abc1234mumbai"
public_subnet_id    = "subnet-0abc1234mumbai"
security_group_id   = "sg-0abc1234mumbai"
instance_id         = "i-0abc1234mumbai"
instance_public_ip  = "13.235.X.X"
application_url     = "http://13.235.X.X:8501"
ecr_repository_url  = "695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor"
```

Save the `instance_id` and `application_url` for Jenkins configuration.

---

## 6. Step 5: ECR Image Preparation & Cross-Region Push

The Mumbai EC2 instance requires the container image in the Mumbai ECR repository (`695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor`).

Execute the following commands to copy/push the verified image:

```bash
# 1. Log in to Amazon ECR in Mumbai
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 695496430374.dkr.ecr.ap-south-1.amazonaws.com

# Option A: If using local image archive smart-energy-monitor-11.tar (Fastest)
docker load -i smart-energy-monitor-11.tar

# Tag the loaded image for Mumbai ECR
docker tag smart-energy-monitor:11 695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor:11
docker tag smart-energy-monitor:11 695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor:latest

# Push to Mumbai ECR
docker push 695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor:11
docker push 695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor:latest

# Option B: Pull directly from Sydney ECR and re-push (if local image not available)
# aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 695496430374.dkr.ecr.ap-southeast-2.amazonaws.com
# docker pull 695496430374.dkr.ecr.ap-southeast-2.amazonaws.com/smart-energy-monitor:latest
# docker tag 695496430374.dkr.ecr.ap-southeast-2.amazonaws.com/smart-energy-monitor:latest 695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor:latest
# docker push 695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor:latest

# 2. Verify image registration in Mumbai ECR
aws ecr describe-images --repository-name smart-energy-monitor --region ap-south-1 --output table
```

---

## 7. Step 6: Verify EC2 Instance and SSM Online Status

Confirm that the new Mumbai EC2 instance has booted, registered with AWS Systems Manager (SSM), and pulled the container:

```bash
# Replace with your actual Mumbai instance ID from terraform output
MUMBAI_INSTANCE_ID="i-0abc1234mumbai"

# Check instance state
aws ec2 describe-instances --instance-ids "$MUMBAI_INSTANCE_ID" --region ap-south-1 --query "Reservations[0].Instances[0].[State.Name, PublicIpAddress]" --output text

# Check SSM Agent connectivity
aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$MUMBAI_INSTANCE_ID" --region ap-south-1 --query "InstanceInformationList[0].[PingStatus, PlatformName]" --output text
```

**Expected Output:**
```
Online    Ubuntu 22.04
```

---

## 8. Step 7: Verify Application Health and Endpoint in Mumbai

Once the user_data script finishes bootstrapping, verify the application:

```bash
# Replace with your actual Mumbai public IP
MUMBAI_IP="13.235.X.X"

# 1. Test Streamlit health endpoint
curl -s -f "http://${MUMBAI_IP}:8501/_stcore/health" && echo "✅ Mumbai Streamlit healthcheck OK"

# 2. Test main dashboard HTTP status
curl -I -s "http://${MUMBAI_IP}:8501/" | head -n 5
```

**Expected Output:**
```
HTTP/1.1 200 OK
```

Open `http://${MUMBAI_IP}:8501/` in your browser to confirm:
* KPI cards render properly (Total Power, Energy, Cost, 6/6 Devices Online).
* Device Monitoring table loads with voltage, current, and status badges.
* Historical charts render without database locks.

---

## 9. Step 8: Execute Jenkins Multi-Region Deployment Pipeline

The `Jenkinsfile` has been parameterized for backward-compatible multi-region deployment.

1. Open Jenkins: `http://localhost:8080/job/smart-energy-monitor-ci/`
2. Click **Build with Parameters**.
3. Configure the build parameters:
   * **`DEPLOY_REGION`:** Select `ap-south-1`
   * **`MUMBAI_EC2_INSTANCE_ID`:** Enter the provisioned Mumbai instance ID (e.g., `i-0abc1234mumbai`)
   * **`MUMBAI_APP_URL`:** Enter the Mumbai application URL (e.g., `http://13.235.X.X:8501`)
   * **`MUMBAI_ECR_REGISTRY`:** Keep default (`695496430374.dkr.ecr.ap-south-1.amazonaws.com`)
4. Click **Build**.
5. Observe execution:
   * Stage 1: Checkout & resolves `ap-south-1` target environment.
   * Stage 2: Runs pytest (39/39 passing).
   * Stage 3: SonarCloud SAST scan & Quality Gate verification.
   * Stage 4: Docker build, Trivy container scan, and push to Mumbai ECR.
   * Stage 5: Validates Terraform definitions in `terraform/mumbai/`.
   * Stage 6: Dispatches AWS SSM deployment to Mumbai instance and verifies `http://${MUMBAI_IP}:8501/_stcore/health`.
   * Execution Summary displays target region `ap-south-1`.

> ℹ️ **Rollback Note:** If any build is triggered without parameters (or via Git webhook poll), it automatically defaults to `DEPLOY_REGION=ap-southeast-2`, preserving the Sydney environment.

---

## 10. Step 9: Post-Migration Dual-Region Verification & Rollback

Before considering any decommissioning of Sydney, perform side-by-side verification:

| Verification Metric | Sydney (`ap-southeast-2`) | Mumbai (`ap-south-1`) | Verification Method |
| :--- | :--- | :--- | :--- |
| **Instance ID** | `i-06e85f034d1c71c9c` | `i-0abc1234mumbai` | `aws ec2 describe-instances` |
| **Public Endpoint** | `http://13.210.96.204:8501` | `http://<MUMBAI_IP>:8501` | Browser & `curl /_stcore/health` |
| **Docker Container** | `smart-energy-monitor` (Healthy) | `smart-energy-monitor` (Healthy) | `docker inspect` via SSM |
| **SQLite Persistence** | `/var/data/energy/energy.db` | `/var/data/energy/energy.db` | Verified non-root UID 1001 write |
| **ECR Registry** | `695496430374.dkr.ecr.ap-southeast-2` | `695496430374.dkr.ecr.ap-south-1` | `aws ecr describe-repositories` |
| **Terraform State** | `terraform/terraform.tfstate` | `terraform/mumbai/terraform.tfstate` | Isolated state files |

Maintain both environments in parallel for at least **48 to 72 hours** to verify network latency, telemetry persistence, and operational stability.

---

## 11. Step 10: Future Sydney Decommissioning (Explicit Human Approval Only)

> ⛔ **CRITICAL WARNING:** Do not perform this step until Mumbai has operated without error for the required observation period and you have explicit authorization to terminate Sydney resources.

When ready to decommission Sydney:

```bash
# 1. Back up Sydney SQLite database (Optional but recommended)
aws ssm send-command \
    --instance-ids "i-06e85f034d1c71c9c" \
    --region ap-southeast-2 \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["tar -czf /tmp/sydney-energy-backup.tar.gz /var/data/energy"]'

# 2. Navigate to Sydney Terraform directory
cd C:\Users\Vishwajeet\.gemini\antigravity-ide\scratch\smart-energy-monitor\terraform

# 3. Generate destruction plan
terraform plan -destroy -out=sydney_destroy.tfplan

# 4. Review destruction plan to confirm ONLY Sydney resources are marked for deletion
terraform show sydney_destroy.tfplan

# 5. Apply destruction
terraform apply sydney_destroy.tfplan
```

---

## 12. Cost Impact Analysis (Sydney vs. Mumbai)

AWS pricing in Mumbai (`ap-south-1`) is comparable to or slightly lower than Sydney (`ap-southeast-2`):

| Resource | Sydney Pricing (`ap-southeast-2`) | Mumbai Pricing (`ap-south-1`) | Estimated Monthly Cost |
| :--- | :--- | :--- | :--- |
| **EC2 `t3.small` (Linux)** | $0.0260 / hr (~$18.98 / mo) | $0.0208 / hr (~$15.18 / mo) | ~$15.20 / mo (Save ~20% in Mumbai) |
| **EC2 `t3.micro` (Alternative)** | $0.0130 / hr (~$9.49 / mo) | $0.0104 / hr (~$7.59 / mo) | ~$7.60 / mo |
| **EBS gp3 Storage (20 GB)** | $0.096 / GB-mo (~$1.92 / mo) | $0.080 / GB-mo (~$1.60 / mo) | ~$1.60 / mo |
| **Amazon ECR Storage (~200MB)** | $0.10 / GB-mo (~$0.02 / mo) | $0.10 / GB-mo (~$0.02 / mo) | ~$0.02 / mo |
| **Internet Data Transfer** | Inbound Free; First 100 GB Out Free | Inbound Free; First 100 GB Out Free | $0.00 / mo |
| **AWS Systems Manager Core** | Included free of charge | Included free of charge | $0.00 / mo |
| **Dual-Run Cost (During Migration)** | Running both Sydney + Mumbai in parallel for 72 hours adds **~$2.00 total**. | | |
| **Total Steady-State Cost (Mumbai)** | | | **~$16.80 / month** (on `t3.small`) |
