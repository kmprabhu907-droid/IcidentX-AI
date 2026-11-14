# 🛡️ INCIDENTX AI

> **The Autonomous Reliability Intelligence System**  
> *Autonomous AI Incident Investigation, Causal Reasoning, and Self-Healing Platform*

[![Presentation Deck](https://img.shields.io/badge/📊_Presentation-Pitch_Deck_(PowerPoint)-orange?style=for-the-badge)](https://1drv.ms/p/c/00BD976D974844F1/IQAyYpedLc2UT4xLKQ9SASnJAY_FSRiA5eGyeO89TX9vrEo?e=RNOHvd)
[![Team TitanIQ](https://img.shields.io/badge/Team-TitanIQ-blue?style=for-the-badge)](#)
[![Hackathon](https://img.shields.io/badge/AgentX_2026-Sahyadri_College-success?style=for-the-badge)](#)

---

## 📊 Presentation & Pitch Deck
- 🖥️ **Official Slide Deck**: **[Click here to view IncidentX AI Pitch Deck (OneDrive PowerPoint)](https://1drv.ms/p/c/00BD976D974844F1/IQAyYpedLc2UT4xLKQ9SASnJAY_FSRiA5eGyeO89TX9vrEo?e=RNOHvd)**
- 👥 **Team**: TitanIQ | **Event**: AgentX 2026 Autonomous AI Showcase

---

## 📌 Executive Overview

**INCIDENTX AI** is an advanced autonomous reliability intelligence platform designed to investigate, diagnose, simulate, and remediate distributed software failures. Rather than relying on superficial text summarization or passive dashboards, INCIDENTX AI operates as an active, evidence-driven reliability copilot and automated investigation system.

### The 5 Core Architectural Pillars

1. **Incident Time Machine**: High-resolution temporal telemetry replay to scrub through and reconstruct the evolution of outages.
2. **Root Cause Courtroom**: Multi-agent adversarial debate (Prosecutor vs. Defense vs. Judge) that evaluates competing failure hypotheses against empirical evidence.
3. **Active Investigation Planner**: Information-theoretic diagnostic tree search (LATS) that selects the safest and most informative next observability action.
4. **What-If Laboratory**: Counterfactual digital twin sandbox that simulates alternative recovery strategies and certifies zero blast radius before live execution.
5. **Reliability Memory**: Episodic knowledge base that transforms resolved incidents into permanent, automated chaos engineering regression suites.

---

## 🏗️ Repository Architecture

This repository is organized as a modular monorepo:

```
incidentx-ai/
├── frontend/             # Next.js 15, TypeScript, Tailwind CSS
├── backend/              # Python 3.12, FastAPI, Pydantic, SQLAlchemy, LangGraph
│   └── app/
│       ├── api/          # REST & WebSocket route handlers
│       ├── core/         # Configuration, logging, database sessions
│       ├── models/       # SQLAlchemy relational database models
│       ├── schemas/      # Pydantic validation schemas
│       └── services/     # Modular domain engines (observability, agents, causal, simulation)
├── infrastructure/       # Docker Compose, Prometheus, OpenTelemetry Collector configs
├── docs/                 # Architectural specifications and phase blueprints
├── scripts/              # Development, data seeding, and utility automation scripts
├── tests/                # Pytest (backend) and Jest/Playwright (frontend) test suites
├── .env.example          # Environment variables template
├── .gitignore            # Version control exclusions
└── README.md             # Project documentation index
```

---

## 📚 Architectural Documentation

The architectural foundation of INCIDENTX AI is defined across six technical specifications located in the `docs/` directory:

- [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) — Strategic manifesto, target personas, core reliability problems, and product capabilities.
- [docs/TECHNICAL_ARCHITECTURE.md](docs/TECHNICAL_ARCHITECTURE.md) — End-to-end technical architecture, component interactions, database schemas, and data flow.
- [docs/COMPETITIVE_ANALYSIS.md](docs/COMPETITIVE_ANALYSIS.md) — Landscape analysis of APM, AIOps, academic papers, and our distinctive research contribution.
- [docs/INNOVATION_PROPOSAL.md](docs/INNOVATION_PROPOSAL.md) — Deep technical specification of the five core innovations.
- [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) — Detailed 10-phase engineering execution plan with milestones, deliverables, and acceptance criteria.
- [docs/SYSTEM_REQUIREMENTS.md](docs/SYSTEM_REQUIREMENTS.md) — Prerequisites, environment specifications, dependency matrix, and hardware/software requirements.

---

## 🔒 Engineering Rules of Engagement

1. **Never fabricate production metrics**: Clearly distinguish live, simulated, and unavailable data in all interfaces.
2. **Never claim an AI agent works unless it has actual execution logic**: No cosmetic mocks or static text facades.
3. **Never claim causal proof from correlation alone**: Formal causal DAGs and conditional independence testing are required.
4. **Never allow unrestricted AI-generated infrastructure commands**: Enforce deterministic safety policy guardrails.
5. **Use isolated environments for failure simulations**: What-If experiments must execute in sandboxed replicas.
6. **Require human approval for state-changing operations**: Destructive mutations require explicit Human-in-the-Loop authorization.
7. **Keep the architecture modular**: Clean separation between ingestion, reasoning, simulation, and execution.
8. **Write testable and maintainable code**: Comprehensive unit, integration, and property-based test coverage.
9. **Document all architectural decisions**: Maintain ADRs (Architectural Decision Records) for all major trade-offs.

---

## 🚦 Project Status

- **Current Phase**: **Phase 0 — Project Initialization & Architectural Blueprint** (Complete)
- **Next Phase**: **Phase 1 — Backend, Frontend and Database Foundation** (Pending user approval)
