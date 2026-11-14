"""
INCIDENTX AI - Environment Access Policy (Phase 8.1)
Enforces enterprise RBAC permissions for environment discovery, inspection, and switching.
"""

from typing import Optional
from backend.app.core.exceptions import IncidentXException
from backend.app.models.user import User


class UnauthorizedEnvironmentActionException(IncidentXException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=403)


class EnvironmentAccessPolicy:
    """Enforces role-based permissions for hybrid infrastructure environments."""

    PERMITTED_SWITCH_ROLES = {"super_admin", "admin", "organization_admin", "sre_lead"}

    @classmethod
    def can_view_environment(cls, user: Optional[User]) -> bool:
        """All authenticated operators, developers, and admins can view environments."""
        return True  # Read-only observability is universally visible

    @classmethod
    def can_switch_environment(cls, user: Optional[User], strict: bool = False) -> bool:
        """Only SRE Leads, Admins, and Super Admins can switch active environments."""
        if not user:
            if not strict:
                from backend.app.core.config import settings
                if getattr(settings, "APP_ENV", "").lower() != "production":
                    return True
            return False
        role = getattr(user, "role", "viewer")
        val = role.value if hasattr(role, "value") else str(role)
        return val.lower() in cls.PERMITTED_SWITCH_ROLES

    @classmethod
    def assert_can_switch(cls, user: Optional[User]) -> None:
        """Raises 403 Forbidden if user lacks environment switching permissions."""
        if not cls.can_switch_environment(user):
            role = getattr(user, "role", "anonymous") if user else "anonymous"
            role_name = role.value if hasattr(role, "value") else str(role)
            raise UnauthorizedEnvironmentActionException(
                f"Role '{role_name}' lacks authorization to switch active infrastructure environment. "
                f"Permitted roles: {sorted(list(cls.PERMITTED_SWITCH_ROLES))}"
            )
