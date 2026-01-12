"""
health.py - Health Check System for ComplianceGPT

Comprehensive health checks for production monitoring.
Supports dependency checks, readiness probes, and liveness probes.
"""

import os
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """Result of a health check."""
    
    name: str
    status: HealthStatus
    latency_ms: float
    message: str = ""
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HealthReport:
    """Overall health report."""
    
    status: HealthStatus
    checks: list[CheckResult]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = ""
    uptime_seconds: float = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "latency_ms": round(check.latency_ms, 2),
                    "message": check.message,
                    "details": check.details
                }
                for check in self.checks
            ]
        }


class HealthChecker:
    """
    Health check system for production monitoring.
    
    Features:
    - Dependency health checks
    - Readiness and liveness probes
    - Caching to prevent thundering herd
    - Async check execution
    """
    
    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self._checks: dict[str, Callable] = {}
        self._start_time = time.time()
        self._cache: Optional[HealthReport] = None
        self._cache_ttl = 5  # seconds
        self._cache_time = 0
    
    def register(self, name: str, check: Callable):
        """Register a health check."""
        self._checks[name] = check
    
    async def _run_check(self, name: str, check: Callable) -> CheckResult:
        """Run a single health check."""
        start = time.time()
        
        try:
            # Support both sync and async checks
            if asyncio.iscoroutinefunction(check):
                result = await check()
            else:
                result = check()
            
            latency = (time.time() - start) * 1000
            
            if isinstance(result, CheckResult):
                result.latency_ms = latency
                return result
            elif isinstance(result, dict):
                return CheckResult(
                    name=name,
                    status=HealthStatus(result.get("status", "healthy")),
                    latency_ms=latency,
                    message=result.get("message", ""),
                    details=result.get("details", {})
                )
            elif isinstance(result, bool):
                return CheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    latency_ms=latency
                )
            else:
                return CheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message=str(result)
                )
        
        except Exception as e:
            latency = (time.time() - start) * 1000
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=str(e)
            )
    
    async def check_all(self, use_cache: bool = True) -> HealthReport:
        """Run all health checks."""
        # Return cached result if fresh
        if use_cache and self._cache:
            if time.time() - self._cache_time < self._cache_ttl:
                return self._cache
        
        # Run all checks concurrently
        tasks = [
            self._run_check(name, check)
            for name, check in self._checks.items()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Determine overall status
        statuses = [result.status for result in results]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        report = HealthReport(
            status=overall,
            checks=results,
            version=self.version,
            uptime_seconds=time.time() - self._start_time
        )
        
        # Cache result
        self._cache = report
        self._cache_time = time.time()
        
        return report
    
    async def is_ready(self) -> bool:
        """Kubernetes readiness probe."""
        report = await self.check_all()
        return report.status != HealthStatus.UNHEALTHY
    
    async def is_alive(self) -> bool:
        """Kubernetes liveness probe."""
        # Simple check that the service is running
        return True
    
    def get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self._start_time


# Predefined health checks

async def check_weaviate() -> CheckResult:
    """Check Weaviate connection."""
    try:
        from src.storage.weaviate_client import get_weaviate_client
        client = get_weaviate_client()
        
        # Check if we can connect
        is_ready = client.is_ready()
        
        if is_ready:
            # Get some metadata
            schema = client.schema.get()
            class_count = len(schema.get("classes", []))
            
            return CheckResult(
                name="weaviate",
                status=HealthStatus.HEALTHY,
                latency_ms=0,
                message=f"Connected with {class_count} classes",
                details={"classes": class_count}
            )
        else:
            return CheckResult(
                name="weaviate",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message="Weaviate is not ready"
            )
    
    except Exception as e:
        return CheckResult(
            name="weaviate",
            status=HealthStatus.UNHEALTHY,
            latency_ms=0,
            message=f"Connection failed: {str(e)}"
        )


async def check_llm_provider() -> CheckResult:
    """Check LLM provider availability."""
    provider = os.getenv("LLM_PROVIDER", "groq")
    
    api_key_vars = {
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY"
    }
    
    api_key_var = api_key_vars.get(provider, "LLM_API_KEY")
    has_key = bool(os.getenv(api_key_var))
    
    if has_key:
        return CheckResult(
            name="llm_provider",
            status=HealthStatus.HEALTHY,
            latency_ms=0,
            message=f"Provider: {provider}",
            details={"provider": provider, "configured": True}
        )
    else:
        return CheckResult(
            name="llm_provider",
            status=HealthStatus.DEGRADED,
            latency_ms=0,
            message=f"API key not configured for {provider}",
            details={"provider": provider, "configured": False}
        )


def check_disk_space() -> CheckResult:
    """Check available disk space."""
    import shutil
    
    try:
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        
        if free_percent < 10:
            status = HealthStatus.UNHEALTHY
            message = f"Critical: {free_percent:.1f}% free"
        elif free_percent < 20:
            status = HealthStatus.DEGRADED
            message = f"Warning: {free_percent:.1f}% free"
        else:
            status = HealthStatus.HEALTHY
            message = f"{free_percent:.1f}% free"
        
        return CheckResult(
            name="disk_space",
            status=status,
            latency_ms=0,
            message=message,
            details={
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "free_percent": round(free_percent, 2)
            }
        )
    except Exception as e:
        return CheckResult(
            name="disk_space",
            status=HealthStatus.DEGRADED,
            latency_ms=0,
            message=f"Could not check: {e}"
        )


def check_memory() -> CheckResult:
    """Check available memory."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        
        if memory.percent > 90:
            status = HealthStatus.UNHEALTHY
            message = f"Critical: {memory.percent}% used"
        elif memory.percent > 80:
            status = HealthStatus.DEGRADED
            message = f"Warning: {memory.percent}% used"
        else:
            status = HealthStatus.HEALTHY
            message = f"{memory.percent}% used"
        
        return CheckResult(
            name="memory",
            status=status,
            latency_ms=0,
            message=message,
            details={
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            }
        )
    except ImportError:
        return CheckResult(
            name="memory",
            status=HealthStatus.DEGRADED,
            latency_ms=0,
            message="psutil not installed"
        )
    except Exception as e:
        return CheckResult(
            name="memory",
            status=HealthStatus.DEGRADED,
            latency_ms=0,
            message=f"Could not check: {e}"
        )


async def check_external_api(
    url: str,
    name: str,
    timeout: float = 5.0
) -> CheckResult:
    """Check external API availability."""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status < 400:
                    return CheckResult(
                        name=name,
                        status=HealthStatus.HEALTHY,
                        latency_ms=0,
                        message=f"HTTP {response.status}"
                    )
                else:
                    return CheckResult(
                        name=name,
                        status=HealthStatus.DEGRADED,
                        latency_ms=0,
                        message=f"HTTP {response.status}"
                    )
    except Exception as e:
        return CheckResult(
            name=name,
            status=HealthStatus.UNHEALTHY,
            latency_ms=0,
            message=str(e)
        )


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker(version: str = "2.1.0") -> HealthChecker:
    """Get or create the global health checker."""
    global _health_checker
    
    if _health_checker is None:
        _health_checker = HealthChecker(version=version)
        
        # Register default checks
        _health_checker.register("weaviate", check_weaviate)
        _health_checker.register("llm_provider", check_llm_provider)
        _health_checker.register("disk_space", check_disk_space)
        _health_checker.register("memory", check_memory)
    
    return _health_checker


def setup_health_routes(app, version: str = "2.1.0"):
    """Set up health check routes for FastAPI."""
    from fastapi import Response
    
    checker = get_health_checker(version)
    
    @app.get("/health", tags=["Health"])
    async def health():
        """Comprehensive health check."""
        report = await checker.check_all()
        return report.to_dict()
    
    @app.get("/health/ready", tags=["Health"])
    async def readiness():
        """Kubernetes readiness probe."""
        is_ready = await checker.is_ready()
        
        if is_ready:
            return {"status": "ready"}
        else:
            return Response(
                content='{"status": "not_ready"}',
                status_code=503,
                media_type="application/json"
            )
    
    @app.get("/health/live", tags=["Health"])
    async def liveness():
        """Kubernetes liveness probe."""
        return {
            "status": "alive",
            "uptime_seconds": round(checker.get_uptime(), 2)
        }
    
    return checker
