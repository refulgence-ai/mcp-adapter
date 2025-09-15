"""
User Data Store for Refulgence Governance System
Provides both demo simulation and real user management capabilities
"""

import asyncio
import json
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging
import os

logger = logging.getLogger(__name__)

class UserRole(Enum):
    ADMIN = "admin"
    SECURITY_ANALYST = "security"
    BUSINESS_LEAD = "business"
    USER = "user"
    AGENT = "agent"
    IT_ADMIN = "it_admin"
    CISO = "ciso"

class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class PermissionLevel(Enum):
    READ_ONLY = "read_only"
    MONITOR_REVIEW = "monitor_review"
    EXECUTE_APPROVE = "execute_approve"
    ADMIN_FULL = "admin_full"

@dataclass
class User:
    """User entity with comprehensive governance data"""
    id: str
    name: str
    email: str
    role: UserRole
    status: UserStatus
    permissions: PermissionLevel
    created_at: datetime
    last_active: datetime
    total_queries: int = 0
    approved_queries: int = 0
    blocked_queries: int = 0
    risk_score: float = 0.0
    department: str = ""
    manager_id: Optional[str] = None
    access_patterns: Dict[str, Any] = None

    def __post_init__(self):
        if self.access_patterns is None:
            self.access_patterns = {
                "frequent_tools": [],
                "peak_hours": [],
                "query_types": defaultdict(int),
                "approval_rate": 0.0
            }

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for JSON serialization"""
        data = asdict(self)
        data['role'] = self.role.value
        data['status'] = self.status.value
        data['permissions'] = self.permissions.value
        data['created_at'] = self.created_at.isoformat()
        data['last_active'] = self.last_active.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary"""
        data['role'] = UserRole(data['role'])
        data['status'] = UserStatus(data['status'])
        data['permissions'] = PermissionLevel(data['permissions'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_active'] = datetime.fromisoformat(data['last_active'])
        return cls(**data)

class UserDataStore:
    """Manages user data with demo simulation and real user capabilities"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.demo_mode = os.getenv('REFULGENCE_DEMO_MODE', 'true').lower() == 'true'
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Set[str]] = defaultdict(set)  # session_id -> user_ids
        self.activity_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self._initialized = True
        self._lock = asyncio.Lock()

        # Set up data persistence paths
        self.data_dir = '/app/data'
        self.users_file = f'{self.data_dir}/users.json'
        self.activity_patterns_file = f'{self.data_dir}/activity_patterns.json'

        # Ensure data directory exists (gracefully handle read-only filesystems in tests)
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            # Load existing data first
            self._load_persistent_data()

            # Initialize with demo data if in demo mode and no existing data
            if self.demo_mode and not self.users:
                self._initialize_demo_users()
                self._save_persistent_data()  # Save demo data immediately
        except (OSError, PermissionError):
            # In test environments or read-only filesystems, skip persistence and use demo data
            logger.warning(f"Cannot create data directory {self.data_dir} - persistence disabled, using demo data")
            if self.demo_mode:
                self._initialize_demo_users()

        logger.info(f"UserDataStore initialized in {'demo' if self.demo_mode else 'real'} mode with {len(self.users)} users")

    def _initialize_demo_users(self):
        """Initialize with realistic demo users"""
        demo_users_data = [
            {
                "id": "sarah_wilson_sec",
                "name": "Sarah Wilson",
                "email": "sarah.wilson@company.com",
                "role": UserRole.SECURITY_ANALYST,
                "status": UserStatus.ACTIVE,
                "permissions": PermissionLevel.MONITOR_REVIEW,
                "department": "Security",
                "total_queries": 45,
                "approved_queries": 42,
                "blocked_queries": 3,
                "risk_score": 0.1
            },
            {
                "id": "mike_chen_admin",
                "name": "Mike Chen",
                "email": "mike.chen@company.com",
                "role": UserRole.ADMIN,
                "status": UserStatus.ACTIVE,
                "permissions": PermissionLevel.ADMIN_FULL,
                "department": "IT",
                "total_queries": 123,
                "approved_queries": 115,
                "blocked_queries": 8,
                "risk_score": 0.2
            },
            {
                "id": "emma_rodriguez_biz",
                "name": "Emma Rodriguez",
                "email": "emma.rodriguez@company.com",
                "role": UserRole.BUSINESS_LEAD,
                "status": UserStatus.ACTIVE,
                "permissions": PermissionLevel.EXECUTE_APPROVE,
                "department": "Analytics",
                "total_queries": 78,
                "approved_queries": 70,
                "blocked_queries": 8,
                "risk_score": 0.3
            },
            {
                "id": "david_kim_user",
                "name": "David Kim",
                "email": "david.kim@company.com",
                "role": UserRole.USER,
                "status": UserStatus.ACTIVE,
                "permissions": PermissionLevel.READ_ONLY,
                "department": "Finance",
                "total_queries": 23,
                "approved_queries": 21,
                "blocked_queries": 2,
                "risk_score": 0.05
            },
            {
                "id": "alex_thompson_agent",
                "name": "Alex Thompson",
                "email": "alex.thompson@company.com",
                "role": UserRole.AGENT,
                "status": UserStatus.ACTIVE,
                "permissions": PermissionLevel.EXECUTE_APPROVE,
                "department": "AI Operations",
                "total_queries": 234,
                "approved_queries": 198,
                "blocked_queries": 36,
                "risk_score": 0.4
            },
            {
                "id": "jennifer_park_ciso",
                "name": "Jennifer Park",
                "email": "jennifer.park@company.com",
                "role": UserRole.CISO,
                "status": UserStatus.ACTIVE,
                "permissions": PermissionLevel.ADMIN_FULL,
                "department": "Executive",
                "total_queries": 67,
                "approved_queries": 65,
                "blocked_queries": 2,
                "risk_score": 0.0
            },
            {
                "id": "tom_watson_inactive",
                "name": "Tom Watson",
                "email": "tom.watson@company.com",
                "role": UserRole.USER,
                "status": UserStatus.INACTIVE,
                "permissions": PermissionLevel.READ_ONLY,
                "department": "Marketing",
                "total_queries": 12,
                "approved_queries": 12,
                "blocked_queries": 0,
                "risk_score": 0.0
            }
        ]

        now = datetime.now(timezone.utc)

        for user_data in demo_users_data:
            # Create realistic timestamps
            created_days_ago = random.randint(30, 365)
            last_active_hours_ago = random.randint(1, 48) if user_data["status"] == UserStatus.ACTIVE else random.randint(168, 720)

            user = User(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                role=user_data["role"],
                status=user_data["status"],
                permissions=user_data["permissions"],
                created_at=now - timedelta(days=created_days_ago),
                last_active=now - timedelta(hours=last_active_hours_ago),
                total_queries=user_data["total_queries"],
                approved_queries=user_data["approved_queries"],
                blocked_queries=user_data["blocked_queries"],
                risk_score=user_data["risk_score"],
                department=user_data["department"]
            )

            # Add realistic access patterns
            user.access_patterns = {
                "frequent_tools": self._generate_frequent_tools(user.role),
                "peak_hours": self._generate_peak_hours(user.department),
                "query_types": self._generate_query_types(user.role),
                "approval_rate": user.approved_queries / max(1, user.total_queries)
            }

            self.users[user.id] = user

    def _generate_frequent_tools(self, role: UserRole) -> List[str]:
        """Generate realistic frequent tools based on role"""
        tool_patterns = {
            UserRole.SECURITY_ANALYST: ["redshift_execute_query", "audit_logs", "security_scan"],
            UserRole.ADMIN: ["redshift_execute_query", "user_management", "system_config"],
            UserRole.BUSINESS_LEAD: ["redshift_execute_query", "analytics_dashboard", "report_generation"],
            UserRole.USER: ["redshift_execute_query", "data_export"],
            UserRole.AGENT: ["redshift_execute_query", "ml_pipeline", "data_processing"],
            UserRole.CISO: ["security_overview", "policy_management", "audit_review"],
            UserRole.IT_ADMIN: ["system_monitoring", "performance_metrics", "backup_management"]
        }
        return tool_patterns.get(role, ["redshift_execute_query"])

    def _generate_peak_hours(self, department: str) -> List[int]:
        """Generate realistic peak usage hours based on department"""
        patterns = {
            "Security": [8, 9, 14, 15, 16],  # Security checks morning/afternoon
            "IT": [9, 10, 11, 13, 14],       # Standard business hours
            "Analytics": [10, 11, 14, 15, 16], # Data analysis times
            "Finance": [9, 10, 11, 14, 15],   # Report generation times
            "AI Operations": [8, 9, 10, 13, 14, 15, 16], # Extended hours
            "Executive": [10, 11, 14, 15],    # Limited peak hours
            "Marketing": [9, 10, 11, 14, 15]  # Standard hours
        }
        return patterns.get(department, [9, 10, 11, 14, 15])

    def _generate_query_types(self, role: UserRole) -> Dict[str, int]:
        """Generate realistic query type distributions"""
        base_patterns = {
            UserRole.SECURITY_ANALYST: {"audit": 20, "monitoring": 15, "investigation": 10},
            UserRole.ADMIN: {"configuration": 30, "monitoring": 20, "maintenance": 15},
            UserRole.BUSINESS_LEAD: {"analytics": 25, "reporting": 20, "dashboard": 15},
            UserRole.USER: {"lookup": 15, "export": 5, "basic_query": 3},
            UserRole.AGENT: {"data_processing": 50, "ml_pipeline": 30, "automation": 20},
            UserRole.CISO: {"audit": 15, "policy": 10, "overview": 8},
            UserRole.IT_ADMIN: {"system": 25, "performance": 15, "backup": 10}
        }
        return base_patterns.get(role, {"basic": 10})

    def start_simulation(self):
        """Start background simulation of user activity (call when event loop is available)"""
        if self.demo_mode and not hasattr(self, '_simulation_started'):
            try:
                asyncio.create_task(self._simulate_user_activity())
                self._simulation_started = True
                logger.info("User activity simulation started")
            except RuntimeError:
                # Event loop not available yet - schedule for later
                logger.info("Event loop not ready - scheduling simulation for startup")
                pass

    async def start_simulation_async(self):
        """Async version to start simulation when event loop is available"""
        if self.demo_mode and not hasattr(self, '_simulation_started'):
            asyncio.create_task(self._simulate_user_activity())
            self._simulation_started = True
            logger.info("High-frequency user activity simulation started (10-100 events/sec)")

    async def _simulate_user_activity(self):
        """Simulate high-frequency user activity (10-100 events per second)"""
        while self.demo_mode:
            try:
                # Generate bursts of activity to simulate realistic enterprise usage
                # Base sleep time: 0.01-0.1 seconds (10-100 events per second)
                base_sleep = random.uniform(0.01, 0.1)

                # Adjust based on time of day
                current_hour = datetime.now().hour
                if 9 <= current_hour <= 17:  # Business hours
                    sleep_time = base_sleep * random.uniform(0.3, 0.8)  # Higher frequency
                    burst_chance = 0.4  # 40% chance of bursts
                elif 6 <= current_hour <= 21:  # Extended hours
                    sleep_time = base_sleep * random.uniform(0.8, 1.2)  # Normal frequency
                    burst_chance = 0.2  # 20% chance of bursts
                else:  # Off hours
                    sleep_time = base_sleep * random.uniform(2, 5)  # Lower frequency
                    burst_chance = 0.05  # 5% chance of bursts

                await asyncio.sleep(sleep_time)

                # Pick multiple users for concurrent activity simulation
                active_users = [u for u in self.users.values() if u.status == UserStatus.ACTIVE]
                if not active_users:
                    continue

                # Generate 1-5 concurrent activities
                concurrent_count = random.choices([1, 2, 3, 4, 5], weights=[40, 25, 20, 10, 5])[0]

                tasks = []
                for _ in range(concurrent_count):
                    user = random.choice(active_users)

                    # Most traffic is normal queries (95%), small fraction are alerts (5%)
                    if random.random() < 0.95:
                        # Normal traffic
                        if random.random() < 0.8:  # 80% queries, 20% other activities
                            tasks.append(self._simulate_user_query(user, is_alert=False))
                        else:
                            tasks.append(self._simulate_other_activity(user, is_alert=False))
                    else:
                        # Alert traffic (5% of total)
                        if random.random() < 0.7:  # 70% alert queries, 30% other alert activities
                            tasks.append(self._simulate_user_query(user, is_alert=True))
                        else:
                            tasks.append(self._simulate_other_activity(user, is_alert=True))

                # Execute concurrent activities
                if tasks:
                    await asyncio.gather(*tasks)

                # Occasional system events (2% of cycles)
                if random.random() < 0.02:
                    asyncio.create_task(self._simulate_system_event())

                # Burst activity during peak times
                if random.random() < burst_chance:
                    # Generate a burst of 5-15 rapid events
                    burst_count = random.randint(5, 15)
                    burst_tasks = []
                    for _ in range(burst_count):
                        user = random.choice(active_users)
                        if random.random() < 0.9:
                            burst_tasks.append(self._simulate_user_query(user))
                        else:
                            burst_tasks.append(self._simulate_other_activity(user))

                    # Execute burst with slight delays
                    for i, task in enumerate(burst_tasks):
                        if i > 0:
                            await asyncio.sleep(random.uniform(0.02, 0.1))
                        asyncio.create_task(task)

            except Exception as e:
                logger.error(f"Error in user activity simulation: {e}")
                await asyncio.sleep(5)  # Short wait on error

    async def _simulate_user_query(self, user: User, is_alert: bool = False):
        """Simulate a single user query"""
        # Import here to avoid circular imports
        from activity_tracker import activity_tracker, ActivityType, ActivitySeverity

        # Choose query type based on user patterns
        query_types = list(user.access_patterns["query_types"].keys())
        if query_types:
            query_type = random.choice(query_types)
        else:
            query_type = "basic_query"

        # Generate simulated query
        if is_alert:
            # Alert queries are more suspicious/dangerous
            alert_queries = {
                "audit": "SELECT * FROM sensitive_audit_logs WHERE user_data LIKE '%ssn%'",
                "monitoring": "SELECT COUNT(*) FROM system_metrics WHERE status = 'critical_failure'",
                "analytics": "SELECT ssn, credit_card FROM customer_data GROUP BY department",
                "reporting": "SELECT * FROM confidential_reports WHERE classification = 'secret'",
                "lookup": "SELECT password, ssn FROM users WHERE role = 'admin'",
                "configuration": "DROP TABLE user_permissions CASCADE",
                "basic_query": "SELECT * FROM production.sensitive_data"
            }
            query = alert_queries.get(query_type, "SELECT * FROM restricted.pii_data")
            block_probability = 0.8 + user.risk_score * 0.15  # High chance of blocking alerts
        else:
            # Normal queries
            sample_queries = {
                "audit": "SELECT * FROM audit_logs WHERE timestamp > NOW() - INTERVAL '1 hour'",
                "monitoring": "SELECT COUNT(*) FROM system_metrics WHERE status = 'error'",
                "analytics": "SELECT department, AVG(revenue) FROM sales_data GROUP BY department",
                "reporting": "SELECT * FROM monthly_reports WHERE month = CURRENT_MONTH",
                "lookup": "SELECT * FROM users WHERE id = 'specific_user'",
                "configuration": "UPDATE system_config SET value = 'new_value' WHERE key = 'setting'",
                "basic_query": "SELECT * FROM public.data_table LIMIT 10"
            }
            query = sample_queries.get(query_type, "SELECT * FROM public.example LIMIT 5")

            # Normal probability for regular queries
            block_probability = user.risk_score * 0.05
            if "DROP" in query.upper() or "DELETE" in query.upper():
                block_probability += 0.3

        is_blocked = random.random() < block_probability

        # Update user stats
        async with self._lock:
            user.total_queries += 1
            user.last_active = datetime.now(timezone.utc)

            if is_blocked:
                user.blocked_queries += 1
            else:
                user.approved_queries += 1

        # Track in activity system with full user context
        if is_blocked:
            severity = ActivitySeverity.CRITICAL if is_alert else ActivitySeverity.WARNING
            await activity_tracker.track_event(
                ActivityType.QUERY_BLOCKED,
                f"{'Alert: ' if is_alert else ''}Query blocked for {user.name}: {query[:50]}...",
                severity,
                {
                    "user_id": user.id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "user_role": user.role.value,
                    "user_department": user.department,
                    "query": query,
                    "query_type": query_type,
                    "risk_score": user.risk_score,
                    "is_alert": is_alert,
                    "simulated": True
                },
                subject_id=user.id,
                tool_name="redshift_execute_query"
            )
        else:
            severity = ActivitySeverity.INFO if is_alert else ActivitySeverity.SUCCESS
            await activity_tracker.track_event(
                ActivityType.QUERY_EXECUTED,
                f"{'Alert query executed by' if is_alert else 'Query executed by'} {user.name}: {query[:50]}...",
                severity,
                {
                    "user_id": user.id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "user_role": user.role.value,
                    "user_department": user.department,
                    "query": query,
                    "query_type": query_type,
                    "is_alert": is_alert,
                    "simulated": True
                },
                subject_id=user.id,
                tool_name="redshift_execute_query"
            )

    async def _simulate_other_activity(self, user: User, is_alert: bool = False):
        """Simulate various non-query activities"""
        # Import here to avoid circular imports
        from activity_tracker import activity_tracker, ActivityType, ActivitySeverity

        # Different activity types based on user role
        activity_options = {
            UserRole.SECURITY_ANALYST: [
                ("security_scan", "Security scan completed", ActivityType.SECURITY_VIOLATION, ActivitySeverity.INFO),
                ("policy_review", "Policy compliance review", ActivityType.PII_ACCESS_ATTEMPTED, ActivitySeverity.WARNING),
                ("audit_review", "Audit log review completed", ActivityType.AUDIT_EXPORTED, ActivitySeverity.INFO),
                ("threat_detection", "Threat detection alert", ActivityType.SECURITY_VIOLATION, ActivitySeverity.WARNING)
            ],
            UserRole.ADMIN: [
                ("system_config", "System configuration updated", ActivityType.POLICY_UPDATED, ActivitySeverity.INFO),
                ("user_management", "User permissions modified", ActivityType.POLICY_CREATED, ActivitySeverity.INFO),
                ("backup_verification", "Backup verification completed", ActivityType.AUDIT_EXPORTED, ActivitySeverity.SUCCESS),
                ("maintenance_task", "Maintenance task executed", ActivityType.SCHEMA_CHANGE_ATTEMPTED, ActivitySeverity.WARNING)
            ],
            UserRole.BUSINESS_LEAD: [
                ("report_generation", "Business report generated", ActivityType.APPROVAL_REQUESTED, ActivitySeverity.INFO),
                ("approval_decision", "Request approval granted", ActivityType.APPROVAL_GRANTED, ActivitySeverity.SUCCESS),
                ("workflow_review", "Workflow approval review", ActivityType.APPROVAL_REQUESTED, ActivitySeverity.INFO),
                ("denial_decision", "Request approval denied", ActivityType.APPROVAL_DENIED, ActivitySeverity.WARNING)
            ],
            UserRole.AGENT: [
                ("automation_run", "Automated task execution", ActivityType.QUERY_EXECUTED, ActivitySeverity.SUCCESS),
                ("data_processing", "Data processing pipeline", ActivityType.QUERY_EXECUTED, ActivitySeverity.INFO),
                ("ml_pipeline", "ML pipeline execution", ActivityType.QUERY_EXECUTED, ActivitySeverity.SUCCESS),
                ("integration_task", "System integration task", ActivityType.QUERY_EXECUTED, ActivitySeverity.INFO)
            ],
            UserRole.CISO: [
                ("policy_creation", "Security policy created", ActivityType.POLICY_CREATED, ActivitySeverity.INFO),
                ("emergency_review", "Emergency security review", ActivityType.EMERGENCY_BLOCK, ActivitySeverity.CRITICAL),
                ("compliance_audit", "Compliance audit initiated", ActivityType.AUDIT_EXPORTED, ActivitySeverity.INFO),
                ("governance_review", "Governance framework review", ActivityType.POLICY_UPDATED, ActivitySeverity.INFO)
            ],
            UserRole.USER: [
                ("data_export", "Data export completed", ActivityType.QUERY_EXECUTED, ActivitySeverity.SUCCESS),
                ("report_download", "Report download", ActivityType.QUERY_EXECUTED, ActivitySeverity.INFO),
                ("dashboard_view", "Dashboard accessed", ActivityType.QUERY_EXECUTED, ActivitySeverity.INFO)
            ]
        }

        # Get activities for this user role
        role_activities = activity_options.get(user.role, activity_options[UserRole.USER])
        activity_name, message, activity_type, severity = random.choice(role_activities)

        # If this is an alert activity, escalate severity and modify message
        if is_alert:
            severity = ActivitySeverity.CRITICAL if severity == ActivitySeverity.WARNING else ActivitySeverity.WARNING
            message = f"Alert: {message}"
            activity_name = f"alert_{activity_name}"

        # Sometimes generate approval workflows
        if random.random() < 0.15:  # 15% chance
            await self._simulate_approval_workflow(user)
            return

        # Sometimes simulate agent connections/disconnections
        if random.random() < 0.05:  # 5% chance
            connected = random.choice([True, False])
            alert_prefix = "Alert: " if is_alert else ""
            await activity_tracker.track_event(
                ActivityType.AGENT_CONNECTED if connected else ActivityType.AGENT_DISCONNECTED,
                f"{alert_prefix}Agent {user.name} {'connected' if connected else 'disconnected'}",
                ActivitySeverity.WARNING if is_alert else ActivitySeverity.INFO,
                {
                    "user_id": user.id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "user_role": user.role.value,
                    "user_department": user.department,
                    "is_alert": is_alert,
                    "simulated": True,
                    "agent_type": user.role.value
                },
                subject_id=user.id,
                tool_name="agent_connection"
            )
            return

        # Track the selected activity with full user context
        await activity_tracker.track_event(
            activity_type,
            f"{message} by {user.name}",
            severity,
            {
                "user_id": user.id,
                "user_name": user.name,
                "user_email": user.email,
                "user_role": user.role.value,
                "user_department": user.department,
                "activity": activity_name,
                "is_alert": is_alert,
                "simulated": True,
                "subject_id": user.id
            },
            subject_id=user.id,
            tool_name=activity_name
        )

    async def _simulate_approval_workflow(self, user: User):
        """Simulate an approval workflow scenario"""
        from activity_tracker import activity_tracker, ActivityType, ActivitySeverity

        # Simulate approval request first
        tools = ["redshift_execute_query", "user_management", "data_export", "system_config"]
        tool_name = random.choice(tools)
        risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        risk_level = random.choice(risk_levels)

        await activity_tracker.track_event(
            ActivityType.APPROVAL_REQUESTED,
            f"Approval requested for {tool_name} by {user.name}",
            ActivitySeverity.WARNING if risk_level in ["HIGH", "CRITICAL"] else ActivitySeverity.INFO,
            {
                "user_id": user.id,
                "user_name": user.name,
                "user_email": user.email,
                "user_role": user.role.value,
                "user_department": user.department,
                "tool": tool_name,
                "risk_level": risk_level,
                "simulated": True
            },
            subject_id=user.id,
            tool_name=tool_name
        )

        # Wait a random amount of time before approval decision (1-8 seconds)
        await asyncio.sleep(random.uniform(1, 8))

        # Business leads and CISO more likely to approve
        if user.role in [UserRole.BUSINESS_LEAD, UserRole.CISO]:
            approved = random.random() < 0.8  # 80% approval rate
        else:
            approved = random.random() < 0.6  # 60% approval rate

        decision_type = ActivityType.APPROVAL_GRANTED if approved else ActivityType.APPROVAL_DENIED
        decision_severity = ActivitySeverity.SUCCESS if approved else ActivitySeverity.WARNING

        await activity_tracker.track_event(
            decision_type,
            f"Request {'approved' if approved else 'denied'} by {user.name}",
            decision_severity,
            {
                "user_id": user.id,
                "user_name": user.name,
                "user_email": user.email,
                "user_role": user.role.value,
                "user_department": user.department,
                "tool": tool_name,
                "decision": "APPROVE" if approved else "DENY",
                "simulated": True
            },
            subject_id=user.id,
            tool_name=tool_name
        )

    async def _simulate_system_event(self):
        """Simulate system-level events not tied to specific users"""
        from activity_tracker import activity_tracker, ActivityType, ActivitySeverity

        system_events = [
            ("rate_limit_check", "Rate limit monitoring check", ActivityType.RATE_LIMIT_WARNING, ActivitySeverity.INFO),
            ("system_backup", "Automated system backup", ActivityType.AUDIT_EXPORTED, ActivitySeverity.SUCCESS),
            ("security_scan", "Automated security scan", ActivityType.SECURITY_VIOLATION, ActivitySeverity.INFO),
            ("policy_sync", "Policy synchronization", ActivityType.POLICY_UPDATED, ActivitySeverity.INFO),
            ("schema_validation", "Database schema validation", ActivityType.SCHEMA_CHANGE_ATTEMPTED, ActivitySeverity.INFO),
            ("emergency_alert", "Emergency security alert", ActivityType.EMERGENCY_BLOCK, ActivitySeverity.CRITICAL),
            ("audit_cleanup", "Audit log cleanup", ActivityType.AUDIT_EXPORTED, ActivitySeverity.INFO),
            ("system_health", "System health check", ActivityType.QUERY_EXECUTED, ActivitySeverity.SUCCESS),
            ("connection_monitor", "Connection monitoring", ActivityType.AGENT_CONNECTED, ActivitySeverity.INFO),
            ("policy_violation", "Policy violation detected", ActivityType.SECURITY_VIOLATION, ActivitySeverity.WARNING)
        ]

        event_name, message, activity_type, severity = random.choice(system_events)

        # Add some variability to system events
        system_details = {
            "event_type": "system",
            "automated": True,
            "simulated": True,
            "system_component": random.choice(["gateway", "database", "auth_service", "monitor", "audit_service"]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Some events might be more critical during certain times
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:  # Off hours
            if event_name in ["emergency_alert", "security_scan"]:
                severity = ActivitySeverity.WARNING

        await activity_tracker.track_event(
            activity_type,
            f"System: {message}",
            severity,
            system_details,
            subject_id="system",
            tool_name=event_name
        )

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)

    async def get_all_users(self) -> List[User]:
        """Get all users"""
        return list(self.users.values())

    async def get_active_users(self) -> List[User]:
        """Get only active users"""
        return [u for u in self.users.values() if u.status == UserStatus.ACTIVE]

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user (real mode only)"""
        if self.demo_mode:
            raise ValueError("Cannot create real users in demo mode")

        async with self._lock:
            user = User(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                role=UserRole(user_data["role"]),
                status=UserStatus(user_data.get("status", "active")),
                permissions=PermissionLevel(user_data["permissions"]),
                created_at=datetime.now(timezone.utc),
                last_active=datetime.now(timezone.utc),
                department=user_data.get("department", "")
            )

            self.users[user.id] = user
            self._save_persistent_data()  # Persist new user
            return user

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[User]:
        """Update user data"""
        async with self._lock:
            user = self.users.get(user_id)
            if not user:
                return None

            for key, value in updates.items():
                if hasattr(user, key):
                    if key in ["role", "status", "permissions"]:
                        # Handle enums
                        enum_map = {
                            "role": UserRole,
                            "status": UserStatus,
                            "permissions": PermissionLevel
                        }
                        setattr(user, key, enum_map[key](value))
                    else:
                        setattr(user, key, value)

            self._save_persistent_data()  # Persist user updates
            return user

    async def delete_user(self, user_id: str) -> bool:
        """Delete user (real mode only)"""
        if self.demo_mode:
            raise ValueError("Cannot delete demo users")

        async with self._lock:
            if user_id in self.users:
                del self.users[user_id]
                self._save_persistent_data()  # Persist user deletion
                return True
            return False

    async def track_user_activity(self, user_id: str, activity_type: str, details: Dict[str, Any]):
        """Track user activity"""
        async with self._lock:
            user = self.users.get(user_id)
            if user:
                user.last_active = datetime.now(timezone.utc)

                # Update activity patterns
                if activity_type == "query_execution":
                    user.total_queries += 1
                    if details.get("approved", False):
                        user.approved_queries += 1
                    else:
                        user.blocked_queries += 1

                # Store activity pattern
                self.activity_patterns[user_id].append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": activity_type,
                    "details": details
                })

                # Keep only recent patterns (last 100)
                if len(self.activity_patterns[user_id]) > 100:
                    self.activity_patterns[user_id] = self.activity_patterns[user_id][-100:]

                # Save activity patterns periodically (every 10 activities)
                total_patterns = sum(len(patterns) for patterns in self.activity_patterns.values())
                if total_patterns % 10 == 0:
                    self._save_persistent_data()

    async def get_user_stats(self) -> Dict[str, Any]:
        """Get aggregate user statistics"""
        total_users = len(self.users)
        active_users = len([u for u in self.users.values() if u.status == UserStatus.ACTIVE])
        inactive_users = len([u for u in self.users.values() if u.status == UserStatus.INACTIVE])
        suspended_users = len([u for u in self.users.values() if u.status == UserStatus.SUSPENDED])

        total_queries = sum(u.total_queries for u in self.users.values())
        total_approved = sum(u.approved_queries for u in self.users.values())
        total_blocked = sum(u.blocked_queries for u in self.users.values())

        # Role distribution
        role_counts = defaultdict(int)
        for user in self.users.values():
            role_counts[user.role.value] += 1

        # Department distribution
        dept_counts = defaultdict(int)
        for user in self.users.values():
            if user.department:
                dept_counts[user.department] += 1

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "suspended_users": suspended_users,
            "total_queries": total_queries,
            "total_approved": total_approved,
            "total_blocked": total_blocked,
            "approval_rate": total_approved / max(1, total_queries),
            "role_distribution": dict(role_counts),
            "department_distribution": dict(dept_counts),
            "demo_mode": self.demo_mode
        }

    async def search_users(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        """Search users by name, email, or other criteria"""
        results = []
        query_lower = query.lower()

        for user in self.users.values():
            # Text search
            if (query_lower in user.name.lower() or
                query_lower in user.email.lower() or
                query_lower in user.id.lower() or
                query_lower in user.department.lower()):

                # Apply filters if provided
                if filters:
                    if filters.get("role") and user.role.value != filters["role"]:
                        continue
                    if filters.get("status") and user.status.value != filters["status"]:
                        continue
                    if filters.get("department") and user.department != filters["department"]:
                        continue

                results.append(user)

        return results

    def get_demo_mode(self) -> bool:
        """Check if running in demo mode"""
        return self.demo_mode

    async def reset_demo_data(self):
        """Reset demo data (demo mode only)"""
        if not self.demo_mode:
            raise ValueError("Can only reset data in demo mode")

        async with self._lock:
            self.users.clear()
            self.activity_patterns.clear()
            self._initialize_demo_users()
            self._save_persistent_data()  # Persist the reset
            logger.info("Demo data reset successfully")

    def _load_persistent_data(self):
        """Load user data and activity patterns from storage"""
        try:
            # Load users
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    for user_data in users_data:
                        user = User.from_dict(user_data)
                        self.users[user.id] = user
                logger.info(f"Loaded {len(self.users)} users from persistent storage")

            # Load activity patterns
            if os.path.exists(self.activity_patterns_file):
                with open(self.activity_patterns_file, 'r') as f:
                    self.activity_patterns = defaultdict(list, json.load(f))
                total_patterns = sum(len(patterns) for patterns in self.activity_patterns.values())
                logger.info(f"Loaded {total_patterns} activity patterns from persistent storage")

        except Exception as e:
            logger.error(f"Error loading persistent data: {e}")
            # Continue with empty data rather than failing

    def _save_persistent_data(self):
        """Save user data and activity patterns to storage"""
        try:
            # Save users
            users_data = [user.to_dict() for user in self.users.values()]
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=2)

            # Save activity patterns
            with open(self.activity_patterns_file, 'w') as f:
                json.dump(dict(self.activity_patterns), f, indent=2)

            logger.debug(f"Saved {len(self.users)} users and activity patterns to persistent storage")

        except (OSError, PermissionError, FileNotFoundError):
            # Silently skip persistence in test environments
            logger.debug("Persistence disabled - skipping save operation")
        except Exception as e:
            logger.error(f"Error saving persistent data: {e}")

    async def _save_async(self):
        """Async wrapper for save operation"""
        await asyncio.get_event_loop().run_in_executor(None, self._save_persistent_data)

# Global store instance
user_store = UserDataStore()