#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#     "fastmcp>=2.10",
#     "uvicorn>=0.35",
#     "httpx>=0.28",
#     "pydantic>=2.11",
#     "fastapi>=0.115"
# ]
# ///
"""
mcp-adapter: Universal MCP-compliant gateway server

Aggregates tools from multiple backend MCP servers using FastMCP 2.0.
All endpoints and tool calls are MCP-compliant (no legacy fields).
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastmcp import FastMCP
import httpx
import asyncio
from fastapi.responses import HTMLResponse, JSONResponse

# Import governance system
from governance import (
    enforce_policy, PolicyDecision,
    get_pending_approvals_for_stakeholder, submit_stakeholder_vote,
    StakeholderRole, PermissionType, PERMISSION_TYPES, governance_engine, start_cleanup_task
)

# Import activity tracking
from activity_tracker import (
    activity_tracker, track_query_execution, track_approval_request,
    track_vote_decision, track_security_event, track_agent_lifecycle
)

# Import user data store
from user_data_store import user_store, User, UserRole, UserStatus, PermissionLevel

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("MCP Adapter")

# Load MCP server configuration
def load_server_config() -> Dict[str, Dict[str, str]]:
    """Load MCP server configuration from servers.json"""
    try:
        with open('servers.json', 'r') as f:
            config = json.load(f)
            servers = config.get('servers', {})
            
            # No URL mapping needed - use the URLs as configured in servers.json
            # Docker networking will handle the internal communication
            return servers
    except FileNotFoundError:
        logger.warning("servers.json not found, using empty server list")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in servers.json: {e}")
        return {}

MCP_SERVERS = load_server_config()

# Global tool registry
tool_registry: Dict[str, Dict[str, Any]] = {}

async def discover_server_tools(server_name: str, config: Dict[str, str]) -> List[Dict[str, Any]]:
    """Discover tools from a single MCP server"""
    tools = []
    try:
        async with httpx.AsyncClient() as client:
            # Try to get tool information from info endpoint
            try:
                info_response = await client.get(f"{config['url']}/info", timeout=5.0)
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    available_tools = info_data.get("available_tools", [])
                    
                    for tool_name in available_tools:
                        tools.append({
                            "name": f"{server_name}_{tool_name}",
                            "description": f"{tool_name} from {server_name} server",
                            "server": server_name,
                            "original_tool": tool_name,
                            "url": config["url"]
                        })
            except Exception as e:
                logger.warning(f"Failed to discover tools from {server_name}: {e}")
                
    except Exception as e:
        logger.error(f"Error discovering tools from {server_name}: {e}")
    
    return tools

async def initialize_tool_registry():
    """Initialize the tool registry by discovering tools from all servers"""
    logger.info("Discovering tools from backend servers...")
    
    for server_name, config in MCP_SERVERS.items():
        tools = await discover_server_tools(server_name, config)
        for tool in tools:
            tool_registry[tool["name"]] = tool
    
    logger.info(f"Discovered {len(tool_registry)} tools from {len(MCP_SERVERS)} servers")

# Create static proxy tools for known backend tools
async def call_backend_tool_direct(server_url: str, tool_name: str, arguments: dict, context: dict = None) -> str:
    """Call a tool on a specific backend server directly using session pool with policy enforcement"""
    session_id = None
    try:
        # Apply governance policy enforcement
        if context is None:
            context = {
                "subject_type": "coding_agent",  # Default to more restrictive
                "subject_id": "unknown_agent",
                "server_url": server_url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Check if this tool requires governance
        if any(governed_tool in tool_name for governed_tool in ["redshift_", "execute_query", "list_tables", "list_databases"]):
            policy_decision = await enforce_policy(tool_name, arguments, context)
            
            if policy_decision.action == "DENY":
                return json.dumps({
                    "status": "blocked",
                    "reason": "policy_violation",
                    "message": policy_decision.message,
                    "tool": tool_name,
                    "governance_enabled": True
                })
            
            elif policy_decision.action == "REQUIRE_APPROVAL":
                return json.dumps({
                    "status": "pending_approval",
                    "reason": "governance_required",
                    "message": policy_decision.message,
                    "vote_request_id": policy_decision.vote_request_id,
                    "tool": tool_name,
                    "governance_enabled": True,
                    "approval_dashboard": "http://localhost:8080/admin"
                })
        
        client, session_id = await get_backend_session(server_url)
        
        # Make MCP call to backend server
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"gateway-call-{tool_name}-{int(time.time())}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await client.post(
            f"{server_url}/mcp",
            json=mcp_request,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = parse_sse_response(response.text)
            if "result" in result:
                # Extract the actual result from MCP response
                tool_result = result["result"]
                if isinstance(tool_result, dict) and "content" in tool_result:
                    # Return the text content directly
                    content = tool_result["content"]
                    if content and isinstance(content, list) and len(content) > 0:
                        return content[0].get("text", str(tool_result))
                return str(tool_result)
            else:
                return f"Error: {result.get('error', 'Unknown error')}"
        else:
            return f"HTTP Error {response.status_code}: {response.text}"
            
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        return f"Failed to call tool: {str(e)}"
    finally:
        # Always release the session back to the pool
        if session_id:
            await release_backend_session(server_url, session_id)

# Get backend server URL based on environment
def get_hello_server_url() -> str:
    """Get hello server URL - use Docker internal URL since we're in Docker"""
    return "http://hello-world:8000"

def get_latex_server_url() -> str:
    """Get latex server URL - use Docker internal URL since we're in Docker"""
    return "http://latex-server:8000"

def get_redshift_server_url() -> str:
    """Get redshift server URL - use Docker internal URL since we're in Docker"""
    return "http://redshift-server:8000"

@mcp.tool
async def hello_greet(name: str = "World", greeting: str = "Hello") -> str:
    """Generate a greeting message via hello server"""
    return await call_backend_tool_direct(get_hello_server_url(), "greet", {"name": name, "greeting": greeting})

@mcp.tool
async def hello_add_numbers(a: int, b: int) -> str:
    """Add two numbers together via hello server"""
    return await call_backend_tool_direct(get_hello_server_url(), "add_numbers", {"a": a, "b": b})

@mcp.tool
async def hello_get_timestamp() -> str:
    """Get the current timestamp via hello server"""
    return await call_backend_tool_direct(get_hello_server_url(), "get_timestamp", {})

@mcp.tool
async def latex_compile_from_template(template_name: str, variables: dict, filename: str = None) -> str:
    """Compile PDF from LaTeX template with variable substitution"""
    request = {"template_name": template_name, "variables": variables}
    if filename:
        request["filename"] = filename
    return await call_backend_tool_direct(get_latex_server_url(), "compile_from_template", {"request": request})

@mcp.tool
async def latex_list_templates() -> str:
    """List available LaTeX templates"""
    return await call_backend_tool_direct(get_latex_server_url(), "list_templates", {})

@mcp.tool
async def latex_upload_latex_file(content: str, filename: str = None) -> str:
    """Upload LaTeX file for efficient compilation workflow"""
    request = {"content": content}
    if filename:
        request["filename"] = filename
    return await call_backend_tool_direct(get_latex_server_url(), "upload_latex_file", {"request": request})

@mcp.tool
async def latex_compile_latex_by_id(file_id: str, compiler: str = None, output_filename: str = None) -> str:
    """Compile previously uploaded LaTeX file by ID"""
    request = {"file_id": file_id}
    if compiler:
        request["compiler"] = compiler
    if output_filename:
        request["output_filename"] = output_filename
    return await call_backend_tool_direct(get_latex_server_url(), "compile_latex_by_id", {"request": request})

# Redshift tools for enterprise data governance demo
@mcp.tool
async def redshift_list_clusters() -> str:
    """List available Redshift clusters with basic information"""
    return await call_backend_tool_direct(get_redshift_server_url(), "list_clusters", {})

@mcp.tool
async def redshift_list_databases() -> str:
    """List available databases in Redshift clusters"""
    return await call_backend_tool_direct(get_redshift_server_url(), "list_databases", {})

@mcp.tool
async def redshift_list_schemas(database: str) -> str:
    """List available schemas in a specific database"""
    return await call_backend_tool_direct(get_redshift_server_url(), "list_schemas", {"database": database})

@mcp.tool
async def redshift_list_tables(database: str, schema: str = "public") -> str:
    """List available tables and views in a specific schema"""
    return await call_backend_tool_direct(get_redshift_server_url(), "list_tables", {"database": database, "schema": schema})

@mcp.tool
async def redshift_list_columns(database: str, schema: str, table: str) -> str:
    """List column definitions for a specific table"""
    return await call_backend_tool_direct(get_redshift_server_url(), "list_columns", {"database": database, "schema": schema, "table": table})

@mcp.tool
async def redshift_execute_query(query: str, database: str = "production_db", limit: int = 100) -> str:
    """Execute a read-only SQL query with governance controls"""
    return await call_backend_tool_direct(get_redshift_server_url(), "execute_query", {"query": query, "database": database, "limit": limit})

async def register_backend_tools():
    """Initialize tool registry (tools are now statically defined above)"""
    if not tool_registry:
        await initialize_tool_registry()
    logger.info(f"Static proxy tools registered for {len(tool_registry)} backend tools")

# Initialize tools on first use
async def ensure_tools_initialized():
    """Ensure tool registry is initialized before tool calls"""
    if not tool_registry:
        await initialize_tool_registry()

# Concurrent Session Pool Management
import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Set

class SessionStatus(Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    FAILED = "failed"
    INITIALIZING = "initializing"

@dataclass
class MCPSession:
    """Represents a single MCP session with a backend server"""
    session_id: str
    client: httpx.AsyncClient
    server_url: str
    status: SessionStatus
    created_at: float
    last_used: float
    current_request_id: Optional[str] = None
    
    def mark_busy(self, request_id: str):
        """Mark session as busy with a specific request"""
        self.status = SessionStatus.BUSY
        self.current_request_id = request_id
        self.last_used = time.time()
    
    def mark_available(self):
        """Mark session as available for use"""
        self.status = SessionStatus.AVAILABLE
        self.current_request_id = None
        self.last_used = time.time()
    
    def mark_failed(self):
        """Mark session as failed"""
        self.status = SessionStatus.FAILED
        self.current_request_id = None

class SessionPool:
    """Manages a pool of MCP sessions for a backend server"""
    
    def __init__(self, server_url: str, max_sessions: int = 10, session_timeout: float = 300.0):
        self.server_url = server_url
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.sessions: Dict[str, MCPSession] = {}
        self.lock = asyncio.Lock()
        self._cleanup_task = None
        
    async def get_session(self, request_id: str) -> MCPSession:
        """Get an available session, creating one if needed"""
        async with self.lock:
            # First, try to find an available session
            for session in self.sessions.values():
                if session.status == SessionStatus.AVAILABLE:
                    session.mark_busy(request_id)
                    logger.debug(f"Allocated existing session {session.session_id} to request {request_id}")
                    return session
            
            # If no available sessions and under limit, create a new one
            if len(self.sessions) < self.max_sessions:
                session = await self._create_session(request_id)
                logger.debug(f"Created new session {session.session_id} for request {request_id}")
                return session
            
            # All sessions are busy, wait for one to become available
            logger.warning(f"All {self.max_sessions} sessions busy for {self.server_url}, waiting...")
            return await self._wait_for_available_session(request_id)
    
    async def release_session(self, session: MCPSession):
        """Release a session back to the pool"""
        async with self.lock:
            if session.session_id in self.sessions:
                session.mark_available()
                logger.debug(f"Released session {session.session_id} back to pool")
    
    async def _create_session(self, request_id: str) -> MCPSession:
        """Create a new MCP session with the backend server"""
        client = httpx.AsyncClient()
        session_id = f"gateway-{self.server_url.replace('://', '-').replace(':', '-')}-{len(self.sessions)}-{int(time.time())}"
        
        # Create session object first
        session = MCPSession(
            session_id=session_id,
            client=client,
            server_url=self.server_url,
            status=SessionStatus.INITIALIZING,
            created_at=time.time(),
            last_used=time.time(),
            current_request_id=request_id
        )
        
        try:
            # Initialize session
            init_request = {
                "jsonrpc": "2.0",
                "id": f"gateway-init-{session_id}",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {
                        "name": "mcp-gateway",
                        "version": "0.3.0"
                    },
                    "capabilities": {}
                }
            }
            
            response = await client.post(
                f"{self.server_url}/mcp",
                json=init_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Failed to initialize session: {response.status_code}")
            
            # Get session ID from response
            backend_session_id = response.headers.get("mcp-session-id")
            if backend_session_id:
                session.session_id = backend_session_id
            
            # Send initialized notification
            initialized_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            
            await client.post(
                f"{self.server_url}/mcp",
                json=initialized_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": session.session_id
                },
                timeout=10.0
            )
            
            # Mark session as busy and add to pool
            session.mark_busy(request_id)
            self.sessions[session.session_id] = session
            
            # Start cleanup task if not already running
            if not self._cleanup_task:
                self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
            
            return session
            
        except Exception as e:
            session.mark_failed()
            logger.error(f"Failed to create session for {self.server_url}: {e}")
            await client.aclose()
            raise
    
    async def _wait_for_available_session(self, request_id: str, timeout: float = 30.0) -> MCPSession:
        """Wait for an available session with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            async with self.lock:
                # Check for available session
                for session in self.sessions.values():
                    if session.status == SessionStatus.AVAILABLE:
                        session.mark_busy(request_id)
                        return session
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
        
        # Timeout - force create a new session (exceeding max_sessions)
        logger.warning(f"Session wait timeout for {self.server_url}, creating emergency session")
        return await self._create_session(request_id)
    
    async def _cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                current_time = time.time()
                expired_sessions = []
                
                async with self.lock:
                    for session_id, session in self.sessions.items():
                        # Remove failed sessions or sessions that haven't been used recently
                        if (session.status == SessionStatus.FAILED or 
                            (session.status == SessionStatus.AVAILABLE and 
                             current_time - session.last_used > self.session_timeout)):
                            expired_sessions.append(session_id)
                    
                    # Remove expired sessions
                    for session_id in expired_sessions:
                        session = self.sessions.pop(session_id)
                        logger.debug(f"Cleaning up expired session {session_id}")
                        try:
                            await session.client.aclose()
                        except:
                            pass
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
    
    async def close_all_sessions(self):
        """Close all sessions in the pool"""
        async with self.lock:
            for session in self.sessions.values():
                try:
                    await session.client.aclose()
                except:
                    pass
            self.sessions.clear()
            
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

# Global session pool manager
session_pools: Dict[str, SessionPool] = {}

async def get_backend_session(server_url: str) -> tuple[httpx.AsyncClient, str]:
    """Get or create a session for a backend server using session pool"""
    if server_url not in session_pools:
        session_pools[server_url] = SessionPool(server_url)
    
    pool = session_pools[server_url]
    request_id = f"req-{int(time.time())}-{id(asyncio.current_task())}"
    
    session = await pool.get_session(request_id)
    return session.client, session.session_id

async def release_backend_session(server_url: str, session_id: str):
    """Release a session back to the pool"""
    if server_url in session_pools:
        pool = session_pools[server_url]
        for session in pool.sessions.values():
            if session.session_id == session_id:
                await pool.release_session(session)
                break

def parse_sse_response(sse_text: str) -> dict:
    """Parse Server-Sent Events response format"""
    lines = sse_text.strip().split('\n')
    
    # Find the data line
    data_line = None
    for line in lines:
        if line.startswith('data: '):
            data_line = line[6:]  # Remove 'data: ' prefix
            break
    
    if not data_line:
        raise ValueError(f"No data line found in SSE response: {sse_text}")
    
    try:
        return json.loads(data_line)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in SSE data: {data_line}") from e

async def call_backend_tool(tool_name: str, arguments: dict) -> str:
    """Call a tool on a specific backend server using session pool"""
    if tool_name not in tool_registry:
        raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(tool_registry.keys())}")
    
    tool_info = tool_registry[tool_name]
    server_name = tool_info["server"]
    original_tool = tool_info["original_tool"]
    server_url = tool_info["url"]
    session_id = None
    
    try:
        client, session_id = await get_backend_session(server_url)
        
        # Make MCP call to backend server
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"gateway-call-{tool_name}-{int(time.time())}",
            "method": "tools/call",
            "params": {
                "name": original_tool,
                "arguments": arguments
            }
        }
        
        response = await client.post(
            f"{server_url}/mcp",
            json=mcp_request,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = parse_sse_response(response.text)
            if "result" in result:
                # Extract the actual result from MCP response
                tool_result = result["result"]
                if isinstance(tool_result, dict) and "content" in tool_result:
                    # Return the text content directly
                    content = tool_result["content"]
                    if content and isinstance(content, list) and len(content) > 0:
                        return content[0].get("text", str(tool_result))
                return str(tool_result)
            else:
                return f"Error: {result.get('error', 'Unknown error')}"
        else:
            return f"HTTP Error {response.status_code}: {response.text}"
            
    except Exception as e:
        logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
        return f"Failed to call tool: {str(e)}"
    finally:
        # Always release the session back to the pool
        if session_id:
            await release_backend_session(server_url, session_id)

# Authentication helper functions
async def validate_bearer_token(request) -> bool:
    """Validate Bearer token from Authorization header"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Check if token exists in valid tokens
    return hasattr(oauth_token, 'valid_tokens') and token in oauth_token.valid_tokens

def create_auth_error_response(message: str = "Authentication required") -> JSONResponse:
    """Create standardized authentication error response"""
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": "auth-error",
        "error": {
            "code": -32001,
            "message": message,
            "data": {
                "auth_required": True,
                "auth_endpoints": {
                    "discovery": "/.well-known/oauth-authorization-server",
                    "register": "/oauth/register",
                    "authorize": "/oauth/authorize",
                    "token": "/oauth/token"
                }
            }
        }
    }, status_code=401)

# Root endpoint handling
@mcp.custom_route(path="/", methods=["GET", "POST"])
async def root_handler(request):
    """Handle root endpoint - GET redirects to dashboard, POST handles MCP protocol"""
    if request.method == "GET":
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard", status_code=302)
    elif request.method == "POST":
        # Require authentication for MCP protocol access
        if not await validate_bearer_token(request):
            logger.warning(f"Unauthorized MCP access attempt from {request.client.host if request.client else 'unknown'}")
            return create_auth_error_response("Valid OAuth token required for MCP access")
        
        # Forward authenticated MCP requests to the built-in MCP handler
        # Claude Code expects MCP at root, but FastMCP serves at /mcp
        try:
            # Use httpx to forward to the /mcp endpoint on the same server
            import httpx
            
            # Get the request body and headers
            body = await request.body()
            headers = dict(request.headers)
            
            # Remove host header to avoid conflicts
            if 'host' in headers:
                del headers['host']
            
            # Forward to /mcp endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://127.0.0.1:8000/mcp",
                    content=body,
                    headers=headers,
                    timeout=30.0
                )
                
                # Return the response with proper headers
                from fastapi.responses import Response
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
        except Exception as e:
            logger.error(f"Error forwarding MCP request: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": "server-error",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            })

# FastMCP creates /mcp automatically - we can't easily override it
# Main security is at root endpoint (/) which is properly protected
# Document this architectural decision for production deployment

@mcp.custom_route(path="/web", methods=["GET"])
async def web_redirect(request):
    """Redirect /web to dashboard"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard", status_code=302)

# Dashboard moved to /dashboard
@mcp.custom_route(path="/dashboard", methods=["GET"])
async def dashboard(request):
    """Dashboard showing all servers and tools"""
    # Ensure registry is initialized
    if not tool_registry:
        await initialize_tool_registry()
    
    # Group tools by server
    server_tools = {}
    for tool_name, tool_info in tool_registry.items():
        server_name = tool_info["server"]
        if server_name not in server_tools:
            server_tools[server_name] = []
        server_tools[server_name].append({
            "name": tool_name,
            "original_name": tool_info["original_tool"],
            "description": tool_info["description"],
            "url": tool_info["url"]
        })
    
    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MCP Adapter Dashboard</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
                position: relative;
            }}
            .admin-link {{
                position: absolute;
                top: 20px;
                right: 20px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .admin-link:hover {{
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                text-decoration: none;
                color: white;
            }}
            .server-card {{
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .server-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #f0f0f0;
            }}
            .server-name {{
                font-size: 1.5em;
                font-weight: bold;
                color: #333;
            }}
            .server-url {{
                color: #666;
                font-family: monospace;
                font-size: 0.9em;
            }}
            .tools-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 15px;
            }}
            .tool-card {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .tool-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            .tool-name {{
                font-weight: bold;
                color: #495057;
                margin-bottom: 5px;
            }}
            .tool-original {{
                color: #6c757d;
                font-size: 0.9em;
                font-family: monospace;
                margin-bottom: 8px;
            }}
            .tool-description {{
                color: #6c757d;
                font-size: 0.9em;
                line-height: 1.4;
            }}
            .stats {{
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .stat-item {{
                display: inline-block;
                margin: 0 20px;
            }}
            .stat-number {{
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }}
            .stat-label {{
                color: #666;
                font-size: 0.9em;
            }}
            .refresh-btn {{
                background: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 0.9em;
                margin-top: 10px;
                transition: background-color 0.2s;
            }}
            .refresh-btn:hover {{
                background: #5a6fd8;
            }}
            .status-indicator {{
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 8px;
            }}
            .status-online {{
                background: #28a745;
            }}
            .status-offline {{
                background: #dc3545;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/admin" class="admin-link">🛡️ Admin Panel</a>
            <h1>🚀 MCP Adapter Dashboard</h1>
            <p>Aggregating tools from multiple backend MCP servers</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Dashboard</button>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{len(MCP_SERVERS)}</div>
                <div class="stat-label">Connected Servers</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(tool_registry)}</div>
                <div class="stat-label">Available Tools</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{datetime.now().strftime('%b %d %H:%M')}</div>
                <div class="stat-label">Last Updated</div>
            </div>
        </div>
    """
    
    if not server_tools:
        html += """
        <div class="server-card">
            <h3>No servers connected</h3>
            <p>Check your servers.json configuration and ensure backend servers are running.</p>
        </div>
        """
    else:
        for server_name, tools in server_tools.items():
            server_config = MCP_SERVERS.get(server_name, {})
            server_url = server_config.get('url', 'Unknown')
            
            html += f"""
            <div class="server-card">
                <div class="server-header">
                    <div class="server-name">🔗 {server_name}</div>
                    <div class="server-url">{server_url}</div>
                </div>
                <div class="tools-grid">
            """
            
            for tool in tools:
                html += f"""
                    <div class="tool-card">
                        <div class="tool-name">{tool['name']}</div>
                        <div class="tool-original">Original: {tool['original_name']}</div>
                        <div class="tool-description">{tool['description']}</div>
                    </div>
                """
            
            html += """
                </div>
            </div>
            """
    
    html += """
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

# ============================================================================
# REFULGENCE ADMIN DASHBOARD AND GOVERNANCE UI
# ============================================================================

@mcp.custom_route(path="/admin", methods=["GET"])
async def admin_dashboard(request):
    """Refulgence admin dashboard for governance and policy management"""
    try:
        # Check for enhanced UI flag
        ui_mode = os.getenv('UI_MODE', 'comprehensive').lower()
        
        template_map = {
            'basic': 'admin.html',
            'enhanced': 'admin_enhanced.html', 
            'enhanced_real': 'admin_enhanced_real.html',
            'comprehensive': 'admin_comprehensive.html'
        }
        
        template = template_map.get(ui_mode, 'admin_comprehensive.html')
        
        with open(f'templates/{template}', 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # Fallback if template file is missing
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Refulgence Admin - Template Missing</title></head>
        <body>
            <h1>Refulgence Admin Dashboard</h1>
            <p>Template file missing. Please check gateway/templates/admin.html</p>
            <p><a href="/dashboard">Back to Basic Dashboard</a></p>
        </body>
        </html>
        """)

@mcp.custom_route(path="/admin/drill-down", methods=["GET"])
async def admin_drill_down_dashboard(request):
    """Drill-down activity analysis dashboard"""
    try:
        with open('templates/admin_drill_down.html', 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Drill-Down Dashboard - Template Missing</title></head>
        <body>
            <h1>Drill-Down Dashboard</h1>
            <p>Template file missing. Please check gateway/templates/admin_drill_down.html</p>
            <p><a href="/admin">Back to Main Dashboard</a></p>
        </body>
        </html>
        """)

@mcp.custom_route(path="/demo", methods=["GET"])
async def demo_guide(request):
    """Simple demo instructions page"""
    try:
        with open('templates/demo_guide.html', 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Demo Guide - Template Missing</title></head>
        <body>
            <h1>Demo Guide</h1>
            <p>Template file missing. Please check gateway/templates/demo_guide.html</p>
            <p><a href="/admin">Go to Admin Dashboard</a></p>
        </body>
        </html>
        """)

@mcp.custom_route(path="/admin/api/stats", methods=["GET"])
async def admin_api_stats(request):
    """API endpoint for dashboard statistics"""
    try:
        pending_votes = await governance_engine.list_pending_votes()
        
        # Count votes by status (simplified for demo)
        stats = {
            "pending_votes": len(pending_votes),
            "approved_today": 0,  # Would calculate from governance_engine.active_votes
            "denied_today": 0,    # Would calculate from governance_engine.active_votes  
            "connected_servers": len(MCP_SERVERS),
            "total_tools": len(tool_registry),
            "governance_enabled": True,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(stats)
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/pending-votes", methods=["GET"])
async def admin_api_pending_votes(request):
    """API endpoint for pending approval requests"""
    try:
        stakeholder_param = request.query_params.get("stakeholder")
        stakeholder = None
        if stakeholder_param:
            try:
                stakeholder = StakeholderRole(stakeholder_param.upper())
            except ValueError:
                pass
        
        pending_approvals = await get_pending_approvals_for_stakeholder(stakeholder)
        
        # Add risk level and enhanced details
        for approval in pending_approvals:
            # Add risk level based on permission type
            permission_type = PermissionType(approval["permission_type"])
            permission_config = PERMISSION_TYPES.get(permission_type, {})
            approval["risk_level"] = permission_config.get("risk_level", "MEDIUM").lower()
            
            # Add security violations if available in context
            context = approval.get("context", {})
            approval["violations"] = context.get("violations", [])
        
        return JSONResponse(pending_approvals)
    except Exception as e:
        logger.error(f"Error getting pending votes: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/vote", methods=["POST"])
async def admin_api_submit_vote(request):
    """API endpoint for submitting stakeholder votes"""
    try:
        data = await request.json()
        request_id = data.get("request_id")
        stakeholder_name = data.get("stakeholder")
        decision = data.get("decision")
        
        if not all([request_id, stakeholder_name, decision]):
            return JSONResponse({"error": "Missing required fields"}, status_code=400)
        
        success = await submit_stakeholder_vote(request_id, stakeholder_name, decision)
        
        # Track the vote decision
        await track_vote_decision(request_id, stakeholder_name, decision)
        
        if success:
            return JSONResponse({"status": "success", "message": "Vote submitted successfully"})
        else:
            return JSONResponse({"error": "Failed to submit vote"}, status_code=400)
            
    except Exception as e:
        logger.error(f"Error submitting vote: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/servers", methods=["GET"])
async def admin_api_list_servers(request):
    """API endpoint for listing MCP servers"""
    try:
        servers = []
        for server_name, config in MCP_SERVERS.items():
            servers.append({
                "name": server_name.title(),
                "url": config["url"],
                "description": config.get("description", ""),
                "vendor": config.get("vendor", "unknown"),
                "access_level": config.get("access_level", "public"),
                "risk_level": config.get("risk_level", "medium"),
                "status": "online"  # Would check actual status
            })
        
        return JSONResponse(servers)
    except Exception as e:
        logger.error(f"Error listing servers: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/servers", methods=["POST"])
async def admin_api_add_server(request):
    """API endpoint for adding new MCP servers"""
    try:
        data = await request.json()
        
        # Basic validation
        required_fields = ["name", "url", "vendor", "access_level"]
        if not all(field in data for field in required_fields):
            return JSONResponse({"error": "Missing required fields"}, status_code=400)
        
        # In a real implementation, would update servers.json and reload configuration
        # For demo purposes, just return success
        logger.info(f"Request to add new server: {data}")
        
        return JSONResponse({
            "status": "success", 
            "message": f"Server '{data['name']}' would be added (demo mode)"
        })
        
    except Exception as e:
        logger.error(f"Error adding server: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/test-governance", methods=["POST"])
async def admin_api_test_governance(request):
    """API endpoint for testing governance with sample queries"""
    try:
        data = await request.json()
        query = data.get("query", "SELECT * FROM customers")
        subject_type = data.get("subject_type", "coding_agent")
        
        # Test the governance engine with the provided query
        context = {
            "subject_type": subject_type,
            "subject_id": "test_user",
            "test_mode": True
        }
        
        policy_decision = await enforce_policy(
            tool_name="redshift_execute_query",
            arguments={"query": query},
            context=context
        )
        
        # Track the governance test as an activity event
        allowed = policy_decision.action == "ALLOW"
        await track_query_execution(query, f"test_user ({subject_type})", allowed)
        
        if policy_decision.action == "REQUIRE_APPROVAL":
            await track_approval_request("redshift_execute_query", "test_user", 
                                       "HIGH" if "DROP" in query.upper() else "MEDIUM")
        
        return JSONResponse({
            "status": "success",
            "policy_decision": policy_decision.action,
            "message": policy_decision.message,
            "vote_request_id": policy_decision.vote_request_id,
            "query": query,
            "subject_type": subject_type
        })
        
    except Exception as e:
        logger.error(f"Error testing governance: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/activity", methods=["GET"])
async def admin_api_activity_feed(request):
    """API endpoint for live activity feed with filtering support"""
    try:
        limit = int(request.query_params.get("limit", "50"))
        severity = request.query_params.get("severity")  # critical, warning, info, success
        event_type = request.query_params.get("type")    # query_blocked, approval_requested, etc.
        subject_id = request.query_params.get("subject_id")
        time_range = request.query_params.get("time_range", "24h")  # 1h, 6h, 24h, 7d, 30d
        search = request.query_params.get("search", "").lower()
        
        events = activity_tracker.get_recent_events(limit * 2)  # Get more for filtering
        
        # Apply filters
        filtered_events = []
        now = datetime.now(timezone.utc)
        
        # Time range filter
        time_deltas = {
            "1h": 3600,
            "6h": 6 * 3600, 
            "24h": 24 * 3600,
            "7d": 7 * 24 * 3600,
            "30d": 30 * 24 * 3600
        }
        time_threshold = now.timestamp() - time_deltas.get(time_range, 24 * 3600)
        
        for event in events:
            event_dict = event if isinstance(event, dict) else event.to_dict()
            event_time = datetime.fromisoformat(event_dict["timestamp"].replace('Z', '+00:00')).timestamp()
            
            # Apply filters
            if event_time < time_threshold:
                continue
                
            if severity and event_dict["severity"] != severity:
                continue
                
            if event_type and event_dict["type"] != event_type:
                continue
                
            if subject_id and event_dict.get("subject_id") != subject_id:
                continue
                
            if search and search not in event_dict["message"].lower():
                continue
            
            filtered_events.append(event_dict)
            
            if len(filtered_events) >= limit:
                break
        
        return JSONResponse(filtered_events)
    except Exception as e:
        logger.error(f"Error getting activity feed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/metrics", methods=["GET"])
async def admin_api_live_metrics(request):
    """API endpoint for live metrics"""
    try:
        stats = activity_tracker.get_stats()
        return JSONResponse(stats)
    except Exception as e:
        logger.error(f"Error getting live metrics: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "servers": len(MCP_SERVERS),
        "tools": len(tool_registry),
        "session_pools": len(session_pools)
    })

@mcp.custom_route(path="/sessions", methods=["GET"])
async def session_status(request):
    """Session pool status endpoint"""
    session_details = {}
    
    for server_url, pool in session_pools.items():
        sessions = []
        for session_id, session in pool.sessions.items():
            sessions.append({
                "session_id": session_id,
                "status": session.status.value,
                "created_at": session.created_at,
                "last_used": session.last_used,
                "current_request_id": session.current_request_id,
                "age_seconds": time.time() - session.created_at,
                "idle_seconds": time.time() - session.last_used
            })
        
        session_details[server_url] = {
            "pool_config": {
                "max_sessions": pool.max_sessions,
                "session_timeout": pool.session_timeout
            },
            "pool_stats": {
                "total_sessions": len(pool.sessions),
                "available_sessions": sum(1 for s in pool.sessions.values() if s.status == SessionStatus.AVAILABLE),
                "busy_sessions": sum(1 for s in pool.sessions.values() if s.status == SessionStatus.BUSY),
                "failed_sessions": sum(1 for s in pool.sessions.values() if s.status == SessionStatus.FAILED),
                "cleanup_task_running": pool._cleanup_task is not None and not pool._cleanup_task.done()
            },
            "sessions": sessions
        }
    
    return JSONResponse({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "concurrent_sessions_enabled": True,
        "session_pools": session_details
    })

@mcp.custom_route(path="/info", methods=["GET"])
async def server_info(request):
    """Server information endpoint"""
    if not tool_registry:
        await initialize_tool_registry()
    
    # Collect session pool statistics
    session_stats = {}
    for server_url, pool in session_pools.items():
        stats = {
            "total_sessions": len(pool.sessions),
            "available_sessions": sum(1 for s in pool.sessions.values() if s.status == SessionStatus.AVAILABLE),
            "busy_sessions": sum(1 for s in pool.sessions.values() if s.status == SessionStatus.BUSY),
            "failed_sessions": sum(1 for s in pool.sessions.values() if s.status == SessionStatus.FAILED),
            "max_sessions": pool.max_sessions,
            "session_timeout": pool.session_timeout
        }
        session_stats[server_url] = stats
    
    return JSONResponse({
        "name": "MCP Adapter",
        "version": "0.3.0",
        "description": "Aggregates tools from multiple backend MCP servers",
        "connected_servers": list(MCP_SERVERS.keys()),
        "available_tools": list(tool_registry.keys()),
        "tool_count": len(tool_registry),
        "server_count": len(MCP_SERVERS),
        "session_pools": session_stats,
        "concurrent_sessions_enabled": True
    })

# OAuth/Authentication endpoints for Claude Code compatibility
@mcp.custom_route(path="/.well-known/oauth-protected-resource", methods=["GET"])
async def oauth_protected_resource(request):
    """OAuth 2.1 protected resource discovery endpoint"""
    # Use the external port for Docker container
    base_url = "http://localhost:8080"
    return JSONResponse({
        "resource_server": base_url,
        "authorization_servers": [base_url],
        "scopes_supported": ["read", "write"],
        "bearer_methods_supported": ["header", "body"],
        "resource_documentation": f"{base_url}/dashboard"
    })

# User Management API Endpoints
@mcp.custom_route(path="/admin/api/users", methods=["GET"])
async def get_users(request):
    """Get all users with optional filtering and search"""
    try:
        query_params = dict(request.query_params)
        search = query_params.get("search", "")
        role_filter = query_params.get("role")
        status_filter = query_params.get("status")
        department_filter = query_params.get("department")

        if search:
            # Search users
            filters = {}
            if role_filter:
                filters["role"] = role_filter
            if status_filter:
                filters["status"] = status_filter
            if department_filter:
                filters["department"] = department_filter

            users = await user_store.search_users(search, filters)
        else:
            # Get all users
            users = await user_store.get_all_users()

            # Apply filters
            if role_filter:
                users = [u for u in users if u.role.value == role_filter]
            if status_filter:
                users = [u for u in users if u.status.value == status_filter]
            if department_filter:
                users = [u for u in users if u.department == department_filter]

        # Convert to dictionaries for JSON response
        users_data = [user.to_dict() for user in users]

        return JSONResponse({
            "users": users_data,
            "total": len(users_data),
            "demo_mode": user_store.get_demo_mode()
        })

    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/users/{user_id}", methods=["GET"])
async def get_user(request):
    """Get specific user by ID"""
    try:
        user_id = request.path_params["user_id"]
        user = await user_store.get_user(user_id)

        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        return JSONResponse({
            "user": user.to_dict(),
            "demo_mode": user_store.get_demo_mode()
        })

    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/users", methods=["POST"])
async def create_user(request):
    """Create new user (real mode only)"""
    try:
        if user_store.get_demo_mode():
            return JSONResponse({"error": "Cannot create users in demo mode"}, status_code=400)

        user_data = await request.json()
        user = await user_store.create_user(user_data)

        return JSONResponse({
            "user": user.to_dict(),
            "message": "User created successfully"
        })

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/users/{user_id}", methods=["PUT"])
async def update_user(request):
    """Update user data"""
    try:
        user_id = request.path_params["user_id"]
        updates = await request.json()

        user = await user_store.update_user(user_id, updates)

        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        return JSONResponse({
            "user": user.to_dict(),
            "message": "User updated successfully"
        })

    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/users/{user_id}", methods=["DELETE"])
async def delete_user(request):
    """Delete user (real mode only)"""
    try:
        if user_store.get_demo_mode():
            return JSONResponse({"error": "Cannot delete users in demo mode"}, status_code=400)

        user_id = request.path_params["user_id"]
        success = await user_store.delete_user(user_id)

        if not success:
            return JSONResponse({"error": "User not found"}, status_code=404)

        return JSONResponse({"message": "User deleted successfully"})

    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/user-stats", methods=["GET"])
async def get_user_stats(request):
    """Get aggregate user statistics"""
    try:
        stats = await user_store.get_user_stats()
        return JSONResponse(stats)

    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/demo/reset", methods=["POST"])
async def reset_demo_data(request):
    """Reset demo data (demo mode only)"""
    try:
        if not user_store.get_demo_mode():
            return JSONResponse({"error": "Reset only available in demo mode"}, status_code=400)

        await user_store.reset_demo_data()

        return JSONResponse({
            "message": "Demo data reset successfully",
            "demo_mode": True
        })

    except Exception as e:
        logger.error(f"Error resetting demo data: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/policies", methods=["POST"])
async def create_policy(request):
    """Create a new governance policy"""
    try:
        # Parse request body
        body = await request.json()

        # Validate required fields
        required_fields = ['name', 'description', 'action', 'risk_level', 'category']
        for field in required_fields:
            if not body.get(field):
                return JSONResponse({"error": f"Missing required field: {field}"}, status_code=400)

        # Generate policy ID
        import time
        policy_id = f"pol_{int(time.time())}_{hash(body['name']) % 10000}"

        # Create policy object
        policy = {
            "id": policy_id,
            "name": body['name'],
            "description": body['description'],
            "action": body['action'],
            "risk_level": body['risk_level'],
            "category": body['category'],
            "query_pattern": body.get('query_pattern', ''),
            "subject_type": body.get('subject_type', 'any'),
            "approvers": body.get('approvers', ['CISO']),
            "active": body.get('active', True),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "admin",  # TODO: Get from auth context
            "version": 1
        }

        # Save policy to governance system
        await save_policy_to_governance(policy)

        # Track policy creation activity
        await track_security_event("policy_created", {
            "policy_id": policy_id,
            "policy_name": policy['name'],
            "risk_level": policy['risk_level'],
            "category": policy['category']
        })

        logger.info(f"Policy created successfully: {policy_id}")

        return JSONResponse({
            "success": True,
            "policy_id": policy_id,
            "message": "Policy created successfully",
            "policy": policy
        })

    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON in request body"}, status_code=400)
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@mcp.custom_route(path="/admin/api/start-simulation", methods=["POST"])
async def start_simulation_endpoint(request):
    """Start the high-frequency activity simulation"""
    try:
        if user_store.demo_mode:
            await user_store.start_simulation_async()
            return JSONResponse({
                "success": True,
                "message": "High-frequency activity simulation started",
                "mode": "demo",
                "frequency": "10-100 events per second"
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Simulation only available in demo mode",
                "mode": "production"
            }, status_code=400)
    except Exception as e:
        logger.error(f"Error starting simulation: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

async def save_policy_to_governance(policy):
    """Save policy to the governance system"""
    try:
        # Load existing policies
        policies_file = 'policies.json'
        policies_data = {}

        try:
            with open(policies_file, 'r') as f:
                policies_data = json.load(f)
        except FileNotFoundError:
            policies_data = {
                "policies": [],
                "policy_rules": {},
                "approval_requests": [],
                "approval_cache": {},
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

        # Add new policy to policies list
        if "policies" not in policies_data:
            policies_data["policies"] = []

        policies_data["policies"].append(policy)

        # Update policy rules for governance engine
        if "policy_rules" not in policies_data:
            policies_data["policy_rules"] = {}

        rule_key = f"{policy['category']}_{policy['subject_type']}"
        policies_data["policy_rules"][rule_key] = {
            "action": policy['action'],
            "approvers": policy['approvers'],
            "risk_level": policy['risk_level'],
            "conditions": {
                "query_pattern": policy['query_pattern']
            }
        }

        # Update timestamp
        policies_data["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Save back to file
        with open(policies_file, 'w') as f:
            json.dump(policies_data, f, indent=2)

        logger.info(f"Policy {policy['id']} saved to governance system")

    except Exception as e:
        logger.error(f"Error saving policy to governance: {e}")
        raise

@mcp.custom_route(path="/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_discovery(request):
    """OAuth 2.1 discovery endpoint"""
    # Use the external port for Docker container
    base_url = "http://localhost:8080"
    return JSONResponse({
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "introspection_endpoint": f"{base_url}/oauth/tokeninfo",
        "registration_endpoint": f"{base_url}/oauth/register",
        "scopes_supported": ["read", "write"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"],
        "introspection_endpoint_auth_methods_supported": ["none", "client_secret_basic"]
    })

@mcp.custom_route(path="/oauth/register", methods=["POST"])
async def oauth_register(request):
    """Dynamic client registration endpoint"""
    try:
        # For development, we'll accept any client registration
        request_data = await request.json()
        
        client_id = f"mcp-client-{hash(str(request_data)) % 10000}"
        
        return JSONResponse({
            "client_id": client_id,
            "client_name": request_data.get("client_name", "MCP Client"),
            "redirect_uris": request_data.get("redirect_uris", []),
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none"
        })
    except Exception as e:
        logger.error(f"OAuth registration error: {e}")
        return JSONResponse({"error": "invalid_request"}, status_code=400)

@mcp.custom_route(path="/oauth/authorize", methods=["GET"])
async def oauth_authorize(request):
    """OAuth authorization endpoint"""
    from fastapi.responses import RedirectResponse
    
    # For development, auto-approve all authorization requests
    query_params = dict(request.query_params)
    redirect_uri = query_params.get("redirect_uri")
    state = query_params.get("state")
    
    if not redirect_uri:
        return JSONResponse({"error": "invalid_request"}, status_code=400)
    
    # Generate a dummy authorization code
    auth_code = f"auth-{hash(str(query_params)) % 100000}"
    
    # Redirect back to Claude Code's callback server
    redirect_url = f"{redirect_uri}?code={auth_code}&state={state}"
    
    return RedirectResponse(url=redirect_url, status_code=302)

@mcp.custom_route(path="/oauth/token", methods=["POST"])
async def oauth_token(request):
    """OAuth token endpoint"""
    try:
        # Handle both form data and JSON
        try:
            form_data = await request.form()
            data = dict(form_data)
        except:
            data = await request.json()
        
        grant_type = data.get("grant_type")
        if grant_type != "authorization_code":
            return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
        
        # Generate a persistent access token
        import time
        access_token = f"mcp-token-{int(time.time())}-{hash(str(data)) % 100000}"
        
        # Store token in memory for validation (in production, use proper storage)
        if not hasattr(oauth_token, 'valid_tokens'):
            oauth_token.valid_tokens = set()
        oauth_token.valid_tokens.add(access_token)
        
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer", 
            "expires_in": 7200,  # 2 hours
            "scope": "read write",
            "refresh_token": f"refresh-{access_token}"
        })
    except Exception as e:
        logger.error(f"OAuth token error: {e}")
        return JSONResponse({"error": "invalid_request"}, status_code=400)

# Add token validation endpoint
@mcp.custom_route(path="/oauth/tokeninfo", methods=["GET", "POST"])
async def token_info(request):
    """Token introspection endpoint"""
    try:
        import time
        
        # Get token from Authorization header or form
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            # Try form data
            try:
                form_data = await request.form()
                token = form_data.get("token", "")
            except:
                data = await request.json()
                token = data.get("token", "")
        
        # Validate token
        is_valid = hasattr(oauth_token, 'valid_tokens') and token in oauth_token.valid_tokens
        
        return JSONResponse({
            "active": is_valid,
            "token_type": "bearer" if is_valid else None,
            "scope": "read write" if is_valid else None,
            "exp": int(time.time()) + 7200 if is_valid else None
        })
    except Exception as e:
        logger.error(f"Token info error: {e}")
        return JSONResponse({"active": False})

if __name__ == "__main__":
    port = int(os.getenv('SERVER_PORT', 8000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    logger.info(f"Starting MCP Adapter on port {port}")
    logger.info(f"Debug mode: {debug}")

    # Start user simulation once event loop is available
    user_store.start_simulation()

    # Run the MCP server (will serve MCP at /mcp and dashboard at /)
    mcp.run(transport="http", host="0.0.0.0", port=port)