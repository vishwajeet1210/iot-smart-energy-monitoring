# 📋 AWS Sydney to Mumbai Migration Audit

**Document:** `MUMBAI_MIGRATION_AUDIT.md`
**Date:** October 19, 2026
**Project:** IoT-Based Smart Energy Monitoring and Management System
**Repository:** [https://github.com/vishwajeet1210/iot-smart-energy-monitoring](https://github.com/vishwajeet1210/iot-smart-energy-monitoring)
**Target AWS Account:** `695496430374`
**Source Region:** AWS Sydney (`ap-southeast-2`)
**Target Region:** AWS Mumbai (`ap-south-1`)
**Application Port:** `8501` (Streamlit Web Dashboard)

---

## 1. Executive Summary

This audit establishes the baseline technical inventory and gap analysis required to prepare an isolated, Terraform-managed migration of the **Smart Energy Monitor** from AWS Sydney (`ap-southeast-2`) to AWS Mumbai (`ap-south-1`).

### Core Safety Directives
1. **Zero Downtime / Dual-Region Integrity:** The current Sydney deployment (`i-06e85f034d1c71c9c` / `13.210.96.204:8501`) must remain operational and untouched throughout the migration process.
2. **State Isolation:** The existing Sydney Terraform state (`terraform/terraform.tfstate`) manages 11 production resources in `ap-southeast-2`. Under no circumstances must this state be used, modified, or overwritten for Mumbai.
3. **Disambiguation of Existing Mumbai Host:** A standalone Ubuntu 24.04 EC2 instance exists in Mumbai at `15.252.18.53` (`i-0c06fe2cc3dd7a63a`). As identified in previous audits, this host was provisioned manually in another AWS account with default security group `launch-wizard-1`. It is **not** managed by Terraform and must not be conflated with the project's target infrastructure in account `695496430374`.
4. **AWS Organizations Access Constraint:** Access to `ap-south-1` was recently modified at the AWS Organizations Service Control Policy (SCP) level. All migration steps must account for potential permission boundaries and authorization delays.

---

## 2. Current Architecture Inventory (AWS Sydney — `ap-southeast-2`)

The active production environment is fully defined in `terraform/` and recorded in `terraform/terraform.tfstate`:

| Resource Identifier | Resource Type | AWS ID / Value | Configuration & Purpose |
| :--- | :--- | :--- | :--- |
| **AWS Region** | Provider Region | `ap-southeast-2` | Primary production region |
| **AWS Account ID** | Target Account | `695496430374` | Project cloud account |
| **VPC** | `aws_vpc.main` | `vpc-05713fbc5a8c9ed52` | CIDR `10.0.0.0/16`, DNS support & hostnames enabled |
| **Public Subnet** | `aws_subnet.public` | `subnet-0db7732a9d0454372` | CIDR `10.0.1.0/24`, AZ `ap-southeast-2a` |
| **Internet Gateway** | `aws_internet_gateway.gw` | `igw-08573fc05e192ff81` | Attached to VPC for public inbound/outbound routing |
| **Route Table** | `aws_route_table.public` | `rtb-0100787a7b8e19e27` | Default route `0.0.0.0/0` targeting IGW |
| **Security Group** | `aws_security_group.app_sg` | `sg-09adc97f05d2f1ac1` | Ingress TCP 8501 from allowed CIDRs; egress `0.0.0.0/0`; SSH 22 disabled |
| **IAM Role** | `aws_iam_role.ec2_role` | `smart-energy-monitor-ec2-role` | Account-global role assumed by `ec2.amazonaws.com` |
| **IAM Policies** | `aws_iam_role_policy_attachment` | SSM + ECR ReadOnly | `AmazonSSMManagedInstanceCore` and `AmazonEC2ContainerRegistryReadOnly` |
| **Instance Profile** | `aws_iam_instance_profile.ec2_profile` | `smart-energy-monitor-instance-profile` | Attached to EC2 instance |
| **EC2 Instance** | `aws_instance.app_server` | `i-06e85f034d1c71c9c` | `t3.small`, Ubuntu 22.04 LTS (`ami-004a6006f1947b907`) |
| **Public IP** | Elastic / Public IPv4 | `13.210.96.204` | Public endpoint for Streamlit dashboard |
| **Storage** | Root Block Device | 20 GB gp3 encrypted | Encrypted EBS; persistent volume mapped to `/var/data/energy` |
| **ECR Registry** | Amazon ECR | `695496430374.dkr.ecr.ap-southeast-2.amazonaws.com` | Private repository: `smart-energy-monitor` |
| **CI/CD Automation** | Jenkins Pipeline | Job `smart-energy-monitor-ci` | Automated build, Trivy scan, and AWS SSM SendCommand deployment |

---

## 3. Inventory of Hard-Coded Sydney References

An exhaustive scan across all configuration, deployment, and CI/CD files revealed the following Sydney-specific references that must be addressed:

| File Path | Line(s) | Hard-Coded Sydney Value | Context & Purpose | Required Migration Action |
| :--- | :---: | :--- | :--- | :--- |
| `Jenkinsfile` | 36 | `AWS_REGION = 'ap-southeast-2'` | Default AWS CLI & SSM execution region | Parameterize via `params.DEPLOY_REGION` |
| `Jenkinsfile` | 37 | `ECR_REGISTRY = '695496430374.dkr.ecr.ap-southeast-2.amazonaws.com'` | Sydney ECR registry URI | Dynamically resolve based on target region |
| `Jenkinsfile` | 39 | `EC2_INSTANCE_ID = 'i-06e85f034d1c71c9c'` | Target Sydney EC2 instance for SSM deployment | Parameterize via `MUMBAI_EC2_INSTANCE_ID` |
| `Jenkinsfile` | 40 | `APP_URL = 'http://13.210.96.204:8501'` | Healthcheck verification endpoint | Parameterize via `MUMBAI_APP_URL` |
| `terraform/terraform.tfvars` | 2 | `aws_region = "ap-southeast-2"` | Active Sydney deployment region | Leave untouched; create separate Mumbai tfvars |
| `terraform/terraform.tfvars` | 16 | `docker_image = "695496430374.dkr.ecr.ap-southeast-2.amazonaws.com/..."` | Sydney ECR image reference | Leave untouched; Mumbai tfvars will use `ap-south-1` ECR |
| `terraform/main.tf` | 19, 134, 161 | `region = var.aws_region`, `name = "${var.project_name}-ec2-role"` | IAM Role & Instance Profile names | Leave untouched; Mumbai config will use distinct names |
| `terraform/main.tf` | 236–244 | `ECR_REGISTRY="$(printf '%s' "$IMAGE" ...)"` checks `*.dkr.ecr."$AWS_REGION".amazonaws.com` | User Data regional ECR validation | Ensure Mumbai user_data expects `ap-south-1` |
| `terraform/terraform.tfstate` | Multiple | Region `ap-southeast-2`, instance `i-06e85f034d1c71c9c` | Active Sydney Terraform state | **Do not touch or overwrite** |

---

## 4. Dependencies, Architectural Risks & Mitigations

### 4.1 IAM Role Name Collision (High Severity)
* **Risk:** AWS IAM roles and instance profiles exist in a **global namespace** within account `695496430374`. The Sydney Terraform configuration declares:
  ```hcl
  resource "aws_iam_role" "ec2_role" {
    name = "${var.project_name}-ec2-role" # resolves to "smart-energy-monitor-ec2-role"
  }
  ```
  If a Mumbai configuration attempts to create a role with the identical name, `terraform apply` will fail with an `EntityAlreadyExists` exception.
* **Mitigation:** In `terraform/mumbai/`, explicit region-differentiated naming is implemented:
  - Role: `${var.project_name}-mumbai-ec2-role`
  - Instance Profile: `${var.project_name}-mumbai-instance-profile`

### 4.2 ECR Private Repositories are Regional (High Severity)
* **Risk:** Private Amazon ECR repositories are regional constructs. An image residing in `695496430374.dkr.ecr.ap-southeast-2.amazonaws.com/smart-energy-monitor` **cannot be pulled directly from `ap-south-1` without cross-region network traversal and cross-region IAM authorization**. Furthermore, if no repository named `smart-energy-monitor` exists in `ap-south-1`, push attempts will fail with `RepositoryNotFoundException`.
* **Mitigation:**
  1. Add an optional managed `aws_ecr_repository` resource in `terraform/mumbai/` to ensure the target repository exists.
  2. Implement a safe cross-region image replication or retag/push workflow using Docker and AWS CLI before provisioning the EC2 instance.
  3. Parameterize the image URI to `695496430374.dkr.ecr.ap-south-1.amazonaws.com/smart-energy-monitor:${IMAGE_TAG}`.

### 4.3 VPC CIDR Overlap (Medium Severity)
* **Risk:** The Sydney VPC uses `10.0.0.0/16`. Reusing `10.0.0.0/16` in Mumbai prevents future cross-region VPC peering or AWS Transit Gateway routing if high availability or data replication is required.
* **Mitigation:** The Mumbai Terraform configuration defaults to `10.1.0.0/16` with public subnet `10.1.1.0/24`.

### 4.4 Terraform State Pollution (Critical Severity)
* **Risk:** Running `terraform apply` in `terraform/` with `aws_region = "ap-south-1"` would destroy Sydney resources and replace them with Mumbai resources.
* **Mitigation:** An entirely separate directory `terraform/mumbai/` is created, maintaining its own isolated state file (`terraform/mumbai/terraform.tfstate`) and variable overrides.

### 4.5 AWS Organizations SCP Boundaries (Medium Severity)
* **Risk:** Organization-level SCP modifications on `ap-south-1` may restrict certain API actions (e.g. `ec2:RunInstances`, `ecr:CreateRepository`, or `iam:CreateRole`).
* **Mitigation:** The runbook defines explicit pre-flight diagnostic commands (`aws ec2 describe-regions`, `aws ecr describe-repositories`, `aws iam get-role`) to confirm SCP clearance before running Terraform.

---

## 5. Required AWS Resources in Mumbai (`ap-south-1`)

The following resources must be created in `ap-south-1` within account `695496430374`:

| Resource | Terraform Resource Name | Proposed Mumbai Configuration |
| :--- | :--- | :--- |
| **VPC** | `aws_vpc.mumbai` | CIDR `10.1.0.0/16`, Name: `smart-energy-monitor-mumbai-vpc` |
| **Public Subnet** | `aws_subnet.mumbai_public` | CIDR `10.1.1.0/24`, AZ dynamic in `ap-south-1a/b`, public IP auto-assign |
| **Internet Gateway** | `aws_internet_gateway.mumbai_gw` | Name: `smart-energy-monitor-mumbai-igw` |
| **Route Table** | `aws_route_table.mumbai_public` | `0.0.0.0/0` routed to Mumbai IGW |
| **Security Group** | `aws_security_group.mumbai_sg` | Port 8501 ingress from allowed CIDRs; egress all; SSH closed |
| **IAM Role** | `aws_iam_role.mumbai_role` | `smart-energy-monitor-mumbai-ec2-role` |
| **IAM Policy Attachments** | `aws_iam_role_policy_attachment` | Attach `AmazonSSMManagedInstanceCore` & `AmazonEC2ContainerRegistryReadOnly` |
| **IAM Instance Profile** | `aws_iam_instance_profile.mumbai_profile`| `smart-energy-monitor-mumbai-instance-profile` |
| **ECR Repository** | `aws_ecr_repository.mumbai_repo` | `smart-energy-monitor` in `ap-south-1` (AES256, scan on push) |
| **EC2 Instance** | `aws_instance.mumbai_server` | `t3.small` / `t3.micro`, Ubuntu 22.04 LTS, 20 GB gp3 encrypted, IMDSv2 required |

---

## 6. Items Requiring Authorized AWS Access (Cannot Be Tested Offline)

1. **Active IAM Session:** The local AWS CLI session token (`assumed-role/AccountFullAccessRole/...`) is currently expired and requires re-authentication (`aws login` or updating profile credentials).
2. **ECR Repository Verification in Mumbai:** Determining whether `smart-energy-monitor` repository already exists in `ap-south-1` in account `695496430374`.
3. **AWS Organizations SCP Validation:** Verifying that `ap-south-1` permits `ec2:RunInstances` for `t3.small` instances and IAM role creation.
4. **Target Instance ID & Public IP:** The live EC2 instance ID and public IP can only be obtained after `terraform apply` is executed in `terraform/mumbai/`.

---

## 7. Migration Preparation Checklist

- [x] Phase 1: Comprehensive architectural inspection & audit completed (`MUMBAI_MIGRATION_AUDIT.md`).
- [x] Phase 2: Create isolated `terraform/mumbai/` configuration with state separation and collision-free naming.
- [x] Phase 3: Define cross-region ECR migration and container readiness workflow.
- [x] Phase 4: Parameterize `Jenkinsfile` for backward-compatible multi-region deployment with Sydney as default.
- [x] Phase 5: Run offline validation (pytest, terraform fmt, terraform validate, static checks).
- [x] Phase 6: Author operator runbook (`MUMBAI_MIGRATION_RUNBOOK.md`) with copy-paste commands.
