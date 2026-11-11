# ==============================================================================
# Terraform Version & Provider Specifications
# IncidentX AI — Cloud Deployment & Infrastructure as Code
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Production backend state should be configured with S3 + DynamoDB locking
  # backend "s3" {
  #   bucket         = "incidentx-terraform-state-prod"
  #   key            = "production/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "incidentx-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "IncidentX-AI"
      ManagedBy   = "Terraform"
      Environment = var.environment
      Platform    = "Continuous-Reliability-Intelligence"
    }
  }
}
