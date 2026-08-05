"""
Demo script for knowledge graph UI generation
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.tools.ui_knowledge_graph import generate_knowledge_graph_ui


async def main():
    print("=" * 60)
    print("Knowledge Graph UI Demo")
    print("=" * 60)

    # Test 1: Full graph
    print("\n[Test 1] Generating full knowledge graph...")
    result = await generate_knowledge_graph_ui()

    print(f"[OK] Generated graph with {len(result.data['nodes'])} nodes")
    print(f"[OK] Generated graph with {len(result.data['edges'])} edges")
    print(f"[OK] Template ID: {result.template_id}")
    print(f"[OK] Template path: {result.template_path}")

    # Convert to JSON-RPC
    jsonrpc = result.to_jsonrpc(request_id=1)

    # Validate structure
    assert "jsonrpc" in jsonrpc, "Missing jsonrpc field"
    assert jsonrpc["jsonrpc"] == "2.0", "Invalid jsonrpc version"
    assert "result" in jsonrpc, "Missing result field"
    assert "_meta" in jsonrpc, "Missing _meta field"
    assert "io.modelcontextprotocol/uiTemplate" in jsonrpc["_meta"], "Missing uiTemplate meta"

    print("[OK] JSON-RPC structure valid")

    # Test 2: Filtered graph
    print("\n[Test 2] Generating filtered graph (kp-001, depth=2)...")
    result2 = await generate_knowledge_graph_ui(
        knowledge_ids=["kp-001"],
        depth=2
    )

    print(f"[OK] Filtered graph has {len(result2.data['nodes'])} nodes")
    print(f"[OK] Filtered graph has {len(result2.data['edges'])} edges")

    # Test 3: Node limit
    print("\n[Test 3] Testing node limit...")
    assert len(result.data['nodes']) <= 100, "Node count exceeds limit"
    print("[OK] Node count within limit")

    # Test 4: Color assignment
    print("\n[Test 4] Testing color assignment...")
    for node in result.data['nodes']:
        assert 'color' in node, f"Node {node['id']} missing color"
    print("[OK] All nodes have colors")

    # Test 5: Config validation
    print("\n[Test 5] Testing config...")
    config = result.data['config']
    assert config['width'] == 800, "Invalid width"
    assert config['height'] == 600, "Invalid height"
    assert config['charge_strength'] == -300, "Invalid charge strength"
    print("[OK] Config valid")

    # Save sample output
    output_file = Path(__file__).parent / "demo_knowledge_graph_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(jsonrpc, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Sample output saved to: {output_file}")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
