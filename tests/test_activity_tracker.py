"""
Tests for Activity Tracker
"""

import pytest
import sys
import os
from datetime import datetime, timezone

# Add gateway directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gateway'))

from activity_tracker import (
    ActivityTracker,
    ActivityEvent,
    ActivityType,
    ActivitySeverity,
    activity_tracker,
    track_query_execution,
    track_approval_request,
    track_vote_decision,
    track_security_event,
    track_agent_lifecycle
)

class TestActivityTracker:
    """Test the activity tracker functionality"""
    
    @pytest.fixture
    def tracker(self):
        """Get the activity tracker instance"""
        # Reset the singleton for testing
        tracker = ActivityTracker()
        tracker.events.clear()
        tracker.stats = {
            "total_queries": 0,
            "blocked_queries": 0,
            "approved_queries": 0,
            "denied_queries": 0,
            "active_agents": 0,
            "queries_per_hour": 0,
            "last_hour_queries": tracker.stats.get("last_hour_queries", [])
        }
        return tracker
    
    @pytest.mark.asyncio
    async def test_track_event(self, tracker):
        """Test tracking a basic event"""
        event = await tracker.track_event(
            activity_type=ActivityType.QUERY_EXECUTED,
            message="Test query executed",
            severity=ActivitySeverity.SUCCESS,
            details={"query": "SELECT * FROM test"},
            subject_id="user123",
            tool_name="test_tool"
        )
        
        assert event is not None
        assert event.activity_type == ActivityType.QUERY_EXECUTED
        assert event.message == "Test query executed"
        assert event.severity == ActivitySeverity.SUCCESS
        assert event.subject_id == "user123"
        assert event.tool_name == "test_tool"
        
        # Check event was added to tracker
        assert len(tracker.events) == 1
        assert tracker.events[0] == event
    
    @pytest.mark.asyncio
    async def test_track_query_execution_allowed(self, tracker):
        """Test tracking an allowed query execution"""
        await track_query_execution(
            query="SELECT name FROM users",
            subject_id="dev456",
            allowed=True
        )
        
        assert len(tracker.events) == 1
        event = tracker.events[0]
        assert event.activity_type == ActivityType.QUERY_EXECUTED
        assert event.severity == ActivitySeverity.SUCCESS
        assert tracker.stats["total_queries"] == 1
    
    @pytest.mark.asyncio
    async def test_track_query_execution_blocked(self, tracker):
        """Test tracking a blocked query execution"""
        await track_query_execution(
            query="DROP TABLE users",
            subject_id="agent789",
            allowed=False
        )
        
        assert len(tracker.events) == 1
        event = tracker.events[0]
        assert event.activity_type == ActivityType.QUERY_BLOCKED
        assert event.severity in [ActivitySeverity.WARNING, ActivitySeverity.CRITICAL]
        assert tracker.stats["blocked_queries"] == 1
    
    @pytest.mark.asyncio
    async def test_track_approval_request(self, tracker):
        """Test tracking an approval request"""
        await track_approval_request(
            tool_name="dangerous_tool",
            subject_id="user001",
            risk_level="HIGH"
        )
        
        assert len(tracker.events) == 1
        event = tracker.events[0]
        assert event.activity_type == ActivityType.APPROVAL_REQUESTED
        assert event.severity == ActivitySeverity.WARNING
        assert event.tool_name == "dangerous_tool"
    
    @pytest.mark.asyncio
    async def test_track_vote_decision_approve(self, tracker):
        """Test tracking an approval vote"""
        await track_vote_decision(
            request_id="req123",
            stakeholder="CISO",
            decision="APPROVE"
        )
        
        assert len(tracker.events) == 1
        event = tracker.events[0]
        assert event.activity_type == ActivityType.APPROVAL_GRANTED
        assert event.severity == ActivitySeverity.INFO
        assert tracker.stats["approved_queries"] == 1
    
    @pytest.mark.asyncio
    async def test_track_vote_decision_deny(self, tracker):
        """Test tracking a denial vote"""
        await track_vote_decision(
            request_id="req456",
            stakeholder="SECURITY_ANALYST",
            decision="DENY"
        )
        
        assert len(tracker.events) == 1
        event = tracker.events[0]
        assert event.activity_type == ActivityType.APPROVAL_DENIED
        assert event.severity == ActivitySeverity.INFO
        assert tracker.stats["denied_queries"] == 1
    
    @pytest.mark.asyncio
    async def test_track_security_event_pii(self, tracker):
        """Test tracking a PII access security event"""
        await track_security_event(
            event_type="pii_access",
            details={"table": "customers", "columns": ["ssn", "credit_card"]}
        )
        
        assert len(tracker.events) == 1
        event = tracker.events[0]
        assert event.activity_type == ActivityType.PII_ACCESS_ATTEMPTED
        assert event.severity == ActivitySeverity.WARNING
    
    @pytest.mark.asyncio
    async def test_track_security_event_schema_change(self, tracker):
        """Test tracking a schema change security event"""
        await track_security_event(
            event_type="schema_change",
            details={"operation": "ALTER TABLE", "table": "users"}
        )
        
        assert len(tracker.events) == 1
        event = tracker.events[0]
        assert event.activity_type == ActivityType.SCHEMA_CHANGE_ATTEMPTED
        assert event.severity == ActivitySeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_track_agent_lifecycle_connect(self, tracker):
        """Test tracking agent connection"""
        await track_agent_lifecycle(
            agent_id="agent001",
            connected=True
        )
        
        assert len(tracker.events) == 1
        event = tracker.events[0]
        assert event.activity_type == ActivityType.AGENT_CONNECTED
        assert event.severity == ActivitySeverity.INFO
        assert tracker.stats["active_agents"] == 1
    
    @pytest.mark.asyncio
    async def test_track_agent_lifecycle_disconnect(self, tracker):
        """Test tracking agent disconnection"""
        # First connect
        await track_agent_lifecycle("agent002", True)
        # Then disconnect
        await track_agent_lifecycle("agent002", False)
        
        assert len(tracker.events) == 2
        assert tracker.events[1].activity_type == ActivityType.AGENT_DISCONNECTED
        assert tracker.stats["active_agents"] == 0
    
    def test_get_recent_events(self, tracker):
        """Test getting recent events"""
        # Add some events manually
        for i in range(5):
            event = ActivityEvent(
                activity_type=ActivityType.QUERY_EXECUTED,
                severity=ActivitySeverity.INFO,
                message=f"Event {i}"
            )
            tracker.events.append(event)
        
        recent = tracker.get_recent_events(limit=3)
        assert len(recent) == 3
        # Should be in reverse order (most recent first)
        assert recent[0]["message"] == "Event 4"
        assert recent[1]["message"] == "Event 3"
        assert recent[2]["message"] == "Event 2"
    
    def test_get_stats(self, tracker):
        """Test getting statistics"""
        # Set some stats
        tracker.stats["total_queries"] = 100
        tracker.stats["blocked_queries"] = 10
        tracker.stats["approved_queries"] = 80
        tracker.stats["denied_queries"] = 10
        tracker.stats["active_agents"] = 5
        
        stats = tracker.get_stats()
        
        assert stats["total_queries"] == 100
        assert stats["blocked_today"] == 10
        assert stats["approved_today"] == 80
        assert stats["denied_today"] == 10
        assert stats["active_agents"] == 5
    
    @pytest.mark.asyncio
    async def test_event_deque_max_size(self, tracker):
        """Test that events deque respects max size"""
        # Add more than maxlen events (1000)
        for i in range(1100):
            await tracker.track_event(
                activity_type=ActivityType.QUERY_EXECUTED,
                message=f"Event {i}",
                severity=ActivitySeverity.INFO
            )
        
        # Should only keep last 1000
        assert len(tracker.events) == 1000
        # Oldest events should be dropped
        assert tracker.events[0].message == "Event 100"
        assert tracker.events[-1].message == "Event 1099"


class TestActivityEvent:
    """Test the ActivityEvent class"""
    
    def test_activity_event_creation(self):
        """Test creating an activity event"""
        event = ActivityEvent(
            activity_type=ActivityType.QUERY_BLOCKED,
            severity=ActivitySeverity.CRITICAL,
            message="Dangerous query blocked",
            details={"query": "DROP TABLE"},
            subject_id="user123",
            tool_name="sql_tool"
        )
        
        assert event.activity_type == ActivityType.QUERY_BLOCKED
        assert event.severity == ActivitySeverity.CRITICAL
        assert event.message == "Dangerous query blocked"
        assert event.subject_id == "user123"
        assert event.tool_name == "sql_tool"
        assert event.id is not None
        assert event.timestamp is not None
    
    def test_activity_event_to_dict(self):
        """Test converting activity event to dictionary"""
        event = ActivityEvent(
            activity_type=ActivityType.APPROVAL_REQUESTED,
            severity=ActivitySeverity.WARNING,
            message="Approval needed",
            details={"reason": "high risk"},
            subject_id="agent456",
            tool_name="risky_tool"
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["type"] == "approval_requested"
        assert event_dict["severity"] == "warning"
        assert event_dict["message"] == "Approval needed"
        assert event_dict["subject_id"] == "agent456"
        assert event_dict["tool_name"] == "risky_tool"
        assert "timestamp" in event_dict
        assert "id" in event_dict
        assert event_dict["details"]["reason"] == "high risk"