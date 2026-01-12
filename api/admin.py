"""
admin.py - Admin API Routes for ComplianceGPT

Provides administrative endpoints for tenant management,
system monitoring, and configuration.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import os

from .tenants import (
    TenantManager, TenantTier, TenantStatus,
    get_tenant_manager, is_multi_tenant_enabled
)
from .metrics import metrics


# Security
security = HTTPBearer()


def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Verify admin API token."""
    admin_token = os.getenv("ADMIN_API_TOKEN")
    
    if not admin_token:
        raise HTTPException(
            status_code=500,
            detail="Admin API not configured"
        )
    
    if credentials.credentials != admin_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token"
        )
    
    return True


# Create router
router = APIRouter(prefix="/admin", tags=["Admin"])


# Request/Response Models

class CreateTenantRequest(BaseModel):
    """Request to create a new tenant."""
    name: str
    email: EmailStr
    tier: TenantTier = TenantTier.FREE


class UpdateTenantRequest(BaseModel):
    """Request to update a tenant."""
    name: Optional[str] = None
    tier: Optional[TenantTier] = None
    status: Optional[TenantStatus] = None


class TenantResponse(BaseModel):
    """Tenant response model."""
    tenant_id: str
    name: str
    email: str
    tier: str
    status: str
    quota: dict
    usage: dict
    created_at: str


class GenerateKeyResponse(BaseModel):
    """Response when generating API key."""
    api_key: str
    message: str


# Admin Endpoints

@router.get("/health")
async def admin_health(
    is_admin: bool = Depends(verify_admin_token)
):
    """Admin health check endpoint."""
    return {
        "status": "healthy",
        "multi_tenancy_enabled": is_multi_tenant_enabled()
    }


@router.get("/system/stats")
async def system_stats(
    is_admin: bool = Depends(verify_admin_token)
):
    """Get system-wide statistics."""
    stats = {
        "metrics": metrics.to_dict(),
        "multi_tenancy": is_multi_tenant_enabled()
    }
    
    tm = get_tenant_manager()
    if tm:
        stats["tenants"] = tm.get_usage_report()
    
    return stats


# Tenant Management Endpoints

@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    request: CreateTenantRequest,
    is_admin: bool = Depends(verify_admin_token)
):
    """Create a new tenant."""
    tm = get_tenant_manager()
    if not tm:
        raise HTTPException(
            status_code=400,
            detail="Multi-tenancy is not enabled"
        )
    
    tenant = tm.create_tenant(
        name=request.name,
        email=request.email,
        tier=request.tier
    )
    
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        email=tenant.email,
        tier=tenant.tier.value,
        status=tenant.status.value,
        quota=tenant.quota.__dict__,
        usage=tenant.usage.__dict__,
        created_at=tenant.created_at
    )


@router.get("/tenants")
async def list_tenants(
    tier: Optional[TenantTier] = Query(None),
    status: Optional[TenantStatus] = Query(None),
    is_admin: bool = Depends(verify_admin_token)
):
    """List all tenants with optional filters."""
    tm = get_tenant_manager()
    if not tm:
        raise HTTPException(
            status_code=400,
            detail="Multi-tenancy is not enabled"
        )
    
    tenants = tm.list_tenants(tier=tier, status=status)
    
    return {
        "tenants": [
            TenantResponse(
                tenant_id=t.tenant_id,
                name=t.name,
                email=t.email,
                tier=t.tier.value,
                status=t.status.value,
                quota=t.quota.__dict__,
                usage=t.usage.__dict__,
                created_at=t.created_at
            ).model_dump()
            for t in tenants
        ],
        "total": len(tenants)
    }


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    is_admin: bool = Depends(verify_admin_token)
):
    """Get a specific tenant."""
    tm = get_tenant_manager()
    if not tm:
        raise HTTPException(
            status_code=400,
            detail="Multi-tenancy is not enabled"
        )
    
    tenant = tm.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found"
        )
    
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        email=tenant.email,
        tier=tenant.tier.value,
        status=tenant.status.value,
        quota=tenant.quota.__dict__,
        usage=tenant.usage.__dict__,
        created_at=tenant.created_at
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    is_admin: bool = Depends(verify_admin_token)
):
    """Update a tenant."""
    tm = get_tenant_manager()
    if not tm:
        raise HTTPException(
            status_code=400,
            detail="Multi-tenancy is not enabled"
        )
    
    updates = request.model_dump(exclude_none=True)
    tenant = tm.update_tenant(tenant_id, **updates)
    
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found"
        )
    
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        email=tenant.email,
        tier=tenant.tier.value,
        status=tenant.status.value,
        quota=tenant.quota.__dict__,
        usage=tenant.usage.__dict__,
        created_at=tenant.created_at
    )


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    is_admin: bool = Depends(verify_admin_token)
):
    """Delete a tenant."""
    tm = get_tenant_manager()
    if not tm:
        raise HTTPException(
            status_code=400,
            detail="Multi-tenancy is not enabled"
        )
    
    success = tm.delete_tenant(tenant_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found"
        )
    
    return {"status": "deleted", "tenant_id": tenant_id}


@router.post("/tenants/{tenant_id}/api-keys", response_model=GenerateKeyResponse)
async def generate_api_key(
    tenant_id: str,
    is_admin: bool = Depends(verify_admin_token)
):
    """Generate a new API key for a tenant."""
    tm = get_tenant_manager()
    if not tm:
        raise HTTPException(
            status_code=400,
            detail="Multi-tenancy is not enabled"
        )
    
    tenant = tm.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found"
        )
    
    api_key = tenant.generate_api_key()
    tm._save_tenant(tenant)
    
    # Index the new key
    import hashlib
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    tm._api_key_index[key_hash] = tenant_id
    
    return GenerateKeyResponse(
        api_key=api_key,
        message="Save this key securely - it won't be shown again"
    )


@router.get("/tenants/{tenant_id}/usage")
async def get_tenant_usage(
    tenant_id: str,
    is_admin: bool = Depends(verify_admin_token)
):
    """Get detailed usage for a tenant."""
    tm = get_tenant_manager()
    if not tm:
        raise HTTPException(
            status_code=400,
            detail="Multi-tenancy is not enabled"
        )
    
    tenant = tm.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found"
        )
    
    # Ensure usage is up to date
    tenant.usage.check_and_reset()
    
    return {
        "tenant_id": tenant_id,
        "tier": tenant.tier.value,
        "quota": {
            "queries_per_day": tenant.quota.queries_per_day,
            "queries_per_month": tenant.quota.queries_per_month
        },
        "usage": {
            "queries_today": tenant.usage.queries_today,
            "queries_this_month": tenant.usage.queries_this_month,
            "remaining_today": max(0, tenant.quota.queries_per_day - tenant.usage.queries_today),
            "remaining_month": max(0, tenant.quota.queries_per_month - tenant.usage.queries_this_month),
            "last_query_at": tenant.usage.last_query_at
        }
    }


# Configuration Endpoints

@router.get("/config")
async def get_config(
    is_admin: bool = Depends(verify_admin_token)
):
    """Get current system configuration (safe values only)."""
    return {
        "multi_tenancy_enabled": is_multi_tenant_enabled(),
        "rate_limiting_enabled": os.getenv("ENABLE_RATE_LIMITING", "true") == "true",
        "auth_enabled": os.getenv("ENABLE_AUTH", "false") == "true",
        "cache_ttl": int(os.getenv("CACHE_TTL", "300")),
        "llm_provider": os.getenv("LLM_PROVIDER", "groq"),
        "debug_mode": os.getenv("DEBUG", "false") == "true"
    }


@router.post("/cache/clear")
async def clear_cache(
    is_admin: bool = Depends(verify_admin_token)
):
    """Clear all response caches."""
    from .middleware import response_cache
    response_cache.clear()
    
    return {"status": "success", "message": "Cache cleared"}
