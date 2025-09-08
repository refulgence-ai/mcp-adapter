"""
Refulgence Governance Engine - Multi-Stakeholder AI Agent Control System

This module implements a policy-as-code governance system where organizational 
stakeholders control access permissions for developers and their AI agents.

Core Philosophy: "We trust the developer, but we don't trust their tools"
"""

import json
import time
import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class SubjectType(Enum):
    DEVELOPER = "developer"
    CODING_AGENT = "coding_agent"

class PermissionType(Enum):
    DATABASE_ADMIN_RIGHTS = "database_admin_rights"
    PRODUCTION_DATA_ACCESS = "production_data_access"
    PII_SENSITIVE_DATA = "pii_sensitive_data"
    SCHEMA_MODIFICATION = "schema_modification"
    QUERY_EXECUTION = "query_execution"
    USER_MANAGEMENT = "user_management"
    EMERGENCY_ACCESS = "emergency_access"

class VoteDecision(Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    PENDING = "PENDING"

class StakeholderRole(Enum):
    CISO = "CISO"
    ENTERPRISE_DEFAULT = "ENTERPRISE_DEFAULT"
    BUSINESS_LEAD = "BUSINESS_LEAD"
    IT_ADMIN = "IT_ADMIN"
    PROJECT_OWNER = "PROJECT_OWNER"
    END_USER = "END_USER"

# Governance Configuration
STAKEHOLDERS = {
    StakeholderRole.CISO: {
        "role": "security_authority",
        "description": "Chief Information Security Officer",
        "voting_weight": 1.0,
        "veto_power": ["user_management", "emergency_access"],
        "auto_vote": None
    },
    StakeholderRole.ENTERPRISE_DEFAULT: {
        "role": "enterprise_governance",
        "description": "Default enterprise security policies",
        "voting_weight": 1.0,
        "auto_vote": VoteDecision.DENY,  # Conservative by default
        "scope": ["all"]
    },
    StakeholderRole.BUSINESS_LEAD: {
        "role": "business_owner",
        "description": "Business unit leader owning the data",
        "voting_weight": 1.0,
        "scope": ["production_data", "pii_data"]
    },
    StakeholderRole.IT_ADMIN: {
        "role": "technical_authority", 
        "description": "IT administration team",
        "voting_weight": 1.0,
        "override_for": ["emergency_situations"]
    },
    StakeholderRole.PROJECT_OWNER: {
        "role": "project_authority",
        "description": "Specific project owner",
        "voting_weight": 0.5,  # Limited influence
        "scope": ["project_specific_data"]
    },
    StakeholderRole.END_USER: {
        "role": "end_user_representative",
        "description": "End user data owner",
        "voting_weight": 0.5,
        "scope": ["development_environment"]
    }
}

# Permission Type Registry
PERMISSION_TYPES = {
    PermissionType.DATABASE_ADMIN_RIGHTS: {
        "mcp_tools": ["redshift_create_user", "redshift_drop_database", "redshift_alter_cluster"],
        "eligible_voters": [StakeholderRole.CISO, StakeholderRole.ENTERPRISE_DEFAULT, StakeholderRole.IT_ADMIN],
        "risk_level": "CRITICAL",
        "description": "SUPERUSER privileges, user management, cluster configuration"
    },
    PermissionType.PRODUCTION_DATA_ACCESS: {
        "mcp_tools": ["redshift_execute_query", "redshift_list_tables"],
        "eligible_voters": [StakeholderRole.CISO, StakeholderRole.ENTERPRISE_DEFAULT, StakeholderRole.BUSINESS_LEAD, StakeholderRole.IT_ADMIN],
        "risk_level": "HIGH",
        "query_filters": ["WHERE", "SELECT", "JOIN"]  # Allowed operations
    },
    PermissionType.PII_SENSITIVE_DATA: {
        "mcp_tools": ["redshift_execute_query{table:contains('customer')}", "redshift_export_data"],
        "eligible_voters": [StakeholderRole.CISO, StakeholderRole.BUSINESS_LEAD],
        "risk_level": "CRITICAL",
        "requires_legal": True
    },
    PermissionType.SCHEMA_MODIFICATION: {
        "mcp_tools": ["redshift_create_table", "redshift_alter_table", "redshift_drop_table"],
        "eligible_voters": [StakeholderRole.CISO, StakeholderRole.ENTERPRISE_DEFAULT, StakeholderRole.IT_ADMIN],
        "risk_level": "HIGH",
        "requires_approval_workflow": True
    },
    PermissionType.QUERY_EXECUTION: {
        "mcp_tools": ["redshift_execute_query"],
        "eligible_voters": [StakeholderRole.ENTERPRISE_DEFAULT, StakeholderRole.IT_ADMIN],
        "risk_level": "MEDIUM",
        "rate_limits": {"developer": 1000, "agent": 100}
    }
}

# Approval Matrix - defines voting thresholds
APPROVAL_MATRIX = {
    SubjectType.DEVELOPER: {
        PermissionType.DATABASE_ADMIN_RIGHTS: {"required": 2, "total": 3, "additional": []},
        PermissionType.PRODUCTION_DATA_ACCESS: {"required": 2, "total": 4, "additional": []},
        PermissionType.PII_SENSITIVE_DATA: {"required": 1, "total": 2, "additional": []},
        PermissionType.SCHEMA_MODIFICATION: {"required": 1, "total": 3, "additional": []},
        PermissionType.QUERY_EXECUTION: {"required": 1, "total": 2, "additional": []}
    },
    SubjectType.CODING_AGENT: {
        PermissionType.DATABASE_ADMIN_RIGHTS: {"required": 3, "total": 3, "additional": ["external_audit"]},
        PermissionType.PRODUCTION_DATA_ACCESS: {"required": 4, "total": 4, "additional": ["time_limit:1h"]},
        PermissionType.PII_SENSITIVE_DATA: {"required": 2, "total": 2, "additional": ["legal_review"]},
        PermissionType.SCHEMA_MODIFICATION: {"required": 3, "total": 3, "additional": ["approval_workflow"]},
        PermissionType.QUERY_EXECUTION: {"required": 2, "total": 2, "additional": ["rate_limit:100/hour"]},
        # Special restrictions for agents
        PermissionType.USER_MANAGEMENT: "NEVER_ALLOWED",
        PermissionType.EMERGENCY_ACCESS: "NEVER_ALLOWED"
    }
}

# ============================================================================
# ARGUMENT INSPECTION FRAMEWORK
# ============================================================================

class SecurityRisk(Enum):
    """Security risk levels for tool call arguments"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class InspectionResult:
    """Result of argument inspection"""
    risk_level: SecurityRisk
    permission_required: PermissionType
    violations: List[str]
    details: Dict[str, Any]
    allow_override: bool = True

class ArgumentInspector(ABC):
    """Base class for tool-specific argument inspectors"""
    
    @abstractmethod
    def inspect(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> InspectionResult:
        """Inspect tool arguments and return security assessment"""
        pass
    
    @abstractmethod
    def get_supported_tools(self) -> List[str]:
        """Return list of tool names this inspector supports"""
        pass

class SQLQueryInspector(ArgumentInspector):
    """Specialized inspector for SQL query operations"""
    
    def __init__(self):
        # Predefined risk patterns with explanations
        self.destructive_patterns = [
            (r"DROP\s+(DATABASE|SCHEMA|TABLE|INDEX|VIEW)", "Destructive DROP operation"),
            (r"DELETE\s+FROM\s+\w+\s*(WHERE\s+1\s*=\s*1|$)", "DELETE without proper WHERE clause"),
            (r"TRUNCATE\s+TABLE", "TRUNCATE operation removes all data"),
            (r"ALTER\s+TABLE\s+\w+\s+DROP\s+COLUMN", "Column deletion"),
            (r"UPDATE\s+\w+\s+SET\s+.*\s*(WHERE\s+1\s*=\s*1|$)", "UPDATE without proper WHERE clause")
        ]
        
        self.pii_patterns = [
            (r"SELECT.*\b(SSN|SOCIAL_SECURITY|CREDIT_CARD|PHONE|ADDRESS)\b", "Direct PII column access"),
            (r"FROM\s+\w*CUSTOMER\w*", "Customer data table access"),
            (r"FROM\s+\w*USER\w*", "User data table access"),
            (r"FROM\s+\w*PERSONAL\w*", "Personal information table access"),
            (r"FROM\s+\w*PII\w*", "PII-designated table access")
        ]
        
        self.schema_patterns = [
            (r"CREATE\s+(TABLE|INDEX|VIEW|DATABASE|SCHEMA)", "Schema creation"),
            (r"ALTER\s+(TABLE|INDEX|VIEW|DATABASE|SCHEMA)", "Schema modification"),
            (r"DROP\s+(TABLE|INDEX|VIEW)", "Schema object deletion"),
            (r"GRANT\s+", "Permission granting"),
            (r"REVOKE\s+", "Permission revocation")
        ]
        
        self.injection_patterns = [
            (r"'.*OR.*'.*=.*'", "Possible SQL injection pattern"),
            (r"UNION\s+SELECT", "UNION-based injection attempt"),
            (r";.*DROP", "Statement chaining with destructive operation"),
            (r"--.*", "SQL comment injection"),
            (r"/\*.*\*/", "Block comment injection")
        ]
    
    def inspect(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> InspectionResult:
        """Inspect SQL query for security risks"""
        violations = []
        risk_level = SecurityRisk.LOW
        permission_required = PermissionType.QUERY_EXECUTION
        
        if "query" not in arguments:
            return InspectionResult(
                risk_level=SecurityRisk.NONE,
                permission_required=PermissionType.QUERY_EXECUTION,
                violations=["No query provided"],
                details={"query": None}
            )
        
        query = arguments["query"].upper().strip()
        original_query = arguments["query"]
        
        # Check for destructive operations
        for pattern, description in self.destructive_patterns:
            if re.search(pattern, query):
                violations.append(f"CRITICAL: {description}")
                risk_level = SecurityRisk.CRITICAL
                permission_required = PermissionType.DATABASE_ADMIN_RIGHTS
        
        # Check for PII access
        for pattern, description in self.pii_patterns:
            if re.search(pattern, query):
                violations.append(f"HIGH: {description}")
                if risk_level.value != SecurityRisk.CRITICAL.value:
                    risk_level = SecurityRisk.HIGH
                    permission_required = PermissionType.PII_SENSITIVE_DATA
        
        # Check for schema modifications
        for pattern, description in self.schema_patterns:
            if re.search(pattern, query):
                violations.append(f"HIGH: {description}")
                if risk_level.value not in [SecurityRisk.CRITICAL.value, SecurityRisk.HIGH.value]:
                    risk_level = SecurityRisk.HIGH
                    permission_required = PermissionType.SCHEMA_MODIFICATION
        
        # Check for SQL injection patterns
        for pattern, description in self.injection_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                violations.append(f"CRITICAL: {description}")
                risk_level = SecurityRisk.CRITICAL
                permission_required = PermissionType.DATABASE_ADMIN_RIGHTS
        
        # Check for data modification operations
        if re.search(r"(INSERT|UPDATE|DELETE)\s+", query):
            violations.append("MEDIUM: Data modification operation")
            if risk_level.value == SecurityRisk.LOW.value:
                risk_level = SecurityRisk.MEDIUM
                permission_required = PermissionType.PRODUCTION_DATA_ACCESS
        
        # Check for bulk operations
        if re.search(r"SELECT\s+\*\s+FROM", query) and not re.search(r"LIMIT\s+\d+", query):
            violations.append("MEDIUM: Unrestricted SELECT * without LIMIT")
            if risk_level.value == SecurityRisk.LOW.value:
                risk_level = SecurityRisk.MEDIUM
        
        return InspectionResult(
            risk_level=risk_level,
            permission_required=permission_required,
            violations=violations,
            details={
                "query": original_query,
                "query_length": len(original_query),
                "tables_accessed": self._extract_table_names(query),
                "operations": self._extract_operations(query)
            }
        )
    
    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from SQL query"""
        tables = []
        # Simple regex to find table names after FROM and JOIN
        from_matches = re.findall(r"FROM\s+(\w+)", query)
        join_matches = re.findall(r"JOIN\s+(\w+)", query)
        tables.extend(from_matches)
        tables.extend(join_matches)
        return list(set(tables))
    
    def _extract_operations(self, query: str) -> List[str]:
        """Extract SQL operations from query"""
        operations = []
        operation_patterns = [
            r"SELECT", r"INSERT", r"UPDATE", r"DELETE", r"CREATE", 
            r"ALTER", r"DROP", r"GRANT", r"REVOKE", r"TRUNCATE"
        ]
        for pattern in operation_patterns:
            if re.search(pattern, query):
                operations.append(pattern.lower())
        return operations
    
    def get_supported_tools(self) -> List[str]:
        return ["redshift_execute_query", "execute_query", "run_sql", "query_database"]

class FileOperationInspector(ArgumentInspector):
    """Inspector for file system operations"""
    
    def __init__(self):
        self.dangerous_paths = [
            r"/etc/passwd", r"/etc/shadow", r"/etc/hosts",
            r"/root/", r"/home/\w+/\.ssh/", r"/var/log/",
            r"\.key$", r"\.pem$", r"\.p12$"
        ]
        
        self.sensitive_extensions = [
            ".key", ".pem", ".p12", ".crt", ".cer", ".config", ".env"
        ]
    
    def inspect(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> InspectionResult:
        violations = []
        risk_level = SecurityRisk.LOW
        
        file_path = arguments.get("file_path", arguments.get("path", ""))
        content = arguments.get("content", "")
        
        # Check for dangerous file paths
        for pattern in self.dangerous_paths:
            if re.search(pattern, file_path, re.IGNORECASE):
                violations.append(f"CRITICAL: Access to sensitive system path: {file_path}")
                risk_level = SecurityRisk.CRITICAL
        
        # Check for sensitive file extensions
        for ext in self.sensitive_extensions:
            if file_path.lower().endswith(ext):
                violations.append(f"HIGH: Sensitive file extension: {ext}")
                if risk_level.value != SecurityRisk.CRITICAL.value:
                    risk_level = SecurityRisk.HIGH
        
        # Check for credential patterns in content
        if content:
            credential_patterns = [
                (r"password\s*=\s*['\"].*['\"]", "Password in content"),
                (r"api[_-]key\s*=\s*['\"].*['\"]", "API key in content"),
                (r"secret\s*=\s*['\"].*['\"]", "Secret in content"),
                (r"-----BEGIN.*PRIVATE KEY-----", "Private key in content")
            ]
            
            for pattern, description in credential_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append(f"CRITICAL: {description}")
                    risk_level = SecurityRisk.CRITICAL
        
        return InspectionResult(
            risk_level=risk_level,
            permission_required=PermissionType.PRODUCTION_DATA_ACCESS,
            violations=violations,
            details={
                "file_path": file_path,
                "content_length": len(content),
                "operation": tool_name
            }
        )
    
    def get_supported_tools(self) -> List[str]:
        return ["read_file", "write_file", "upload_file", "download_file", "list_files"]

class NetworkOperationInspector(ArgumentInspector):
    """Inspector for network operations"""
    
    def __init__(self):
        self.internal_networks = [
            r"192\.168\.", r"10\.", r"172\.(1[6-9]|2\d|3[01])\.",
            r"127\.", r"localhost"
        ]
        
        self.sensitive_ports = [22, 23, 21, 3389, 5432, 3306, 1521, 443]
    
    def inspect(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> InspectionResult:
        violations = []
        risk_level = SecurityRisk.LOW
        
        url = arguments.get("url", arguments.get("host", ""))
        port = arguments.get("port", 80)
        
        # Check for internal network access
        for pattern in self.internal_networks:
            if re.search(pattern, url):
                violations.append(f"HIGH: Internal network access: {url}")
                risk_level = SecurityRisk.HIGH
        
        # Check for sensitive ports
        if port in self.sensitive_ports:
            violations.append(f"MEDIUM: Access to sensitive port: {port}")
            if risk_level.value == SecurityRisk.LOW.value:
                risk_level = SecurityRisk.MEDIUM
        
        return InspectionResult(
            risk_level=risk_level,
            permission_required=PermissionType.PRODUCTION_DATA_ACCESS,
            violations=violations,
            details={"url": url, "port": port}
        )
    
    def get_supported_tools(self) -> List[str]:
        return ["fetch_url", "make_request", "connect_to", "download_from"]

class ArgumentInspectionEngine:
    """Central engine for inspecting tool call arguments"""
    
    def __init__(self):
        self.inspectors: Dict[str, ArgumentInspector] = {}
        self._register_default_inspectors()
    
    def _register_default_inspectors(self):
        """Register default inspectors"""
        inspectors = [
            SQLQueryInspector(),
            FileOperationInspector(),
            NetworkOperationInspector()
        ]
        
        for inspector in inspectors:
            for tool_name in inspector.get_supported_tools():
                self.inspectors[tool_name] = inspector
    
    def register_inspector(self, tool_names: List[str], inspector: ArgumentInspector):
        """Register a custom inspector for specific tools"""
        for tool_name in tool_names:
            self.inspectors[tool_name] = inspector
    
    def inspect_arguments(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> InspectionResult:
        """Inspect arguments for security risks"""
        # Find appropriate inspector
        inspector = self.inspectors.get(tool_name)
        
        if not inspector:
            # Default inspection for unknown tools
            return self._default_inspection(tool_name, arguments, context)
        
        try:
            return inspector.inspect(tool_name, arguments, context)
        except Exception as e:
            logger.error(f"Error during argument inspection: {e}")
            return InspectionResult(
                risk_level=SecurityRisk.MEDIUM,
                permission_required=PermissionType.QUERY_EXECUTION,
                violations=[f"Inspection error: {str(e)}"],
                details={"error": str(e)}
            )
    
    def _default_inspection(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> InspectionResult:
        """Default inspection for tools without specific inspectors"""
        violations = []
        risk_level = SecurityRisk.LOW
        
        # Look for common risky patterns in any argument values
        for key, value in arguments.items():
            if isinstance(value, str):
                # Check for potential credential leaks
                if re.search(r"(password|secret|key|token)", key, re.IGNORECASE):
                    violations.append(f"MEDIUM: Potential credential argument: {key}")
                    risk_level = SecurityRisk.MEDIUM
                
                # Check for suspicious command patterns
                if re.search(r"(rm -rf|del /|format|mkfs)", value, re.IGNORECASE):
                    violations.append(f"HIGH: Destructive command pattern in {key}")
                    risk_level = SecurityRisk.HIGH
        
        return InspectionResult(
            risk_level=risk_level,
            permission_required=PermissionType.QUERY_EXECUTION,
            violations=violations,
            details={"tool_name": tool_name, "arguments_inspected": list(arguments.keys())}
        )

# Global argument inspection engine
argument_inspector = ArgumentInspectionEngine()

@dataclass
class VoteInstance:
    """Represents a single voting request"""
    request_id: str
    permission_type: PermissionType
    subject_type: SubjectType
    subject_id: str
    mcp_tool: str
    tool_arguments: Dict[str, Any]
    votes: Dict[StakeholderRole, VoteDecision]
    status: VoteDecision
    created_at: datetime
    expires_at: datetime
    current_request_context: Optional[Dict[str, Any]] = None
    
    def check_threshold(self) -> bool:
        """Check if voting threshold has been met"""
        if self.subject_type not in APPROVAL_MATRIX:
            return False
        
        permission_rules = APPROVAL_MATRIX[self.subject_type]
        if self.permission_type not in permission_rules:
            return False
        
        rules = permission_rules[self.permission_type]
        
        # Handle special restrictions
        if isinstance(rules, str) and rules == "NEVER_ALLOWED":
            return False
        
        approved_count = sum(1 for v in self.votes.values() if v == VoteDecision.APPROVE)
        return approved_count >= rules["required"]
    
    def has_veto(self) -> bool:
        """Check if any stakeholder with veto power has denied"""
        for stakeholder, vote in self.votes.items():
            stakeholder_config = STAKEHOLDERS.get(stakeholder, {})
            veto_permissions = stakeholder_config.get("veto_power", [])
            
            if (vote == VoteDecision.DENY and 
                self.permission_type.value in veto_permissions):
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "request_id": self.request_id,
            "permission_type": self.permission_type.value,
            "subject_type": self.subject_type.value,
            "subject_id": self.subject_id,
            "mcp_tool": self.mcp_tool,
            "tool_arguments": self.tool_arguments,
            "votes": {k.value: v.value for k, v in self.votes.items()},
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "current_request_context": self.current_request_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoteInstance":
        """Create from dictionary"""
        return cls(
            request_id=data["request_id"],
            permission_type=PermissionType(data["permission_type"]),
            subject_type=SubjectType(data["subject_type"]),
            subject_id=data["subject_id"],
            mcp_tool=data["mcp_tool"],
            tool_arguments=data["tool_arguments"],
            votes={StakeholderRole(k): VoteDecision(v) for k, v in data["votes"].items()},
            status=VoteDecision(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            current_request_context=data.get("current_request_context")
        )

class GovernanceEngine:
    """Main governance engine managing policy enforcement and voting"""
    
    def __init__(self, policies_file: str = "policies.json"):
        self.policies_file = policies_file
        self.active_votes: Dict[str, VoteInstance] = {}
        self.approval_cache: Dict[str, Dict[str, Any]] = {}
        self._load_persistent_data()
    
    def _load_persistent_data(self):
        """Load existing policies and votes from storage"""
        try:
            with open(self.policies_file, 'r') as f:
                data = json.load(f)
                
            # Load active votes
            for vote_data in data.get("active_votes", []):
                vote = VoteInstance.from_dict(vote_data)
                self.active_votes[vote.request_id] = vote
                
            # Load approval cache
            self.approval_cache = data.get("approval_cache", {})
            
            logger.info(f"Loaded {len(self.active_votes)} active votes and approval cache")
            
        except FileNotFoundError:
            logger.info("No existing policies file, starting fresh")
            self._save_persistent_data()
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
    
    def _save_persistent_data(self):
        """Save policies and votes to storage"""
        try:
            data = {
                "governance": {
                    "stakeholders": {k.value: v for k, v in STAKEHOLDERS.items()},
                    "permission_types": {k.value: v for k, v in PERMISSION_TYPES.items()},
                    "approval_matrix": {
                        k.value: {p.value: rules for p, rules in v.items()}
                        for k, v in APPROVAL_MATRIX.items()
                    }
                },
                "active_votes": [vote.to_dict() for vote in self.active_votes.values()],
                "approval_cache": self.approval_cache,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.policies_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Error saving policies: {e}")
    
    def map_tool_to_permission(self, tool_name: str, arguments: Dict[str, Any] = None, context: Dict[str, Any] = None) -> Tuple[PermissionType, InspectionResult]:
        """Map an MCP tool call to a permission type with comprehensive argument inspection"""
        # Use the argument inspection framework
        inspection_result = argument_inspector.inspect_arguments(
            tool_name, arguments or {}, context or {}
        )
        
        # The inspection result contains the permission recommendation
        return inspection_result.permission_required, inspection_result
    
    async def check_approval_cache(self, subject_id: str, permission: PermissionType, tool: str) -> Optional[Dict[str, Any]]:
        """Check for existing approvals"""
        cache_key = f"{subject_id}:{permission.value}:{tool}"
        cached = self.approval_cache.get(cache_key)
        
        if cached and datetime.fromisoformat(cached["expires_at"]) > datetime.now(timezone.utc):
            return cached
        
        # Remove expired cache entry
        if cached:
            del self.approval_cache[cache_key]
            
        return None
    
    async def create_vote_request(self, 
                                subject_id: str, 
                                subject_type: SubjectType,
                                tool_name: str, 
                                arguments: Dict[str, Any],
                                context: Optional[Dict[str, Any]] = None) -> Tuple[VoteInstance, InspectionResult]:
        """Create a new voting request with detailed inspection results"""
        permission, inspection_result = self.map_tool_to_permission(tool_name, arguments, context)
        if not permission:
            raise ValueError(f"Could not map tool {tool_name} to permission type")
        
        request_id = f"vote_{int(time.time())}_{hash(subject_id + tool_name) % 10000}"
        
        # Get eligible voters for this permission
        permission_config = PERMISSION_TYPES[permission]
        eligible_voters = permission_config["eligible_voters"]
        
        # Initialize votes
        votes = {}
        for voter in eligible_voters:
            # Check for auto-votes
            stakeholder_config = STAKEHOLDERS[voter]
            auto_vote = stakeholder_config.get("auto_vote")
            if auto_vote:
                votes[voter] = auto_vote
            else:
                votes[voter] = VoteDecision.PENDING
        
        vote_instance = VoteInstance(
            request_id=request_id,
            permission_type=permission,
            subject_type=subject_type,
            subject_id=subject_id,
            mcp_tool=tool_name,
            tool_arguments=arguments,
            votes=votes,
            status=VoteDecision.PENDING,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            current_request_context=context
        )
        
        self.active_votes[request_id] = vote_instance
        self._save_persistent_data()
        
        logger.info(f"Created vote request {request_id} for {subject_type.value} {subject_id} to use {tool_name}")
        logger.info(f"Security violations detected: {inspection_result.violations}")
        
        return vote_instance, inspection_result
    
    async def cast_vote(self, request_id: str, stakeholder: StakeholderRole, decision: VoteDecision) -> bool:
        """Cast a vote for a pending request"""
        if request_id not in self.active_votes:
            return False
        
        vote_instance = self.active_votes[request_id]
        
        # Check if stakeholder is eligible
        if stakeholder not in vote_instance.votes:
            logger.warning(f"Stakeholder {stakeholder.value} not eligible to vote on {request_id}")
            return False
        
        # Cast the vote
        vote_instance.votes[stakeholder] = decision
        
        # Update status based on new vote
        if vote_instance.has_veto():
            vote_instance.status = VoteDecision.DENY
        elif vote_instance.check_threshold():
            vote_instance.status = VoteDecision.APPROVE
        
        self._save_persistent_data()
        
        logger.info(f"Vote cast by {stakeholder.value}: {decision.value} on request {request_id}")
        return True
    
    async def get_vote_status(self, request_id: str) -> Optional[VoteInstance]:
        """Get current status of a vote"""
        return self.active_votes.get(request_id)
    
    async def list_pending_votes(self, stakeholder: Optional[StakeholderRole] = None) -> List[VoteInstance]:
        """List pending votes, optionally filtered by stakeholder"""
        pending = []
        
        for vote in self.active_votes.values():
            if vote.status != VoteDecision.PENDING:
                continue
            
            if datetime.now(timezone.utc) > vote.expires_at:
                # Mark as expired
                vote.status = VoteDecision.DENY
                continue
            
            if stakeholder and stakeholder not in vote.votes:
                continue
            
            if stakeholder and vote.votes[stakeholder] != VoteDecision.PENDING:
                continue
            
            pending.append(vote)
        
        return pending
    
    async def cleanup_expired_votes(self):
        """Clean up expired votes"""
        current_time = datetime.now(timezone.utc)
        expired_requests = []
        
        for request_id, vote in self.active_votes.items():
            if current_time > vote.expires_at:
                vote.status = VoteDecision.DENY
                expired_requests.append(request_id)
        
        if expired_requests:
            logger.info(f"Marked {len(expired_requests)} votes as expired")
            self._save_persistent_data()

class PolicyDecision:
    """Result of policy enforcement"""
    
    def __init__(self, action: str, message: str = "", vote_request_id: str = None):
        self.action = action  # "ALLOW", "DENY", "REQUIRE_APPROVAL"
        self.message = message
        self.vote_request_id = vote_request_id
    
    @classmethod
    def ALLOW(cls, message: str = ""):
        return cls("ALLOW", message)
    
    @classmethod
    def DENY(cls, message: str):
        return cls("DENY", message)
    
    @classmethod
    def REQUIRE_APPROVAL(cls, vote_request_id: str, message: str = ""):
        return cls("REQUIRE_APPROVAL", message, vote_request_id)

# Global governance engine instance
governance_engine = GovernanceEngine()

async def enforce_policy(tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> PolicyDecision:
    """
    Main entry point for policy enforcement during MCP tool calls with granular argument inspection
    """
    try:
        # 1. Perform comprehensive argument inspection
        permission, inspection_result = governance_engine.map_tool_to_permission(tool_name, arguments, context)
        if not permission:
            return PolicyDecision.ALLOW("Tool not subject to governance")
        
        # 2. Check for critical security violations that should never be allowed
        if inspection_result.risk_level == SecurityRisk.CRITICAL and not inspection_result.allow_override:
            violation_summary = "; ".join(inspection_result.violations)
            return PolicyDecision.DENY(
                f"CRITICAL security violation detected: {violation_summary}. "
                f"Tool: {tool_name}. This action is categorically blocked."
            )
        
        # 3. Determine subject type (developer vs agent)
        subject_type = SubjectType(context.get("subject_type", "coding_agent"))  # Default to stricter
        subject_id = context.get("subject_id", "unknown")
        
        # 4. Check for existing approvals
        existing_approval = await governance_engine.check_approval_cache(
            subject_id, permission, tool_name
        )
        
        if existing_approval:
            return PolicyDecision.ALLOW("Pre-approved access")
        
        # 5. Check for categorical denials (agents with restricted permissions)
        if subject_type == SubjectType.CODING_AGENT:
            agent_rules = APPROVAL_MATRIX[SubjectType.CODING_AGENT]
            if permission in agent_rules and agent_rules[permission] == "NEVER_ALLOWED":
                return PolicyDecision.DENY(f"Coding agents cannot perform {permission.value}")
        
        # 6. For high-risk operations, require additional scrutiny
        if inspection_result.risk_level in [SecurityRisk.HIGH, SecurityRisk.CRITICAL]:
            detailed_message = (
                f"HIGH-RISK operation detected. "
                f"Security violations: {'; '.join(inspection_result.violations)}. "
                f"Risk level: {inspection_result.risk_level.value.upper()}. "
                f"Details: {inspection_result.details}"
            )
        else:
            detailed_message = f"Approval required for {permission.value}"
        
        # 7. Create vote request with inspection details
        vote_request, _ = await governance_engine.create_vote_request(
            subject_id=subject_id,
            subject_type=subject_type,
            tool_name=tool_name,
            arguments=arguments,
            context={**context, "inspection_result": inspection_result.details, "violations": inspection_result.violations}
        )
        
        # 8. Check if immediately approved (auto-votes might be sufficient)
        if vote_request.check_threshold() and not vote_request.has_veto():
            # Cache approval for future use, but with shorter duration for high-risk operations
            cache_duration_hours = 1 if inspection_result.risk_level in [SecurityRisk.HIGH, SecurityRisk.CRITICAL] else 2
            
            cache_key = f"{subject_id}:{permission.value}:{tool_name}"
            governance_engine.approval_cache[cache_key] = {
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=cache_duration_hours)).isoformat(),
                "vote_request_id": vote_request.request_id,
                "risk_level": inspection_result.risk_level.value,
                "violations": inspection_result.violations
            }
            governance_engine._save_persistent_data()
            
            return PolicyDecision.ALLOW(f"Automatically approved by stakeholder votes")
        
        # 9. Require approval workflow with detailed inspection information
        return PolicyDecision.REQUIRE_APPROVAL(
            vote_request.request_id,
            detailed_message
        )
        
    except Exception as e:
        logger.error(f"Error in policy enforcement: {e}")
        return PolicyDecision.DENY(f"Policy enforcement error: {str(e)}")

async def get_pending_approvals_for_stakeholder(stakeholder: StakeholderRole) -> List[Dict[str, Any]]:
    """Get pending approval requests for a specific stakeholder"""
    pending_votes = await governance_engine.list_pending_votes(stakeholder)
    
    return [
        {
            "request_id": vote.request_id,
            "subject_type": vote.subject_type.value,
            "subject_id": vote.subject_id,
            "permission_type": vote.permission_type.value,
            "tool": vote.mcp_tool,
            "arguments": vote.tool_arguments,
            "created_at": vote.created_at.isoformat(),
            "expires_at": vote.expires_at.isoformat(),
            "description": PERMISSION_TYPES[vote.permission_type]["description"]
        }
        for vote in pending_votes
    ]

async def submit_stakeholder_vote(request_id: str, stakeholder_name: str, decision: str) -> bool:
    """Submit a vote from a stakeholder"""
    try:
        stakeholder = StakeholderRole(stakeholder_name)
        vote_decision = VoteDecision(decision.upper())
        
        return await governance_engine.cast_vote(request_id, stakeholder, vote_decision)
    
    except (ValueError, KeyError) as e:
        logger.error(f"Invalid stakeholder vote submission: {e}")
        return False

# Background task to clean up expired votes
async def start_cleanup_task():
    """Background task to clean up expired votes"""
    while True:
        try:
            await governance_engine.cleanup_expired_votes()
            await asyncio.sleep(300)  # Clean up every 5 minutes
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error