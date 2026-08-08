"""
Graph Management Tools

MCP tools for knowledge graph CRUD operations.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


async def create_knowledge_graph(
    name: str,
    description: str = "",
    kg_storage = None
) -> Dict[str, Any]:
    """
    创建新的知识图谱

    Args:
        name: 图谱名称
        description: 图谱描述
        kg_storage: PostgresKnowledgeGraph 实例

    Returns:
        {success: bool, graph: {id, name, description, created_at, node_count}}
    """
    if not kg_storage:
        return {
            "success": False,
            "error": "Knowledge graph storage not initialized"
        }

    try:
        graph = await kg_storage.create_graph(name, description)
        logger.info(f"Created knowledge graph: {name} (id: {graph['id']})")

        return {
            "success": True,
            "graph": {
                "id": graph['id'],
                "name": graph['name'],
                "description": graph['description'],
                "created_at": str(graph['created_at']),
                "node_count": graph['node_count']
            }
        }
    except Exception as e:
        logger.error(f"Failed to create knowledge graph: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def list_knowledge_graphs(
    kg_storage = None
) -> Dict[str, Any]:
    """
    列出所有知识图谱

    Args:
        kg_storage: PostgresKnowledgeGraph 实例

    Returns:
        {success: bool, graphs: [{id, name, description, node_count, created_at}, ...]}
    """
    if not kg_storage:
        return {
            "success": False,
            "error": "Knowledge graph storage not initialized"
        }

    try:
        graphs = await kg_storage.list_graphs()

        # 转换日期格式为字符串
        formatted_graphs = []
        for graph in graphs:
            formatted_graphs.append({
                "id": graph['id'],
                "name": graph['name'],
                "description": graph.get('description', ''),
                "node_count": graph['node_count'],
                "created_at": str(graph['created_at'])
            })

        logger.info(f"Listed {len(formatted_graphs)} knowledge graphs")

        return {
            "success": True,
            "graphs": formatted_graphs
        }
    except Exception as e:
        logger.error(f"Failed to list knowledge graphs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def delete_knowledge_graph(
    graph_id: int,
    kg_storage = None
) -> Dict[str, Any]:
    """
    删除知识图谱

    Args:
        graph_id: 图谱ID
        kg_storage: PostgresKnowledgeGraph 实例

    Returns:
        {success: bool, message: str}
    """
    if not kg_storage:
        return {
            "success": False,
            "error": "Knowledge graph storage not initialized"
        }

    try:
        success = await kg_storage.delete_graph(graph_id)

        if success:
            logger.info(f"Deleted knowledge graph {graph_id}")
            return {
                "success": True,
                "message": f"Knowledge graph {graph_id} deleted successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Knowledge graph {graph_id} not found"
            }
    except Exception as e:
        logger.error(f"Failed to delete knowledge graph: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def merge_knowledge_graphs(
    source_ids: List[int],
    target_name: str,
    target_description: str = "",
    kg_storage = None
) -> Dict[str, Any]:
    """
    合并多个知识图谱

    Args:
        source_ids: 源图谱ID列表
        target_name: 目标图谱名称
        target_description: 目标图谱描述
        kg_storage: PostgresKnowledgeGraph 实例

    Returns:
        {success: bool, graph: {id, name, description, created_at, node_count}}
    """
    if not kg_storage:
        return {
            "success": False,
            "error": "Knowledge graph storage not initialized"
        }

    if not source_ids or len(source_ids) < 2:
        return {
            "success": False,
            "error": "At least 2 source graphs are required for merging"
        }

    try:
        merged_graph = await kg_storage.merge_graphs(
            source_ids=source_ids,
            target_name=target_name,
            target_description=target_description
        )

        logger.info(f"Merged graphs {source_ids} into {merged_graph['id']}")

        return {
            "success": True,
            "graph": {
                "id": merged_graph['id'],
                "name": merged_graph['name'],
                "description": merged_graph['description'],
                "created_at": str(merged_graph['created_at']),
                "node_count": merged_graph['node_count']
            }
        }
    except Exception as e:
        logger.error(f"Failed to merge knowledge graphs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_knowledge_graph(
    graph_id: int,
    kg_storage = None
) -> Dict[str, Any]:
    """
    获取知识图谱的可视化数据

    Args:
        graph_id: 图谱ID
        kg_storage: PostgresKnowledgeGraph 实例

    Returns:
        {success: bool, graph: {nodes: [...], edges: [...]}}
    """
    if not kg_storage:
        return {
            "success": False,
            "error": "Knowledge graph storage not initialized"
        }

    try:
        graph_data = await kg_storage.get_graph_data(graph_id)

        logger.info(f"Retrieved graph {graph_id}: {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")

        return {
            "success": True,
            "graph": graph_data
        }
    except Exception as e:
        logger.error(f"Failed to get knowledge graph data: {e}")
        return {
            "success": False,
            "error": str(e)
        }
