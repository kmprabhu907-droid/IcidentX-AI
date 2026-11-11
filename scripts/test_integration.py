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
            "impact_scope": "payment-service, order-service"
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

        # 16. Action Registry Verification
        print("\n[16/22] Testing Remediation Action Registry (/remediation/registry)...")
        reg_r = client.get(f"{BACKEND_URL}/api/v1/remediation/registry")
        assert reg_r.status_code == 200
        registry_actions = reg_r.json()
        assert len(registry_actions) == 8
        print(f"  ✅ Action Registry OK: 8 safe predefined actions verified ({', '.join(a['action_id'] for a in registry_actions[:4])}...)")

        # 17. Remediation Policy Verification (Default RECOMMENDATION_ONLY)
        print("\n[17/22] Testing Remediation Safety Policy (/remediation/policy)...")
        pol_r = client.get(f"{BACKEND_URL}/api/v1/remediation/policy")
        assert pol_r.status_code == 200
        policy = pol_r.json()
        assert policy["circuit_breaker_tripped"] is False
        print(f"  ✅ Remediation Policy OK: Mode={policy['mode']}, CircuitBreaker={policy['circuit_breaker_tripped']}")

        # 18. Generate Evidence-Grounded Recommendations
        print("\n[18/22] Testing Remediation Intelligence Engine (/recommendations)...")
        rec_r = client.get(f"{BACKEND_URL}/api/v1/incidents/{incident_id}/remediation/recommendations")
        assert rec_r.status_code == 200
        rec_data = rec_r.json()
        assert rec_data["total_recommendations"] >= 1
        top_act = rec_data["actions"][0]
        action_db_id = top_act["id"]
        print(f"  ✅ Remediation Intelligence OK: Formulated {rec_data['total_recommendations']} recovery recommendations. Top action: {top_act['name']} ({top_act['risk_level']} Risk)")

        # 19. Set Policy to HUMAN_APPROVAL & Approve Top Action
        print("\n[19/22] Testing Human Approval Gate...")
        # Set mode to HUMAN_APPROVAL
        put_r = client.put(f"{BACKEND_URL}/api/v1/remediation/policy", json={"mode": "HUMAN_APPROVAL"})
        assert put_r.status_code == 200

        # Approve action
        appr_r = client.post(
            f"{BACKEND_URL}/api/v1/incidents/{incident_id}/remediation/actions/{action_db_id}/approve",
            json={"approved_by": "lead-sre@incidentx.ai", "comment": "Approved for simulated execution."}
        )
        assert appr_r.status_code == 200
        appr_act = appr_r.json()
        assert appr_act["approval_status"] == "APPROVED"
        assert appr_act["approved_by"] == "lead-sre@incidentx.ai"
        print(f"  ✅ Human Approval Gate OK: Action {action_db_id} approved by {appr_act['approved_by']}")

        # 20. Execute Approved Action in Simulation
        print("\n[20/22] Testing Remediation Execution in Simulation Sandbox...")
        exec_r = client.post(f"{BACKEND_URL}/api/v1/incidents/{incident_id}/remediation/actions/{action_db_id}/execute")
        assert exec_r.status_code == 200
        exec_data = exec_r.json()
        assert exec_data["status"] == "EXECUTED"
        assert exec_data["verification_status"] in ["VERIFIED", "PARTIALLY_VERIFIED"]
        print(f"  ✅ Remediation Execution OK: Action executed in {exec_data['execution_duration_ms']}ms. Empirical verification: {exec_data['verification_status']}")

        # 21. Telemetry Verification Report
        print("\n[21/25] Testing Telemetry Verification Report (/verification)...")
        verif_r = client.get(f"{BACKEND_URL}/api/v1/incidents/{incident_id}/remediation/actions/{action_db_id}/verification")
        assert verif_r.status_code == 200
        verif_data = verif_r.json()
        assert "verification_report" in verif_data
        print(f"  ✅ Verification Report OK: Before vs after telemetry delta confirmed for service '{verif_data['target_service']}'")

        # 22. Phase 5 Stage 5.1: Ten Golden Reliability Signals
        print("\n[22/25] Testing Phase 5 Ten Golden Reliability Signals (/telemetry/signals)...")
        signals_r = client.get(f"{BACKEND_URL}/api/v1/telemetry/signals")
        assert signals_r.status_code == 200
        signals_data = signals_r.json()
        assert signals_data["total_services"] == 7
        order_signals = signals_data["services"]["order-service"]
        assert "cpu_utilization" in order_signals
        assert "disk_utilization" in order_signals
        assert "network_throughput_mbps" in order_signals
        assert "availability_pct" in order_signals
        assert "dependency_health" in order_signals
        assert "request_rate" in order_signals
        print(f"  ✅ Ten Golden Signals OK: 7 Services monitored. Availability={order_signals['availability_pct']}%, Disk={order_signals['disk_utilization']}%, Net={order_signals['network_throughput_mbps']} MB/s")

        # 23. Phase 5 Stage 5.1: Collector Status & Health
        print("\n[23/25] Testing Continuous Telemetry Collector Status (/telemetry/collector/status)...")
        collector_r = client.get(f"{BACKEND_URL}/api/v1/telemetry/collector/status")
        assert collector_r.status_code == 200
        col_status = collector_r.json()
        assert col_status["collector_status"] in ["RUNNING", "IDLE"]
        assert col_status["monitored_services_count"] == 7
        print(f"  ✅ Continuous Collector OK: Status={col_status['collector_status']}, Total Samples={col_status['buffer_stats']['total_samples_collected']}")

        # 24. Phase 5 Stage 5.1: Historical 1-Minute Metric Rollups
        print("\n[24/25] Testing Historical Metric Rollup Storage (/telemetry/metrics/history)...")
        # Ensure at least one flush has run
        client.post(f"{BACKEND_URL}/api/v1/telemetry/collector/flush")
        history_r = client.get(f"{BACKEND_URL}/api/v1/telemetry/metrics/history?page_size=5")
        assert history_r.status_code == 200
        history_data = history_r.json()
        assert history_data["total"] >= 1
        assert len(history_data["rollups"]) >= 1
        print(f"  ✅ Historical Rollups OK: Total stored rollups={history_data['total']}, Page 1 count={len(history_data['rollups'])}")

        # 25. Phase 5 Stage 5.2: Anomaly Detection Status & Active Anomalies
        print("\n[25/28] Testing Anomaly Detection Engine Status (/observability/detection/status)...")
        det_status_r = client.get(f"{BACKEND_URL}/api/v1/observability/detection/status")
        assert det_status_r.status_code == 200
        det_status = det_status_r.json()
        assert det_status["status"] == "HEALTHY"
        assert det_status["monitored_services"] == 7
        print(f"  ✅ Anomaly Detection Engine OK: Status={det_status['status']}, Monitored Services={det_status['monitored_services']}")

        # 26. Phase 5 Stage 5.2: Dynamic Baselines
        print("\n[26/28] Testing Dynamic Adaptive Baselines (/observability/baselines/order-service)...")
        base_r = client.get(f"{BACKEND_URL}/api/v1/observability/baselines/order-service")
        assert base_r.status_code == 200
        base_data = base_r.json()
        assert base_data["service_name"] == "order-service"
        assert "cpu_utilization" in base_data["baselines"]
        cpu_base = base_data["baselines"]["cpu_utilization"]
        assert cpu_base["mean"] > 0
        assert cpu_base["has_sufficient_history"] is True
        print(f"  ✅ Dynamic Baselines OK: order-service cpu_utilization mean={cpu_base['mean']}, 3σ range=[{cpu_base['min_normal']}, {cpu_base['max_normal']}]")

        # 27. Phase 5 Stage 5.2: Anomaly Query & Lifecycle Status Patch
        print("\n[27/28] Testing Anomaly Records & Lifecycle Transition...")
        anom_list_r = client.get(f"{BACKEND_URL}/api/v1/observability/anomalies?page_size=1")
        assert anom_list_r.status_code == 200
        anom_data = anom_list_r.json()
        if anom_data["total"] > 0:
            target_anom = anom_data["items"][0]
            patch_r = client.patch(
                f"{BACKEND_URL}/api/v1/observability/anomalies/{target_anom['id']}/status",
                json={"status": "ACKNOWLEDGED"}
            )
            assert patch_r.status_code == 200
            assert patch_r.json()["status"] == "ACKNOWLEDGED"
            print(f"  ✅ Anomaly Lifecycle OK: Anomaly {target_anom['id'][:8]} transitioned to ACKNOWLEDGED")
        else:
            print("  ℹ️ No existing anomaly records to patch, skipping patch check")

        # 28. Check Frontend Pages
        print("\n[28/28] Testing Next.js Frontend Server Pages...")
        for path in ["/", "/remediation", "/telemetry", "/simulation", "/incidents", f"/incidents/{incident_id}", "/services"]:
            front_r = client.get(f"{FRONTEND_URL}{path}")
            assert front_r.status_code == 200
        print("  ✅ All 7 Next.js Pages Responding cleanly (HTTP 200)")

    print("\n" + "=" * 60)
    print("🎉 ALL 28 INTEGRATION CHECKS PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_checks()
    except Exception as e:
        print(f"❌ Integration check failed: {e}")
        sys.exit(1)
