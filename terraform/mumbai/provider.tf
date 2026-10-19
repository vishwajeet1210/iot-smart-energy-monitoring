# ==============================================================================
# AWS Provider Configuration - Mumbai Region (ap-south-1)
# IoT-Based Smart Energy Monitoring and Management System
# ==============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Region      = var.aws_region
      ManagedBy   = "Terraform"
      Owner       = "Vishwajeet"
      Repository  = "https://github.com/vishwajeet1210/iot-smart-energy-monitoring"
    }
  }
}
