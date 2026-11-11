# ==============================================================================
# IncidentX AI — Main Infrastructure as Code Definition
# Enterprise Cloud Architecture (VPC, ECS Fargate, RDS Multi-AZ, KMS, S3, ALB)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Cryptographic Key Management (AWS KMS)
# ------------------------------------------------------------------------------
resource "aws_kms_key" "incidentx_key" {
  description             = "IncidentX AI enterprise master encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "incidentx-${var.environment}-kms"
  }
}

resource "aws_kms_alias" "incidentx_key_alias" {
  name          = "alias/incidentx-${var.environment}"
  target_key_id = aws_kms_key.incidentx_key.key_id
}

# ------------------------------------------------------------------------------
# 2. Secret Management (AWS Secrets Manager)
# ------------------------------------------------------------------------------
resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "incidentx_secrets" {
  name                    = "incidentx-${var.environment}-app-secrets"
  kms_key_id              = aws_kms_key.incidentx_key.arn
  recovery_window_in_days = 7

  tags = {
    Name = "incidentx-${var.environment}-secrets"
  }
}

resource "aws_secretsmanager_secret_version" "incidentx_secrets_val" {
  secret_id = aws_secretsmanager_secret.incidentx_secrets.id
  secret_string = jsonencode({
    POSTGRES_USER     = var.db_username
    POSTGRES_PASSWORD = random_password.db_password.result
    POSTGRES_DB       = var.db_name
    SECRET_KEY        = "prod-entropy-secret-key-incidentx-platform-256bit"
    DATABASE_URL      = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
  })
}

# ------------------------------------------------------------------------------
# 3. Durable Storage for DR Backups & Evidence (Amazon S3)
# ------------------------------------------------------------------------------
resource "aws_s3_bucket" "evidence_storage" {
  bucket        = "incidentx-${var.environment}-evidence-${var.aws_region}"
  force_destroy = var.environment == "staging" ? true : false

  tags = {
    Name = "incidentx-${var.environment}-evidence"
  }
}

resource "aws_s3_bucket_versioning" "evidence_versioning" {
  bucket = aws_s3_bucket.evidence_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence_encryption" {
  bucket = aws_s3_bucket.evidence_storage.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.incidentx_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "evidence_block_public" {
  bucket                  = aws_s3_bucket.evidence_storage.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ------------------------------------------------------------------------------
# 4. Enterprise VPC & Multi-Tier Subnet Topology
# ------------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "incidentx-${var.environment}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "incidentx-${var.environment}-igw"
  }
}

resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "incidentx-${var.environment}-public-${var.availability_zones[count.index]}"
    Tier = "Public"
  }
}

resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "incidentx-${var.environment}-private-${var.availability_zones[count.index]}"
    Tier = "Application"
  }
}

resource "aws_subnet" "database" {
  count             = length(var.database_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.database_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "incidentx-${var.environment}-db-${var.availability_zones[count.index]}"
    Tier = "Database"
  }
}

# NAT Gateway for outbound egress from private app subnets
resource "aws_eip" "nat" {
  domain = "vpc"
  tags = {
    Name = "incidentx-${var.environment}-nat-eip"
  }
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "incidentx-${var.environment}-nat-gw"
  }
  depends_on = [aws_internet_gateway.igw]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = {
    Name = "incidentx-${var.environment}-rt-public"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }
  tags = {
    Name = "incidentx-${var.environment}-rt-private"
  }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ------------------------------------------------------------------------------
# 5. Security Groups (Least-Privilege Network Isolation)
# ------------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name        = "incidentx-${var.environment}-sg-alb"
  description = "Controls HTTPS access to IncidentX Load Balancers"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Allow HTTPS from trusted clients"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound to ECS application tasks"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "incidentx-${var.environment}-sg-alb"
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "incidentx-${var.environment}-sg-ecs"
  description = "Allows ingress only from ALB into backend and frontend tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow backend API traffic from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Allow frontend traffic from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow outbound Internet egress via NAT"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "incidentx-${var.environment}-sg-ecs"
  }
}

resource "aws_security_group" "db" {
  name        = "incidentx-${var.environment}-sg-db"
  description = "Isolated PostgreSQL security group accepting connections only from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL access strictly from ECS task tier"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "incidentx-${var.environment}-sg-db"
  }
}

# ------------------------------------------------------------------------------
# 6. Database Tier (AWS RDS PostgreSQL Multi-AZ with Automated Backups)
# ------------------------------------------------------------------------------
resource "aws_db_subnet_group" "db_subnets" {
  name        = "incidentx-${var.environment}-db-subnet-group"
  subnet_ids  = aws_subnet.database[*].id
  description = "Dedicated isolated subnets for IncidentX relational persistence"

  tags = {
    Name = "incidentx-${var.environment}-db-subnet-group"
  }
}

resource "aws_db_instance" "postgres" {
  identifier                  = "incidentx-${var.environment}-postgres"
  engine                      = "postgres"
  engine_version              = "16.1"
  instance_class              = var.db_instance_class
  allocated_storage           = var.db_allocated_storage
  max_allocated_storage       = var.db_allocated_storage * 3
  storage_type                = "gp3"
  storage_encrypted           = true
  kms_key_id                  = aws_kms_key.incidentx_key.arn
  multi_az                    = var.db_multi_az
  db_name                     = var.db_name
  username                    = var.db_username
  password                    = random_password.db_password.result
  db_subnet_group_name        = aws_db_subnet_group.db_subnets.name
  vpc_security_group_ids      = [aws_security_group.db.id]
  skip_final_snapshot         = var.environment == "staging" ? true : false
  final_snapshot_identifier   = "incidentx-${var.environment}-final-snapshot"
  backup_retention_period     = var.environment == "production" ? 30 : 7
  backup_window               = "03:00-04:00"
  maintenance_window          = "Sun:04:30-Sun:05:30"
  auto_minor_version_upgrade  = true
  deletion_protection         = var.environment == "production" ? true : false

  tags = {
    Name = "incidentx-${var.environment}-postgres"
  }
}

# ------------------------------------------------------------------------------
# 7. Compute Tier (AWS ECS Fargate Cluster & Service Orchestration)
# ------------------------------------------------------------------------------
resource "aws_ecs_cluster" "cluster" {
  name = "incidentx-${var.environment}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "incidentx-${var.environment}-ecs"
  }
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/incidentx-${var.environment}"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.incidentx_key.arn

  tags = {
    Name = "incidentx-${var.environment}-logs"
  }
}
