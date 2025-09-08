#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28",
# ]
# ///
"""Test what Claude Code might be doing that causes 'reconnection failed'"""

import asyncio
import httpx
import json

async def simulate_claude_code():
    """Simulate Claude Code's connection pattern"""
    
    print("SIMULATING CLAUDE CODE CONNECTION PATTERN")
    print("=" * 60)
    
    # Claude Code likely does:
    # 1. Initial authentication (works)
    # 2. Tries to establish persistent connection (fails)
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        # Step 1: Authentication (this works according to error message)
        print("\n1. AUTHENTICATION PHASE")
        print("-" * 40)
        
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-1", 
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "claude-code-sim", "version": "1.0.0"},
                "capabilities": {}
            }
        }
        
        print("Sending initialize...")
        try:
            response = await client.post(
                "http://localhost:8080/mcp",
                json=init_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                follow_redirects=True
            )
            
            session_id = response.headers.get('mcp-session-id')
            print(f"✅ Authentication successful!")
            print(f"   Session ID: {session_id}")
            print(f"   Status: {response.status_code}")
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return
        
        # Step 2: Server Reconnection (this is what fails)
        print("\n2. SERVER RECONNECTION PHASE") 
        print("-" * 40)
        print("Attempting what Claude Code calls 'server reconnection'...")
        
        # Theory 1: Claude Code might expect SSE stream to stay open
        print("\n   Theory 1: Testing SSE stream persistence...")
        try:
            # Try to establish SSE connection
            async with client.stream(
                "POST",
                "http://localhost:8080/mcp",
                json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "Mcp-Session-Id": session_id
                }
            ) as stream_response:
                print(f"   Stream status: {stream_response.status_code}")
                if stream_response.status_code == 200:
                    print("   ✅ SSE stream established")
                else:
                    print(f"   ❌ SSE stream failed: {stream_response.status_code}")
        except Exception as e:
            print(f"   ❌ SSE stream error: {e}")
        
        # Theory 2: Claude Code might try WebSocket upgrade
        print("\n   Theory 2: Testing WebSocket-like persistent connection...")
        try:
            response = await client.post(
                "http://localhost:8080/mcp",
                json={"jsonrpc": "2.0", "id": "ping", "method": "ping", "params": {}},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": session_id,
                    "Connection": "keep-alive"  # Request persistent connection
                }
            )
            if response.status_code == 200:
                print("   ✅ Keep-alive connection works")
            else:
                print(f"   ❌ Keep-alive failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Persistent connection error: {e}")
        
        # Theory 3: Claude Code might expect session to persist across reconnects
        print("\n   Theory 3: Testing session persistence after disconnect...")
        
    # Simulate disconnect/reconnect
    print("\n3. SIMULATING DISCONNECT/RECONNECT")
    print("-" * 40)
    print("Creating new client (simulating Claude Code restart)...")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as new_client:
        # Try to use old session
        print(f"Attempting to reuse session: {session_id}")
        try:
            response = await new_client.post(
                "http://localhost:8080/mcp",
                json={"jsonrpc": "2.0", "id": "test", "method": "tools/list", "params": {}},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": session_id
                }
            )
            
            if response.status_code == 200:
                print("✅ Session reuse successful - server maintains session state")
            else:
                print(f"❌ Session reuse failed ({response.status_code}) - this might be the 'reconnection failed'")
                print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Reconnection error: {e}")
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("-" * 40)
    print("If 'Authentication successful' but 'server reconnection failed',")
    print("Claude Code might be expecting:")
    print("1. Persistent SSE streams (not just request/response)")
    print("2. WebSocket-like persistent connections")
    print("3. Session state to survive client reconnections")
    print("4. Different endpoint structure (e.g., separate auth vs data endpoints)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(simulate_claude_code())