# IncidentX AI — Stage 6.9: Cloud Deployment & Infrastructure as Code Guide

## 1. Overview & Cloud Architecture Philosophy

The IncidentX AI platform is engineered for cloud-agnostic, enterprise-grade deployment across major cloud providers (AWS, Google Cloud, Microsoft Azure) using standard container runtimes, managed relational persistence, distributed memory caches, and Infrastructure as Code (IaC) via Terraform.

The architecture enforces:
- **Zero-Trust Network Isolation:** Public ingress terminates at the Application Load Balancer (ALB). Application containers reside in isolated private subnets with outbound NAT egress only. Databases and caches operate within completely isolated private subnets with no public internet ingress.
- **Defense in Depth & Cryptographic Protection:** All data at rest is encrypted with customer-managed KMS keys. Secrets are dynamically retrieved from managed Secret Stores.
- **High Availability & Zero Downtime:** Multi-AZ deployment across three Availability Zones with automated failover and health probes.

---

## 2. Multi-Cloud Architecture Mapping

| Component | AWS Topology | Google Cloud Platform (GCP) | Microsoft Azure |
| :--- | :--- | :--- | :--- |
| **Container Compute** | Amazon ECS Fargate | Google Cloud Run / GKE Autopilot | Azure Container Apps / AKS |
| **Relational Database** | Amazon RDS PostgreSQL (Multi-AZ) | Google Cloud SQL for PostgreSQL | Azure Database for PostgreSQL Flexible Server |
| **Cache & Event Bus** | Amazon ElastiCache for Redis | Google Cloud Memorystore for Redis | Azure Cache for Redis |
| **Object / Evidence Store**| Amazon S3 (Encrypted + Versioned) | Google Cloud Storage (Standard) | Azure Blob Storage (ZRS) |
| **Key & Secret Management**| AWS KMS & Secrets Manager | Google Cloud KMS & Secret Manager| Azure Key Vault |
| **Load Balancing & Ingress**| Application Load Balancer (ALB) | Cloud Load Balancing + Cloud Armor | Azure Application Gateway (WAF v2) |
| **Observability** | Amazon CloudWatch & OpenTelemetry | Google Cloud Monitoring & Trace | Azure Monitor & Log Analytics |

---

## 3. Environment Segregation Matrix

| Attribute | Local Development | Staging | Production |
| :--- | :--- | :--- | :--- |
| **Host Environment** | Docker Compose (`docker-compose.yml`) | Cloud VPC (Staging) | Cloud VPC (Production) |
| **Database** | Local SQLite / Postgres container | Cloud RDS (Single-AZ / db.t4g.medium) | Cloud RDS (Multi-AZ / db.r6g.xlarge) |
| **Telemetry Ingestion** | Simulated 7-Node DemoMesh | Synthetic load generator + Mock integrations | Live OpenTelemetry Collectors + Real Integrations |
| **Data Retention** | Ephemeral | 7 Days | 30 Days (Continuous Point-in-time recovery) |
| **Auto-Scaling Range** | 1 instance | 1 – 3 instances | 2 – 10 instances |
| **Audit Log Integrity** | Local SHA256 chain | CloudWatch encrypted log stream | CloudWatch encrypted + WORM S3 audit vault |

---

## 4. Container Hardening Architecture

Both Backend and Frontend images are constructed with minimal attack surfaces:

1. **Backend (`infrastructure/docker/Dockerfile.backend`):**
   - **Stage 1 (Builder):** Uses `python:3.12-slim` to build Python wheels in `/build/wheels` with build essentials and compilers.
   - **Stage 2 (Runner):** Installs pre-compiled wheels into a fresh `python:3.12-slim` container without compilers (`gcc`, `g++`, `make` removed).
   - Dedicated non-root user `incidentx:10001`.
   - Native Kubernetes/Docker healthcheck probe targeting `/healthz` or `/api/v1/health/live`.
   - `STOPSIGNAL SIGTERM` for graceful request draining.

2. **Frontend (`infrastructure/docker/Dockerfile.frontend`):**
   - **Stage 1 (Deps):** `node:22-alpine` with `libc6-compat` installing dependencies via `npm ci`.
   - **Stage 2 (Builder):** Compiles Next.js 15.5 application into standalone server output.
   - **Stage 3 (Runner):** Lightweight runner containing only `server.js` and `.next/static` assets.
   - Dedicated non-root user `nextjs:1001`.

---

## 5. Terraform Infrastructure as Code (IaC)

The Terraform blueprint in `infrastructure/terraform/` defines the complete cloud footprint:
- **`versions.tf`**: Pinned provider requirements (AWS `>= 5.0`, Terraform `>= 1.5.0`).
- **`variables.tf`**: Parameterized inputs for environment sizing, CIDRs, and container images.
- **`main.tf`**: 
  - Dedicated VPC with 3-tier subnets (Public, Application Private, Database Isolated).
  - AWS KMS Key with 30-day rotation and automated cryptographic alias.
  - S3 bucket for incident evidence with versioning and KMS SSE.
  - Multi-AZ PostgreSQL 16 RDS instance with automated backup retention.
  - Least-privilege security groups strictly restricting database access to ECS tasks.
  - CloudWatch Log Group with KMS encryption.
- **`outputs.tf`**: Critical infrastructure outputs (VPC ID, RDS Endpoint, S3 Bucket, KMS ARN).

---

## 6. Deployment & Rollback Playbook

### Step 1: Validate IaC Templates
```bash
cd infrastructure/terraform
terraform init
terraform validate
terraform plan -var-file=terraform.tfvars.example
```

### Step 2: Database Migration Execution
```bash
# Execute idempotent Phase 6 database schema migrations prior to container deployment
python -m backend.app.core.migration_phase6
```

### Step 3: Blue/Green Container Rolling Update
```bash
# Deploy updated backend and frontend tasks with zero downtime
aws ecs update-service \
  --cluster incidentx-production-cluster \
  --service incidentx-backend-service \
  --force-new-deployment
```

### Step 4: Verification Probes
```bash
# Verify health of deployed container services
curl -f https://api.incidentx.enterprise.internal/api/v1/health/live
curl -f https://api.incidentx.enterprise.internal/api/v1/health/ready
```

### Emergency Rollback Playbook
If health check failure rates exceed 1% or P99 latency exceeds 500ms after a deployment:
1. **Rollback Container Image:**
   ```bash
   aws ecs update-service \
     --cluster incidentx-production-cluster \
     --service incidentx-backend-service \
     --task-definition incidentx-backend-service:<PREVIOUS_STABLE_REVISION>
   ```
2. **Rollback Database (if schema changes were backwards-incompatible):**
   ```bash
   python infrastructure/scripts/restore.py --backup-id <PRE_DEPLOYMENT_BACKUP_ID>
   ```
3. **Verify Restored Service:**
   ```bash
   curl -f https://api.incidentx.enterprise.internal/api/v1/health/live
   ```
