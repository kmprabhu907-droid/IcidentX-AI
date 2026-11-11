# IncidentX AI — Phase 5 Reproducible Demonstration Scenario
## Hackathon Live Demonstration Guide

This scenario demonstrates the complete autonomous reliability intelligence loop in under 3 minutes.

### Scenario Flow: The Creeping Database Connection Starvation

#### Step 1: Open the SRE Command Center
1. Navigate to `http://localhost:3000/reliability` in the browser.
2. Observe the **Overview Tab**: 7 monitored DemoMesh nodes operating nominally.
3. Review the **SLO & Error Budget Tab**: 100% budget remaining, burn rate $\le 1.0\times$.

#### Step 2: Inject Resource Degradation
Open a terminal and inject a database connection leak on `order-service`:
```bash
curl -X POST http://localhost:8000/api/v1/simulation/scenarios/order-db-leak/start \
  -H "Content-Type: application/json" \
  -d '{"severity": "CRITICAL"}'
```

#### Step 3: Anomaly & Predictive Detection
1. Refresh `http://localhost:3000/reliability` or watch live updates.
2. In the **Predictive Warnings Tab**, observe:
   - `db_pool_utilization` trend slope turns sharply positive ($+0.5\%/\text{sec}$).
   - **Time-to-Exhaustion (TTE)** displays: `4.2 minutes to 95% threshold breach`.
   - Forward 30-minute projections show confidence intervals diverging upwards.

#### Step 4: Multi-Window Error Budget Burn Rate Alert
1. In the **SLO Tab**, notice the 1-hour burn rate spikes to `18.5x`.
2. A **CRITICAL FAST BURN** badge appears:
   > *"Fast burn detected: 30-day budget will exhaust in under 48 hours."*

#### Step 5: Autonomous LangGraph Agent Assessment
1. Switch to the **Autonomous Agent Tab** or click **"Execute Agent Loop"**:
2. Watch the 8-node LangGraph execution trace:
   - Node 1: Gather streaming telemetry
   - Node 2: Retrieve active anomalies
   - Node 3: Query Reliability Memory for matching past pool leaks
   - Node 4: Regression check
   - Node 5: Evaluate TTE
   - Node 6: SLO burn rate assessment
   - Node 7: Decision policy triggers safe action: `act-reset-db-pool` with `CONTROLLED_AUTONOMOUS` mode (due to past memory confirmation).
   - Node 8: Tamper-evident audit log written.

#### Step 6: Incident Time Machine & NetworkX Causal Graph
1. Switch to the **Incident Time Machine Tab**:
2. Observe the NetworkX dependency topology:
   - `postgres-db` marked as `FAILING` / Root Cause Candidate.
   - Failure propagation path highlighted: `api-gateway ➔ order-service ➔ postgres-db`.
   - Blast radius score evaluated at `62%`.
3. Review the unified chronological timeline correlating metrics, logs, hypotheses, and remediations.

#### Step 7: Safe Autonomous Remediation & Verification
1. Safe action `act-reset-db-pool` executes.
2. Clear the simulation fault:
```bash
curl -X POST http://localhost:8000/api/v1/simulation/scenarios/clear
```
3. Observe continuous verification:
   - DB pool utilization drops from 95% back to 18%.
   - Four-state comparison engine validates zero regression (`WORSENING_METRICS = []`).
   - Incident resolves and updates Reliability Memory with outcome `SUSTAINED_SUCCESS`.
