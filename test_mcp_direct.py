#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28",
# ]
# ///
"""Direct MCP server connectivity test - bypasses Claude Code entirely"""

import asyncio
import httpx
import json
from typing import Dict, Any

async def test_mcp_server(base_url: str, server_name: str) -> bool:
    """Test if an MCP server is responding correctly"""
    print(f"\n{'='*60}")
    print(f"Testing {server_name} at {base_url}")
    print('='*60)
    
    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Initialize MCP session
            init_request = {
                "jsonrpc": "2.0",
                "id": "init-1",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "direct-test", "version": "1.0.0"},
                    "capabilities": {}
                }
            }
            
            print(f"1. Sending initialize request...")
            response = await client.post(
                f"{base_url}/mcp",  # Remove trailing slash, let redirect happen
                json=init_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                follow_redirects=True  # Follow 307 redirects
            )
            
            if response.status_code != 200:
                print(f"   ❌ Initialize failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
            # Get session ID from headers (FastMCP style)
            session_id = response.headers.get('mcp-session-id')
            
            if not session_id:
                print(f"   ❌ No session ID in headers")
                print(f"   Headers: {dict(response.headers)}")
                return False
            
            print(f"   ✅ Session initialized: {session_id}")
            
            # Also verify the response data
            for line in response.text.split('\n'):
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'result' in data:
                            server_info = data['result'].get('serverInfo', {})
                            print(f"   Server: {server_info.get('name')} v{server_info.get('version')}")
                            break
                    except json.JSONDecodeError:
                        pass
            
            # Step 2: Send initialized notification
            initialized_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            
            print(f"2. Sending initialized notification...")
            response = await client.post(
                f"{base_url}/mcp",
                json=initialized_request,
                headers={
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id
                },
                follow_redirects=True
            )
            
            if response.status_code != 200:
                print(f"   ❌ Initialized notification failed: HTTP {response.status_code}")
                return False
            print(f"   ✅ Session ready")
            
            # Step 3: List available tools
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": "list-1",
                "method": "tools/list",
                "params": {}
            }
            
            print(f"3. Listing available tools...")
            response = await client.post(
                f"{base_url}/mcp",
                json=list_tools_request,
                headers={
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id
                },
                follow_redirects=True
            )
            
            if response.status_code != 200:
                print(f"   ❌ List tools failed: HTTP {response.status_code}")
                return False
            
            # Parse tools from SSE response
            tools = []
            for line in response.text.split('\n'):
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    if 'result' in data and 'tools' in data['result']:
                        tools = data['result']['tools']
                        break
            
            print(f"   ✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"      - {tool['name']}: {tool.get('description', 'No description')}")
            
            # Step 4: Test a simple tool call (if available)
            if server_name == "Gateway" and any(t['name'] == 'hello_greet' for t in tools):
                print(f"4. Testing hello_greet tool...")
                tool_request = {
                    "jsonrpc": "2.0",
                    "id": "tool-1",
                    "method": "tools/call",
                    "params": {
                        "name": "hello_greet",
                        "arguments": {"name": "MCP Test"}
                    }
                }
                
                response = await client.post(
                    f"{base_url}/mcp",
                    json=tool_request,
                    headers={
                        "Content-Type": "application/json",
                        "Mcp-Session-Id": session_id
                    },
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    for line in response.text.split('\n'):
                        if line.startswith('data: '):
                            data = json.loads(line[6:])
                            if 'result' in data:
                                content = data['result'].get('content', [])
                                if content and 'text' in content[0]:
                                    print(f"   ✅ Tool response: {content[0]['text']}")
                                    break
                else:
                    print(f"   ❌ Tool call failed: HTTP {response.status_code}")
            
            print(f"\n✅ {server_name} MCP server is working correctly!")
            return True
            
        except httpx.ConnectError as e:
            print(f"❌ Connection failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

async def check_docker_services():
    """Check if Docker services are running"""
    print("\n" + "="*60)
    print("Docker Service Status")
    print("="*60)
    
    import subprocess
    result = subprocess.run(
        ["docker-compose", "ps"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    # Also check Docker networks
    print("\n" + "="*60)
    print("Docker Networks")
    print("="*60)
    result = subprocess.run(
        ["docker", "network", "ls"],
        capture_output=True,
        text=True
    )
    print(result.stdout)

async def main():
    """Test all MCP servers"""
    print("MCP DIRECT CONNECTIVITY TEST")
    print("This bypasses Claude Code and tests MCP servers directly")
    
    # Check Docker first
    await check_docker_services()
    
    # Test each server
    servers = [
        ("http://localhost:8080", "Gateway"),
        ("http://localhost:8001", "Hello World"),
        ("http://localhost:8002", "LaTeX Server"),
    ]
    
    results = {}
    for url, name in servers:
        results[name] = await test_mcp_server(url, name)
        await asyncio.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_working = all(results.values())
    
    for name, success in results.items():
        status = "✅ WORKING" if success else "❌ FAILED"
        print(f"{name:15} : {status}")
    
    print("\n" + "="*60)
    if all_working:
        print("✅ ALL MCP SERVERS ARE WORKING CORRECTLY!")
        print("\nThis means the issue is likely with Claude Code, not your MCP servers.")
        print("Your MCP implementation is functioning properly.")
    else:
        print("❌ Some MCP servers are not responding correctly.")
        print("Check the failed servers above for details.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())