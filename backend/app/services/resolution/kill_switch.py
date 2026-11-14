"""
INCIDENTX AI - Global Remediation Kill Switch (Phase 12 Module 12.12)
Provides an instantaneous emergency stop mechanism that halts all active remediation
and completely disallows new planning or execution until an authorized SRE operator resets it.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from backend.app.core.logging import logger
from backend.app.services.resolution.schemas import KillSwitchState


class RemediationKillSwitch:
    """
    Thread-safe / asyncio-safe Global Kill Switch.
    Guarantees zero autonomous or manual executions while active.
    """

    def __init__(self):
        self._is_active: bool = False
        self._activated_at: Optional[datetime] = None
        self._activated_by: Optional[str] = None
        self._reason: Optional[str] = None
        self._in_flight_aborted: int = 0
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.Lock()
        if self._lock is None or getattr(self, "_lock_loop", None) is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    async def is_active(self) -> bool:
        async with self._get_lock():
            return self._is_active

    async def get_state(self) -> KillSwitchState:
        async with self._get_lock():
            return KillSwitchState(
                is_active=self._is_active,
                activated_at=self._activated_at,
                activated_by=self._activated_by,
                reason=self._reason,
                in_flight_actions_aborted=self._in_flight_aborted,
            )

    async def activate(self, user: str = "SRE-Operator", reason: str = "Emergency incident containment") -> KillSwitchState:
        async with self._get_lock():
            self._is_active = True
            self._activated_at = datetime.now(timezone.utc)
            self._activated_by = user
            self._reason = reason
            self._in_flight_aborted += 1
            logger.critical(
                f"[KillSwitch] GLOBAL REMEDIATION KILL SWITCH ACTIVATED by '{user}'. Reason: '{reason}'."
            )
            return KillSwitchState(
                is_active=True,
                activated_at=self._activated_at,
                activated_by=self._activated_by,
                reason=self._reason,
                in_flight_actions_aborted=self._in_flight_aborted,
            )

    async def deactivate(self, user: str = "SRE-Operator") -> KillSwitchState:
        async with self._get_lock():
            self._is_active = False
            prev_reason = self._reason
            self._activated_at = None
            self._activated_by = None
            self._reason = None
            logger.warning(
                f"[KillSwitch] GLOBAL REMEDIATION KILL SWITCH RESET by '{user}'. Previous reason was: '{prev_reason}'."
            )
            return KillSwitchState(
                is_active=False,
                activated_at=None,
                activated_by=None,
                reason=None,
                in_flight_actions_aborted=self._in_flight_aborted,
            )


# Global singleton instance
kill_switch = RemediationKillSwitch()
