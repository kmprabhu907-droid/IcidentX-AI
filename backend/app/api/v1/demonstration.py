"""
INCIDENTX AI - Hackathon Demonstration & Orchestration API Endpoints (Phase 16)
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.services.demonstration.orchestration_engine import demonstration_orchestrator
from backend.app.services.demonstration.schemas import (
    DemonstrationScenario,
    DemonstrationScenarioID,
    OrchestrationExecutionResult,
)

router = APIRouter(prefix="/demonstration", tags=["Hackathon Live Demonstration (Phase 16)"])


class ExecuteScenarioRequest(BaseModel):
    environment: str = "DEMOMESH"


@router.get("/scenarios", response_model=List[DemonstrationScenario])
async def list_scenarios():
    return demonstration_orchestrator.list_scenarios()


@router.post("/scenarios/{scenario_id}/execute", response_model=OrchestrationExecutionResult)
async def execute_scenario(scenario_id: DemonstrationScenarioID, payload: ExecuteScenarioRequest):
    return await demonstration_orchestrator.execute_scenario(
        scenario_id=scenario_id,
        environment=payload.environment,
    )


@router.post("/scenarios/reset")
async def reset_scenarios():
    demonstration_orchestrator.reset_scenarios()
    return {"status": "RESET", "message": "All demonstration scenarios reset."}


@router.get("/executions", response_model=List[OrchestrationExecutionResult])
async def list_executions():
    return demonstration_orchestrator.list_executions()


@router.get("/executions/{execution_id}", response_model=OrchestrationExecutionResult)
async def get_execution(execution_id: str):
    res = demonstration_orchestrator.get_execution(execution_id)
    if not res:
        raise HTTPException(status_code=404, detail="Execution not found")
    return res
