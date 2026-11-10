# ⚙️ INCIDENTX AI — System Requirements & Environment Specifications

> **Project Name:** INCIDENTX AI  
> **Status:** Phase 0 Architectural Blueprint  
> **Target Audience:** Core Developers, DevOps Engineers & Infrastructure Evaluators

---

## 1. Development & Runtime Environment Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SYSTEM ENVIRONMENT MATRIX                         │
├───────────────────────┬─────────────────────────────┬───────────────────────┤
│ Component             │ Minimum Requirement         │ Recommended Production│
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **Operating System**  │ macOS 14+, Ubuntu 22.04 LTS,│ Linux (Ubuntu/Debian) │
│                       │ Windows 11 with WSL2        │ or macOS (Apple Silicon)│
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **CPU Architecture**  │ 4 Cores (x86_64 / ARM64)    │ 8+ Cores              │
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **System Memory**     │ 8 GB RAM                    │ 16 GB - 32 GB RAM     │
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **Disk Space**        │ 10 GB Free Storage          │ 50 GB SSD             │
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **Python Runtime**    │ Python 3.12+                │ Python 3.12.7         │
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **Node.js Runtime**   │ Node.js 20 LTS (v20.14+)    │ Node.js 22 LTS        │
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **Package Managers**  │ `pip` 24+, `pnpm` 9+ or npm │ `pnpm` & `uv`         │
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **Container Engine**  │ Docker Engine 24+           │ Docker Engine 26+ with│
│                       │ Docker Compose v2.20+       │ Compose v2            │
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ **Database**          │ PostgreSQL 15+              │ PostgreSQL 16 with    │
│                       │                             │ `pgvector` extension  │
└───────────────────────┴─────────────────────────────┴───────────────────────┘
```

---

## 2. Software Dependencies & Toolchain

### 2.1 Backend Core Dependencies (Python)

```text
# Web Framework & Async I/O
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.9.0
pydantic-settings>=2.5.0
httpx>=0.27.0
websockets>=13.0

# Database & ORM
sqlalchemy[asyncio]>=2.0.35
asyncpg>=0.29.0
alembic>=1.13.0
psycopg2-binary>=2.9.9

# AI & Multi-Agent Orchestration
langgraph>=0.2.35
langchain-core>=0.3.0
google-genai>=1.0.0
anthropic>=0.37.0
openai>=1.52.0

# Causal & Graph Processing
networkx>=3.4.0
scipy>=1.14.0
numpy>=2.1.0

# Observability & Security
opentelemetry-api>=1.27.0
opentelemetry-sdk>=1.27.0
prometheus-client>=0.21.0
cryptography>=43.0.0

# Testing & Quality
pytest>=8.3.0
pytest-asyncio>=0.24.0
pytest-cov>=5.0.0
black>=24.8.0
ruff>=0.7.0
```

### 2.2 Frontend Core Dependencies (Node / Next.js)

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.6.0",
    "tailwindcss": "^3.4.14",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4",
    "lucide-react": "^0.454.0",
    "@xyflow/react": "^12.3.0",
    "canvas-confetti": "^1.9.3",
    "uplot": "^1.6.30"
  },
  "devDependencies": {
    "@types/node": "^22.8.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@types/canvas-confetti": "^1.9.0",
    "postcss": "^8.4.47",
    "autoprefixer": "^10.4.20",
    "eslint": "^9.13.0",
    "eslint-config-next": "^15.0.0"
  }
}
```

---

## 3. Network Ports & Service Topology

| Port | Service | Protocol | Access Scope | Description |
| :--- | :--- | :--- | :--- | :--- |
| **3000** | Next.js Frontend | HTTP / WebSocket | Public / Internal | IncidentX Web User Interface & Time Machine |
| **8000** | FastAPI Backend | HTTP / REST / WS | Internal / Proxy | API Gateway, Agent Orchestrator, WebSocket Bus |
| **5432** | PostgreSQL Database | TCP (Postgres Wire)| Internal Only | Core relational storage & pgvector embeddings |
| **9090** | Prometheus Server | HTTP | Internal Only | Telemetry metrics collection & PromQL queries |
| **4317** | OpenTelemetry Collector | gRPC | Internal Only | Ingestion of distributed trace spans |
| **4318** | OpenTelemetry Collector | HTTP | Internal Only | Ingestion of OTel JSON traces & metrics |

---

## 4. Environment Variables Specification

The platform requires configuration defined in `.env` (derived from `.env.example`):

```bash
# Core Environment
APP_ENV=development                       # 'development' | 'staging' | 'production'
APP_DEBUG=true                            # Enables verbose exception logging
LOG_LEVEL=INFO                            # 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
SECRET_KEY=generate-32-byte-hex-key       # Used for session security

# Backend Network
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000

# Frontend Network
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Database Connection
DATABASE_URL=postgresql+asyncpg://incidentx_admin:incidentx_dev_password@localhost:5432/incidentx_db

# LLM Providers (At least one key required for AI reasoning)
LLM_PROVIDER=gemini                       # 'gemini' | 'claude' | 'openai' | 'ollama'
GEMINI_API_KEY=                           # Google Gemini API key
ANTHROPIC_API_KEY=                        # Anthropic Claude API key
OPENAI_API_KEY=                           # OpenAI API key
OLLAMA_BASE_URL=http://localhost:11434    # Local Ollama endpoint

# Telemetry Integrations
PROMETHEUS_ENDPOINT=http://localhost:9090
OPENTELEMETRY_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=incidentx-backend

# Security & Governance
ENABLE_EXECUTION_GUARDRAILS=true          # Strictly enforces safety policies
REQUIRE_HUMAN_APPROVAL_MUTATION=true      # Requires 1-click confirmation for mutations
SLACK_WEBHOOK_URL=                        # Optional Slack notification webhook
```

---

## 5. Security & Isolation Prerequisites

1. **Local Container Isolation**:
   - Docker daemon must be running with permissions to create and destroy isolated bridge networks for the What-If simulation sandbox.
2. **Keypair Generation for Attestations**:
   - The backend generates an Ed25519 keypair on startup to sign verified simulation attestations.
3. **No Root Privilege Execution**:
   - All backend containers and application processes must run under dedicated non-root users (`uid=10001`).
4. **Data Sanitization**:
   - PII filtering and credential scrubbing are enforced on all inbound payloads before telemetry is stored or passed to agent reasoning graphs.
