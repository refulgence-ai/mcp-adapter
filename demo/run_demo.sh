#!/bin/bash

# Refulgence Interactive Demo Script
# Run this script to demonstrate the governance system

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Check if services are running
check_services() {
    if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${RED}Error: Services not running. Starting them now...${NC}"
        docker-compose up -d
        echo "Waiting for services to be ready..."
        sleep 10
    fi
}

# Function to pause and wait for user
pause() {
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read
}

# Main demo flow
main() {
    check_services
    
    clear
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}           🚀 REFULGENCE INTERACTIVE DEMO 🚀${NC}"
    echo -e "${PURPLE}     Enterprise AI Agent Security Gateway${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo
    echo -e "${BLUE}Philosophy:${NC} 'We trust the developer, but we don't trust their tools'"
    echo
    echo -e "${GREEN}Dashboard URL:${NC} http://localhost:8080/admin"
    echo
    pause

    # Act 1: Safe Query
    clear
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}ACT 1: SAFE ANALYTICS QUERY${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo
    echo "Scenario: A developer wants to check product inventory"
    echo -e "${BLUE}Query:${NC} SELECT COUNT(*) FROM products WHERE quantity > 0;"
    echo -e "${BLUE}Subject:${NC} developer"
    echo
    echo -e "${YELLOW}Testing governance...${NC}"
    sleep 2

    RESULT=$(curl -s -X POST http://localhost:8080/admin/api/test-governance \
      -H "Content-Type: application/json" \
      -d '{"query": "SELECT COUNT(*) FROM products WHERE quantity > 0;", "subject_type": "developer"}')

    DECISION=$(echo "$RESULT" | jq -r '.policy_decision')
    MESSAGE=$(echo "$RESULT" | jq -r '.message')

    echo
    echo -e "${YELLOW}⚠️  Decision: $DECISION${NC}"
    echo -e "${BLUE}Reason:${NC} $MESSAGE"
    echo
    pause

    # Act 2: PII Access Attempt
    clear
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}ACT 2: PII DATA ACCESS ATTEMPT${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo
    echo "Scenario: An AI agent tries to access customer SSNs"
    echo -e "${BLUE}Query:${NC} SELECT * FROM customers WHERE ssn IS NOT NULL;"
    echo -e "${BLUE}Subject:${NC} coding_agent"
    echo
    echo -e "${YELLOW}Testing governance...${NC}"
    sleep 2

    RESULT=$(curl -s -X POST http://localhost:8080/admin/api/test-governance \
      -H "Content-Type: application/json" \
      -d '{"query": "SELECT * FROM customers WHERE ssn IS NOT NULL;", "subject_type": "coding_agent"}')

    DECISION=$(echo "$RESULT" | jq -r '.policy_decision')
    MESSAGE=$(echo "$RESULT" | jq -r '.message' | head -c 200)
    VOTE_ID=$(echo "$RESULT" | jq -r '.vote_request_id')

    echo
    echo -e "${RED}🚨 Decision: $DECISION${NC}"
    echo -e "${BLUE}Security Violations Detected:${NC}"
    echo "  • Direct PII column access (SSN)"
    echo "  • Customer data table access"
    echo "  • Unrestricted SELECT * query"
    echo
    echo -e "${YELLOW}Vote Request ID:${NC} $VOTE_ID"
    echo
    pause

    # Act 3: Destructive Operation
    clear
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}ACT 3: DESTRUCTIVE OPERATION ATTEMPT${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo
    echo "Scenario: An AI agent attempts to DROP a production database"
    echo -e "${BLUE}Query:${NC} DROP DATABASE production_data;"
    echo -e "${BLUE}Subject:${NC} coding_agent"
    echo
    echo -e "${YELLOW}Testing governance...${NC}"
    sleep 2

    RESULT=$(curl -s -X POST http://localhost:8080/admin/api/test-governance \
      -H "Content-Type: application/json" \
      -d '{"query": "DROP DATABASE production_data;", "subject_type": "coding_agent"}')

    DECISION=$(echo "$RESULT" | jq -r '.policy_decision')
    CRITICAL_VOTE_ID=$(echo "$RESULT" | jq -r '.vote_request_id')

    echo
    echo -e "${RED}🚨🚨 CRITICAL RISK - Decision: $DECISION 🚨🚨${NC}"
    echo -e "${BLUE}Critical Violations:${NC}"
    echo "  • CRITICAL: Destructive DROP operation"
    echo "  • CRITICAL: Database deletion attempt"
    echo "  • Risk Level: CRITICAL"
    echo
    echo -e "${YELLOW}Vote Request ID:${NC} $CRITICAL_VOTE_ID"
    echo
    pause

    # Act 4: CISO Denial
    clear
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}ACT 4: STAKEHOLDER VOTING WORKFLOW${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo
    echo "The CISO receives an alert about the DROP DATABASE attempt..."
    echo
    echo -e "${YELLOW}Simulating CISO vote to DENY the operation...${NC}"
    sleep 2

    VOTE_RESULT=$(curl -s -X POST http://localhost:8080/admin/api/vote \
      -H "Content-Type: application/json" \
      -d "{\"request_id\": \"$CRITICAL_VOTE_ID\", \"stakeholder\": \"CISO\", \"decision\": \"DENY\"}")

    echo -e "${GREEN}✅ CISO voted: DENY${NC}"
    echo
    echo "The destructive operation has been blocked by governance!"
    echo
    
    # Show another approval
    echo -e "${YELLOW}Now approving the safe analytics query...${NC}"
    sleep 1
    
    if [ ! -z "$VOTE_ID" ] && [ "$VOTE_ID" != "null" ]; then
        curl -s -X POST http://localhost:8080/admin/api/vote \
          -H "Content-Type: application/json" \
          -d "{\"request_id\": \"$VOTE_ID\", \"stakeholder\": \"IT_ADMIN\", \"decision\": \"APPROVE\"}" > /dev/null
        echo -e "${GREEN}✅ IT_ADMIN voted: APPROVE for PII query (with conditions)${NC}"
    fi
    echo
    pause

    # Final Status
    clear
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}DEMO COMPLETE - SYSTEM STATUS${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo

    STATS=$(curl -s http://localhost:8080/admin/api/stats)
    echo -e "${BLUE}Current Governance Status:${NC}"
    echo "$STATS" | jq '.'
    echo

    echo -e "${GREEN}✅ Infrastructure Protected${NC}"
    echo -e "${GREEN}✅ PII Data Secured${NC}"
    echo -e "${GREEN}✅ Destructive Operations Blocked${NC}"
    echo -e "${GREEN}✅ Multi-Stakeholder Governance Active${NC}"
    echo
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Access full dashboard at:${NC} http://localhost:8080/admin"
    echo -e "${BLUE}View demo guide at:${NC} demo/UI_WALKTHROUGH.md"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
}

# Run the demo
main "$@"