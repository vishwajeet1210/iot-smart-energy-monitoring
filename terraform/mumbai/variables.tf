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
  description = "Public subnet CIDR block for Mumbai"
  default     = "10.1.1.0/24"
}

variable "instance_type" {
  type        = string
  description = "EC2 compute instance type (t3.small or t3.micro)"
  default     = "t3.small"
}

variable "app_port" {
  type        = number
  description = "Application listening port (Streamlit web interface)"
  default     = 8501
}

variable "allowed_ingress_cidrs" {
  type        = list(string)
  description = "Allowed CIDR blocks for accessing the Streamlit web dashboard. In production, restrict to corporate VPN or personal IP."
  default     = ["0.0.0.0/0"]
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
