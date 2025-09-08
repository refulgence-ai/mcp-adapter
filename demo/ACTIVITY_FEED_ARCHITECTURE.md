# 📊 Live Activity Feed Architecture

## 🎯 **YOUR QUESTION: "Where is the Live Activity feed coming from?"**

### **ANSWER: It comes from 3 different sources depending on the UI version**

---

## 🔄 **Three UI Versions & Their Data Sources**

### **Version 1: Basic UI** (`admin.html`)
- **No activity feed** - Just basic stats

### **Version 2: Enhanced UI** (`admin_enhanced.html`) 
- **Data Source:** JavaScript simulation for demo purposes
- **Location:** Lines 950-965 in the template
- **How it works:** Random events every 5 seconds + user-triggered events

### **Version 3: Enhanced Real UI** (`admin_enhanced_real.html`) - **DEFAULT**
- **Data Source:** Real governance events from backend activity tracker
- **API Endpoints:** 
  - `/admin/api/activity` - Live activity feed
  - `/admin/api/metrics` - Real-time metrics
- **How it works:** Tracks actual governance decisions and votes

---

## 🏗️ **Real Activity Feed Architecture**

### **Backend Components**

#### **1. Activity Tracker** (`gateway/activity_tracker.py`)
- **Singleton class** that tracks all governance events
- **In-memory storage** of last 1000 events
- **Event types:** Query blocked, approval requested, vote submitted, etc.
- **Automatic statistics** calculation

#### **2. Event Integration** (`gateway/gateway.py`)
- **Lines 115-121**: Tracks governance test results
- **Lines 1040-1041**: Tracks vote decisions  
- **API endpoints**: `/admin/api/activity` and `/admin/api/metrics`

#### **3. Real-Time Frontend** (`admin_enhanced_real.html`)
- **Auto-refresh**: Fetches new data every 3 seconds
- **Live updates**: Shows actual governance decisions
- **Real metrics**: Displays current system stats

---

## 📈 **Data Flow Diagram**

```
User Tests Query
       ↓
Governance Engine Evaluates
       ↓
Policy Decision Made
       ↓
Activity Tracker Records Event
       ↓
Event Stored in Memory (last 1000)
       ↓
Frontend Polls /admin/api/activity
       ↓
Real-Time UI Updates
```

---

## 🧪 **Live Demo - Generate Real Activity**

### **Test 1: Generate Activity Events**
```bash
# Test a dangerous query
curl -X POST http://localhost:8080/admin/api/test-governance \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers WHERE ssn IS NOT NULL;", "subject_type": "coding_agent"}'

# Test a destructive query  
curl -X POST http://localhost:8080/admin/api/test-governance \
  -H "Content-Type: application/json" \
  -d '{"query": "DROP TABLE orders;", "subject_type": "coding_agent"}'
```

### **Test 2: Submit Votes**
```bash
# Submit a CISO vote
curl -X POST http://localhost:8080/admin/api/vote \
  -H "Content-Type: application/json" \
  -d '{"request_id": "vote_12345", "stakeholder": "CISO", "decision": "DENY"}'
```

### **Test 3: View Real Activity**
```bash
# See the activity feed
curl http://localhost:8080/admin/api/activity | jq

# See live metrics
curl http://localhost:8080/admin/api/metrics | jq
```

---

## 📊 **Real Activity Events You'll See**

### **Event Types Generated:**
1. **Query Blocked** - When governance denies a query
2. **Approval Requested** - When high-risk query needs votes
3. **Vote Submitted** - When stakeholder approves/denies
4. **Security Violation** - When dangerous patterns detected

### **Current Live Data** (from your tests):
```json
[
  {
    "type": "approval_requested",
    "message": "Approval requested for redshift_execute_query",
    "severity": "info",
    "timestamp": "2025-09-08T16:59:39.623845+00:00"
  },
  {
    "type": "query_blocked", 
    "message": "Query blocked: SELECT * FROM customers WHERE ssn IS NOT NULL;...",
    "severity": "warning",
    "timestamp": "2025-09-08T16:59:39.623767+00:00"
  }
]
```

---

## 🎛️ **Switch Between UI Versions**

Control which UI version loads with environment variables:

```bash
# Use real activity feed (DEFAULT)
export UI_MODE=enhanced_real
docker-compose restart gateway

# Use simulated activity feed  
export UI_MODE=enhanced
docker-compose restart gateway

# Use basic UI (no activity feed)
export UI_MODE=basic
docker-compose restart gateway
```

---

## 🔍 **How to Verify Real vs Simulated**

### **Real Activity Feed Indicators:**
- ✅ Events have actual timestamps
- ✅ Events match your test actions
- ✅ Metrics reflect actual governance decisions
- ✅ No random events appear
- ✅ UI shows "Live Data" indicator with pulsing dot

### **Simulated Activity Feed Indicators:**
- ❌ Random events appear every few seconds
- ❌ Generic messages like "PII access blocked"
- ❌ Events don't match your actions
- ❌ Metrics increment randomly

---

## 🎯 **Current Status**

**You are now using the REAL activity feed!**

- **URL:** http://localhost:8080/admin
- **Data Source:** `activity_tracker.py` with actual governance events
- **API Endpoints:** `/admin/api/activity` and `/admin/api/metrics`
- **Update Frequency:** Every 3 seconds
- **Events Tracked:** 5 real events from your governance tests
- **Metrics:** 2 blocked queries, 1 denied vote, real statistics

**Every query test, vote, and governance decision creates real activity events that appear instantly in the UI!** 🚀

---

## 💡 **Next Steps**

1. **Test the Real Feed:** 
   - Open http://localhost:8080/admin
   - Test queries in the UI
   - Watch real events appear instantly

2. **Add More Event Types:**
   - Agent connections/disconnections
   - Policy creations/updates
   - Security scans
   - Emergency blocks

3. **Add WebSocket Support:**
   - Replace polling with push notifications
   - Instant updates without refresh
   - Better performance

4. **Add Event Persistence:**
   - Store events in database
   - Historical analysis
   - Compliance reporting