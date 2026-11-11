# IncidentX AI — Stage 6.10: Enterprise Governance, Audit & Operational Management

## 1. Overview & Governance Philosophy

IncidentX AI operates as a mission-critical Continuous Reliability Intelligence Platform. Because autonomous operations, AI investigation agents, and remediation execution can influence live service availability, enterprise-grade governance is non-negotiable.

Stage 6.10 establishes:
1. **Cryptographically Chained Audit Ledger:** Append-only, tamper-evident SHA-256 hash chaining (blockchain-style ledger) for all system actions, agent decisions, and human interventions.
2. **Automated Sensitive-Data Redaction:** Prevention of secrets, credentials, API keys, or JWT tokens from being written to persistent audit storage.
3. **Deterministic Governance Policy Engine:** Configurable policies governing AI autonomous execution permissions, dual-engineer approval gates, data retention schedules, and organizational resource limits.
4. **Consolidated Operational Administration:** Real-time visibility into platform health, agent activity, integration statuses, and storage utilization.
5. **Compliance Readiness:** Technical and architectural alignment with SOC 2 Trust Services Criteria and ISO/IEC 27001.

---

## 2. Cryptographic Audit Ledger Architecture

### SHA-256 Block Chaining Mechanism
Every audit entry is cryptographically linked to the immediately preceding record within that organization's ledger:

$$\text{Block Hash}_i = \text{SHA256}\Big(\text{Hash}_{i-1} \,\|\, \text{Timestamp} \,\|\, \text{ActorType} \,\|\, \text{ActorID} \,\|\, \text{Action} \,\|\, \text{Resource} \,\|\, \text{Details}\Big)$$

- **Genesis Record:** The initial record links to $\text{Hash}_0 = 0^{64}$.
- **Immutability Guarantee:** Any modification, insertion, or retroactive deletion of an audit record invalidates all subsequent checksums across the entire organization's history.
- **Verification API (`/api/v1/audit-logs/verify`):** Performs full ledger traversal, recomputing each block's cryptographic hash and verifying chain continuity. Any detected inconsistency immediately surfaces the exact tampered record ID and broken linkage.

### Sensitive Data Redaction
Before any audit record is persisted, `sanitize_audit_details` inspects all payload attributes and recursively redacts sensitive fields matching:
`password`, `token`, `secret`, `authorization`, `api_key`, `credentials`, `access_token`, `refresh_token`.

---

## 3. Governance Policy Framework

The platform provides a centralized, deterministic Policy Engine (`backend/app/services/governance/policy_engine.py`) supporting four configurable policy categories:

| Policy Category | Key Configurable Parameters | Default Baseline |
| :--- | :--- | :--- |
| **`AI_EXECUTION_PERMISSION`** | `allowed_autonomous_actions`<br>`max_autonomous_risk_score`<br>`max_daily_autonomous_executions`<br>`require_human_gate_for_destructive` | Allowlist: `["scale_service", "restart_pod", "clear_cache"]`<br>Max Risk: `0.40`<br>Max Daily: `25`<br>Human Gate: `True` |
| **`APPROVAL_POLICY`** | `require_dual_approval`<br>`dual_approval_risk_threshold`<br>`allowed_approver_roles` | Dual Threshold: `0.70`<br>Approver Roles: `SUPER_ADMIN`, `ORGANIZATION_ADMIN`, `SRE_ENGINEER` |
| **`DATA_RETENTION`** | `retention_days`<br>`archive_before_purge`<br>`immutable_audit_years` | Retention: `90 days`<br>Audit Storage: `7 years` |
| **`ORG_LIMITS`** | `max_concurrent_simulations`<br>`max_monthly_incidents`<br>`max_registered_users` | Concurrent Sims: `5`<br>Incidents/Mo: `500`<br>Users: `50` |

---

## 4. Role-Based Access Control & Segregation of Duties

The IncidentX RBAC model enforces strict segregation of duties across six enterprise roles:

1. **`SUPER_ADMIN`:** Full cross-organization visibility, global system configuration, infrastructure administration.
2. **`ORGANIZATION_ADMIN`:** Tenant-level management, member invitation, role assignment, governance policy modification.
3. **`SRE_ENGINEER`:** Full operational access: trigger simulations, investigate incidents, execute approved remediations, configure SLOs.
4. **`INCIDENT_RESPONDER`:** Incident investigation, evidence analysis, triage, and what-if simulation execution.
5. **`SECURITY_AUDITOR`:** Read-only access to tamper-evident audit logs, compliance reports, and system activity logs.
6. **`READ_ONLY_VIEWER`:** Dashboard observation only; mutations and sensitive endpoints blocked.

---

## 5. Compliance Framework Alignment

IncidentX AI implements technical controls designed to satisfy external audit standards:

### SOC 2 Trust Services Criteria (TSC)
- **CC6.1 (Logical Access Controls):** Enforced via PyJWT HMAC-SHA256 bearer tokens, bcrypt password hashing, and granular RBAC role dependencies.
- **CC6.2 (User Registration & Access Modification):** Role changes and organization membership modifications are cryptographically recorded in the audit ledger.
- **CC6.3 (Least Privilege):** Separation of SRE, Responder, and Auditor roles ensures least privilege.
- **CC6.6 (Boundary Protection):** Multi-tier VPC isolation, ALB HTTPS termination, and internal-only database subnets.
- **CC7.1 & CC7.2 (Vulnerability Management & Monitoring):** Bandit AST scanning, GitHub Actions CI DevSecOps checks, Prometheus metrics, and OpenTelemetry distributed tracing.
- **CC7.4 (Incident Response Governance):** Strict human approval workflow for high-risk remediations, automated rollback playbooks, and root-cause evidence tracking.

### ISO/IEC 27001:2022 Mapping
- **A.5.15 (Access Control):** Strict role definitions with tenant boundary isolation.
- **A.8.15 (Logging):** Tamper-evident, cryptographically chained audit logging.
- **A.8.16 (Monitoring Activities):** Continuous telemetry collector with sliding-window anomaly and regression detection.
- **A.8.24 (Use of Cryptography):** TLS 1.3 in transit, KMS AES-256 at rest for RDS and S3, bcrypt for credentials.

> [!IMPORTANT]
> **Compliance Disclaimer:** While IncidentX AI provides the architectural safeguards and technical mechanisms to support compliance audits, no software platform can be "certified" in isolation. Formal SOC 2 or ISO 27001 certification requires an independent third-party audit of the operational organization, policies, and production deployment.
