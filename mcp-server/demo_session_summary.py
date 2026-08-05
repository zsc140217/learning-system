"""
Demo: Session Summary UI Tool
Shows complete JSON-RPC response
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import json
from src.tools.ui_session_summary import generate_session_summary_ui


async def main():
    print("=== MCP Apps: Session Summary UI Demo ===\n")
    
    # Generate UI
    result = await generate_session_summary_ui("demo-session-001")
    
    # Convert to JSON-RPC
    jsonrpc = result.to_jsonrpc(request_id=1)
    
    # Pretty print
    print(json.dumps(jsonrpc, indent=2, ensure_ascii=False))
    
    print("\n=== Summary ===")
    print(f"Template ID: {result.template_id}")
    print(f"Sections: {len(result.template_data['sections'])}")
    
    for i, section in enumerate(result.template_data['sections'], 1):
        print(f"  {i}. {section['type']}")


if __name__ == "__main__":
    asyncio.run(main())
