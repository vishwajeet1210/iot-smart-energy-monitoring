# ==============================================================================
# Terraform Outputs - AWS Mumbai Deployment
# IoT-Based Smart Energy Monitoring and Management System
# Production-Hardened Architecture: Private Compute + Dual-AZ ALB + TLS
# ==============================================================================

output "aws_region" {
  description = "Deployed AWS Region"
  value       = var.aws_region
}

output "vpc_id" {
  description = "ID of the created AWS VPC in Mumbai"
  value       = aws_vpc.main.id
}

output "public_subnet_a_id" {
  description = "ID of public subnet A (AZ 1) for Application Load Balancer"
  value       = aws_subnet.public_a.id
}

output "public_subnet_b_id" {
  description = "ID of public subnet B (AZ 2) for Application Load Balancer"
  value       = aws_subnet.public_b.id
}

output "public_subnet_id" {
  description = "Backward-compatible alias for primary public subnet A"
  value       = aws_subnet.public_a.id
}

output "private_subnet_a_id" {
  description = "ID of private subnet A where the compute instance resides"
  value       = aws_subnet.private_a.id
}

output "private_subnet_b_id" {
  description = "ID of private subnet B for redundant compute workloads"
  value       = aws_subnet.private_b.id
}

output "alb_security_group_id" {
  description = "ID of the Application Load Balancer security group"
  value       = aws_security_group.alb_sg.id
}

output "app_security_group_id" {
  description = "ID of the EC2 instance security group (accepts traffic strictly from ALB)"
  value       = aws_security_group.app_sg.id
}

output "security_group_id" {
  description = "Backward-compatible alias for EC2 application security group"
  value       = aws_security_group.app_sg.id
}

output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer"
  value       = aws_lb.app_alb.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.app_alb.arn
}

output "target_group_arn" {
  description = "ARN of the ALB Target Group for Streamlit application"
  value       = aws_lb_target_group.app_tg.arn
}

output "instance_id" {
  description = "Terraform-managed Mumbai EC2 instance ID used by the guarded Jenkins SSM deployment stage"
  value       = aws_instance.app_server.id
}

output "instance_private_ip" {
  description = "Private IP address of the deployed Mumbai EC2 server (zero public IP associated)"
  value       = aws_instance.app_server.private_ip
}

output "application_url" {
  description = "URL to access the deployed Streamlit Energy Dashboard via ALB"
  value       = local.has_tls ? "https://${var.domain_name}" : "http://${aws_lb.app_alb.dns_name}"
}

output "is_https_active" {
  description = "Whether HTTPS listener and certificate are actively configured for the deployment"
  value       = local.has_tls
}

output "iam_role_arn" {
  description = "ARN of the IAM role attached to the Mumbai EC2 instance"
  value       = aws_iam_role.ec2_role.arn
}

output "ecr_repository_url" {
  description = "URL of the created private ECR repository in Mumbai (if enabled)"
  value       = var.create_ecr_repository ? aws_ecr_repository.app_repo[0].repository_url : ""
}

output "nat_gateway_ip" {
  description = "Elastic IP allocated for the NAT Gateway (if enabled)"
  value       = var.enable_nat_gateway ? aws_eip.nat[0].public_ip : ""
}
