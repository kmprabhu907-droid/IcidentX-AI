"""
INCIDENTX AI - Failure Injection Lab API Endpoints
Controls chaos simulation scenarios, fault injection parameters, and active fault states.
All synthetic operations are labeled with data_source='SIMULATED'.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.app.services.simulation.chaos_controller import chaos_controller

router = APIRouter(prefix="/simulation", tags=["Simulation & Chaos Lab"])


class InjectFaultRequest(BaseModel):
    scenario_id: str = Field(..., description="Unique ID of chaos scenario (e.g. payment_latency, db_pool_exhaustion)")
    target_service: Optional[str] = Field(None, description="Optional override for target microservice")
    duration_seconds: Optional[int] = Field(None, ge=10, le=600, description="Duration in seconds before auto-remediation")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Fine-grained scenario parameters")


class StopFaultRequest(BaseModel):
    scenario_id: str = Field(..., description="Unique ID of chaos scenario to terminate")


@router.get("/scenarios")
async def list_chaos_scenarios() -> List[Dict[str, Any]]:
    """List all 9 available production failure injection scenarios with impact descriptions."""
    return chaos_controller.list_scenarios()


@router.get("/status")
async def get_simulation_status() -> Dict[str, Any]:
    """Retrieve current state of all active fault injections, elapsed times, and affected components."""
    return chaos_controller.get_status()


@router.post("/inject")
async def inject_fault(request: InjectFaultRequest) -> Dict[str, Any]:
    """Inject a controlled failure scenario into the running system."""
    try:
        active_fault = await chaos_controller.inject(
            scenario_id=request.scenario_id,
            target_service=request.target_service,
            duration_seconds=request.duration_seconds,
            parameters=request.parameters,
        )
        return {
            "status": "INJECTED",
            "message": f"Successfully injected fault scenario '{request.scenario_id}'",
            "fault": active_fault,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop_fault(request: StopFaultRequest) -> Dict[str, Any]:
    """Stop a specific active fault injection and restore baseline operational parameters."""
    stopped = await chaos_controller.stop(request.scenario_id)
    if not stopped:
        raise HTTPException(
            status_code=404,
            detail=f"Fault scenario '{request.scenario_id}' is not currently active.",
        )
    return {
        "status": "STOPPED",
        "message": f"Fault scenario '{request.scenario_id}' has been deactivated.",
    }


@router.post("/stop-all")
async def stop_all_faults() -> Dict[str, Any]:
    """Emergency stop all active chaos scenarios immediately, restoring healthy baseline."""
    count = await chaos_controller.stop_all()
    return {
        "status": "ALL_STOPPED",
        "stopped_count": count,
        "message": f"Deactivated all {count} active failure injections. Restored baseline telemetry.",
    }
