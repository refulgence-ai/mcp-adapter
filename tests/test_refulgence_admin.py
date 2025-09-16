"""
Integration tests for Refulgence Admin features
These test the actual implemented functionality
"""

import pytest
import httpx

BASE_URL = "http://localhost:8080"

class TestRefulgenceAdminPages:
    """Test that all admin pages load correctly"""
    
    @pytest.mark.asyncio
    async def test_admin_dashboard_loads(self):
        """Test main admin dashboard loads"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/admin")
            assert response.status_code == 200
            # Check for key UI elements
            assert "Refulgence" in response.text
            assert "startContextualTour" in response.text
    
    @pytest.mark.asyncio
    async def test_drill_down_page_loads(self):
        """Test drill-down analysis page loads"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/admin/drill-down")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_demo_guide_page_loads(self):
        """Test demo guide page loads"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/demo")
            assert response.status_code == 200
            assert "Demo Guide" in response.text
            assert "Opening - The Problem" in response.text


class TestRefulgenceAdminAPI:
    """Test admin API endpoints"""
    
    @pytest.mark.asyncio
    async def test_metrics_api(self):
        """Test metrics API returns expected structure"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/admin/api/metrics")
            assert response.status_code == 200
            data = response.json()
            # Check expected metrics exist
            assert isinstance(data, dict)
            assert "queries_per_hour" in data
    
    @pytest.mark.asyncio
    async def test_activity_api(self):
        """Test activity API returns list"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/admin/api/activity")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_stats_api(self):
        """Test stats API endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/admin/api/stats")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_servers_api(self):
        """Test servers API endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/admin/api/servers")
            assert response.status_code == 200
            data = response.json()
            # API returns list directly, not wrapped in object
            assert isinstance(data, list)
            assert len(data) > 0
            # Check server structure
            assert "name" in data[0]
            assert "status" in data[0]
    
    @pytest.mark.asyncio
    async def test_test_governance_api(self):
        """Test the governance testing endpoint"""
        async with httpx.AsyncClient() as client:
            test_data = {
                "query": "SELECT * FROM users",
                "subject_type": "developer"
            }
            response = await client.post(
                f"{BASE_URL}/admin/api/test-governance",
                json=test_data
            )
            assert response.status_code == 200
            data = response.json()
            assert "policy_decision" in data
            assert "message" in data
    
    @pytest.mark.asyncio
    async def test_dangerous_query_blocked(self):
        """Test that dangerous queries are blocked or require approval"""
        async with httpx.AsyncClient() as client:
            test_data = {
                "query": "DROP TABLE customers",
                "subject_type": "coding_agent"
            }
            response = await client.post(
                f"{BASE_URL}/admin/api/test-governance",
                json=test_data
            )
            assert response.status_code == 200
            data = response.json()
            # Should be denied or require approval
            assert data["policy_decision"] in ["DENY", "BLOCKED", "REQUIRE_APPROVAL"]
            # Verify it's not simply allowed
            assert data["policy_decision"] != "ALLOW"