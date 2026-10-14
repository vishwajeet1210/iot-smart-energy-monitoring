# ==============================================================================
# Terraform Variables
# IoT-Based Smart Energy Monitoring and Management System
# ==============================================================================

variable "aws_region" {
  type        = string
  description = "Target AWS region for deploying infrastructure"
  default     = "ap-south-1"
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

variable "instance_type" {
  type        = string
  description = "EC2 compute instance type"
  default     = "t3.small"
}

variable "app_port" {
  type        = number
  description = "Application listening port (Streamlit web interface)"
  default     = 8501
}

variable "allowed_ingress_cidrs" {
  type        = list(string)
  description = "Allowed CIDR blocks for accessing the Streamlit web dashboard. In production, restrict to corporate VPN or office IP."
  default     = ["0.0.0.0/0"]
}

variable "enable_ssh" {
  type        = bool
  description = "Whether to open port 22 in security group. Recommended false because SSM Session Manager is enabled."
  default     = false
}

variable "admin_cidr" {
  type        = list(string)
  description = "Allowed CIDR blocks for SSH access when enable_ssh is true"
  default     = ["0.0.0.0/0"]
}

variable "ssh_key_name" {
  type        = string
  description = "Optional EC2 Key Pair name for SSH key login"
  default     = ""
}

variable "docker_image" {
  type        = string
  description = "Docker image repository and tag to run on the EC2 instance"
  default     = "ghcr.io/vishwajeet1210/iot-smart-energy-monitoring:latest"
}
