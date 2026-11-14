"""
INCIDENTX AI - Collaborative Investigation Protocol (Phase 10 Module 10.4)
Enables structured, bounded inter-agent communication, evidence cross-referencing,
counter-hypothesis challenges, contradiction reporting, and consensus voting
without infinite conversational loops.
"""

from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.investigation import AgentMessageModel


class CollaborationMessageType(str, Enum):
    EVIDENCE_SHARED = "EVIDENCE_SHARED"
    EVIDENCE_REQUEST = "EVIDENCE_REQUEST"
    CHALLENGE_HYPOTHESIS = "CHALLENGE_HYPOTHESIS"
    REPORT_CONTRADICTION = "REPORT_CONTRADICTION"
    REINVESTIGATE_TARGET = "REINVESTIGATE_TARGET"
    CONSENSUS_VOTE = "CONSENSUS_VOTE"


class AgentMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str
    investigation_id: str
    sender_agent: str
    recipient_agent: str = "BROADCAST"  # Specific agent name or BROADCAST
    message_type: CollaborationMessageType
    round_number: int = 1
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CollaborationProtocolEngine:
    """
    Structured Message Bus and Coordination Controller for Multi-Agent Collaboration.
    Enforces maximum rounds, message retention, and audit logging.
    """

    def __init__(
        self,
        max_rounds: int = 3,
        max_messages: int = 50,
    ):
        self.max_rounds = max_rounds
        self.max_messages = max_messages
        # In-memory message bus: investigation_id -> List[AgentMessage]
        self._message_bus: Dict[str, List[AgentMessage]] = {}

    def get_messages(self, investigation_id: str) -> List[AgentMessage]:
        return self._message_bus.get(investigation_id, [])

    async def send_message(
        self,
        incident_id: str,
        investigation_id: str,
        sender_agent: str,
        message_type: CollaborationMessageType,
        summary: str,
        recipient_agent: str = "BROADCAST",
        round_number: int = 1,
        payload: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> AgentMessage:
        """
        Transmits a structured message on the investigation bus and persists to database.
        """
        if round_number > self.max_rounds:
            logger.warning(
                f"[CollaborationProtocol] Message rejected: round {round_number} exceeds max_rounds {self.max_rounds}"
            )
            raise ValueError(f"Investigation collaboration exceeded maximum rounds ({self.max_rounds}).")

        msg = AgentMessage(
            incident_id=incident_id,
            investigation_id=investigation_id,
            sender_agent=sender_agent,
            recipient_agent=recipient_agent,
            message_type=message_type,
            round_number=round_number,
            summary=summary,
            payload=payload or {},
        )

        if investigation_id not in self._message_bus:
            self._message_bus[investigation_id] = []

        if len(self._message_bus[investigation_id]) < self.max_messages:
            self._message_bus[investigation_id].append(msg)

        # Persist to database if session provided
        if session is not None:
            db_msg = AgentMessageModel(
                id=msg.id,
                incident_id=incident_id,
                investigation_id=investigation_id,
                sender_agent=sender_agent,
                recipient_agent=recipient_agent,
                message_type=message_type.value,
                round_number=round_number,
                summary=summary[:255],
                payload_json=json.dumps(payload or {}),
            )
            session.add(db_msg)
            await session.flush()

        logger.info(
            f"[CollaborationProtocol] [{investigation_id[:8]}] {sender_agent} -> {recipient_agent} [{message_type.value}]: {summary}"
        )
        return msg

    async def list_persisted_messages(
        self,
        incident_id: str,
        session: AsyncSession,
        limit: int = 50,
    ) -> List[AgentMessageModel]:
        """
        Retrieves persisted collaboration messages from database.
        """
        query = (
            select(AgentMessageModel)
            .where(AgentMessageModel.incident_id == incident_id)
            .order_by(desc(AgentMessageModel.created_at))
            .limit(limit)
        )
        res = await session.execute(query)
        return list(res.scalars().all())


# Singleton instance
collaboration_protocol_engine = CollaborationProtocolEngine()
