# ==============================================================================
# Terraform Outputs - AWS Mumbai Deployment
# IoT-Based Smart Energy Monitoring and Management System
# ==============================================================================

output "aws_region" {
  description = "Deployed AWS Region"
  value       = var.aws_region
}

output "vpc_id" {
  description = "ID of the created AWS VPC in Mumbai"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet where the Mumbai app server resides"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "ID of the Mumbai application security group"
  value       = aws_security_group.app_sg.id
}

output "instance_id" {
  description = "Mumbai EC2 Instance ID (required for Jenkins MUMBAI_EC2_INSTANCE_ID parameter)"
  value       = aws_instance.app_server.id
}

output "instance_public_ip" {
  description = "Public IP address of the deployed Mumbai EC2 server"
  value       = aws_instance.app_server.public_ip
}

output "application_url" {
  description = "Full URL to access the deployed Streamlit Energy Dashboard in Mumbai"
  value       = "http://${aws_instance.app_server.public_ip}:${var.app_port}"
}

output "iam_role_arn" {
  description = "ARN of the IAM role attached to the Mumbai EC2 instance"
  value       = aws_iam_role.ec2_role.arn
}

output "ecr_repository_url" {
  description = "URL of the created private ECR repository in Mumbai (if enabled)"
  value       = var.create_ecr_repository ? aws_ecr_repository.app_repo[0].repository_url : ""
}
