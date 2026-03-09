"""Audit logging system for security events.

Provides structured logging of authentication, authorization, and security events.
"""
import logging
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pathlib import Path


class AuditEvent(str, Enum):
    """Enumeration of audit event types."""
    
    # Authentication events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_MISSING = "auth.missing"
    
    # Crawl events
    CRAWL_START = "crawl.start"
    CRAWL_COMPLETE = "crawl.complete"
    CRAWL_FAILED = "crawl.failed"
    CRAWL_CANCELLED = "crawl.cancelled"
    
    # Security events
    SSRF_BLOCKED = "security.ssrf_blocked"
    RATE_LIMITED = "security.rate_limited"
    INVALID_REQUEST = "security.invalid_request"
    
    # Administrative events
    CONFIG_CHANGED = "admin.config_changed"
    SERVICE_START = "admin.service_start"
    SERVICE_STOP = "admin.service_stop"


class AuditLogger:
    """Structured audit logger for security and operational events."""
    
    def __init__(
        self,
        log_file: Optional[str] = None,
        console_output: bool = False,
        log_level: int = logging.INFO
    ):
        """
        Initialize audit logger.
        
        Args:
            log_file: Path to audit log file (defaults to data/audit.log)
            console_output: Whether to also output to console
            log_level: Logging level (default INFO)
        """
        # Create logger
        self.logger = logging.getLogger("spider.audit")
        self.logger.setLevel(log_level)
        self.logger.propagate = False  # Don't propagate to root logger
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler for audit log
        if log_file is None:
            log_dir = Path(__file__).parent.parent / "data"
            log_dir.mkdir(exist_ok=True)
            log_file = str(log_dir / "audit.log")
        
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # Use JSON formatter for structured logs
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Optional console output
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        self.log_file = log_file
    
    def log(
        self,
        event: AuditEvent,
        client_ip: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True
    ):
        """
        Log an audit event.
        
        Args:
            event: The type of event
            client_ip: IP address of the client
            user_id: Optional user identifier
            details: Additional event-specific details
            success: Whether the operation was successful
        """
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event.value,
            "client_ip": client_ip,
            "user_id": user_id,
            "success": success,
            "details": details or {}
        }
        
        # Determine log level based on event type
        if event in [
            AuditEvent.AUTH_FAILURE,
            AuditEvent.SSRF_BLOCKED,
            AuditEvent.RATE_LIMITED
        ]:
            level = logging.WARNING
        elif event in [AuditEvent.CRAWL_FAILED]:
            level = logging.ERROR
        else:
            level = logging.INFO
        
        self.logger.log(level, json.dumps(record))
    
    def log_auth_success(self, client_ip: str, user_id: Optional[str] = None):
        """Log successful authentication."""
        self.log(
            AuditEvent.AUTH_SUCCESS,
            client_ip=client_ip,
            user_id=user_id,
            success=True
        )
    
    def log_auth_failure(
        self,
        client_ip: str,
        reason: str = "Invalid credentials"
    ):
        """Log failed authentication attempt."""
        self.log(
            AuditEvent.AUTH_FAILURE,
            client_ip=client_ip,
            details={"reason": reason},
            success=False
        )
    
    def log_crawl_start(
        self,
        client_ip: str,
        task_id: str,
        target_url: str,
        user_id: Optional[str] = None
    ):
        """Log crawl task start."""
        self.log(
            AuditEvent.CRAWL_START,
            client_ip=client_ip,
            user_id=user_id,
            details={
                "task_id": task_id,
                "target_url": target_url
            }
        )
    
    def log_crawl_complete(
        self,
        client_ip: str,
        task_id: str,
        pages_crawled: int,
        duration_seconds: float,
        user_id: Optional[str] = None
    ):
        """Log crawl task completion."""
        self.log(
            AuditEvent.CRAWL_COMPLETE,
            client_ip=client_ip,
            user_id=user_id,
            details={
                "task_id": task_id,
                "pages_crawled": pages_crawled,
                "duration_seconds": round(duration_seconds, 2)
            }
        )
    
    def log_ssrf_blocked(
        self,
        client_ip: str,
        target_url: str,
        reason: str
    ):
        """Log blocked SSRF attempt."""
        self.log(
            AuditEvent.SSRF_BLOCKED,
            client_ip=client_ip,
            details={
                "target_url": target_url,
                "reason": reason
            },
            success=False
        )
    
    def log_rate_limited(
        self,
        client_ip: str,
        endpoint: str
    ):
        """Log rate limit enforcement."""
        self.log(
            AuditEvent.RATE_LIMITED,
            client_ip=client_ip,
            details={"endpoint": endpoint},
            success=False
        )
    
    def get_recent_events(
        self,
        count: int = 100,
        event_type: Optional[AuditEvent] = None
    ) -> list:
        """
        Read recent audit events from log file.
        
        Args:
            count: Maximum number of events to return
            event_type: Optional filter by event type
            
        Returns:
            List of audit event dictionaries (most recent first)
        """
        events = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Read file in reverse (most recent first)
                lines = f.readlines()
                for line in reversed(lines):
                    if len(events) >= count:
                        break
                    
                    try:
                        event = json.loads(line.strip())
                        
                        # Filter by event type if specified
                        if event_type and event.get("event") != event_type.value:
                            continue
                        
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
                        
        except FileNotFoundError:
            pass
        
        return events


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get or create the global audit logger instance.
    
    Returns:
        AuditLogger: The global audit logger
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience function for direct access
audit = get_audit_logger()
