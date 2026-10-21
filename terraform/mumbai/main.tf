# ==============================================================================
# Terraform Infrastructure as Code - AWS Mumbai (ap-south-1) Architecture
# IoT-Based Smart Energy Monitoring and Management System
# Production-Hardened Architecture: Private Compute + Dual-AZ ALB + TLS
# ==============================================================================

locals {
  effective_docker_image     = var.docker_image != "" ? var.docker_image : "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.project_name}:latest"
  create_managed_certificate = var.enable_https && var.certificate_arn == "" && var.domain_name != "" && var.route53_zone_id != ""
  has_tls                    = var.enable_https && var.domain_name != "" && (var.certificate_arn != "" || local.create_managed_certificate)
}

check "tls_configuration" {
  assert {
    condition     = !var.enable_https || (var.domain_name != "" && (var.certificate_arn != "" || var.route53_zone_id != ""))
    error_message = "When enable_https is true, domain_name and either an issued certificate_arn or a Route 53 zone ID for ACM DNS validation are required. Public HTTPS cannot be provisioned for the default AWS ALB DNS name."
  }
}

# ==============================================================================
# 1. NETWORKING (MUMBAI) - DUAL-AZ PUBLIC AND PRIVATE SUBNETS
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

# Preserve existing state resources from previous architecture
moved {
  from = aws_subnet.public
  to   = aws_subnet.public_a
}

moved {
  from = aws_route_table_association.public_assoc
  to   = aws_route_table_association.public_a_assoc
}

# Public Subnets (Dual-AZ for Application Load Balancer)
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  map_public_ip_on_launch = false
  availability_zone       = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-mumbai-public-subnet-a"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_b_cidr
  map_public_ip_on_launch = false
  availability_zone       = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.project_name}-mumbai-public-subnet-b"
  }
}

# Private Subnets (Isolated compute tier with zero public IP association)
resource "aws_subnet" "private_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet_a_cidr
  map_public_ip_on_launch = false
  availability_zone       = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-mumbai-private-subnet-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet_b_cidr
  map_public_ip_on_launch = false
  availability_zone       = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.project_name}-mumbai-private-subnet-b"
  }
}

# Internet Gateway for Public Tier
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-mumbai-igw"
  }
}

# Public Route Table & Associations
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

resource "aws_route_table_association" "public_a_assoc" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b_assoc" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# NAT Gateway for Outbound Private Connectivity (Package updates, ECR pulls)
# Note: AWS charges ~$0.045/hour (~$32.40/month) + data transfer fees for NAT Gateways.
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-mumbai-nat-eip"
  }
}

resource "aws_nat_gateway" "nat" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public_a.id

  tags = {
    Name = "${var.project_name}-mumbai-nat-gw"
  }

  depends_on = [aws_internet_gateway.gw]
}

# Private Route Table & Associations
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.nat[0].id
    }
  }

  tags = {
    Name = "${var.project_name}-mumbai-private-rt"
  }
}

resource "aws_route_table_association" "private_a_assoc" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b_assoc" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# AWS VPC Gateway Endpoint for S3 (Zero-cost direct layer pulls from ECR)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name = "${var.project_name}-mumbai-s3-endpoint"
  }
}

# AWS Interface VPC Endpoints (ECR API, ECR DKR, SSM, SSMMessages, EC2Messages)
# Required when NAT Gateway is disabled, or to keep AWS API traffic 100% private.
locals {
  vpce_services = var.enable_vpc_endpoints ? toset([
    "ecr.api",
    "ecr.dkr",
    "ssm",
    "ssmmessages",
    "ec2messages",
    "logs"
  ]) : toset([])
}

resource "aws_security_group" "vpce_sg" {
  count       = var.enable_vpc_endpoints ? 1 : 0
  name        = "${var.project_name}-mumbai-vpce-sg"
  description = "Security group for AWS Interface VPC Endpoints (ECR, SSM)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from VPC private compute tier"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Outbound from interface endpoints to VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-mumbai-vpce-sg"
  }
}

resource "aws_vpc_endpoint" "interface_endpoints" {
  for_each            = local.vpce_services
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.vpce_sg[0].id]
  private_dns_enabled = true

  tags = {
    Name = "${var.project_name}-mumbai-vpce-${each.value}"
  }
}

# ==============================================================================
# 2. SECURITY GROUPS (MUMBAI) - STRICT TIER ISOLATION
# ==============================================================================

# ALB Security Group: Receives external traffic on 80/443 restricted to allowed CIDRs
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-mumbai-alb-sg"
  description = "Security group for internet-facing Application Load Balancer in Mumbai"
  vpc_id      = aws_vpc.main.id

  lifecycle {
    precondition {
      condition     = length(var.allowed_ingress_cidrs) > 0
      error_message = "A restricted allowed_ingress_cidrs value is required before creating the public ALB. Supply it through a reviewed tfvars file or TF_VAR_allowed_ingress_cidrs; the configuration intentionally has no permissive default."
    }
  }

  ingress {
    description = "Restricted HTTP ingress for redirection or direct access"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_ingress_cidrs
  }

  ingress {
    description = "Restricted HTTPS ingress for secure Streamlit dashboard access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_ingress_cidrs
  }

  egress {
    description = "Forward traffic strictly to backend compute instances in VPC"
    from_port   = var.app_port
    to_port     = var.app_port
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-mumbai-alb-sg"
  }
}

# EC2 Application Security Group: Accepts traffic ONLY from ALB security group
resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-mumbai-app-sg"
  description = "Security group for private Streamlit application server in Mumbai"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Streamlit dashboard access strictly from ALB"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
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
    description = "Outbound access via NAT/endpoints for packages and ECR"
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
  # CI publishes unique build tags. Immutable tags prevent a previously
  # reviewed artifact from being silently replaced in the private registry.
  image_tag_mutability = "IMMUTABLE"

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
# 6. EC2 INSTANCE (PRIVATE SUBNET - ZERO PUBLIC IP - S6329 RESOLVED)
# ==============================================================================

resource "aws_instance" "app_server" {
  ami                         = var.custom_ami_id != "" ? var.custom_ami_id : data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.private_a.id
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.app_sg.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  key_name                    = var.ssh_key_name != "" ? var.ssh_key_name : null

  lifecycle {
    precondition {
      condition     = var.enable_nat_gateway
      error_message = "enable_nat_gateway must remain true: the instance user_data installs Ubuntu packages and therefore needs outbound internet access. Interface endpoints do not provide Ubuntu package-mirror access."
    }
  }

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

    echo "Starting Smart Energy Monitor deployment in Mumbai (ap-south-1) [Private Subnet]"

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

# ==============================================================================
# 7. APPLICATION LOAD BALANCER (ALB), TARGET GROUP & LISTENERS
# ==============================================================================

resource "aws_lb" "app_alb" {
  name                       = "${var.project_name}-mumbai-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb_sg.id]
  subnets                    = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  drop_invalid_header_fields = true

  tags = {
    Name = "${var.project_name}-mumbai-alb"
  }
}

resource "aws_lb_target_group" "app_tg" {
  name        = "${var.project_name}-mumbai-tg"
  port        = var.app_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"

  health_check {
    enabled             = true
    path                = "/_stcore/health"
    port                = tostring(var.app_port)
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.project_name}-mumbai-tg"
  }
}

resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app_tg.arn
  target_id        = aws_instance.app_server.id
  port             = var.app_port
}

# Optional ACM Certificate with DNS validation (configured when custom domain is provided)
resource "aws_acm_certificate" "cert" {
  count             = local.create_managed_certificate ? 1 : 0
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_name}-mumbai-cert"
  }
}

# Managed ACM certificates stay in Pending validation until the DNS records exist. This
# path deliberately supports only Route 53 zones; use a pre-issued certificate_arn for
# externally managed DNS rather than creating an unverifiable certificate request.
resource "aws_route53_record" "cert_validation" {
  for_each = local.create_managed_certificate ? {
    for option in aws_acm_certificate.cert[0].domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }
  } : {}

  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 60
  records = [each.value.record]
}

resource "aws_acm_certificate_validation" "cert" {
  count                   = local.create_managed_certificate ? 1 : 0
  certificate_arn         = aws_acm_certificate.cert[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# HTTP Listener on Port 80 (Redirects to HTTPS if TLS enabled; forwards to TG otherwise)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = local.has_tls ? "redirect" : "forward"
    target_group_arn = local.has_tls ? null : aws_lb_target_group.app_tg.arn

    dynamic "redirect" {
      for_each = local.has_tls ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

# HTTPS Listener on Port 443 (Active only when TLS certificate is provisioned)
resource "aws_lb_listener" "https" {
  count             = local.has_tls ? 1 : 0
  load_balancer_arn = aws_lb.app_alb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn != "" ? var.certificate_arn : aws_acm_certificate_validation.cert[0].certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_tg.arn
  }
}
