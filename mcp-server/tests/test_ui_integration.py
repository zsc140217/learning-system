"""
Integration tests for all UI templates
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools import (
    generate_session_summary_ui,
    generate_knowledge_graph_ui,
    generate_project_config_ui,
    generate_review_dashboard_ui
)


async def test_full_workflow():
    """Test complete UI workflow."""
    print("=" * 60)
    print("UI Integration Tests")
    print("=" * 60)

    # Test 1: Session Summary UI
    print("\n[Test 1] Session Summary UI...")
    summary = await generate_session_summary_ui("sess-001")
    assert summary.template_id == "com.learning-system.session-summary"
    assert "sections" in summary.data
    assert len(summary.data["sections"]) == 5
    print(f"[OK] Generated {len(summary.data['sections'])} sections")

    # Test 2: Knowledge Graph UI
    print("\n[Test 2] Knowledge Graph UI...")
    kg_result = await generate_knowledge_graph_ui(knowledge_ids=["kp-001"], depth=2)
    assert kg_result.template_id == "com.learning-system.knowledge-graph"
    assert "nodes" in kg_result.data
    assert "edges" in kg_result.data
    assert len(kg_result.data["nodes"]) <= 100
    print(f"[OK] Generated graph with {len(kg_result.data['nodes'])} nodes")

    # Test 3: Project Config UI
    print("\n[Test 3] Project Config UI...")
    config = await generate_project_config_ui()
    assert config.template_id == "com.learning-system.project-config"
    assert "steps" in config.data
    assert len(config.data["steps"]) == 4
    assert "actions" in config.data
    print(f"[OK] Generated wizard with {len(config.data['steps'])} steps")

    # Test 4: Review Dashboard UI
    print("\n[Test 4] Review Dashboard UI...")
    dashboard = await generate_review_dashboard_ui()
    assert dashboard.template_id == "com.learning-system.review-dashboard"
    assert "widgets" in dashboard.data
    assert len(dashboard.data["widgets"]) == 4
    assert "quick_actions" in dashboard.data
    print(f"[OK] Generated dashboard with {len(dashboard.data['widgets'])} widgets")

    print("\n" + "=" * 60)
    print("All integration tests passed!")
    print("=" * 60)


async def test_jsonrpc_format():
    """Test JSON-RPC format compliance."""
    print("\n[Test] JSON-RPC Format Compliance...")

    summary = await generate_session_summary_ui("sess-001")
    jsonrpc = summary.to_jsonrpc(request_id=1)

    # Validate JSON-RPC structure
    assert "jsonrpc" in jsonrpc
    assert jsonrpc["jsonrpc"] == "2.0"
    assert "id" in jsonrpc
    assert jsonrpc["id"] == 1
    assert "result" in jsonrpc
    assert "_meta" in jsonrpc

    # Validate _meta field
    meta = jsonrpc["_meta"]
    assert "io.modelcontextprotocol/uiTemplate" in meta

    ui_template = meta["io.modelcontextprotocol/uiTemplate"]
    assert "templateId" in ui_template
    assert "templatePath" in ui_template
    assert "data" in ui_template

    print("[OK] JSON-RPC format valid")


async def test_error_handling():
    """Test error handling."""
    print("\n[Test] Error Handling...")

    try:
        # Invalid depth
        await generate_knowledge_graph_ui(depth=5)
        assert False, "Should raise ValueError"
    except ValueError as e:
        print(f"[OK] Caught expected error: {e}")

    print("[OK] Error handling works")


async def test_performance():
    """Test rendering performance."""
    print("\n[Test] Performance...")

    import time

    start = time.time()
    await generate_session_summary_ui("sess-001")
    duration = time.time() - start

    assert duration < 0.5, f"Rendering too slow: {duration}s"
    print(f"[OK] Rendering took {duration:.3f}s (< 0.5s)")


if __name__ == "__main__":
    async def main():
        try:
            await test_full_workflow()
            await test_jsonrpc_format()
            await test_error_handling()
            await test_performance()

            print("\n" + "=" * 60)
            print("SUCCESS: All tests passed!")
            print("=" * 60)
        except AssertionError as e:
            print(f"\n[FAILED] {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    asyncio.run(main())
