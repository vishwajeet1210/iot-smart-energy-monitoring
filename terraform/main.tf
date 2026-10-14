# ==============================================================================
# Terraform Infrastructure as Code - AWS Architecture
# IoT-Based Smart Energy Monitoring and Management System
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "Vishwajeet"
      Repository  = "https://github.com/vishwajeet1210/iot-smart-energy-monitoring"
    }
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# 1. NETWORKING (VPC, Subnet, Internet Gateway, Routing)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-public-subnet"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ──────────────────────────────────────────────────────────────────────────────
# 2. SECURITY GROUPS (Strict Ingress & Controlled Egress)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-app-sg"
  description = "Security Group for IoT Smart Energy Monitor Streamlit App"
  vpc_id      = aws_vpc.main.id

  # Streamlit Web Application Ingress
  ingress {
    description = "Streamlit dashboard ingress"
    from_port   = var.app_port
    to_port     = var.app_port
    protocol    = "tcp"
    cidr_blocks = var.allowed_ingress_cidrs
  }

  # Optional SSH Access (Restricted to specific management CIDRs)
  dynamic "ingress" {
    for_each = var.enable_ssh ? [1] : []
    content {
      description = "SSH ingress for administration"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.admin_cidr
    }
  }

  # Outbound egress to fetch container images, system packages, and updates
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-app-sg"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# 3. IAM ROLE & INSTANCE PROFILE (SSM Access, Least Privilege)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# Attach AWS Systems Manager (SSM) policy for secure shell access without open SSH
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.ec2_role.name
}

# ──────────────────────────────────────────────────────────────────────────────
# 4. AMI & COMPUTE INSTANCE (EC2 with Hardened Configuration)
# ──────────────────────────────────────────────────────────────────────────────

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app_server" {
  ami                  = data.aws_ami.amazon_linux_2023.id
  instance_type        = var.instance_type
  subnet_id            = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name
  key_name             = var.ssh_key_name != "" ? var.ssh_key_name : null

  # Security Hardening: Enforce IMDSv2 (prevents SSRF metadata theft)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  # Security Hardening: Encrypted Root Storage
  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  # Automated User Data Deployment Script
  user_data = <<-EOF
              #!/bin/bash
              set -xe
              dnf update -y
              dnf install -y docker git
              systemctl enable --now docker
              usermod -aG docker ec2-user

              # Create persistent host data directory for SQLite database
              mkdir -p /var/data/energy
              chown -R 1001:1001 /var/data/energy
              chmod 755 /var/data/energy

              # Run the hardened container with mounted SQLite persistence
              docker run -d \
                --name smart-energy-monitor \
                --restart unless-stopped \
                -p ${var.app_port}:8501 \
                -v /var/data/energy:/app/data \
                -e ENERGY_DB_DIR=/app/data \
                -e ENERGY_DB_PATH=/app/data/energy.db \
                ${var.docker_image}
              EOF

  tags = {
    Name = "${var.project_name}-server"
  }
}
