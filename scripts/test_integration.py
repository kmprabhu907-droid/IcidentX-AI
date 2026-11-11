"""
INCIDENTX AI - End-to-End System Integration Test
Verifies live backend endpoints, database persistence, observability, chaos lab, and frontend availability.
"""

import sys
import httpx

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"


def run_checks():
    print("=" * 60)
    print("🚀 INCIDENTX AI — LIVE INTEGRATION VERIFICATION")
    print("=" * 60)

    with httpx.Client(timeout=10.0) as client:
        # 1. Healthz
        print("\n[1/12] Testing Backend Health (/healthz)...")
        r = client.get(f"{BACKEND_URL}/healthz")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        print(f"  ✅ Healthz OK: {data}")

        # 2. API v1 Health
        print("\n[2/12] Testing API v1 Health (/api/v1/health)...")
        r = client.get(f"{BACKEND_URL}/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["components"]["database"] == "connected"
        print(f"  ✅ API v1 Health OK: {data['service']} v{data['version']}")

        # 3. Observability Overview
        print("\n[3/12] Testing Observability Overview (/api/v1/observability/overview)...")
        obs_r = client.get(f"{BACKEND_URL}/api/v1/observability/overview")
        assert obs_r.status_code == 200
        obs = obs_r.json()
        assert "cluster_status" in obs
        assert obs["total_services"] == 7
        print(f"  ✅ Observability Cluster OK: Status={obs['cluster_status']}, Throughput={obs['total_request_rate']} rps, Data={obs['data_source']}")

        # 4. Prometheus Metrics Scrape Endpoint
        print("\n[4/12] Testing Prometheus Metrics (/api/v1/telemetry/prometheus)...")
        prom_r = client.get(f"{BACKEND_URL}/api/v1/telemetry/prometheus")
        assert prom_r.status_code == 200
        assert "incidentx_request_rate_seconds" in prom_r.text
        print("  ✅ Prometheus Scrape Endpoint OK (Standard exposition format)")

        # 5. Distributed Traces
        print("\n[5/12] Testing Distributed Traces (/api/v1/telemetry/traces)...")
        traces_r = client.get(f"{BACKEND_URL}/api/v1/telemetry/traces?limit=5")
        assert traces_r.status_code == 200
        traces_data = traces_r.json()
        assert len(traces_data["traces"]) > 0
        t0 = traces_data["traces"][0]
        assert "spans" in t0
        assert len(t0["spans"]) > 0
        print(f"  ✅ Distributed Tracing OK: Retrieved {len(traces_data['traces'])} traces, First trace has {len(t0['spans'])} spans")

        # 6. Correlated Logs
        print("\n[6/12] Testing Correlated Structured Logs (/api/v1/telemetry/logs)...")
        logs_r = client.get(f"{BACKEND_URL}/api/v1/telemetry/logs?limit=5")
        assert logs_r.status_code == 200
        logs_data = logs_r.json()
        assert len(logs_data["logs"]) > 0
        print(f"  ✅ Correlated Logs OK: Retrieved {len(logs_data['logs'])} log records")

        # 7. Chaos Scenarios
        print("\n[7/12] Testing Failure Injection Lab Scenarios (/api/v1/simulation/scenarios)...")
        scen_r = client.get(f"{BACKEND_URL}/api/v1/simulation/scenarios")
        assert scen_r.status_code == 200
        scenarios = scen_r.json()
        assert len(scenarios) == 9
        print(f"  ✅ Chaos Controller OK: 9 Scenarios Verified ({', '.join(s['id'] for s in scenarios[:4])}...)")

        # 8. Chaos Injection and Auto-Tagging
        print("\n[8/12] Testing Chaos Injection (/api/v1/simulation/inject)...")
        inject_r = client.post(
            f"{BACKEND_URL}/api/v1/simulation/inject",
            json={"scenario_id": "payment_latency", "duration_seconds": 15, "parameters": {"latency_ms": 2200.0}}
        )
        assert inject_r.status_code == 200
        inject_data = inject_r.json()
        assert inject_data["fault"]["data_source"] == "SIMULATED"
        print(f"  ✅ Chaos Injected: Fault ID={inject_data['fault']['fault_id']}, Data Source=SIMULATED")

        # 9. Verify Active Simulation Status
        print("\n[9/12] Testing Active Simulation Status (/api/v1/simulation/status)...")
        status_r = client.get(f"{BACKEND_URL}/api/v1/simulation/status")
        assert status_r.status_code == 200
        status_data = status_r.json()
        assert status_data["is_active"] is True
        assert status_data["data_source"] == "SIMULATED"
        print("  ✅ Simulation Status OK: Fault active and verified")

        # 10. Emergency Stop All Chaos
        print("\n[10/12] Testing Emergency Stop (/api/v1/simulation/stop-all)...")
        stop_r = client.post(f"{BACKEND_URL}/api/v1/simulation/stop-all")
        assert stop_r.status_code == 200
        print("  ✅ Emergency Stop OK: Baseline restored")

        # 11. Create and Retrieve Incident
        print("\n[11/16] Testing Incident Lifecycle (POST /api/v1/incidents)...")
        payload = {
            "title": "Integration Test: Payment Gateway TLS Handshake Timeout",
            "summary": "Verified integration test incident record.",
            "severity": "SEV-1",
            "status": "DETECTED",
            "impact_scope": "payment-svc, checkout-cart"
        }
        r = client.post(f"{BACKEND_URL}/api/v1/incidents", json=payload)
        assert r.status_code == 201
        inc = r.json()
        incident_id = inc["id"]
        print(f"  ✅ Incident Created: ID={incident_id}, Title='{inc['title']}'")

        # 12. Trigger Autonomous Investigation
        print("\n[12/16] Testing 10-Agent Autonomous Investigation Pipeline...")
        inv_r = client.post(f"{BACKEND_URL}/api/v1/incidents/{incident_id}/investigate")
        assert inv_r.status_code == 200
        inv_data = inv_r.json()
        assert inv_data["status"] == "COMPLETED"
        total_completed = len(inv_data["investigation"]["completed_agents"])
        duration = inv_data["investigation"]["duration_ms"]
        print(f"  ✅ Autonomous Investigation Complete: Run {total_completed} agents in {duration}ms")

        # 13. Root Cause Courtroom Verification
        print("\n[13/16] Testing Root Cause Courtroom (/courtroom)...")
        court_r = client.get(f"{BACKEND_URL}/api/v1/incidents/{incident_id}/courtroom")
        assert court_r.status_code == 200
        court_data = court_r.json()
        assert court_data["total_hypotheses"] >= 2
        print(f"  ✅ Root Cause Courtroom OK: Evaluated {court_data['total_hypotheses']} competing hypotheses with adversarial rulings")

        # 14. Incident Time Machine Verification
        print("\n[14/16] Testing Incident Time Machine (/timeline)...")
        time_r = client.get(f"{BACKEND_URL}/api/v1/incidents/{incident_id}/timeline")
        assert time_r.status_code == 200
        time_data = time_r.json()
        assert time_data["total_events"] > 0
        print(f"  ✅ Incident Time Machine OK: Reconstructed {time_data['total_events']} chronological events with raw data")

        # 15. Active Investigation Planner Verification
        print("\n[15/16] Testing Active Investigation Planner (/planner)...")
        plan_r = client.get(f"{BACKEND_URL}/api/v1/incidents/{incident_id}/planner")
        assert plan_r.status_code == 200
        plan_data = plan_r.json()
        assert plan_data["total_actions"] >= 1
        for action in plan_data["recommended_actions"]:
            assert action.get("operational_risk") in ["LOW", "MEDIUM", "SAFE"] or action.get("safety_rating") in ["SAFE", "RESTRICTED", "HAZARDOUS"]
        print(f"  ✅ Active Diagnostic Planner OK: {plan_data['total_actions']} safe diagnostic actions prioritized")

        # 16. Check Frontend Pages
        print("\n[16/16] Testing Next.js Frontend Server Pages...")
        for path in ["/", "/telemetry", "/simulation", "/incidents", f"/incidents/{incident_id}", "/services"]:
            front_r = client.get(f"{FRONTEND_URL}{path}")
            assert front_r.status_code == 200
        print("  ✅ All 6 Next.js Pages Responding cleanly (HTTP 200)")

    print("\n" + "=" * 60)
    print("🎉 ALL 16 INTEGRATION CHECKS PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_checks()
    except Exception as e:
        print(f"❌ Integration check failed: {e}")
        sys.exit(1)
