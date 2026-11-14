#!/usr/bin/env python3
"""
INCIDENTX AI - On-Call Incident Agent Interactive Live Demo
Executes the flagship Hackathon Scenario:
'The Midnight Black Friday Meltdown' (P1 Outage)
"""

import asyncio
import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.agents.oncall_demo_scenario import OnCallDemoScenarioRunner


async def main():
    print("=" * 78)
    print("  INCIDENTX AI — ON-CALL INCIDENT RESPONSE AGENT DEMONSTRATION")
    print("  Scenario: The Midnight Black Friday Meltdown (P1 Incident)")
    print("=" * 78)

    print("\n[>>] Starting autonomous incident response workflow...")
    result = await OnCallDemoScenarioRunner.run_black_friday_meltdown()

    print(f"\n[+] INCIDENT CREATED: {result.incident_id}")
    print(f"[+] PAGER ALERT ID:   {result.page_id}")
    print(f"[+] MTTA ACHIEVED:    {result.mtta_seconds}s (Auto-acknowledged by Tier-1 AI)")
    print(f"[+] TOTAL MTTR:       {result.mttr_seconds}s")
    print(f"[+] DURATION:         {result.total_execution_ms:.2f}ms")

    print("\n" + "-" * 78)
    print("  9-STAGE ON-CALL INCIDENT LIFECYCLE EXECUTION")
    print("-" * 78)

    stage_emojis = {
        1: "🚨", 2: "⚡", 3: "🔍", 4: "⚖️", 5: "🛠️", 6: "🛡️", 7: "📈", 8: "📋"
    }

    for st in result.lifecycle_stages:
        emoji = stage_emojis.get(st.get("stage_index"), "•")
        print(f" {emoji} Stage {st.get('stage_index')}: {st.get('stage_name'):<26} [{st.get('duration_ms')}ms]")
        if st.get("stage_name") == "ALERT_RECEIVED":
            print(f"    Source: {st.get('source')} | Alert: {st.get('alert_name')}")
        elif st.get("stage_name") == "INCIDENT_TRIAGE":
            print(f"    Responder: {st.get('responder')} | MTTA: {st.get('mtta_seconds')}s")
        elif st.get("stage_name") == "MULTI_AGENT_INVESTIGATION":
            print(f"    Agents ({st.get('agents_count')}): {', '.join(st.get('completed_agents', [])[:5])}...")
        elif st.get("stage_name") == "ROOT_CAUSE_ANALYSIS":
            print(f"    Ruling: {st.get('leading_root_cause')} (Confidence: {st.get('confidence_score') * 100:.0f}%)")
        elif st.get("stage_name") == "REMEDIATION_PROPOSAL":
            rec = st.get("recommended_action", {})
            print(f"    Recipe: {rec.get('name')} | Risk: {rec.get('risk_score', 'LOW')}")
        elif st.get("stage_name") == "CONTROLLED_EXECUTION":
            print(f"    Status: {st.get('execution_status')} | Approved by: {st.get('authorized_by')}")
        elif st.get("stage_name") == "RECOVERY_VERIFICATION":
            print(f"    Health: {st.get('overall_status')} | Latency: 2840ms -> 38ms | Errors: 0.48 -> 0.00")
        elif st.get("stage_name") == "INCIDENT_REPORTING":
            print(f"    Format: {st.get('postmortem_format')} | Slack announcement broadcasted")

    print("\n" + "=" * 78)
    print("  COURTROOM 2.0 ADJUDICATION")
    print("=" * 78)
    print(f"  Verdict:    {result.root_cause_ruling}")
    print(f"  Confidence: {result.confidence_score * 100:.1f}%")

    print("\n" + "=" * 78)
    print("  POST-MORTEM EXECUTIVE SUMMARY")
    print("=" * 78)
    print(f"  {result.postmortem_summary}")

    print("\n" + "=" * 78)
    print("  SLACK EXECUTIVE ANNOUNCEMENT")
    print("=" * 78)
    print(f"  {result.slack_announcement.strip()}")
    print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())
