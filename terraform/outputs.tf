# ==============================================================================
# Terraform Outputs
# IoT-Based Smart Energy Monitoring and Management System
# ==============================================================================

output "vpc_id" {
  description = "ID of the created AWS VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet where the app server resides"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "ID of the application security group"
  value       = aws_security_group.app_sg.id
}

output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.app_server.id
}

output "instance_public_ip" {
  description = "Public IP address of the deployed EC2 server"
  value       = aws_instance.app_server.public_ip
}

output "application_url" {
  description = "Full URL to access the deployed Streamlit Energy Dashboard"
  value       = "http://${aws_instance.app_server.public_ip}:${var.app_port}"
}

output "iam_role_arn" {
  description = "ARN of the IAM role attached to the EC2 instance"
  value       = aws_iam_role.ec2_role.arn
}
