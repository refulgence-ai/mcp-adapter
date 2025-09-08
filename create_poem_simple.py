#!/usr/bin/env python3
"""
Simple script to create America poem PDF using direct HTTP calls
"""

import asyncio
import httpx
import json

GATEWAY_URL = "http://localhost:8080"

AMERICA_POEM = r"""
\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=1in]{geometry}
\usepackage{titling}
\usepackage{verse}

\title{Land of Liberty}
\author{A Poem About America}
\date{\today}

\begin{document}

\maketitle

\begin{verse}
Across the amber waves of grain,\\
Where purple mountains touch the sky,\\
From sea to shining sea's refrain,\\
The eagle soars forever high.

Land of the free, home of the brave,\\
Where dreams are born and futures made,\\
From valley green to ocean wave,\\
A tapestry of hope displayed.

In cities tall and prairies wide,\\
Where liberty's torch burns so bright,\\
United we stand, side by side,\\
Guardians of freedom's sacred light.

O beautiful, America,\\
Your stars and stripes forever wave,\\
Through trials faced and victories won,\\
Land of the free, home of the brave.
\end{verse}

\vspace{1cm}

\begin{center}
\textit{A celebration of America's enduring spirit and natural beauty}
\end{center}

\end{document}
""".strip()

def parse_sse_response(text):
    """Parse Server-Sent Events response"""
    lines = text.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            return json.loads(line[6:])  # Remove 'data: ' prefix
    return {}

async def main():
    """Create and compile the America poem"""
    print("Creating America poem PDF using the fixed MCP infrastructure...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Initialize MCP session
        print("1. Initializing MCP session...")
        init_response = await client.post(
            f"{GATEWAY_URL}/mcp",  # No trailing slash!
            json={
                "jsonrpc": "2.0",
                "id": "init-1", 
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "poem-creator", "version": "1.0"},
                    "capabilities": {}
                }
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
        )
        
        if init_response.status_code != 200:
            print(f"Failed to initialize: {init_response.status_code}")
            return
            
        session_id = init_response.headers.get("mcp-session-id")
        print(f"   Session ID: {session_id}")
        
        # Step 2: Send initialized notification
        await client.post(
            f"{GATEWAY_URL}/mcp",  # No trailing slash!
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized", 
                "params": {}
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id
            }
        )
        
        # Step 3: Upload LaTeX file
        print("2. Uploading LaTeX file...")
        upload_response = await client.post(
            f"{GATEWAY_URL}/mcp",  # No trailing slash!
            json={
                "jsonrpc": "2.0",
                "id": "upload-1",
                "method": "tools/call",
                "params": {
                    "name": "latex_upload_latex_file",
                    "arguments": {
                        "content": AMERICA_POEM,
                        "filename": "america_poem.tex"
                    }
                }
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id
            }
        )
        
        if upload_response.status_code != 200:
            print(f"Upload failed: {upload_response.status_code} - {upload_response.text}")
            return
            
        upload_result = parse_sse_response(upload_response.text)
        if "error" in upload_result:
            print(f"Upload error: {upload_result['error']}")
            return
            
        file_id = upload_result["result"]["content"][0]["text"]
        file_data = json.loads(file_id)
        actual_file_id = file_data["file_id"]
        print(f"   File uploaded with ID: {actual_file_id}")
        
        # Step 4: Compile to PDF
        print("3. Compiling to PDF...")
        compile_response = await client.post(
            f"{GATEWAY_URL}/mcp",  # No trailing slash!
            json={
                "jsonrpc": "2.0",
                "id": "compile-1",
                "method": "tools/call",
                "params": {
                    "name": "latex_compile_latex_by_id",
                    "arguments": {
                        "file_id": actual_file_id,
                        "output_filename": "america_poem.pdf"
                    }
                }
            },
            headers={
                "Content-Type": "application/json", 
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id
            }
        )
        
        if compile_response.status_code != 200:
            print(f"Compilation failed: {compile_response.status_code} - {compile_response.text}")
            return
            
        compile_result = parse_sse_response(compile_response.text)
        if "error" in compile_result:
            print(f"Compilation error: {compile_result['error']}")
            return
            
        result_text = compile_result["result"]["content"][0]["text"] 
        result_data = json.loads(result_text)
        
        if result_data.get("success"):
            print(f"✅ SUCCESS: America poem compiled to PDF!")
            print(f"   PDF file: {result_data.get('output_file')}")
            if 'pdf_download_url' in result_data:
                print(f"   Download URL: {result_data['pdf_download_url']}")
        else:
            print(f"Compilation failed: {result_data}")

if __name__ == "__main__":
    asyncio.run(main())