# Refulgence Admin Dashboard - UI Walkthrough

## 🎯 Precise Step-by-Step Demo Guide

### Prerequisites
```bash
# Ensure services are running
docker-compose up -d

# Verify all services are healthy
docker-compose ps
```

### Access the Dashboard
1. Open your browser
2. Navigate to: **http://localhost:8080/admin**
3. You should see the Refulgence Admin Dashboard

---

## 📋 UI Demo Steps

### Step 1: Overview Tab (Default View)
**Location:** Main dashboard page loads with Overview tab active

**What to show:**
1. **Governance Statistics Panel** (top cards)
   - Point to "Pending Approvals" count (may show 0 initially)
   - Note "Connected Servers: 3"
   - Highlight "Governance Enabled" status

2. **Test Governance Section** (center)
   - This is where we'll demonstrate query testing

3. **Recent Activity** (bottom)
   - Will populate as we test queries

**Talk track:** "The Overview tab shows real-time governance statistics and allows testing of SQL queries against our policy engine."

---

### Step 2: Test a Safe Query
**Location:** Overview Tab → Test Governance section

**Exact steps:**
1. Click in the **"SQL Query"** text area
2. Type exactly: `SELECT COUNT(*) FROM products WHERE price > 100;`
3. From the **"Subject Type"** dropdown, select: `developer`
4. Click the **"Test Query"** button

**Expected result:**
- A message appears showing the policy decision
- Decision will be either "ALLOW" or "REQUIRE_APPROVAL" depending on configuration
- No critical violations shown

**Talk track:** "Safe analytical queries are allowed or require minimal approval."

---

### Step 3: Test a PII Access Query
**Location:** Overview Tab → Test Governance section

**Exact steps:**
1. Clear the SQL Query text area
2. Type exactly: `SELECT * FROM customers WHERE ssn IS NOT NULL;`
3. Keep **"Subject Type"** as: `coding_agent`
4. Click the **"Test Query"** button

**Expected result:**
- **Red alert box** appears
- Shows "REQUIRE_APPROVAL" decision
- Lists violations:
  - "Direct PII column access"
  - "Customer data table access"
  - "Unrestricted SELECT *"
- A vote request ID is generated

**Talk track:** "The system immediately detects PII access attempts and blocks them, requiring stakeholder approval."

---

### Step 4: Test a Destructive Query
**Location:** Overview Tab → Test Governance section

**Exact steps:**
1. Clear the SQL Query text area
2. Type exactly: `DROP TABLE customers;`
3. Keep **"Subject Type"** as: `coding_agent`
4. Click the **"Test Query"** button

**Expected result:**
- **Critical red alert** appears
- Shows "REQUIRE_APPROVAL" with CRITICAL risk level
- Lists violations:
  - "CRITICAL: Destructive DROP operation"
  - "Schema object deletion"
- Vote request ID generated

**Talk track:** "Destructive operations are immediately flagged as critical risks and blocked."

---

### Step 5: View Pending Approvals
**Location:** Click the **"⚖️ Pending Approvals"** tab

**What you'll see:**
1. List of pending approval requests from previous tests
2. Each request shows:
   - Risk level (color-coded: yellow=medium, red=high, dark red=critical)
   - Tool name being called
   - Subject who made the request
   - Time elapsed since request
   - The actual query/arguments

**Exact steps:**
1. Click on **"⚖️ Pending Approvals"** tab
2. Observe the pending requests from your tests
3. Note the risk levels and violation details

**Talk track:** "All high-risk operations queue here for stakeholder review."

---

### Step 6: Submit a Stakeholder Vote
**Location:** Pending Approvals tab

**Exact steps:**
1. Find the DROP TABLE request (highest risk)
2. In the **"Vote as Stakeholder"** section at the top:
   - Select **"CISO"** from the dropdown
3. For the DROP TABLE request:
   - Click the **"Deny"** button
4. Observe the request disappear from pending list

**For the PII access request:**
1. Still as CISO, find the SSN query
2. Click **"Approve"** (with conditions)
3. Request moves to approved status

**Talk track:** "Stakeholders can review the context and make informed decisions. Critical operations often require multiple approvals."

---

### Step 7: View Policy Matrix
**Location:** Click the **"📋 Policy Matrix"** tab

**What to show:**
1. **Permission Types grid**
   - Shows different permission categories
   - Risk levels for each
   - Which stakeholders can vote

2. **Approval Rules matrix**
   - Shows required votes for each risk level
   - Thresholds for approval

**Talk track:** "The policy matrix defines who can approve what, and how many votes are needed based on risk."

---

### Step 8: Server Management
**Location:** Click the **"🔗 Server Management"** tab

**What to show:**
1. **Connected Servers list**
   - Hello World (internal) - PUBLIC access
   - LaTeX Server (internal) - PUBLIC access
   - AWS Redshift (aws) - RESTRICTED access, HIGH risk

2. **Server Details**
   - Each shows vendor, access level, risk level
   - Status indicators (green = online)

**Exact steps:**
1. Click on **"AWS Redshift"** server card
2. Note the HIGH risk level and restricted access
3. Show this requires governance for all operations

**Talk track:** "Different servers have different risk profiles. Production databases require strict governance."

---

### Step 9: Return to Overview - Show Final Stats
**Location:** Click **"📊 Overview"** tab

**What to show:**
1. Updated statistics after your testing
2. Approved/Denied counts may have changed
3. Recent activity log showing your tests

**Talk track:** "The dashboard provides complete visibility into all AI agent activities and governance decisions."

---

## 🎬 Demo Script Summary

### Opening (30 seconds)
1. Load dashboard: http://localhost:8080/admin
2. Show Overview tab statistics
3. Explain the philosophy: "We trust developers, not their tools"

### Main Demo (3-4 minutes)
1. Test safe query → Show it's allowed/low-risk
2. Test PII query → Show violations and blocking
3. Test DROP query → Show critical risk detection
4. Switch to Pending Approvals → Show queue
5. Vote as CISO → Deny destructive, approve with conditions
6. Show Policy Matrix → Explain governance rules
7. Show Servers → Highlight risk levels

### Closing (30 seconds)
1. Return to Overview
2. Show updated stats
3. "Your infrastructure is now protected by granular governance"

---

## 🚀 Quick Command Reference

### Test Queries via API (for technical audience)
```bash
# Safe query
curl -X POST http://localhost:8080/admin/api/test-governance \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) FROM orders;", "subject_type": "developer"}'

# PII query
curl -X POST http://localhost:8080/admin/api/test-governance \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers WHERE ssn IS NOT NULL;", "subject_type": "coding_agent"}'

# Destructive query
curl -X POST http://localhost:8080/admin/api/test-governance \
  -H "Content-Type: application/json" \
  -d '{"query": "DROP DATABASE prod;", "subject_type": "coding_agent"}'
```

### Check Status
```bash
# View pending votes
curl http://localhost:8080/admin/api/pending-votes | jq

# View system stats
curl http://localhost:8080/admin/api/stats | jq

# View connected servers
curl http://localhost:8080/admin/api/servers | jq
```

---

## 💡 Tips for Presenters

1. **Start with the problem** - Explain AI agent risks first
2. **Build tension** - Show increasingly dangerous queries
3. **Be interactive** - Let audience suggest queries
4. **Show the workflow** - Demo the complete approval process
5. **End with confidence** - Infrastructure is protected

## 🎯 Key Messages

- **Granular Control**: "We inspect every argument of every tool call"
- **Multi-Stakeholder**: "Different roles for different risks"
- **Real-time**: "Instant detection and blocking"
- **Enterprise-Ready**: "Built for production from day one"

---

## Troubleshooting

### If dashboard won't load:
```bash
docker-compose down
docker-compose up -d
# Wait 30 seconds
curl http://localhost:8080/health
```

### If no pending votes appear:
- Make sure to test queries first
- Check that governance is enabled
- Verify services are running: `docker-compose ps`

### If votes aren't working:
- Check browser console for errors
- Ensure you've selected a stakeholder
- Try refreshing the page