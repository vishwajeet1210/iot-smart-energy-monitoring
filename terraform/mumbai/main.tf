# ==============================================================================
# Terraform Infrastructure as Code - AWS Mumbai (ap-south-1) Architecture
# IoT-Based Smart Energy Monitoring and Management System
# ==============================================================================

locals {
  effective_docker_image = var.docker_image != "" ? var.docker_image : "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.project_name}:latest"
}

# ==============================================================================
# 1. NETWORKING (MUMBAI)
# ==============================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-mumbai-vpc"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-mumbai-public-subnet"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-mumbai-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "${var.project_name}-mumbai-public-rt"
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ==============================================================================
# 2. SECURITY GROUP (MUMBAI)
# ==============================================================================

resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-mumbai-app-sg"
  description = "Security group for Streamlit energy monitoring application in Mumbai"
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
    Name = "${var.project_name}-mumbai-app-sg"
  }
}

# ==============================================================================
# 3. AMAZON ECR PRIVATE REPOSITORY (MUMBAI)
# ==============================================================================

resource "aws_ecr_repository" "app_repo" {
  count = var.create_ecr_repository ? 1 : 0

  name                 = var.project_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.project_name}-mumbai-ecr"
  }
}

# ==============================================================================
# 4. IAM ROLE, POLICIES AND INSTANCE PROFILE (REGION-DIFFERENTIATED)
# ==============================================================================

# Distinct role name avoids collision with Sydney's smart-energy-monitor-ec2-role
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-mumbai-ec2-role"

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

  tags = {
    Name = "${var.project_name}-mumbai-ec2-role"
  }
}

# Allows the Mumbai instance to register with AWS Systems Manager (SSM)
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Allows pulling images from private Amazon ECR in Mumbai
resource "aws_iam_role_policy_attachment" "ecr_read_only" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-mumbai-instance-profile"
  role = aws_iam_role.ec2_role.name
}

# ==============================================================================
# 5. UBUNTU AMI LOOKUP (MUMBAI ap-south-1)
# ==============================================================================

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

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
# 6. EC2 INSTANCE AND AUTOMATED CONTAINER BOOTSTRAP (MUMBAI)
# ==============================================================================

resource "aws_instance" "app_server" {
  ami                         = var.custom_ami_id != "" ? var.custom_ami_id : data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.app_sg.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  key_name                    = var.ssh_key_name != "" ? var.ssh_key_name : null

  # Require IMDSv2 (Session token requirement for security hardening)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  # Encrypted persistent root volume
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

    echo "Starting Smart Energy Monitor deployment in Mumbai (ap-south-1)"

    export DEBIAN_FRONTEND=noninteractive

    apt-get update -y
    apt-get install -y docker.io awscli ca-certificates curl

    systemctl enable --now docker

    # Create persistent host directory for the SQLite database
    mkdir -p /var/data/energy
    chown -R 1001:1001 /var/data/energy
    chmod 755 /var/data/energy

    IMAGE='${local.effective_docker_image}'
    AWS_REGION='${var.aws_region}'
    ECR_REGISTRY="$(printf '%s' "$IMAGE" | cut -d/ -f1)"

    # If the image is hosted on Amazon ECR, authenticate via the instance profile
    if [[ "$ECR_REGISTRY" == *.dkr.ecr."$AWS_REGION".amazonaws.com ]]; then
      echo "Authenticating to Amazon ECR in $AWS_REGION ($ECR_REGISTRY)..."

      for attempt in $(seq 1 5); do
        if aws ecr get-login-password --region "$AWS_REGION" \
          | docker login --username AWS --password-stdin "$ECR_REGISTRY"; then
          echo "ECR login succeeded."
          break
        fi

        if [[ "$attempt" -eq 5 ]]; then
          echo "ERROR: Could not authenticate to Amazon ECR."
          exit 1
        fi

        echo "ECR authentication attempt $attempt failed; retrying in 10s..."
        sleep 10
      done
    else
      echo "Non-ECR or external registry detected ($ECR_REGISTRY). Skipping ECR login."
    fi

    # Pull container image
    echo "Pulling container image: $IMAGE..."
    docker pull "$IMAGE"

    # Replace any existing container safely
    if docker container inspect smart-energy-monitor >/dev/null 2>&1; then
      echo "Stopping and replacing previous container..."
      docker rm -f smart-energy-monitor
    fi

    # Run application container under non-root appuser (UID 1001)
    docker run -d \
      --name smart-energy-monitor \
      --restart unless-stopped \
      -p ${var.app_port}:8501 \
      -v /var/data/energy:/app/data \
      -e ENERGY_DB_DIR=/app/data \
      -e ENERGY_DB_PATH=/app/data/energy.db \
      "$IMAGE"

    # Await container health verification
    for attempt in $(seq 1 30); do
      RUNNING="$(docker inspect --format '{{.State.Running}}' smart-energy-monitor 2>/dev/null || true)"

      if [[ "$RUNNING" == "true" ]]; then
        echo "Smart Energy Monitor container is running successfully in Mumbai."
        exit 0
      fi

      sleep 5
    done

    echo "ERROR: Container failed to remain running."
    docker logs smart-energy-monitor || true
    exit 1
  EOF

  depends_on = [
    aws_iam_role_policy_attachment.ssm_policy,
    aws_iam_role_policy_attachment.ecr_read_only
  ]

  tags = {
    Name = "${var.project_name}-mumbai-server"
  }
}
