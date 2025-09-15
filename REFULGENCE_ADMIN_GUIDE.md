# 🛡️ Refulgence Admin Interface Guide

## 🎯 Overview

The Refulgence Admin Interface is a comprehensive AI Agent Security Gateway that provides enterprise-grade governance, monitoring, and control over AI agent activities. This guide enables any developer to understand, use, and extend the system.

---

## 🚀 Quick Start Demo

### **Access the Admin Interface**
- **Main Dashboard**: http://localhost:8080/admin
- **Activity Drill-Down**: http://localhost:8080/admin/drill-down
- **MCP Dashboard**: http://localhost:8080/dashboard
- **Session Monitor**: http://localhost:8080/sessions

### **🎮 Demo Features**
The admin interface includes comprehensive demo capabilities:

#### **Header Demo Controls**
- **🎮 Start Demo Tour** - Interactive guided tour of all features
- **🧪 Generate Demo Data** - Create sample governance events
- **⚡ Simulate Event** - Trigger sample governance scenarios  
- **🔒 Security Test** - Run sample security validations

#### **Tab-Specific Demo Tools**
Each management tab includes demo test buttons:

**👥 User Management Tab:**
- Load Demo Users - Populate with realistic user data
- Test Inspector - Demo user inspection capabilities
- Simulate Activity - Generate user activity events

**📋 Policy Matrix Tab:**
- Load Demo Matrix - Apply enterprise policy configuration
- Test Logic - Validate policy decision scenarios
- Export Demo - Generate sample policy files

---

## 🏗️ Architecture Overview

### **Core Components**

```
Refulgence Admin Interface
├── 🎛️ Management Tabs
│   ├── 📊 Overview - Live metrics & quick actions
│   ├── 👥 User Management - User inspector & role management
│   ├── 📋 Policy Matrix - Interactive governance rules
│   ├── 🔄 Workflows - Approval process designer
│   ├── ⚖️ Approvals - Real-time voting & decisions
│   ├── 🔗 Servers - Backend MCP server management
│   └── 🔒 Security - Threat monitoring & controls
│
├── 🔍 Activity Analysis
│   ├── Real-time Activity Feed
│   ├── Advanced Filtering & Search
│   └── Forensic Event Drill-Down
│
└── 🧪 Demo & Testing
    ├── Interactive Guided Tours
    ├── Sample Data Generation
    └── Security Test Simulation
```

### **Backend Integration**
- **Gateway Server** (gateway.py) - Main MCP server with governance
- **Activity Tracker** (activity_tracker.py) - Real-time event monitoring  
- **Governance Engine** (governance.py) - Policy enforcement & voting
- **Template System** - Multiple UI modes and responsive design

---

## 📋 Tab-by-Tab Feature Guide

### **📊 Overview Tab**
**Purpose**: Central dashboard with live metrics and quick actions

**Key Features**:
- Real-time statistics (queries/hour, blocked events, approvals)
- Quick action cards for common tasks
- Server health monitoring
- Activity feed preview

**Demo Functions**:
- Live metrics simulation
- Server status testing
- Quick action demonstrations

### **👥 User Management Tab**
**Purpose**: Comprehensive user inspection and role management

**Key Features**:
- User Inspector with detailed analysis
- Role assignment and modification
- Permission matrix management
- User activity tracking
- Credential oversight

**Demo Functions**:
- `loadDemoUsers()` - Populate realistic user database
- `testUserInspector()` - Demonstrate inspection capabilities
- `simulateUserActivity()` - Generate user activity events

**API Endpoints**:
- `/admin/api/users` - User management operations
- `/admin/api/roles` - Role configuration
- `/admin/api/permissions` - Permission management

### **📋 Policy Matrix Tab**
**Purpose**: Interactive governance rule configuration

**Key Features**:
- Click-to-edit policy matrix
- Subject type vs. permission mapping
- Real-time policy validation
- Export/import capabilities
- Version control for policy changes

**Demo Functions**:
- `loadDemoMatrix()` - Apply enterprise policy set
- `testMatrixLogic()` - Validate decision scenarios
- `exportDemoPolicy()` - Generate configuration files

**Policy Structure**:
```javascript
{
  "subject_types": ["developer", "coding_agent", "security_analyst"],
  "permissions": ["database_admin", "pii_access", "schema_modify"],
  "matrix": {
    "developer": {"database_admin": "DENY", "pii_access": "REQUIRE_APPROVAL"},
    "coding_agent": {"database_admin": "DENY", "pii_access": "DENY"},
    "security_analyst": {"database_admin": "ALLOW", "pii_access": "ALLOW"}
  }
}
```

### **🔄 Workflows Tab**
**Purpose**: Design and manage approval workflows

**Key Features**:
- Visual workflow builder
- Multi-stakeholder approval chains
- Conditional logic support
- Timeout and escalation rules
- Workflow testing and validation

### **⚖️ Approvals Tab**
**Purpose**: Real-time approval tracking and voting

**Key Features**:
- Live approval requests
- Stakeholder voting interface
- Vote history and audit trail
- Automatic decision execution
- Emergency override capabilities

### **🔗 Servers Tab**
**Purpose**: Backend MCP server management

**Key Features**:
- Server health monitoring
- Connection pool statistics
- Tool availability tracking
- Performance metrics
- Server configuration management

### **🔒 Security Tab**
**Purpose**: Comprehensive security monitoring and controls

**Key Features**:
- Threat detection dashboard
- Security violation tracking
- Compliance reporting
- Emergency controls
- Audit log management

---

## 🔍 Activity Drill-Down Interface

### **Access**: http://localhost:8080/admin/drill-down

### **Three-Panel Layout**:

#### **Left Panel: Filters & Search**
- Real-time search across all events
- Severity filtering (Critical, Warning, Info, Success)
- Event type filtering (Blocked queries, approvals, votes)
- Time range selection (1h, 6h, 24h, 7d, 30d)
- Subject/user filtering
- Clear all filters option

#### **Center Panel: Activity Feed**
- Live event stream with auto-refresh
- Clickable events for detailed analysis
- Color-coded severity indicators
- Smart tagging (severity, type, subject, tool)
- Relative timestamps ("2m ago", "1h ago")

#### **Right Panel: Event Details**
- Complete event information
- JSON detail viewer with syntax highlighting
- Action buttons (Export, Block Similar, Create Policy)
- Related event linking
- Compliance reporting tools

---

## 🛠️ Development Guide

### **File Structure**
```
gateway/
├── templates/
│   ├── admin_comprehensive.html    # Main admin interface
│   ├── admin_drill_down.html      # Activity analysis interface
│   ├── admin_enhanced_real.html   # Real-time enhanced UI
│   └── admin.html                 # Basic admin interface
├── gateway.py                     # Main gateway server
├── governance.py                  # Policy enforcement engine
├── activity_tracker.py           # Event tracking system
└── servers.json                  # Backend server configuration
```

### **Environment Configuration**
```bash
# UI Mode Selection
UI_MODE=comprehensive    # Default: full-featured interface
UI_MODE=enhanced_real    # Real-time focused interface  
UI_MODE=basic           # Minimal interface

# Debug Settings
DEBUG=true              # Enable debug logging
LOG_LEVEL=INFO          # Logging verbosity
```

### **Adding New Features**

#### **1. Add New Tab**
```html
<!-- In admin_comprehensive.html -->
<button class="tab-button" onclick="showTab('newtab')">🆕 New Feature</button>

<div id="newtab" class="tab-content">
    <div class="card">
        <h3>🆕 New Feature</h3>
        <!-- Feature content -->
    </div>
</div>
```

#### **2. Add Demo Functionality**
```javascript
function demoNewFeature() {
    alert('🆕 Demonstrating new feature capabilities!');
    // Demo logic here
}
```

#### **3. Add Backend API Endpoint**
```python
# In gateway.py
@app.get("/admin/api/new-feature")
async def new_feature_api():
    return {"status": "success", "data": "feature_data"}
```

### **Testing Integration**
- All admin features integrate with the comprehensive test suite
- Demo functions provide immediate validation
- API endpoints include built-in testing capabilities
- Security functions validate against real governance policies

---

## 🧪 Testing & Validation

### **Built-in Demo System**
The admin interface includes comprehensive testing capabilities:

#### **Guided Demo Tours**
- Interactive step-by-step feature demonstrations
- Highlighted UI elements with contextual explanations
- Skip/navigation controls for flexible exploration
- Complete feature coverage across all tabs

#### **Sample Data Generation**
- Realistic user profiles and roles
- Enterprise policy configurations  
- Governance event simulation
- Security scenario testing

#### **Real-time Validation**
- Live API endpoint testing
- Policy logic validation
- Security control verification
- Performance impact assessment

### **Integration with Test Suite**
The admin interface connects to the broader test infrastructure:

```bash
# Run admin-specific tests
cd tests && uv run pytest test_admin_interface.py

# Test governance integration
cd tests && uv run pytest test_governance.py

# Validate activity tracking
cd tests && uv run pytest test_activity_tracker.py
```

---

## 📊 API Reference

### **Admin Management APIs**

#### **Metrics & Statistics**
```bash
GET /admin/api/metrics
# Returns: real-time governance statistics

GET /admin/api/activity?limit=50&severity=critical
# Returns: filtered activity events

POST /admin/api/test-governance
# Body: {"query": "SQL", "subject_type": "agent"}
# Returns: policy decision simulation
```

#### **User Management**
```bash
GET /admin/api/users
# Returns: user list with roles and permissions

POST /admin/api/users
# Body: {"username": "user", "role": "SECURITY_ANALYST"}
# Returns: user creation status

PUT /admin/api/users/{user_id}/role
# Body: {"role": "NEW_ROLE"}
# Returns: role update confirmation
```

#### **Policy Management**
```bash
GET /admin/api/policies
# Returns: current policy matrix

PUT /admin/api/policies/matrix
# Body: {"matrix": {...}}
# Returns: policy update status

POST /admin/api/policies/test
# Body: {"scenario": {...}}
# Returns: policy decision for scenario
```

---

## 🔧 Customization Guide

### **Styling & Theming**
The interface uses CSS custom properties for easy theming:

```css
:root {
    --primary-color: #667eea;
    --success-color: #28a745;
    --warning-color: #ffc107;
    --danger-color: #dc3545;
    --info-color: #17a2b8;
}
```

### **Adding Custom Demo Functions**
```javascript
// Add to the demo functionality section
function customDemoFunction() {
    // Your custom demo logic
    alert('🎯 Custom demo feature activated!');
    
    // Optional: integrate with backend
    fetch('/admin/api/custom-demo', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({demo: 'custom'})
    });
}
```

### **Extending the Tour System**
```javascript
// Add new steps to demoTourSteps array
{
    target: '.your-new-feature',
    title: '🆕 Your New Feature',
    content: 'Description of your new feature capabilities.',
    position: 'bottom'
}
```

---

## 🚨 Security Considerations

### **Administrative Access**
- Admin interface provides full system control
- Implement proper authentication before production use
- Consider role-based access control for different admin functions
- Audit all administrative actions

### **Demo Mode Safety**
- Demo functions are designed for testing environments
- Production deployments should disable or restrict demo capabilities
- Simulated data should not affect production governance decisions
- Security tests use safe, non-destructive validation

### **Data Protection**
- Activity tracking may contain sensitive information
- Implement proper data retention policies
- Consider encryption for sensitive governance data
- Ensure compliance with organizational data policies

---

## 🎯 Next Steps for Development

### **Immediate Enhancements**
1. **Authentication Integration** - Add OAuth/SAML support
2. **Real-time Updates** - Implement WebSocket push notifications
3. **Advanced Analytics** - Add trend analysis and reporting
4. **Mobile Optimization** - Enhance responsive design

### **Advanced Features**
1. **AI-Powered Insights** - Automated policy recommendations
2. **Compliance Automation** - Regulatory reporting tools
3. **Integration APIs** - Connect with enterprise security tools
4. **Multi-tenant Support** - Organization isolation and management

### **Scalability Improvements**
1. **Database Backend** - Replace in-memory storage with persistent database
2. **Caching Layer** - Add Redis for high-performance scenarios
3. **Load Balancing** - Support for multiple gateway instances
4. **Monitoring Integration** - Prometheus/Grafana integration

---

## 📞 Support & Resources

### **Documentation Links**
- [Main README](README.md) - Project overview and setup
- [Testing Guide](tests/CLAUDE.md) - Comprehensive testing documentation
- [Development Plan](REFULGENCE_DEVELOPMENT_PLAN.md) - Roadmap and architecture
- [Session Plan](NEXT_SESSION_PLAN.md) - Current development priorities

### **Key URLs for Development**
- **Admin Interface**: http://localhost:8080/admin
- **Activity Drill-Down**: http://localhost:8080/admin/drill-down  
- **MCP Dashboard**: http://localhost:8080/dashboard
- **Session Monitor**: http://localhost:8080/sessions
- **API Documentation**: http://localhost:8080/docs (FastAPI auto-docs)

### **Development Commands**
```bash
# Start full development environment
docker-compose up -d

# Run comprehensive tests
cd tests && uv run pytest

# Restart gateway after code changes
docker-compose restart gateway

# Monitor logs
docker-compose logs -f gateway
```

---

**This guide provides everything needed for vanilla session development - comprehensive understanding, demo capabilities, testing tools, and clear development pathways for extending the Refulgence AI Agent Security Gateway.**