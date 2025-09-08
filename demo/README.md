# 🎭 Refulgence Demo Guide

This directory contains all materials needed to demonstrate Refulgence, the Enterprise AI Agent Security Gateway.

## 📁 Demo Files

- **`run_demo.sh`** - Interactive command-line demo script
- **`UI_WALKTHROUGH.md`** - Precise step-by-step UI demonstration guide
- **`test_queries.json`** - Sample queries for testing governance

## 🚀 Quick Start

### Option 1: Run Interactive Demo (Automated)
```bash
cd demo
chmod +x run_demo.sh
./run_demo.sh
```
This runs an automated walkthrough showing:
- Safe queries being processed
- PII access being blocked
- Destructive operations being prevented
- Stakeholder voting workflow

### Option 2: Manual UI Demo
1. Open browser to: http://localhost:8080/admin
2. Follow the steps in `UI_WALKTHROUGH.md`

## 🎯 Demo Scenarios

### Scenario 1: Safe Analytics Query
- **Query**: `SELECT COUNT(*) FROM products WHERE price > 100;`
- **Expected**: Allowed or low-risk approval required
- **Purpose**: Show legitimate queries work normally

### Scenario 2: PII Data Access
- **Query**: `SELECT * FROM customers WHERE ssn IS NOT NULL;`
- **Expected**: Blocked, requires approval, shows violations
- **Purpose**: Demonstrate PII protection

### Scenario 3: Destructive Operation
- **Query**: `DROP TABLE customers;`
- **Expected**: Critical risk, blocked, multiple approvals needed
- **Purpose**: Show critical operation prevention

### Scenario 4: Stakeholder Voting
- **Action**: CISO reviews and votes on pending requests
- **Expected**: Approved/Denied based on risk
- **Purpose**: Show governance workflow

## 📊 Key Demo Points

### Opening Hook
> "AI agents with unrestricted tool access can destroy your infrastructure in seconds. Refulgence provides governance at the argument level."

### Core Value Props
1. **Granular Control**: Inspect every argument of every tool call
2. **Multi-Stakeholder Governance**: CISO, IT Admin, and automated policies
3. **Risk-Based Enforcement**: Different responses based on risk level
4. **Real-Time Monitoring**: See what AI agents are trying to do

### Closing Message
> "With Refulgence, you can safely give AI agents access to production systems. The governance engine ensures nothing dangerous happens without human oversight."

## 🛠️ Setup Requirements

```bash
# 1. Start all services
docker-compose up -d

# 2. Verify health
curl http://localhost:8080/health

# 3. Access dashboard
open http://localhost:8080/admin
```

## 📝 Demo Checklist

Before starting your demo:
- [ ] Docker services running (`docker-compose ps`)
- [ ] Gateway accessible (`curl http://localhost:8080/health`)
- [ ] Dashboard loads (http://localhost:8080/admin)
- [ ] Test queries ready (see test_queries.json)
- [ ] Browser console open (for debugging if needed)

## 🎬 Demo Duration

- **Quick Demo**: 3-5 minutes (automated script)
- **Full Demo**: 7-10 minutes (UI walkthrough)
- **Technical Deep-Dive**: 15-20 minutes (with architecture discussion)

## 💡 Tips for Success

1. **Start with impact** - Show what could go wrong without governance
2. **Build tension** - Escalate from safe to dangerous queries
3. **Be interactive** - Let audience suggest queries to test
4. **Show the fix** - Demonstrate how governance prevents disasters
5. **End with confidence** - Their infrastructure is now protected

## 🔧 Troubleshooting

### Services not responding
```bash
docker-compose down
docker-compose up -d --build
```

### Dashboard not loading
```bash
docker-compose logs gateway
curl http://localhost:8080/health
```

### No pending votes showing
```bash
# Create new test queries
curl -X POST http://localhost:8080/admin/api/test-governance \
  -H "Content-Type: application/json" \
  -d '{"query": "DELETE FROM users;", "subject_type": "coding_agent"}'
```

## 📚 Additional Resources

- Main README: [../README.md](../README.md)
- Architecture: [../REFULGENCE_DEVELOPMENT_PLAN.md](../REFULGENCE_DEVELOPMENT_PLAN.md)
- API Docs: See gateway API endpoints in code

---

**Remember**: The goal is to show that Refulgence makes AI agents safe for enterprise use by enforcing governance at the most granular level possible.