"""
INCIDENTX AI - Base Investigation Agent
Defines the abstract interface, timeout management, execution logging, and error boundaries
for all 10 specialized investigation agents.
"""

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.investigation import AgentExecution


class BaseInvestigationAgent(ABC):
    """
    Abstract Base Class for Autonomous Investigation Agents.
    """

    def __init__(
        self,
        name: str,
        role: str,
        execution_phase: str,
        timeout_seconds: float = 15.0,
    ):
        self.name = name
        self.role = role
        self.execution_phase = execution_phase
        self.timeout_seconds = timeout_seconds

    async def run(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Executes the agent with timeout boundaries and records an immutable
        audit entry in the agent_executions table.
        """
        start_time = time.perf_counter()
        execution_record = AgentExecution(
            incident_id=incident_id,
            agent_role=self.role,
            execution_phase=self.execution_phase,
            status="RUNNING",
            model_version=settings.AI_MODEL,
            prompt_version=settings.PROMPT_VERSION,
            thought_process=f"Agent '{self.name}' starting phase '{self.execution_phase}'.",
        )
        session.add(execution_record)
        await session.flush()

        logger.info(f"[{self.name}] Initiated execution for incident {incident_id}")

        try:
            # Execute with timeout boundary
            result_state = await asyncio.wait_for(
                self.execute(incident_id, state, session),
                timeout=self.timeout_seconds
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            execution_record.status = "COMPLETED"
            execution_record.duration_ms = elapsed_ms
            execution_record.observation = f"Completed successfully in {elapsed_ms}ms."
            execution_record.thought_process = f"{self.name} concluded successfully with state updates."
            await session.flush()

            logger.info(f"[{self.name}] Finished execution in {elapsed_ms}ms")
            return result_state

        except asyncio.TimeoutError:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"[{self.name}] Timed out after {self.timeout_seconds}s")
            execution_record.status = "FAILED"
            execution_record.duration_ms = elapsed_ms
            execution_record.error_message = f"Execution exceeded timeout limit of {self.timeout_seconds}s."
            await session.flush()
            # Return existing state gracefully on failure
            return state

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"[{self.name}] Error during execution: {e}", exc_info=True)
            execution_record.status = "FAILED"
            execution_record.duration_ms = elapsed_ms
            execution_record.error_message = str(e)
            await session.flush()
            # Return existing state gracefully on error
            return state

    @abstractmethod
    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Subclasses implement specific agent domain intelligence."""
        pass
