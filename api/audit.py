"""
audit.py - Audit Logging for ComplianceGPT

Enterprise-grade audit trail for compliance and security.
"""

import json
import logging
import hashlib
import os
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import threading
from queue import Queue


class AuditAction(str, Enum):
    """Audit event actions."""
    # Query actions
    QUERY_SUBMITTED = "query.submitted"
    QUERY_COMPLETED = "query.completed"
    QUERY_FAILED = "query.failed"
    
    # Authentication actions
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_RATE_LIMITED = "auth.rate_limited"
    
    # Admin actions
    CACHE_CLEARED = "admin.cache_cleared"
    CONFIG_CHANGED = "admin.config_changed"
    
    # Data actions
    DATA_INDEXED = "data.indexed"
    DATA_DELETED = "data.deleted"
    
    # System actions
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents an audit log entry."""
    
    # Core fields
    event_id: str
    timestamp: str
    action: str
    severity: str
    
    # Actor information
    client_ip: Optional[str] = None
    user_id: Optional[str] = None
    api_key_hash: Optional[str] = None
    
    # Request context
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    
    # Event details
    resource: Optional[str] = None
    details: dict = field(default_factory=dict)
    
    # Outcome
    success: bool = True
    error_message: Optional[str] = None
    
    # Performance
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Enterprise audit logger with async writing and multiple outputs.
    
    Features:
    - Async log writing (non-blocking)
    - Multiple output targets (file, stdout, webhook)
    - Log rotation support
    - PII hashing
    - Structured JSON format
    """
    
    def __init__(
        self,
        log_dir: Optional[str] = None,
        enable_file: bool = True,
        enable_stdout: bool = False,
        enable_webhook: bool = False,
        webhook_url: Optional[str] = None,
        max_queue_size: int = 10000
    ):
        self.log_dir = Path(log_dir) if log_dir else Path("logs/audit")
        self.enable_file = enable_file
        self.enable_stdout = enable_stdout
        self.enable_webhook = enable_webhook
        self.webhook_url = webhook_url or os.getenv("AUDIT_WEBHOOK_URL")
        
        # Async queue for non-blocking writes
        self._queue: Queue = Queue(maxsize=max_queue_size)
        self._running = True
        self._event_counter = 0
        self._lock = threading.Lock()
        
        # Setup
        if self.enable_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Start background writer thread
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer_thread.start()
        
        # Logger for internal errors
        self._logger = logging.getLogger("audit")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        with self._lock:
            self._event_counter += 1
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            return f"AUD-{timestamp}-{self._event_counter:06d}"
    
    def _hash_sensitive(self, value: str) -> str:
        """Hash sensitive data for audit trail."""
        if not value:
            return ""
        return hashlib.sha256(value.encode()).hexdigest()[:16]
    
    def log(
        self,
        action: AuditAction,
        severity: AuditSeverity = AuditSeverity.INFO,
        client_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> str:
        """
        Log an audit event.
        
        Returns:
            Event ID for tracking
        """
        event = AuditEvent(
            event_id=self._generate_event_id(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action.value if isinstance(action, AuditAction) else action,
            severity=severity.value if isinstance(severity, AuditSeverity) else severity,
            client_ip=client_ip,
            user_id=user_id,
            api_key_hash=self._hash_sensitive(api_key) if api_key else None,
            request_id=request_id,
            endpoint=endpoint,
            method=method,
            resource=resource,
            details=details or {},
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        # Queue for async writing
        try:
            self._queue.put_nowait(event)
        except:
            # Queue full - log synchronously as fallback
            self._write_event(event)
        
        return event.event_id
    
    def _writer_loop(self):
        """Background loop for writing audit events."""
        while self._running:
            try:
                event = self._queue.get(timeout=1)
                self._write_event(event)
            except:
                continue
    
    def _write_event(self, event: AuditEvent):
        """Write event to all enabled outputs."""
        json_line = event.to_json()
        
        if self.enable_file:
            self._write_to_file(json_line)
        
        if self.enable_stdout:
            print(f"[AUDIT] {json_line}")
        
        if self.enable_webhook and self.webhook_url:
            self._send_webhook(event)
    
    def _write_to_file(self, json_line: str):
        """Write to daily rotating log file."""
        try:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            log_file = self.log_dir / f"audit-{date_str}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json_line + "\n")
        except Exception as e:
            self._logger.error(f"Failed to write audit log: {e}")
    
    def _send_webhook(self, event: AuditEvent):
        """Send event to webhook endpoint."""
        try:
            import httpx
            httpx.post(
                self.webhook_url,
                json=event.to_dict(),
                timeout=5
            )
        except Exception as e:
            self._logger.warning(f"Failed to send audit webhook: {e}")
    
    def query_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
        client_ip: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Query audit logs (for admin dashboard).
        
        Note: For production, use a proper log aggregation system.
        """
        results = []
        
        # Determine date range
        if not start_date:
            start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        # Read log files in date range
        current = start_date
        while current <= end_date and len(results) < limit:
            date_str = current.strftime("%Y-%m-%d")
            log_file = self.log_dir / f"audit-{date_str}.jsonl"
            
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if len(results) >= limit:
                            break
                        
                        try:
                            event = json.loads(line)
                            
                            # Apply filters
                            if action and event.get("action") != action:
                                continue
                            if client_ip and event.get("client_ip") != client_ip:
                                continue
                            
                            results.append(event)
                        except:
                            continue
            
            current = current.replace(day=current.day + 1)
        
        return results
    
    def shutdown(self):
        """Gracefully shutdown the audit logger."""
        self._running = False
        
        # Flush remaining events
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                self._write_event(event)
            except:
                break


# Global audit logger instance
audit_logger = AuditLogger(
    enable_file=os.getenv("AUDIT_LOG_FILE", "true").lower() == "true",
    enable_stdout=os.getenv("AUDIT_LOG_STDOUT", "false").lower() == "true"
)


# Convenience functions
def log_query(
    question: str,
    regulation: Optional[str],
    client_ip: str,
    request_id: str,
    success: bool = True,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None
) -> str:
    """Log a compliance query."""
    return audit_logger.log(
        action=AuditAction.QUERY_COMPLETED if success else AuditAction.QUERY_FAILED,
        severity=AuditSeverity.INFO if success else AuditSeverity.ERROR,
        client_ip=client_ip,
        request_id=request_id,
        endpoint="/api/query",
        method="POST",
        details={
            "question_length": len(question),
            "regulation": regulation,
            "question_hash": hashlib.md5(question.encode()).hexdigest()[:8]
        },
        success=success,
        error_message=error,
        duration_ms=duration_ms
    )


def log_auth_event(
    success: bool,
    client_ip: str,
    api_key: Optional[str] = None,
    reason: Optional[str] = None
) -> str:
    """Log an authentication event."""
    return audit_logger.log(
        action=AuditAction.AUTH_SUCCESS if success else AuditAction.AUTH_FAILURE,
        severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
        client_ip=client_ip,
        api_key=api_key,
        success=success,
        error_message=reason
    )


def log_rate_limit(client_ip: str, endpoint: str) -> str:
    """Log a rate limit event."""
    return audit_logger.log(
        action=AuditAction.AUTH_RATE_LIMITED,
        severity=AuditSeverity.WARNING,
        client_ip=client_ip,
        endpoint=endpoint,
        success=False,
        error_message="Rate limit exceeded"
    )
