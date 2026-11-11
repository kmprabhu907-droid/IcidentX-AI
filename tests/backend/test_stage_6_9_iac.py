# ==============================================================================
# IncidentX AI — Stage 6.9 Test Suite: Cloud Deployment & Infrastructure as Code
# Validates Hardened Dockerfiles, Compose Topologies, and Terraform Blueprints
# ==============================================================================

import os
from pathlib import Path
import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestStage69ContainerHardening:
    """Validates container definitions adhere to enterprise security and hardening guidelines."""

    def test_backend_dockerfile_multi_stage_and_non_root(self):
        backend_df = REPO_ROOT / "infrastructure" / "docker" / "Dockerfile.backend"
        assert backend_df.exists(), "Dockerfile.backend must exist"

        content = backend_df.read_text()
        assert "AS builder" in content, "Backend Dockerfile must utilize multi-stage builder"
        assert "AS runner" in content, "Backend Dockerfile must utilize lean runner stage"
        assert "USER incidentx" in content, "Backend container must execute under non-root incidentx user"
        assert "HEALTHCHECK" in content, "Backend container must declare an automated healthcheck probe"
        assert "STOPSIGNAL SIGTERM" in content, "Backend container must declare SIGTERM for graceful shutdown"

    def test_frontend_dockerfile_standalone_and_non_root(self):
        frontend_df = REPO_ROOT / "infrastructure" / "docker" / "Dockerfile.frontend"
        assert frontend_df.exists(), "Dockerfile.frontend must exist"

        content = frontend_df.read_text()
        assert "AS builder" in content, "Frontend Dockerfile must utilize multi-stage builder"
        assert "AS runner" in content, "Frontend Dockerfile must utilize lean runner stage"
        assert "USER nextjs" in content, "Frontend container must execute under non-root nextjs user"
        assert "HEALTHCHECK" in content, "Frontend container must declare an automated healthcheck probe"
        assert "STOPSIGNAL SIGTERM" in content, "Frontend container must declare SIGTERM for graceful shutdown"

    def test_production_docker_compose_valid_and_hardened(self):
        prod_compose = REPO_ROOT / "docker-compose.prod.yml"
        assert prod_compose.exists(), "docker-compose.prod.yml must exist"

        with open(prod_compose, "r") as f:
            data = yaml.safe_load(f)

        assert "services" in data, "Compose must declare services"
        services = data["services"]

        # Verify key services
        assert "backend" in services, "Backend service must be declared"
        assert "frontend" in services, "Frontend service must be declared"
        assert "postgres" in services, "PostgreSQL service must be declared"
        assert "redis" in services, "Redis service must be declared"

        # Verify network segregation and resource limits
        for svc_name in ["backend", "frontend", "postgres"]:
            svc = services[svc_name]
            assert "healthcheck" in svc, f"{svc_name} must declare automated healthcheck"
            assert "deploy" in svc and "resources" in svc["deploy"], f"{svc_name} must define resource constraints"
            assert "logging" in svc, f"{svc_name} must configure log rotation"

        assert "incidentx_internal" in data["networks"], "Internal network must be present"
        assert "incidentx_data" in data["networks"], "Isolated database network must be present"


class TestStage69TerraformIaC:
    """Validates Infrastructure as Code Terraform blueprints."""

    def test_terraform_files_exist(self):
        tf_dir = REPO_ROOT / "infrastructure" / "terraform"
        assert (tf_dir / "versions.tf").exists(), "versions.tf must exist"
        assert (tf_dir / "variables.tf").exists(), "variables.tf must exist"
        assert (tf_dir / "main.tf").exists(), "main.tf must exist"
        assert (tf_dir / "outputs.tf").exists(), "outputs.tf must exist"
        assert (tf_dir / "terraform.tfvars.example").exists(), "terraform.tfvars.example must exist"

    def test_terraform_resources_and_security_controls(self):
        main_tf = (REPO_ROOT / "infrastructure" / "terraform" / "main.tf").read_text()

        # KMS Key encryption
        assert "aws_kms_key" in main_tf, "Terraform must define master KMS key"
        assert "enable_key_rotation" in main_tf, "Terraform must enforce KMS key rotation"

        # Secrets Manager
        assert "aws_secretsmanager_secret" in main_tf, "Terraform must define Secrets Manager resource"

        # S3 Evidence Vault
        assert "aws_s3_bucket" in main_tf, "Terraform must define S3 evidence storage"
        assert "aws_s3_bucket_server_side_encryption_configuration" in main_tf, "S3 must enforce KMS encryption"
        assert "aws_s3_bucket_public_access_block" in main_tf, "S3 must block public access"

        # Network Isolation (VPC, Subnets, Security Groups)
        assert "aws_vpc" in main_tf, "Terraform must define dedicated VPC"
        assert "aws_security_group" in main_tf, "Terraform must define tier-specific security groups"

        # RDS PostgreSQL Multi-AZ
        assert "aws_db_instance" in main_tf, "Terraform must define managed PostgreSQL instance"
        assert "multi_az" in main_tf, "Terraform must configure Multi-AZ failover"
        assert "storage_encrypted" in main_tf, "Terraform must enforce database storage encryption"

        # ECS Fargate Compute
        assert "aws_ecs_cluster" in main_tf, "Terraform must define ECS cluster"
        assert "aws_cloudwatch_log_group" in main_tf, "Terraform must configure CloudWatch logging"

    def test_deployment_documentation_exists(self):
        doc = REPO_ROOT / "docs" / "phase6" / "stage_6_9_cloud_deployment.md"
        assert doc.exists(), "Cloud deployment documentation must exist"
        content = doc.read_text()
        assert "Multi-Cloud Architecture Mapping" in content
        assert "Rollback Playbook" in content
