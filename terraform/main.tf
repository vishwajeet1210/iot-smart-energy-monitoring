
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

# ==============================================================================
# 1. NETWORKING
# ==============================================================================

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

# ==============================================================================
# 2. SECURITY GROUP
# ==============================================================================

resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-app-sg"
  description = "Security group for the Streamlit energy monitoring application"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Restricted Streamlit dashboard access"
    from_port   = var.app_port
    to_port     = var.app_port
    protocol    = "tcp"
    cidr_blocks = var.allowed_ingress_cidrs
  }

  dynamic "ingress" {
    for_each = var.enable_ssh ? [1] : []

    content {
      description = "Restricted SSH administration"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.admin_cidr
    }
  }

  egress {
    description = "Outbound access for packages and ECR"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-app-sg"
  }
}

# ==============================================================================
# 3. IAM ROLE, ECR PULL PERMISSION AND INSTANCE PROFILE
# ==============================================================================

resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

# Allows the instance to register with AWS Systems Manager.
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Allows pulling images from private Amazon ECR repositories.
resource "aws_iam_role_policy_attachment" "ecr_read_only" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.ec2_role.name
}

# ==============================================================================
# 4. UBUNTU AMI
# ==============================================================================

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# ==============================================================================
# 5. EC2 INSTANCE AND AUTOMATED CONTAINER DEPLOYMENT
# ==============================================================================

resource "aws_instance" "app_server" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  associate_public_ip_address = true # NOSONAR: retained for the existing Sydney deployment until an approved migration.
  vpc_security_group_ids      = [aws_security_group.app_sg.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  key_name                    = var.ssh_key_name != "" ? var.ssh_key_name : null

  # Require IMDSv2.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  # Encrypted persistent storage for the instance.
  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = <<-EOF
    #!/bin/bash
    set -Eeuo pipefail

    exec > >(tee -a /var/log/smart-energy-deploy.log) 2>&1

    echo "Starting Smart Energy Monitor deployment"

    export DEBIAN_FRONTEND=noninteractive

    apt-get update -y
    apt-get install -y docker.io awscli ca-certificates

    systemctl enable --now docker

    # Create persistent host directory for the SQLite database.
    mkdir -p /var/data/energy
    chown -R 1001:1001 /var/data/energy
    chmod 755 /var/data/energy

    # Extract the ECR registry hostname from the configured image URI.
    IMAGE='${var.docker_image}'
    AWS_REGION='${var.aws_region}'
    ECR_REGISTRY="$(printf '%s' "$IMAGE" | cut -d/ -f1)"

    if [[ "$ECR_REGISTRY" != *.dkr.ecr."$AWS_REGION".amazonaws.com ]]; then
      echo "ERROR: Image registry does not match the configured AWS region."
      exit 1
    fi

    # Authenticate using the EC2 instance role. Do not store AWS access keys.
    echo "Authenticating to Amazon ECR"

    for attempt in $(seq 1 5); do
      if aws ecr get-login-password --region "$AWS_REGION" \
        | docker login --username AWS --password-stdin "$ECR_REGISTRY"; then
        break
      fi

      if [[ "$attempt" -eq 5 ]]; then
        echo "ERROR: Could not authenticate to ECR."
        exit 1
      fi

      echo "ECR authentication attempt $attempt failed; retrying."
      sleep 10
    done

    # Pull the image before replacing or starting the application container.
    docker pull "$IMAGE"

    # Replace a previous container if this startup script is rerun.
    if docker container inspect smart-energy-monitor >/dev/null 2>&1; then
      docker rm -f smart-energy-monitor
    fi

    docker run -d \
      --name smart-energy-monitor \
      --restart unless-stopped \
      -p ${var.app_port}:8501 \
      -v /var/data/energy:/app/data \
      -e ENERGY_DB_DIR=/app/data \
      -e ENERGY_DB_PATH=/app/data/energy.db \
      "$IMAGE"

    # Wait for the container to become healthy or report its logs.
    for attempt in $(seq 1 30); do
      RUNNING="$(docker inspect --format '{{.State.Running}}' smart-energy-monitor || true)"

      if [[ "$RUNNING" == "true" ]]; then
        echo "Smart Energy Monitor container is running."
        exit 0
      fi

      sleep 5
    done

    echo "ERROR: Container failed to remain running."
    docker logs smart-energy-monitor || true
    exit 1
  EOF

  # Ensure permissions are attached before EC2 boots.
  depends_on = [
    aws_iam_role_policy_attachment.ssm_policy,
    aws_iam_role_policy_attachment.ecr_read_only
  ]

  tags = {
    Name = "${var.project_name}-server"
  }
}
