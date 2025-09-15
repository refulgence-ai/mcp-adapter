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

        # Initialize with demo data if in demo mode
        if self.demo_mode:
            self._initialize_demo_users()

        logger.info(f"UserDataStore initialized in {'demo' if self.demo_mode else 'real'} mode")

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
                # Event loop not available yet - will try again later
                pass

    async def _simulate_user_activity(self):
        """Simulate ongoing user activity for demo purposes"""
        while self.demo_mode:
            try:
                # Simulate user activity every 10-30 seconds
                await asyncio.sleep(random.randint(10, 30))

                # Pick a random active user
                active_users = [u for u in self.users.values() if u.status == UserStatus.ACTIVE]
                if not active_users:
                    continue

                user = random.choice(active_users)

                # Simulate query activity
                current_hour = datetime.now().hour
                if current_hour in user.access_patterns["peak_hours"]:
                    # Higher activity during peak hours
                    if random.random() < 0.3:  # 30% chance during peak
                        await self._simulate_user_query(user)
                else:
                    # Lower activity during off-peak
                    if random.random() < 0.1:  # 10% chance during off-peak
                        await self._simulate_user_query(user)

            except Exception as e:
                logger.error(f"Error in user activity simulation: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _simulate_user_query(self, user: User):
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

        # Determine if query should be blocked (based on user risk score and query type)
        block_probability = user.risk_score * 0.1
        if "DROP" in query.upper() or "DELETE" in query.upper():
            block_probability += 0.8

        is_blocked = random.random() < block_probability

        # Update user stats
        async with self._lock:
            user.total_queries += 1
            user.last_active = datetime.now(timezone.utc)

            if is_blocked:
                user.blocked_queries += 1
            else:
                user.approved_queries += 1

        # Track in activity system
        if is_blocked:
            await activity_tracker.track_event(
                ActivityType.QUERY_BLOCKED,
                f"Simulated query blocked for {user.name}",
                ActivitySeverity.WARNING,
                {"user_id": user.id, "query": query, "simulated": True}
            )
        else:
            await activity_tracker.track_event(
                ActivityType.QUERY_EXECUTED,
                f"Simulated query executed by {user.name}",
                ActivitySeverity.SUCCESS,
                {"user_id": user.id, "query": query, "simulated": True}
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

            return user

    async def delete_user(self, user_id: str) -> bool:
        """Delete user (real mode only)"""
        if self.demo_mode:
            raise ValueError("Cannot delete demo users")

        async with self._lock:
            if user_id in self.users:
                del self.users[user_id]
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
            logger.info("Demo data reset successfully")

# Global store instance
user_store = UserDataStore()