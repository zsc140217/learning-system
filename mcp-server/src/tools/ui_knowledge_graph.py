"""
Knowledge Graph UI Tool

Generates interactive D3.js force-directed graph visualization for knowledge points.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..ui.components import UIComponent, ComponentType
from ..ui.template_manager import TemplateManager, UITemplateResult

logger = logging.getLogger(__name__)


def _get_node_color(node_type: str) -> str:
    """Get color for node type."""
    color_map = {
        "concept": "#4CAF50",
        "skill": "#2196F3",
        "project": "#FF9800",
        "tool": "#9C27B0",
    }
    return color_map.get(node_type, "#757575")


def _get_demo_graph_data() -> Dict[str, Any]:
    """Get demo knowledge graph data."""
    nodes = [
        {
            "id": "kp-001",
            "label": "FastAPI Basics",
            "type": "concept",
            "size": 20,
            "description": "Core FastAPI concepts and routing"
        },
        {
            "id": "kp-002",
            "label": "Dependency Injection",
            "type": "concept",
            "size": 18,
            "description": "FastAPI dependency injection system"
        },
        {
            "id": "kp-003",
            "label": "Pydantic Models",
            "type": "skill",
            "size": 16,
            "description": "Data validation with Pydantic"
        },
        {
            "id": "kp-004",
            "label": "Async Programming",
            "type": "concept",
            "size": 22,
            "description": "Python async/await patterns"
        },
        {
            "id": "kp-005",
            "label": "MCP Server",
            "type": "project",
            "size": 25,
            "description": "Model Context Protocol implementation"
        },
        {
            "id": "kp-006",
            "label": "SQLAlchemy ORM",
            "type": "tool",
            "size": 15,
            "description": "Database ORM for Python"
        },
        {
            "id": "kp-007",
            "label": "REST API Design",
            "type": "concept",
            "size": 17,
            "description": "RESTful API design principles"
        },
        {
            "id": "kp-008",
            "label": "Authentication",
            "type": "skill",
            "size": 19,
            "description": "JWT and OAuth2 implementation"
        }
    ]

    edges = [
        {"source": "kp-001", "target": "kp-002", "type": "prerequisite"},
        {"source": "kp-001", "target": "kp-003", "type": "uses"},
        {"source": "kp-004", "target": "kp-001", "type": "prerequisite"},
        {"source": "kp-002", "target": "kp-005", "type": "applied_in"},
        {"source": "kp-003", "target": "kp-005", "type": "applied_in"},
        {"source": "kp-006", "target": "kp-005", "type": "used_by"},
        {"source": "kp-007", "target": "kp-001", "type": "prerequisite"},
        {"source": "kp-008", "target": "kp-005", "type": "applied_in"},
        {"source": "kp-001", "target": "kp-008", "type": "related_to"}
    ]

    return {"nodes": nodes, "edges": edges}


async def generate_knowledge_graph_ui(
    knowledge_ids: Optional[List[str]] = None,
    depth: int = 2,
    memory_manager = None
) -> UITemplateResult:
    """
    Generate knowledge graph UI with D3.js force-directed layout.

    Args:
        knowledge_ids: Starting node IDs (None = all nodes)
        depth: Subgraph depth (1-3)
        memory_manager: MemoryManager instance for fetching real data

    Returns:
        UITemplateResult with HTML template

    Example:
        >>> result = await generate_knowledge_graph_ui(["kp-001"], depth=2, memory_manager=manager)
        >>> jsonrpc = result.to_jsonrpc(request_id=1)
    """
    # Validate depth
    if depth < 1 or depth > 3:
        raise ValueError("Depth must be between 1 and 3")

    # Fetch real data from MemoryManager or use demo data
    if memory_manager:
        try:
            # Get knowledge graph from MemoryManager
            graph_response = await memory_manager.get_knowledge_graph(
                node_name=knowledge_ids[0] if knowledge_ids else None
            )

            # Transform to UI format
            graph_data = {
                "nodes": [],
                "edges": []
            }

            # Transform entities to nodes
            for entity in graph_response.get("entities", []):
                observations = entity.get("observations", [])
                node = {
                    "id": entity.get("id") or entity.get("name"),
                    "label": entity.get("name", "Unknown"),
                    "type": entity.get("entityType", "Knowledge").lower(),
                    "size": 20,
                    "description": " | ".join(observations[:2]) if observations else "",
                    "observations": observations  # 添加完整的观察列表，供前端详情面板使用
                }
                graph_data["nodes"].append(node)

            # Transform relations to edges
            for relation in graph_response.get("relations", []):
                relation_type = relation.get("relationType") or relation.get("relation_type", "related_to")
                edge = {
                    "source": relation.get("from") or relation.get("from_entity"),
                    "target": relation.get("to") or relation.get("to_entity"),
                    "type": relation_type,
                    "label": relation_type  # 添加边标签，支持前端显示中文关系名
                }
                graph_data["edges"].append(edge)

            logger.info(f"Loaded real knowledge graph: {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")

            # If no data loaded, use demo data
            if len(graph_data['nodes']) == 0:
                logger.info("No data in knowledge graph, using demo data")
                graph_data = _get_demo_graph_data()
        except Exception as e:
            logger.warning(f"Failed to load real data: {e}, using demo data")
            graph_data = _get_demo_graph_data()
    else:
        # Use demo data if no MemoryManager provided
        graph_data = _get_demo_graph_data()

    # Apply knowledge_ids filter if provided
    if knowledge_ids:
        # Filter nodes
        filtered_node_ids = set(knowledge_ids)
        # Add connected nodes up to depth
        for _ in range(depth):
            new_ids = set()
            for edge in graph_data["edges"]:
                if edge["source"] in filtered_node_ids:
                    new_ids.add(edge["target"])
                if edge["target"] in filtered_node_ids:
                    new_ids.add(edge["source"])
            filtered_node_ids.update(new_ids)

        # Filter nodes and edges
        graph_data["nodes"] = [
            n for n in graph_data["nodes"]
            if n["id"] in filtered_node_ids
        ]
        graph_data["edges"] = [
            e for e in graph_data["edges"]
            if e["source"] in filtered_node_ids and e["target"] in filtered_node_ids
        ]

    # Limit node count for performance
    max_nodes = 100
    if len(graph_data["nodes"]) > max_nodes:
        logger.warning(
            f"Graph too large ({len(graph_data['nodes'])} nodes), "
            f"limiting to {max_nodes} nodes"
        )
        graph_data["nodes"] = graph_data["nodes"][:max_nodes]

        # Filter edges to match remaining nodes
        node_ids = {n["id"] for n in graph_data["nodes"]}
        graph_data["edges"] = [
            e for e in graph_data["edges"]
            if e["source"] in node_ids and e["target"] in node_ids
        ]

    # Add colors based on type
    for node in graph_data["nodes"]:
        if "color" not in node:
            node["color"] = _get_node_color(node.get("type", "default"))

    # Prepare template data
    data = {
        "nodes": graph_data["nodes"],
        "edges": graph_data["edges"],
        "config": {
            "width": 800,
            "height": 600,
            "charge_strength": -300
        }
    }

    # Get template path
    template_path = Path(__file__).parent.parent.parent / "templates" / "knowledge_graph.html"

    # Render using TemplateManager
    template_mgr = TemplateManager()

    # Register template if not already registered
    template_id = "com.learning-system.knowledge-graph"
    if template_id not in template_mgr._template_paths:
        template_mgr.register_template(
            template_id=template_id,
            validator=lambda d: "nodes" in d and "edges" in d,
            template_path=str(template_path)
        )

    return template_mgr.render_template(
        template_id=template_id,
        data=data
    )


# Example usage for testing
if __name__ == "__main__":
    import asyncio
    import json

    async def main():
        # Test 1: Full graph
        print("=== Test 1: Full Graph ===")
        result = await generate_knowledge_graph_ui()
        jsonrpc = result.to_jsonrpc(request_id=1)
        print(json.dumps(jsonrpc, indent=2))

        # Test 2: Filtered graph
        print("\n=== Test 2: Filtered Graph (kp-001, depth=2) ===")
        result = await generate_knowledge_graph_ui(
            knowledge_ids=["kp-001"],
            depth=2
        )
        jsonrpc = result.to_jsonrpc(request_id=2)
        print(json.dumps(jsonrpc, indent=2))

        # Test 3: Validate node count
        print("\n=== Test 3: Validation ===")
        assert len(result.data["nodes"]) <= 100, "Node count exceeds limit"
        assert "config" in result.data, "Missing config"
        print("[OK] All validations passed")

    asyncio.run(main())
