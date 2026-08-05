"""Tests for Session Summary UI Tool"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from src.tools.ui_session_summary import generate_session_summary_ui

async def test_basic():
    result = await generate_session_summary_ui("test-001")
    assert result.template_id == "com.learning-system.session-summary"
    sections = result.template_data["sections"]
    assert len(sections) >= 4
    print(f"[OK] Generated {len(sections)} sections")
    
    jsonrpc = result.to_jsonrpc(1)
    assert jsonrpc["jsonrpc"] == "2.0"
    assert "_meta" in jsonrpc
    print("[OK] JSON-RPC valid")

asyncio.run(test_basic())
print("\n[PASSED] Session Summary UI tests passed!")
