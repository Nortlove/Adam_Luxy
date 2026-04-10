"""
ADAM Multi-Tenant Namespace System

Provides tenant lifecycle management, data isolation via namespace partitioning
across Neo4j, Redis, and Kafka, and Blueprint composition for instant deployment.
"""

from adam.platform.tenants.models import (
    Tenant,
    TenantConfig,
    TenantStatus,
    BlueprintType,
    ScaleTier,
    ActivationResult,
)
from adam.platform.tenants.service import TenantService, get_tenant_service
from adam.platform.tenants.namespace import TenantNamespace
from adam.platform.tenants.middleware import TenantMiddleware, get_current_tenant

__all__ = [
    "Tenant",
    "TenantConfig",
    "TenantStatus",
    "BlueprintType",
    "ScaleTier",
    "ActivationResult",
    "TenantService",
    "get_tenant_service",
    "TenantNamespace",
    "TenantMiddleware",
    "get_current_tenant",
]
