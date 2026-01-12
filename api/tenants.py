"""
tenants.py - Multi-Tenant Support for ComplianceGPT

Enterprise multi-tenancy with tenant isolation, quotas, and billing.
"""

import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
from pathlib import Path
import threading


class TenantTier(str, Enum):
    """Subscription tiers for tenants."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantStatus(str, Enum):
    """Tenant account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    CANCELLED = "cancelled"


@dataclass
class TenantQuota:
    """Quota limits for a tenant."""
    queries_per_day: int = 50
    queries_per_month: int = 1000
    max_query_length: int = 500
    regulations: list = field(default_factory=lambda: ["GDPR"])
    priority_support: bool = False
    custom_regulations: bool = False
    api_access: bool = False
    audit_logs_days: int = 7
    
    @classmethod
    def for_tier(cls, tier: TenantTier) -> "TenantQuota":
        """Get quota for a subscription tier."""
        quotas = {
            TenantTier.FREE: cls(
                queries_per_day=50,
                queries_per_month=500,
                max_query_length=500,
                regulations=["GDPR"],
                audit_logs_days=7
            ),
            TenantTier.PRO: cls(
                queries_per_day=500,
                queries_per_month=10000,
                max_query_length=1000,
                regulations=["GDPR", "CCPA", "PCI-DSS"],
                api_access=True,
                audit_logs_days=30
            ),
            TenantTier.ENTERPRISE: cls(
                queries_per_day=10000,
                queries_per_month=500000,
                max_query_length=2000,
                regulations=["GDPR", "CCPA", "PCI-DSS", "HIPAA", "SOX"],
                priority_support=True,
                custom_regulations=True,
                api_access=True,
                audit_logs_days=365
            )
        }
        return quotas.get(tier, quotas[TenantTier.FREE])


@dataclass
class TenantUsage:
    """Track tenant usage metrics."""
    queries_today: int = 0
    queries_this_month: int = 0
    last_query_at: Optional[str] = None
    last_reset_daily: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    last_reset_monthly: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m"))
    
    def check_and_reset(self):
        """Reset counters if needed."""
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        month = now.strftime("%Y-%m")
        
        if self.last_reset_daily != today:
            self.queries_today = 0
            self.last_reset_daily = today
        
        if self.last_reset_monthly != month:
            self.queries_this_month = 0
            self.last_reset_monthly = month
    
    def record_query(self):
        """Record a query."""
        self.check_and_reset()
        self.queries_today += 1
        self.queries_this_month += 1
        self.last_query_at = datetime.now(timezone.utc).isoformat()


@dataclass
class Tenant:
    """Represents a tenant in the multi-tenant system."""
    
    # Identity
    tenant_id: str
    name: str
    email: str
    
    # Subscription
    tier: TenantTier = TenantTier.FREE
    status: TenantStatus = TenantStatus.ACTIVE
    
    # API Keys
    api_keys: list = field(default_factory=list)
    
    # Quota and Usage
    quota: TenantQuota = field(default_factory=TenantQuota)
    usage: TenantUsage = field(default_factory=TenantUsage)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    settings: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "email": self.email,
            "tier": self.tier.value if isinstance(self.tier, TenantTier) else self.tier,
            "status": self.status.value if isinstance(self.status, TenantStatus) else self.status,
            "api_keys": self.api_keys,
            "quota": asdict(self.quota),
            "usage": asdict(self.usage),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": self.settings
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Tenant":
        """Create from dictionary."""
        return cls(
            tenant_id=data["tenant_id"],
            name=data["name"],
            email=data["email"],
            tier=TenantTier(data.get("tier", "free")),
            status=TenantStatus(data.get("status", "active")),
            api_keys=data.get("api_keys", []),
            quota=TenantQuota(**data.get("quota", {})),
            usage=TenantUsage(**data.get("usage", {})),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            settings=data.get("settings", {})
        )
    
    def generate_api_key(self) -> str:
        """Generate a new API key for this tenant."""
        key = f"cgpt_{self.tenant_id[:8]}_{secrets.token_urlsafe(24)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        self.api_keys.append({
            "key_hash": key_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
            "name": f"Key {len(self.api_keys) + 1}"
        })
        
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return key  # Return unhashed key (only shown once)
    
    def validate_api_key(self, key: str) -> bool:
        """Validate an API key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        for api_key in self.api_keys:
            if api_key["key_hash"] == key_hash:
                api_key["last_used"] = datetime.now(timezone.utc).isoformat()
                return True
        
        return False
    
    def can_query(self) -> tuple[bool, str]:
        """Check if tenant can make a query."""
        if self.status != TenantStatus.ACTIVE and self.status != TenantStatus.TRIAL:
            return False, f"Account is {self.status.value}"
        
        self.usage.check_and_reset()
        
        if self.usage.queries_today >= self.quota.queries_per_day:
            return False, "Daily query limit reached"
        
        if self.usage.queries_this_month >= self.quota.queries_per_month:
            return False, "Monthly query limit reached"
        
        return True, "OK"
    
    def can_access_regulation(self, regulation: str) -> bool:
        """Check if tenant can access a regulation."""
        if regulation.lower() == "all":
            return True
        return regulation.upper() in [r.upper() for r in self.quota.regulations]


class TenantManager:
    """
    Manages tenants for multi-tenant deployments.
    
    Features:
    - Tenant CRUD operations
    - API key management
    - Usage tracking
    - Quota enforcement
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else Path("data/tenants")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._tenants: dict[str, Tenant] = {}
        self._api_key_index: dict[str, str] = {}  # key_hash -> tenant_id
        self._lock = threading.Lock()
        self._load_tenants()
    
    def _load_tenants(self):
        """Load tenants from storage."""
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    tenant = Tenant.from_dict(data)
                    self._tenants[tenant.tenant_id] = tenant
                    
                    # Index API keys
                    for api_key in tenant.api_keys:
                        self._api_key_index[api_key["key_hash"]] = tenant.tenant_id
            except Exception as e:
                print(f"Error loading tenant {file_path}: {e}")
    
    def _save_tenant(self, tenant: Tenant):
        """Save tenant to storage."""
        file_path = self.storage_path / f"{tenant.tenant_id}.json"
        with open(file_path, "w") as f:
            json.dump(tenant.to_dict(), f, indent=2)
    
    def create_tenant(
        self,
        name: str,
        email: str,
        tier: TenantTier = TenantTier.FREE
    ) -> Tenant:
        """Create a new tenant."""
        tenant_id = f"tenant_{secrets.token_hex(8)}"
        
        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            email=email,
            tier=tier,
            quota=TenantQuota.for_tier(tier)
        )
        
        with self._lock:
            self._tenants[tenant_id] = tenant
            self._save_tenant(tenant)
        
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get a tenant by ID."""
        return self._tenants.get(tenant_id)
    
    def get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """Get a tenant by API key."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        tenant_id = self._api_key_index.get(key_hash)
        
        if tenant_id:
            tenant = self._tenants.get(tenant_id)
            if tenant and tenant.validate_api_key(api_key):
                return tenant
        
        return None
    
    def update_tenant(self, tenant_id: str, **updates) -> Optional[Tenant]:
        """Update a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        tenant.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Update quota if tier changed
        if "tier" in updates:
            tenant.quota = TenantQuota.for_tier(tenant.tier)
        
        with self._lock:
            self._save_tenant(tenant)
        
        return tenant
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant."""
        if tenant_id not in self._tenants:
            return False
        
        tenant = self._tenants[tenant_id]
        
        # Remove API key index entries
        for api_key in tenant.api_keys:
            self._api_key_index.pop(api_key["key_hash"], None)
        
        # Remove from memory and storage
        del self._tenants[tenant_id]
        
        file_path = self.storage_path / f"{tenant_id}.json"
        if file_path.exists():
            file_path.unlink()
        
        return True
    
    def record_query(self, tenant_id: str) -> bool:
        """Record a query for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        tenant.usage.record_query()
        
        with self._lock:
            self._save_tenant(tenant)
        
        return True
    
    def list_tenants(
        self,
        tier: Optional[TenantTier] = None,
        status: Optional[TenantStatus] = None
    ) -> list[Tenant]:
        """List tenants with optional filters."""
        tenants = list(self._tenants.values())
        
        if tier:
            tenants = [t for t in tenants if t.tier == tier]
        
        if status:
            tenants = [t for t in tenants if t.status == status]
        
        return tenants
    
    def get_usage_report(self) -> dict:
        """Get usage report across all tenants."""
        total_queries_today = 0
        total_queries_month = 0
        tenants_by_tier = {tier.value: 0 for tier in TenantTier}
        
        for tenant in self._tenants.values():
            tenant.usage.check_and_reset()
            total_queries_today += tenant.usage.queries_today
            total_queries_month += tenant.usage.queries_this_month
            tenants_by_tier[tenant.tier.value] += 1
        
        return {
            "total_tenants": len(self._tenants),
            "tenants_by_tier": tenants_by_tier,
            "total_queries_today": total_queries_today,
            "total_queries_this_month": total_queries_month
        }


# Global tenant manager instance (disabled by default)
_tenant_manager: Optional[TenantManager] = None


def get_tenant_manager() -> Optional[TenantManager]:
    """Get the global tenant manager (if multi-tenancy is enabled)."""
    global _tenant_manager
    
    if os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true":
        if _tenant_manager is None:
            _tenant_manager = TenantManager()
        return _tenant_manager
    
    return None


def is_multi_tenant_enabled() -> bool:
    """Check if multi-tenancy is enabled."""
    return os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true"
