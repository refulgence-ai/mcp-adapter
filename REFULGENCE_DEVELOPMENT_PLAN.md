# Refulgence Development Plan
## Transforming MCP Adapter into Enterprise AI Agent Security Gateway

### Vision Statement
Refulgence is a centralized security gateway that provides authentication, access control, policy-as-code enforcement, and runtime governance for autonomous AI agents interacting with enterprise tools and cloud resources.

### Target Customer Profile
**Primary**: IT Directors managing enterprise AI agent deployments
**Secondary**: Security teams, DevOps engineers, Compliance officers

---

## Current Foundation Analysis

### Existing MCP Adapter Capabilities
✅ **OAuth Integration**: Claude Code compatible authentication endpoints  
✅ **Session Management**: Concurrent session pools with backend servers  
✅ **Tool Proxying**: Static tool discovery and proxying architecture  
✅ **Basic Dashboard**: Server/tool visualization interface  
✅ **RBAC Structure**: Partial role-based access in `servers.json`  
✅ **Backend Servers**: Hello World (3 tools), LaTeX (4 tools)

### Current Limitations (Read-Only Foundation)
❌ **Static Configuration**: Server management requires file edits  
❌ **Limited RBAC**: Basic role structure without enforcement  
❌ **No Policy Engine**: No runtime policy evaluation  
❌ **Basic UI**: Simple dashboard without admin capabilities  
❌ **No Persistence**: Configuration changes not saved  
❌ **Limited Security**: Basic OAuth without proper user management

---

## Phase 1: Core Refulgence Transformation (Demo Focus)

### 1.1 Enhanced UI Framework
**Objective**: Transform read-only dashboard into interactive security admin interface

**Components**:
- **Server Management Panel**: Add/remove/configure MCP servers dynamically
- **Role & Permission Manager**: Visual RBAC configuration interface
- **Policy Builder**: Drag-and-drop policy creation with real-time preview
- **User Management**: Authentication, roles, and session oversight
- **Security Dashboard**: Live agent activity and policy enforcement status

**Technical Approach**:
- Extend existing FastAPI HTML endpoints with modern JavaScript
- Add HTMX for dynamic interactions without full SPA complexity
- Maintain single-file deployment model for easy enterprise adoption

### 1.2 AWS Redshift MCP Integration
**Objective**: Add enterprise-grade cloud resource management capabilities

**Redshift Server Capabilities** (from research):
- `list_clusters()`: Discover Redshift resources
- `list_databases()`, `list_schemas()`, `list_tables()`, `list_columns()`: Schema exploration
- `execute_query()`: Safe SQL execution with read-only protections

**Integration Requirements**:
- Python 3.10+ compatibility (current: 3.12 ✅)
- AWS credentials configuration
- IAM permissions for Redshift discovery
- Docker containerization within existing compose stack

**Gateway Integration**:
- Add `redshift-server/` directory with Dockerfile
- Register Redshift tools in gateway with `redshift_` prefix
- Configure AWS credential management in Docker environment
- Add Redshift-specific RBAC policies

### 1.3 Dynamic Server Management
**Objective**: Replace static `servers.json` with dynamic configuration

**Features**:
- **Add MCP Server**: URL, credentials, metadata input with validation
- **Server Health Monitoring**: Real-time connectivity and tool discovery
- **Configuration Persistence**: Enhanced JSON storage with backup/restore
- **Hot Reloading**: Add/remove servers without gateway restart

**Data Model**:
```json
{
  "servers": {
    "server-id": {
      "name": "Human-readable name",
      "url": "http://server:port",
      "description": "Server purpose",
      "vendor": "aws|custom|internal",
      "auth_method": "none|bearer|oauth",
      "credentials": {...},
      "health_status": "online|offline|error",
      "tools": [...],
      "added_by": "user-id",
      "added_at": "timestamp"
    }
  }
}
```

### 1.4 Policy-as-Code Engine: Multi-Stakeholder Governance Model
**Objective**: Implement a voting-based permission system where organizational stakeholders control access for developers and their coding agents

**Core Philosophy**: "We trust the developer, but we don't trust their tools"

#### Governance Architecture

**Layer 1: Stakeholder Registry**
```python
STAKEHOLDERS = {
    "CISO": {
        "role": "security_authority",
        "description": "Chief Information Security Officer",
        "voting_weight": 1.0,
        "veto_power": ["user_management", "emergency_access"]
    },
    "ENTERPRISE_DEFAULT": {
        "role": "enterprise_governance",
        "description": "Default enterprise security policies",
        "voting_weight": 1.0,
        "auto_vote": "DENY"  # Conservative by default
    },
    "BUSINESS_LEAD": {
        "role": "business_owner",
        "description": "Business unit leader owning the data",
        "voting_weight": 1.0,
        "scope": ["production_data", "pii_data"]
    },
    "IT_ADMIN": {
        "role": "technical_authority", 
        "description": "IT administration team",
        "voting_weight": 1.0,
        "override_for": ["emergency_situations"]
    },
    "PROJECT_OWNER": {
        "role": "project_authority",
        "description": "Specific project owner",
        "voting_weight": 0.5,  # Limited influence
        "scope": ["project_specific_data"]
    },
    "END_USER": {
        "role": "end_user_representative",
        "description": "End user data owner",
        "voting_weight": 0.5,
        "scope": ["development_environment"]
    }
}
```

**Layer 2: Permission Type Registry**
```python
PERMISSION_TYPES = {
    # Redshift-specific permissions mapped to our use case
    "database_admin_rights": {
        "mcp_tools": ["redshift:create_user", "redshift:drop_database", "redshift:alter_cluster"],
        "eligible_voters": ["CISO", "ENTERPRISE_DEFAULT", "IT_ADMIN"],
        "risk_level": "CRITICAL",
        "description": "SUPERUSER privileges, user management, cluster configuration"
    },
    "production_data_access": {
        "mcp_tools": ["redshift:execute_query", "redshift:list_tables"],
        "eligible_voters": ["CISO", "ENTERPRISE_DEFAULT", "BUSINESS_LEAD", "IT_ADMIN"],
        "risk_level": "HIGH",
        "query_filters": ["WHERE", "SELECT", "JOIN"]  # Allowed operations
    },
    "pii_sensitive_data": {
        "mcp_tools": ["redshift:execute_query{table:contains('customer')}", "redshift:export_data"],
        "eligible_voters": ["CISO", "BUSINESS_LEAD"],
        "risk_level": "CRITICAL",
        "requires_legal": True
    },
    "schema_modification": {
        "mcp_tools": ["redshift:create_table", "redshift:alter_table", "redshift:drop_table"],
        "eligible_voters": ["CISO", "ENTERPRISE_DEFAULT", "IT_ADMIN"],
        "risk_level": "HIGH",
        "requires_approval_workflow": True
    },
    "query_execution": {
        "mcp_tools": ["redshift:execute_query"],
        "eligible_voters": ["ENTERPRISE_DEFAULT", "IT_ADMIN"],
        "risk_level": "MEDIUM",
        "rate_limits": {"developer": 1000, "agent": 100}
    }
}
```

**Layer 3: Voting Rules & Thresholds**
```python
APPROVAL_MATRIX = {
    "developer": {
        "database_admin_rights": {"required": 2, "total": 3, "additional": []},
        "production_data_access": {"required": 2, "total": 4, "additional": []},
        "pii_sensitive_data": {"required": 1, "total": 2, "additional": []},
        "schema_modification": {"required": 1, "total": 3, "additional": []},
        "query_execution": {"required": 1, "total": 2, "additional": []}
    },
    "coding_agent": {
        "database_admin_rights": {"required": 3, "total": 3, "additional": ["external_audit"]},
        "production_data_access": {"required": 4, "total": 4, "additional": ["time_limit:1h"]},
        "pii_sensitive_data": {"required": 2, "total": 2, "additional": ["legal_review"]},
        "schema_modification": {"required": 3, "total": 3, "additional": ["approval_workflow"]},
        "query_execution": {"required": 2, "total": 2, "additional": ["rate_limit:100/hour"]},
        "user_management": "NEVER_ALLOWED",
        "emergency_access": "NEVER_ALLOWED",
        "export_permissions": "NEVER_ALLOWED"
    }
}
```

**Layer 4: Runtime Vote Processing**
```python
class VoteInstance:
    def __init__(self, request):
        self.request_id = generate_id()
        self.permission_type = request.permission
        self.subject_type = "developer" if request.is_human else "coding_agent"
        self.subject_id = request.subject_id
        self.mcp_tool = request.tool  # e.g., "redshift:execute_query"
        self.tool_arguments = request.arguments  # Actual SQL query, etc.
        self.votes = {}
        self.status = "PENDING"
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(hours=1)
        
    def check_threshold(self):
        rules = APPROVAL_MATRIX[self.subject_type][self.permission_type]
        approved_count = sum(1 for v in self.votes.values() if v == "APPROVE")
        return approved_count >= rules["required"]
```

#### Implementation Architecture for Demo

**1. UI Components**

```
┌─────────────────────────────────────────────────────────────┐
│                    Refulgence Admin Dashboard               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Active Requests  │  │ Stakeholder View │                │
│  │                  │  │                  │                │
│  │ • Dev Alice      │  │ CISO Panel:      │                │
│  │   Redshift Query │  │ [3] Pending Votes│                │
│  │   2/3 Votes ✓    │  │ [✓] Approve All  │                │
│  │                  │  │ [✗] Deny All     │                │
│  │ • Agent Bob      │  │                  │                │
│  │   Schema Modify  │  │ IT_ADMIN Panel:  │                │
│  │   0/3 Votes ⏳   │  │ [2] Pending Votes│                │
│  └──────────────────┘  └──────────────────┘                │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Permission Matrix Editor                 │  │
│  │                                                       │  │
│  │  Permission: [Dropdown: Production Data Access]       │  │
│  │  Developer Threshold:  [2]/[4] votes                  │  │
│  │  Agent Threshold:      [4]/[4] votes + [Time Limit]  │  │
│  │  Eligible Voters: ☑ CISO ☑ IT_ADMIN ☐ PROJECT_OWNER │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**2. Backend Policy Engine Integration**

```python
# In gateway.py - Policy enforcement at tool invocation
async def enforce_policy(tool_name: str, arguments: dict, context: dict) -> PolicyDecision:
    """
    Main entry point for policy enforcement during MCP tool calls
    """
    # 1. Identify permission type needed
    permission = map_tool_to_permission(tool_name)
    
    # 2. Check if subject is developer or agent
    subject_type = context.get("subject_type", "coding_agent")  # Default to stricter
    
    # 3. Check for existing approvals
    existing_approval = await check_approval_cache(
        subject_id=context["subject_id"],
        permission=permission,
        tool=tool_name
    )
    
    if existing_approval and not existing_approval.expired:
        return PolicyDecision.ALLOW
    
    # 4. Check if permission is categorically denied
    if subject_type == "coding_agent" and permission in ["user_management", "emergency_access"]:
        return PolicyDecision.DENY("Coding agents cannot perform this action")
    
    # 5. Create vote request
    vote_request = VoteInstance({
        "permission": permission,
        "tool": tool_name,
        "arguments": arguments,
        "subject_id": context["subject_id"],
        "is_human": subject_type == "developer"
    })
    
    # 6. Collect votes (async with timeout)
    await collect_votes(vote_request)
    
    # 7. Evaluate decision
    if vote_request.check_threshold():
        # 8. Apply additional requirements for agents
        if subject_type == "coding_agent":
            additional = APPROVAL_MATRIX["coding_agent"][permission]["additional"]
            for requirement in additional:
                if not await verify_additional_requirement(requirement, context):
                    return PolicyDecision.DENY(f"Failed requirement: {requirement}")
        
        return PolicyDecision.ALLOW
    
    return PolicyDecision.REQUIRE_APPROVAL(vote_request.request_id)
```

**3. Persistence Layer**

```json
// policies.json - Store policy configuration
{
  "governance": {
    "stakeholders": {...},
    "permission_types": {...},
    "approval_matrix": {...}
  },
  "active_votes": [
    {
      "request_id": "req_12345",
      "permission": "production_data_access",
      "tool": "redshift:execute_query",
      "arguments": {"query": "SELECT * FROM customers"},
      "subject": "agent_claude_code_123",
      "votes": {
        "CISO": "APPROVE",
        "IT_ADMIN": "PENDING",
        "BUSINESS_LEAD": "APPROVE",
        "ENTERPRISE_DEFAULT": "DENY"
      },
      "status": "PENDING",
      "created_at": "2024-01-07T10:00:00Z",
      "expires_at": "2024-01-07T11:00:00Z"
    }
  ],
  "approval_history": [...]
}
```

**4. Demo Scenarios**

**Scenario 1: Developer Requests Redshift Query Access**
- Alice (developer) wants to run `SELECT * FROM sales_data`
- System identifies this as "production_data_access"
- Needs 2/4 votes from [CISO, ENTERPRISE_DEFAULT, BUSINESS_LEAD, IT_ADMIN]
- CISO and IT_ADMIN approve → Access granted
- Query executes successfully

**Scenario 2: Coding Agent Attempts Schema Modification**
- Claude Code attempts to run `ALTER TABLE customers ADD COLUMN`
- System identifies this as "schema_modification"
- Needs 3/3 votes from [CISO, ENTERPRISE_DEFAULT, IT_ADMIN]
- Even with all approvals, requires additional approval_workflow
- Shows UI for multi-step approval process

**Scenario 3: Agent Blocked from Dangerous Operation**
- Agent attempts `DROP TABLE users`
- System immediately denies - no voting needed
- "NEVER_ALLOWED" for destructive operations by agents
- Logs attempt for security review

#### Technical Implementation Steps

1. **Extend `gateway.py`** with policy engine hooks
2. **Create `governance.py`** module for voting logic
3. **Add `/admin` routes** for policy management UI
4. **Implement WebSocket** for real-time vote updates
5. **Add `VoteCache` class** for temporary approval storage
6. **Create approval workflow UI** with stakeholder panels
7. **Integrate with Redshift MCP** for demo scenarios

---

## Phase 2: Enterprise Features (Future)

### 2.1 Advanced Authentication
- SAML/LDAP integration
- Multi-factor authentication
- Session timeout policies
- API key management

### 2.2 Advanced Policy Engine
- Machine learning-based anomaly detection
- Risk scoring algorithms
- Contextual policy evaluation (time, location, behavior)
- Policy versioning and rollback

### 2.3 Compliance & Governance
- SOC2, GDPR, HIPAA compliance templates
- Automated compliance reporting
- Policy violation analytics
- Risk assessment dashboards

---

## Technical Architecture Decisions

### Persistence Strategy
**Decision**: Enhanced JSON file storage with migration path
**Rationale**: 
- Immediate implementation without database complexity
- Easy backup/restore and version control
- Clear migration path to PostgreSQL/MySQL for enterprise
- Maintains single-container deployment simplicity

### UI Framework Choice
**Decision**: FastAPI + HTMX + Minimal JavaScript
**Rationale**:
- Extends existing FastAPI foundation
- HTMX provides dynamic interactions without SPA complexity
- Maintains single-file deployment model
- Easy to understand and modify for enterprise customization

### Policy Engine Implementation
**Decision**: Python-based rules engine with YAML configuration
**Rationale**:
- Native integration with FastAPI backend
- YAML provides readable policy definition
- Python expressions for complex logic
- Easy to extend with custom functions

---

## Development Priorities for Demo

### High Priority (Evening Focus)
1. **AWS Redshift Integration**: Demonstrate enterprise cloud resource control
2. **Dynamic Server Management**: Show real-time configuration capabilities
3. **Basic Policy Builder UI**: Visual policy creation with immediate enforcement
4. **Enhanced Dashboard**: Security-focused interface transformation

### Medium Priority (If Time Permits)
1. **User Role Management**: Basic authentication beyond OAuth tokens
2. **Policy Templates**: Pre-built policies for common security scenarios
3. **Real-time Enforcement**: Live policy evaluation during tool calls

### Deferred (Post-Demo)
1. **Audit & Monitoring**: Comprehensive logging and analytics
2. **Advanced Policy Features**: ML-based detection, complex workflows
3. **Enterprise Authentication**: SAML, LDAP integration

---

## Success Metrics for Demo

### Functional Demonstrations
- [ ] Add new MCP server (Redshift) through UI without code changes
- [ ] Create and enforce policy blocking dangerous SQL operations
- [ ] Show role-based access control preventing unauthorized tool usage
- [ ] Display security posture dashboard with live policy enforcement

### Technical Validation
- [ ] All existing tests continue to pass
- [ ] New Redshift integration tests validate AWS connectivity
- [ ] Policy engine correctly blocks/allows operations based on rules
- [ ] UI remains responsive and intuitive for IT Director persona

---

## File Structure Changes

```
/
├── gateway/
│   ├── gateway.py (enhanced with policy engine)
│   ├── servers.json (enhanced with dynamic capabilities)
│   ├── policies.yaml (new: policy definitions)
│   ├── static/ (new: UI assets)
│   └── templates/ (new: HTML templates)
├── redshift-server/ (new)
│   ├── Dockerfile
│   ├── server.py
│   └── requirements.txt
├── docker-compose.yml (updated with Redshift service)
├── tests/
│   ├── test_redshift_server.py (new)
│   ├── test_policy_engine.py (new)
│   └── test_dynamic_config.py (new)
└── REFULGENCE_DEVELOPMENT_PLAN.md (this document)
```

---

## Implementation Roadmap for Next Session

### Step 1: Core Infrastructure Setup (30 minutes)
1. **Start Docker services**: `docker-compose up -d`
2. **Create governance module**: `gateway/governance.py`
   - Import stakeholder definitions
   - Implement VoteInstance class
   - Create voting collection mechanism
3. **Update gateway.py**:
   - Add policy enforcement hooks to tool calls
   - Integrate with governance module
   - Add context tracking for developer vs agent

### Step 2: Redshift MCP Server Integration (45 minutes)
1. **Create redshift-server directory**:
   ```bash
   mkdir redshift-server
   cd redshift-server
   ```
2. **Create server.py** with FastMCP framework:
   - Implement 6 core Redshift tools
   - Add AWS credential handling
   - Implement query safety checks
3. **Create Dockerfile** for Redshift server
4. **Update docker-compose.yml** to include Redshift service
5. **Register Redshift tools in gateway**:
   - Add static proxy functions with `redshift_` prefix
   - Map tools to permission types

### Step 3: Enhanced UI Development (60 minutes)
1. **Transform dashboard** (`/dashboard` endpoint):
   - Add tabbed interface: Overview | Permissions | Policies | Servers
   - Implement HTMX for dynamic updates
2. **Create Permission Matrix Editor**:
   - Visual grid showing stakeholders vs permissions
   - Editable thresholds for developer/agent
   - Real-time preview of policy impact
3. **Build Active Requests Panel**:
   - Show pending approval requests
   - Vote collection interface
   - Approval/denial buttons for stakeholders
4. **Add Server Management Interface**:
   - Form to add new MCP servers
   - Test connection functionality
   - Tool discovery and registration

### Step 4: Policy Engine Implementation (45 minutes)
1. **Create policies.json** structure:
   - Initialize with default governance model
   - Add Redshift-specific permissions
2. **Implement enforce_policy function**:
   - Tool-to-permission mapping
   - Vote threshold checking
   - Additional requirement verification
3. **Add vote collection system**:
   - Async vote gathering with timeout
   - WebSocket notifications for real-time updates
4. **Create approval cache**:
   - Time-limited approval storage
   - Subject-based permission tracking

### Step 5: Demo Scenario Setup (30 minutes)
1. **Create demo users**:
   - Developer "Alice" with partial permissions
   - Agent "Claude Code" with restricted access
   - Stakeholder accounts (CISO, IT_ADMIN, etc.)
2. **Prepare SQL queries** for demonstration:
   - Safe SELECT query for developer
   - Schema modification attempt by agent
   - Dangerous DROP TABLE blocked example
3. **Configure initial policies**:
   - Production data access rules
   - Schema modification restrictions
   - PII data protection policies

### Step 6: Testing & Validation (30 minutes)
1. **Test Redshift connectivity**:
   ```bash
   cd tests && uv run pytest test_redshift_server.py -v
   ```
2. **Validate policy enforcement**:
   - Test developer vs agent permissions
   - Verify vote collection works
   - Check NEVER_ALLOWED blocks
3. **UI functionality testing**:
   - Add server through UI
   - Create/modify policies
   - Process approval requests

### Key Files to Create/Modify

**New Files**:
- `gateway/governance.py` - Voting and permission logic
- `gateway/policies.json` - Policy configuration
- `gateway/templates/admin.html` - Enhanced UI
- `redshift-server/server.py` - Redshift MCP implementation
- `redshift-server/Dockerfile` - Container configuration
- `tests/test_governance.py` - Policy engine tests
- `tests/test_redshift_integration.py` - Redshift tests

**Modified Files**:
- `gateway/gateway.py` - Add policy hooks, enhanced UI
- `gateway/servers.json` - Add Redshift configuration
- `docker-compose.yml` - Include Redshift service
- `tests/test_gateway.py` - Update for new functionality

### Environment Variables Needed
```bash
# .env file
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
REDSHIFT_CLUSTER_ID=your_cluster
REDSHIFT_DATABASE=your_database
REDSHIFT_USER=your_user
```

### Quick Start Commands for Next Session
```bash
# 1. Checkout branch and review plan
git checkout refulgence-ui-demo
cat REFULGENCE_DEVELOPMENT_PLAN.md

# 2. Start services
docker-compose up -d

# 3. Begin implementation
cd gateway
# Start with governance.py implementation

# 4. Test as you go
cd tests && uv run pytest -v

# 5. Access UI
open http://localhost:8080/dashboard
```

### Demo Script Outline
1. **Opening**: Show current MCP adapter limitations
2. **Problem Statement**: "We trust developers, not their tools"
3. **Solution Demo**:
   - Add Redshift server dynamically through UI
   - Show permission matrix configuration
   - Demonstrate developer getting approval for query
   - Show agent being blocked from dangerous operation
   - Display real-time vote collection
4. **Value Proposition**: Enterprise control without blocking productivity

This plan provides a clear roadmap for transforming the MCP Adapter into Refulgence while maintaining focus on the demo objectives and evening timeline constraints.