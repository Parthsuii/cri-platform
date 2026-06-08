"""Governance, RBAC, tenant quota, and audit primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class Permission(StrEnum):
    ACTION_SUBMIT = "action:submit"
    ACTION_APPROVE = "action:approve"
    POLICY_MANAGE = "policy:manage"
    ROLLBACK_EXECUTE = "rollback:execute"
    TRACE_READ = "trace:read"
    ADMIN = "admin:*"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "viewer": {Permission.TRACE_READ},
    "operator": {Permission.ACTION_SUBMIT, Permission.TRACE_READ},
    "governor": {Permission.ACTION_APPROVE, Permission.POLICY_MANAGE, Permission.TRACE_READ},
    "admin": set(Permission),
}


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str = "default"
    roles: tuple[str, ...] = ("viewer",)


@dataclass(frozen=True)
class AuditRecord:
    actor: str
    tenant_id: str
    action: str
    resource: str
    decision: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernanceEngine:
    audit_log: list[AuditRecord] = field(default_factory=list)

    def is_allowed(self, principal: Principal, permission: Permission) -> bool:
        permissions: set[Permission] = set()
        for role in principal.roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        return Permission.ADMIN in permissions or permission in permissions

    def authorize(
        self,
        principal: Principal,
        permission: Permission,
        resource: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        allowed = self.is_allowed(principal, permission)
        self.audit_log.append(
            AuditRecord(
                actor=principal.subject,
                tenant_id=principal.tenant_id,
                action=permission.value,
                resource=resource,
                decision="allow" if allowed else "deny",
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata=metadata or {},
            )
        )
        return allowed


@dataclass(frozen=True)
class TenantQuota:
    tenant_id: str
    max_concurrent_actions: int = 10
    max_cpu_millis: int = 4_000
    max_memory_mb: int = 2_048
    max_storage_mb: int = 10_240

