#!/usr/bin/env python3
"""
Script to create the America poem PDF using the fixed MCP infrastructure
"""

import asyncio
import sys
import os

# Add the test directory to the Python path
sys.path.append('tests')

from integration.conftest import MCPToolHelper

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

async def main():
    """Create and compile the America poem"""
    print("Creating America poem PDF...")
    
    async with MCPToolHelper(GATEWAY_URL) as helper:
        # Step 1: Upload the LaTeX file
        print("1. Uploading LaTeX file...")
        upload_result = await helper.call_tool(
            "latex_upload_latex_file", 
            {
                "content": AMERICA_POEM,
                "filename": "america_poem.tex"
            }
        )
        
        if not upload_result.get("success"):
            print(f"Upload failed: {upload_result}")
            return
            
        file_id = upload_result.get("file_id")
        print(f"   File uploaded with ID: {file_id}")
        
        # Step 2: Compile to PDF
        print("2. Compiling to PDF...")
        compile_result = await helper.call_tool(
            "latex_compile_latex_by_id",
            {
                "file_id": file_id,
                "output_filename": "america_poem.pdf"
            }
        )
        
        if compile_result.get("success"):
            pdf_url = compile_result.get("pdf_download_url")
            print(f"   PDF compiled successfully!")
            print(f"   Download URL: {pdf_url}")
            print("\n✅ SUCCESS: Your America poem has been compiled to PDF!")
        else:
            print(f"   Compilation failed: {compile_result}")

if __name__ == "__main__":
    asyncio.run(main())