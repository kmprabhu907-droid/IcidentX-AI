# ==============================================================================
# Terraform Input Variables for IncidentX AI
# ==============================================================================

variable "aws_region" {
  description = "Target AWS region for deploying IncidentX AI infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated IncidentX VPC"
  type        = string
  default     = "10.100.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones for Multi-AZ resilience"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (ALB, NAT Gateways)"
  type        = list(string)
  default     = ["10.100.1.0/24", "10.100.2.0/24", "10.100.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private application subnets (ECS / Containers)"
  type        = list(string)
  default     = ["10.100.11.0/24", "10.100.12.0/24", "10.100.13.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for isolated database subnets (RDS PostgreSQL)"
  type        = list(string)
  default     = ["10.100.21.0/24", "10.100.22.0/24", "10.100.23.0/24"]
}

# --- Database Configurations ---
variable "db_instance_class" {
  description = "RDS instance class (e.g. db.r6g.xlarge for prod, db.t4g.medium for staging)"
  type        = string
  default     = "db.t4g.medium"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB for PostgreSQL"
  type        = number
  default     = 100
}

variable "db_multi_az" {
  description = "Enable Multi-AZ high availability failover"
  type        = bool
  default     = true
}

variable "db_name" {
  description = "Initial database name"
  type        = string
  default     = "incidentx_db"
}

variable "db_username" {
  description = "Master username for PostgreSQL database"
  type        = string
  default     = "incidentx_admin"
}

# --- Compute Configurations ---
variable "backend_cpu" {
  description = "Fargate task vCPU allocation for Backend (1024 = 1 vCPU)"
  type        = number
  default     = 2048
}

variable "backend_memory" {
  description = "Fargate task RAM allocation in MB for Backend"
  type        = number
  default     = 4096
}

variable "backend_desired_count" {
  description = "Desired number of running backend container instances"
  type        = number
  default     = 2
}

variable "backend_min_count" {
  description = "Minimum auto-scaling count"
  type        = number
  default     = 2
}

variable "backend_max_count" {
  description = "Maximum auto-scaling count during high load"
  type        = number
  default     = 10
}

variable "frontend_desired_count" {
  description = "Desired number of running frontend container instances"
  type        = number
  default     = 2
}

variable "container_image_backend" {
  description = "ECR image URI for the backend service"
  type        = string
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/incidentx-backend:latest"
}

variable "container_image_frontend" {
  description = "ECR image URI for the frontend service"
  type        = string
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/incidentx-frontend:latest"
}

variable "domain_name" {
  description = "Apex domain name for SSL/TLS certificate"
  type        = string
  default     = "incidentx.enterprise.internal"
}
