"""
Activity Tracker for Refulgence Governance System
Tracks all governance events and provides real-time activity feed
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum
from collections import deque
import logging

logger = logging.getLogger(__name__)

class ActivityType(Enum):
    QUERY_EXECUTED = "query_executed"
    QUERY_BLOCKED = "query_blocked"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    PII_ACCESS_ATTEMPTED = "pii_access_attempted"
    SCHEMA_CHANGE_ATTEMPTED = "schema_change_attempted"
    AGENT_CONNECTED = "agent_connected"
    AGENT_DISCONNECTED = "agent_disconnected"
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    EMERGENCY_BLOCK = "emergency_block"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_WARNING = "rate_limit_warning"
    AUDIT_EXPORTED = "audit_exported"

class ActivitySeverity(Enum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class ActivityEvent:
    """Represents a single activity event"""
    
    def __init__(
        self,
        activity_type: ActivityType,
        severity: ActivitySeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        subject_id: Optional[str] = None,
        tool_name: Optional[str] = None
    ):
        self.id = f"event_{int(datetime.now().timestamp() * 1000)}"
        self.timestamp = datetime.now(timezone.utc)
        self.activity_type = activity_type
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.subject_id = subject_id
        self.tool_name = tool_name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.activity_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "subject_id": self.subject_id,
            "tool_name": self.tool_name
        }

class ActivityTracker:
    """Singleton activity tracker for the governance system"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Store last 1000 events in memory
        self.events = deque(maxlen=1000)
        self.subscribers = []
        self._initialized = True
        self._lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "blocked_queries": 0,
            "approved_queries": 0,
            "denied_queries": 0,
            "active_agents": 0,
            "queries_per_hour": 0,
            "last_hour_queries": deque(maxlen=3600)  # Track last hour
        }
    
    async def track_event(
        self,
        activity_type: ActivityType,
        message: str,
        severity: ActivitySeverity = ActivitySeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        subject_id: Optional[str] = None,
        tool_name: Optional[str] = None
    ) -> ActivityEvent:
        """Track a new activity event"""
        async with self._lock:
            event = ActivityEvent(
                activity_type=activity_type,
                severity=severity,
                message=message,
                details=details,
                subject_id=subject_id,
                tool_name=tool_name
            )
            
            self.events.append(event)
            
            # Update statistics
            self._update_stats(event)
            
            # Notify subscribers (for WebSocket/SSE)
            await self._notify_subscribers(event)
            
            logger.info(f"Activity tracked: {event.message} [{event.severity.value}]")
            
            return event
    
    def _update_stats(self, event: ActivityEvent):
        """Update internal statistics based on event"""
        now = datetime.now(timezone.utc)
        
        if event.activity_type == ActivityType.QUERY_EXECUTED:
            self.stats["total_queries"] += 1
            self.stats["last_hour_queries"].append(now)
        elif event.activity_type == ActivityType.QUERY_BLOCKED:
            self.stats["blocked_queries"] += 1
        elif event.activity_type == ActivityType.APPROVAL_GRANTED:
            self.stats["approved_queries"] += 1
        elif event.activity_type == ActivityType.APPROVAL_DENIED:
            self.stats["denied_queries"] += 1
        elif event.activity_type == ActivityType.AGENT_CONNECTED:
            self.stats["active_agents"] += 1
        elif event.activity_type == ActivityType.AGENT_DISCONNECTED:
            self.stats["active_agents"] = max(0, self.stats["active_agents"] - 1)
        
        # Calculate queries per hour
        hour_ago = now.timestamp() - 3600
        recent_queries = [q for q in self.stats["last_hour_queries"] 
                         if q.timestamp() > hour_ago]
        self.stats["queries_per_hour"] = len(recent_queries)
    
    async def _notify_subscribers(self, event: ActivityEvent):
        """Notify all subscribers of new event (for real-time updates)"""
        for subscriber in self.subscribers:
            try:
                await subscriber(event)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity events"""
        events = list(self.events)[-limit:]
        events.reverse()  # Most recent first
        return [event.to_dict() for event in events]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            "total_queries": self.stats["total_queries"],
            "blocked_today": self.stats["blocked_queries"],
            "approved_today": self.stats["approved_queries"],
            "denied_today": self.stats["denied_queries"],
            "active_agents": self.stats["active_agents"],
            "queries_per_hour": self.stats["queries_per_hour"]
        }
    
    def subscribe(self, callback):
        """Subscribe to activity events (for WebSocket/SSE)"""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback):
        """Unsubscribe from activity events"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

# Global tracker instance
activity_tracker = ActivityTracker()

# Helper functions for common events
async def track_query_execution(query: str, subject_id: str, allowed: bool):
    """Track a query execution attempt"""
    if allowed:
        await activity_tracker.track_event(
            ActivityType.QUERY_EXECUTED,
            f"Query executed: {query[:50]}...",
            ActivitySeverity.SUCCESS,
            {"query": query, "subject": subject_id}
        )
    else:
        severity = ActivitySeverity.CRITICAL if "DROP" in query.upper() else ActivitySeverity.WARNING
        await activity_tracker.track_event(
            ActivityType.QUERY_BLOCKED,
            f"Query blocked: {query[:50]}...",
            severity,
            {"query": query, "subject": subject_id}
        )

async def track_approval_request(tool_name: str, subject_id: str, risk_level: str):
    """Track an approval request"""
    severity = {
        "CRITICAL": ActivitySeverity.CRITICAL,
        "HIGH": ActivitySeverity.WARNING,
        "MEDIUM": ActivitySeverity.INFO,
        "LOW": ActivitySeverity.INFO
    }.get(risk_level, ActivitySeverity.INFO)
    
    await activity_tracker.track_event(
        ActivityType.APPROVAL_REQUESTED,
        f"Approval requested for {tool_name}",
        severity,
        {"tool": tool_name, "subject": subject_id, "risk_level": risk_level},
        subject_id,
        tool_name
    )

async def track_vote_decision(request_id: str, stakeholder: str, decision: str):
    """Track a stakeholder vote"""
    activity_type = (ActivityType.APPROVAL_GRANTED 
                    if decision == "APPROVE" 
                    else ActivityType.APPROVAL_DENIED)
    
    await activity_tracker.track_event(
        activity_type,
        f"{stakeholder} {decision.lower()}d request {request_id}",
        ActivitySeverity.INFO,
        {"request_id": request_id, "stakeholder": stakeholder, "decision": decision}
    )

async def track_security_event(event_type: str, details: Dict[str, Any]):
    """Track a security-related event"""
    severity_map = {
        "pii_access": ActivitySeverity.WARNING,
        "schema_change": ActivitySeverity.CRITICAL,
        "rate_limit": ActivitySeverity.WARNING,
        "sql_injection": ActivitySeverity.CRITICAL,
        "emergency_block": ActivitySeverity.CRITICAL
    }
    
    severity = severity_map.get(event_type, ActivitySeverity.WARNING)
    
    activity_type_map = {
        "pii_access": ActivityType.PII_ACCESS_ATTEMPTED,
        "schema_change": ActivityType.SCHEMA_CHANGE_ATTEMPTED,
        "rate_limit": ActivityType.RATE_LIMIT_WARNING,
        "emergency_block": ActivityType.EMERGENCY_BLOCK
    }
    
    activity_type = activity_type_map.get(event_type, ActivityType.SECURITY_VIOLATION)
    
    await activity_tracker.track_event(
        activity_type,
        f"Security event: {event_type}",
        severity,
        details
    )

async def track_agent_lifecycle(agent_id: str, connected: bool):
    """Track agent connection/disconnection"""
    if connected:
        await activity_tracker.track_event(
            ActivityType.AGENT_CONNECTED,
            f"Agent {agent_id} connected",
            ActivitySeverity.INFO,
            {"agent_id": agent_id}
        )
    else:
        await activity_tracker.track_event(
            ActivityType.AGENT_DISCONNECTED,
            f"Agent {agent_id} disconnected",
            ActivitySeverity.INFO,
            {"agent_id": agent_id}
        )