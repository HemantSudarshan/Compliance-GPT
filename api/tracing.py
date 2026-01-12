"""
tracing.py - Distributed Tracing for ComplianceGPT

OpenTelemetry integration for distributed tracing and observability.
Supports Jaeger, Zipkin, and OTLP exporters.
"""

import os
import functools
from typing import Optional, Callable, Any
from contextlib import contextmanager
from datetime import datetime


class SpanContext:
    """Lightweight span context for tracing."""
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_id: Optional[str] = None
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_id = parent_id


class Span:
    """Represents a trace span."""
    
    def __init__(
        self,
        name: str,
        context: SpanContext,
        attributes: Optional[dict] = None
    ):
        self.name = name
        self.context = context
        self.attributes = attributes or {}
        self.events: list[dict] = []
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.status = "OK"
        self.status_message = ""
    
    def set_attribute(self, key: str, value: Any):
        """Set a span attribute."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[dict] = None):
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {}
        })
    
    def set_status(self, status: str, message: str = ""):
        """Set span status."""
        self.status = status
        self.status_message = message
    
    def end(self):
        """End the span."""
        self.end_time = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert span to dictionary."""
        return {
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_id": self.context.parent_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": (self.end_time - self.start_time).total_seconds() * 1000 if self.end_time else None,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
            "status_message": self.status_message
        }


class Tracer:
    """
    Lightweight tracer for distributed tracing.
    
    In production, this would be replaced with OpenTelemetry SDK.
    """
    
    def __init__(self, service_name: str = "compliancegpt"):
        self.service_name = service_name
        self._current_span: Optional[Span] = None
        self._spans: list[Span] = []
        self._exporter: Optional[Callable] = None
        self._enabled = os.getenv("ENABLE_TRACING", "false").lower() == "true"
    
    def _generate_id(self, length: int = 16) -> str:
        """Generate a random trace/span ID."""
        import secrets
        return secrets.token_hex(length)
    
    def set_exporter(self, exporter: Callable):
        """Set the span exporter function."""
        self._exporter = exporter
    
    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[dict] = None
    ):
        """Start a new span."""
        if not self._enabled:
            yield None
            return
        
        # Create span context
        parent_span = self._current_span
        
        context = SpanContext(
            trace_id=parent_span.context.trace_id if parent_span else self._generate_id(16),
            span_id=self._generate_id(8),
            parent_id=parent_span.context.span_id if parent_span else None
        )
        
        span = Span(name=name, context=context, attributes=attributes)
        span.set_attribute("service.name", self.service_name)
        
        # Set as current span
        previous_span = self._current_span
        self._current_span = span
        
        try:
            yield span
        except Exception as e:
            span.set_status("ERROR", str(e))
            span.add_event("exception", {
                "type": type(e).__name__,
                "message": str(e)
            })
            raise
        finally:
            span.end()
            self._current_span = previous_span
            self._spans.append(span)
            
            # Export span
            if self._exporter:
                try:
                    self._exporter(span)
                except Exception:
                    pass
    
    def get_current_span(self) -> Optional[Span]:
        """Get the current active span."""
        return self._current_span
    
    def inject_context(self, headers: dict) -> dict:
        """Inject trace context into headers."""
        if self._current_span:
            headers["X-Trace-ID"] = self._current_span.context.trace_id
            headers["X-Span-ID"] = self._current_span.context.span_id
        return headers
    
    def extract_context(self, headers: dict) -> Optional[SpanContext]:
        """Extract trace context from headers."""
        trace_id = headers.get("X-Trace-ID") or headers.get("x-trace-id")
        span_id = headers.get("X-Span-ID") or headers.get("x-span-id")
        
        if trace_id:
            return SpanContext(
                trace_id=trace_id,
                span_id=span_id or self._generate_id(8)
            )
        return None
    
    def get_spans(self) -> list[dict]:
        """Get all recorded spans."""
        return [span.to_dict() for span in self._spans]
    
    def clear_spans(self):
        """Clear recorded spans."""
        self._spans = []


# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer(service_name="compliancegpt")
    return _tracer


def trace(name: Optional[str] = None, attributes: Optional[dict] = None):
    """Decorator to trace a function."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_span(span_name, attributes) as span:
                if span:
                    # Add function info as attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_span(span_name, attributes) as span:
                if span:
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                
                return func(*args, **kwargs)
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


class TracingMiddleware:
    """ASGI middleware for request tracing."""
    
    def __init__(self, app, tracer: Optional[Tracer] = None):
        self.app = app
        self.tracer = tracer or get_tracer()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract request info
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        headers = dict(scope.get("headers", []))
        
        # Extract trace context from headers
        trace_context = self.tracer.extract_context({
            k.decode(): v.decode() for k, v in headers.items()
            if isinstance(k, bytes)
        })
        
        span_name = f"HTTP {method} {path}"
        
        with self.tracer.start_span(span_name) as span:
            if span:
                span.set_attribute("http.method", method)
                span.set_attribute("http.url", path)
                span.set_attribute("http.scheme", scope.get("scheme", "http"))
                
                if trace_context:
                    span.set_attribute("trace.parent_id", trace_context.span_id)
            
            # Capture response status
            response_status = None
            
            async def send_wrapper(message):
                nonlocal response_status
                if message["type"] == "http.response.start":
                    response_status = message.get("status", 200)
                    if span:
                        span.set_attribute("http.status_code", response_status)
                        if response_status >= 400:
                            span.set_status("ERROR", f"HTTP {response_status}")
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as e:
                if span:
                    span.set_status("ERROR", str(e))
                raise


# Exporters

def console_exporter(span: Span):
    """Export spans to console (for development)."""
    print(f"[TRACE] {span.name} - {span.context.trace_id[:8]}... "
          f"({(span.end_time - span.start_time).total_seconds() * 1000:.2f}ms)")


def file_exporter(file_path: str = "traces.jsonl"):
    """Create a file exporter."""
    import json
    
    def exporter(span: Span):
        with open(file_path, "a") as f:
            f.write(json.dumps(span.to_dict()) + "\n")
    
    return exporter


async def otlp_exporter(endpoint: str):
    """
    OTLP exporter (placeholder for production use).
    
    In production, use opentelemetry-sdk:
    
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    """
    import aiohttp
    
    async def exporter(span: Span):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{endpoint}/v1/traces",
                json={"spans": [span.to_dict()]},
                headers={"Content-Type": "application/json"}
            ) as response:
                return response.status == 200
    
    return exporter


# FastAPI integration

def setup_tracing(app, service_name: str = "compliancegpt"):
    """Set up tracing for a FastAPI application."""
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    
    tracer = get_tracer()
    tracer.service_name = service_name
    
    # Set up exporter based on environment
    exporter_type = os.getenv("TRACE_EXPORTER", "console")
    
    if exporter_type == "console":
        tracer.set_exporter(console_exporter)
    elif exporter_type == "file":
        tracer.set_exporter(file_exporter(os.getenv("TRACE_FILE", "traces.jsonl")))
    
    # Add middleware
    app.add_middleware(TracingMiddleware, tracer=tracer)
    
    # Add trace endpoint
    @app.get("/api/traces", tags=["Observability"])
    async def get_traces(request: Request, limit: int = 100):
        """Get recent traces (development only)."""
        if os.getenv("DEBUG", "false").lower() != "true":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        
        spans = tracer.get_spans()
        return {
            "spans": spans[-limit:],
            "total": len(spans)
        }
    
    return tracer
