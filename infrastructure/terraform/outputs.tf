# ==============================================================================
# IncidentX AI — Terraform Outputs
# ==============================================================================

output "vpc_id" {
  description = "The ID of the IncidentX VPC"
  value       = aws_vpc.main.id
}

output "kms_key_arn" {
  description = "The ARN of the master encryption KMS key"
  value       = aws_kms_key.incidentx_key.arn
}

output "secrets_manager_secret_arn" {
  description = "The ARN of the application Secrets Manager secret"
  value       = aws_secretsmanager_secret.incidentx_secrets.arn
}

output "evidence_s3_bucket" {
  description = "The name of the S3 bucket for evidence storage and disaster recovery backups"
  value       = aws_s3_bucket.evidence_storage.id
}

output "rds_postgres_endpoint" {
  description = "Private endpoint of the PostgreSQL database instance"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.cluster.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for container metrics and logs"
  value       = aws_cloudwatch_log_group.ecs_logs.name
}
