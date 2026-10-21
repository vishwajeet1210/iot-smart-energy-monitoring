# ==============================================================================
# Terraform Variables - AWS Mumbai Deployment
# IoT-Based Smart Energy Monitoring and Management System
# ==============================================================================

variable "aws_region" {
  type        = string
  description = "Target AWS region for Mumbai deployment"
  default     = "ap-south-1"
}

variable "aws_account_id" {
  type        = string
  description = "Target AWS 12-digit Account ID"
  default     = "695496430374"
}

variable "environment" {
  type        = string
  description = "Deployment environment name (e.g., dev, staging, prod)"
  default     = "dev"
}

variable "project_name" {
  type        = string
  description = "Resource naming prefix"
  default     = "smart-energy-monitor"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block for Mumbai (10.1.0.0/16 avoids overlap with Sydney 10.0.0.0/16)"
  default     = "10.1.0.0/16"
}

variable "public_subnet_cidr" {
  type        = string
  description = "Public subnet A CIDR block for Mumbai (first AZ for ALB)"
  default     = "10.1.1.0/24"
}

variable "public_subnet_b_cidr" {
  type        = string
  description = "Public subnet B CIDR block for Mumbai (second AZ required by ALB)"
  default     = "10.1.2.0/24"
}

variable "private_subnet_a_cidr" {
  type        = string
  description = "Private subnet A CIDR block for Mumbai (where the EC2 instance resides without public IP)"
  default     = "10.1.10.0/24"
}

variable "private_subnet_b_cidr" {
  type        = string
  description = "Private subnet B CIDR block for Mumbai (second AZ for private workloads)"
  default     = "10.1.20.0/24"
}

variable "instance_type" {
  type        = string
  description = "EC2 compute instance type (t3.small or t3.micro)"
  default     = "t3.small"
}

variable "app_port" {
  type        = number
  description = "Application listening port (Streamlit web interface on EC2)"
  default     = 8501
}

variable "allowed_ingress_cidrs" {
  type        = list(string)
  description = "Explicit IPv4 CIDR blocks allowed to reach the ALB. Leave empty for validation-only work; an infrastructure plan/apply fails until a restricted value is supplied."
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.allowed_ingress_cidrs :
      can(cidrnetmask(cidr)) &&
      can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/([1-9]|[12][0-9]|3[0-2])$", cidr)) &&
      !startswith(cidr, "0.")
    ])
    error_message = "allowed_ingress_cidrs must contain only restricted IPv4 CIDRs; IPv6, malformed values, /0, and unspecified 0.0.0.0 ranges are not supported by these IPv4 security-group rules."
  }
}

variable "enable_ssh" {
  type        = bool
  description = "Whether to open port 22 in security group. Kept false by default because AWS SSM Session Manager is enabled."
  default     = false
}

variable "admin_cidr" {
  type        = list(string)
  description = "Allowed CIDR blocks for SSH access when enable_ssh is true"
  default     = ["127.0.0.1/32"]
}

variable "ssh_key_name" {
  type        = string
  description = "Optional EC2 Key Pair name for SSH key login"
  default     = ""
}

variable "create_ecr_repository" {
  type        = bool
  description = "Whether to create and manage a private ECR repository in Mumbai (ap-south-1)"
  default     = true
}

variable "docker_image" {
  type        = string
  description = "Docker image repository and tag to run on the EC2 instance. If empty, defaults to local Mumbai ECR image."
  default     = ""
}

variable "custom_ami_id" {
  type        = string
  description = "Optional custom AMI ID to override automated Ubuntu 22.04 LTS lookup in ap-south-1"
  default     = ""
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Deploy an AWS NAT Gateway for private subnet outbound internet connectivity (package updates, external registries). NOTE: Incurs ~$0.045/hr (~$32.40/month) + data transfer fees."
  default     = true
}

variable "enable_vpc_endpoints" {
  type        = bool
  description = "Deploy AWS Interface VPC Endpoints (ECR, SSM, and CloudWatch Logs) in addition to the required NAT Gateway."
  default     = false
}

variable "domain_name" {
  type        = string
  description = "Custom domain name for HTTPS (for example, energy.example.com). Required whenever enable_https is true."
  default     = ""
}

variable "certificate_arn" {
  type        = string
  description = "Optional ARN of an existing AWS Certificate Manager (ACM) certificate for HTTPS listener on port 443."
  default     = ""
}

variable "route53_zone_id" {
  type        = string
  description = "Optional Route 53 hosted-zone ID used to create ACM DNS validation records when requesting a new certificate. Required when enable_https=true and certificate_arn is empty."
  default     = ""
}

variable "enable_https" {
  type        = bool
  description = "Whether to configure an HTTPS listener on port 443 and redirect HTTP (port 80) to HTTPS. Requires domain_name plus either certificate_arn or route53_zone_id."
  default     = false
}
