"""
Learning System MCP Server
基于自研 MCP 2026-07-28 协议层实现
"""
import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from config import settings
from src.protocol import MCPServer, MCPResult, TaskHandleResult, StdioTransport, MCPError
from src.bus.agent_bus import bus
from src.agents.session_analyzer import SessionAnalyzer
from src.agents.memory_manager import MemoryManager
from src.agents.learning_coach import LearningCoach
from src.triggers import IdleDetector
from src.security import JWTHandler, NonceStore
from src.tasks import task_manager
from src.cache import cacheable, CacheManager


# 创建 MCP Server 实例
server = MCPServer("Learning System")

# 全局 Agents
session_analyzer = None
memory_manager = None
learning_coach = None
project_agent = None
interview_agent = None
idle_detector = None

# 安全组件
nonce_store = None
jwt_handler = None

# 缓存管理
cache_manager = None

# LLM Provider
llm_provider = None

# 会话历史存储（内存）
session_histories = {}

# 系统提示词
BASE_SYSTEM_PROMPT = """你是一个智能学习助手，帮助用户学习技术知识和准备面试。

你的职责：
1. 回答用户的技术问题，提供清晰、准确的解释
2. 当用户学习新知识时，帮助总结关键知识点
3. 支持多轮对话，记住上下文

## 可用工具

你可以使用以下 MCP 工具来增强回答能力：

### 文件操作工具
- `read_file(file_path, encoding="utf-8")` - 读取本地文件内容
  示例: 当用户提供文件路径时（如 `E:\\Desktop\\...\\file.md`），使用此工具读取文件
- `list_directory(directory_path, max_depth=1)` - 列出目录内容
- `search_files(directory_path, pattern)` - 搜索文件（支持通配符如 *.py）
- `get_file_info(file_path)` - 获取文件信息（大小、修改时间等）

### 知识管理工具
- `search_knowledge(query)` - 搜索知识图谱
- `save_knowledge(knowledge_points, session_id)` - 保存知识点
- `get_knowledge_graph(node_name)` - 获取知识图谱

### 项目分析工具
- `track_project(project_path)` - 分析项目结构和技术栈
- `project/detect_framework(project_path)` - 检测项目框架
- `project/analyze_dependencies(project_path)` - 分析项目依赖

**重要**: 当用户提到文件路径时，主动使用 `read_file` 工具读取内容，而不是告诉用户"我无法读取文件"。

回答风格：
- 简洁明了，避免冗长
- 使用 Markdown 格式（代码块、列表、加粗）
- 提供实际例子和代码示例
"""


# ============ 会话管理辅助函数 ============

def _get_session_history(session_id: str) -> List[Dict[str, str]]:
    """获取会话历史"""
    if session_id not in session_histories:
        session_histories[session_id] = []
    return session_histories[session_id]


def _save_to_session_history(session_id: str, user_message: str, assistant_message: str):
    """保存消息到会话历史"""
    if session_id not in session_histories:
        session_histories[session_id] = []

    session_histories[session_id].append({"role": "user", "content": user_message})
    session_histories[session_id].append({"role": "assistant", "content": assistant_message})

    # 限制历史长度（保留最近 10 轮对话）
    if len(session_histories[session_id]) > 20:
        session_histories[session_id] = session_histories[session_id][-20:]


def _build_system_prompt(skill_context: str = None) -> str:
    """构建系统提示词"""
    prompt = BASE_SYSTEM_PROMPT

    if skill_context:
        prompt += f"\n\n# Active Skill\n\n当前已加载以下 Skill 工作流，请按照 Skill 中的指令执行：\n\n{skill_context}"

    return prompt


def _detect_wait_confirm(response: str) -> tuple:
    """
    检测响应中是否包含 WAIT for user CONFIRM 标记

    返回: (wait_confirm: bool, confirm_data: dict | None)
    """
    # 简单检测：如果响应中包含特殊标记
    if "WAIT_CONFIRM:" in response:
        # 提取确认数据
        import json
        try:
            start = response.find("WAIT_CONFIRM:")
            end = response.find("\n", start)
            if end == -1:
                end = len(response)
            data_str = response[start + 13:end].strip()
            confirm_data = json.loads(data_str)
            return True, confirm_data
        except:
            return True, None

    return False, None


# ============ MCP Tools ============

@server.tool("analyze_session")
@cacheable(ttl_seconds=300, scope="session")  # 5分钟会话级缓存
async def analyze_session(
    session_data: str,
    session_id: str = None
) -> MCPResult:
    """
    分析会话内容，提取知识点

    Args:
        session_data: 会话内容 (Markdown格式)
        session_id: 可选的会话ID，不提供则自动生成

    Returns:
        MCPResult with:
        {
            "session_id": "session_1722518400_a7b3c9d2",
            "status": "completed",
            "message": "..."
        }
    """
    # 记录活动
    if idle_detector:
        idle_detector.record_activity("tool_call", {"tool_name": "analyze_session"})

    from src.utils.id_generator import generate_session_id

    if session_id is None:
        session_id = generate_session_id()

    logger.info(f"分析会话: {session_id}")

    # 解析会话内容为 transcript 格式
    transcript = _parse_session_data(session_data)

    # 发布 session.completed 事件（SessionAnalyzer 会处理）
    await bus.publish({
        "type": "session.completed",
        "session_id": session_id,
        "transcript": transcript
    })

    # 等待 SessionAnalyzer 处理
    await asyncio.sleep(0.2)

    return MCPResult(
        data={
            "session_id": session_id,
            "status": "completed",
            "message": "Session analysis triggered. Knowledge points will be extracted."
        }
    )


def _parse_session_data(session_data: str) -> list[Dict[str, str]]:
    """
    解析会话数据为 transcript 格式

    Args:
        session_data: Markdown 格式的会话内容

    Returns:
        transcript 列表
    """
    lines = session_data.strip().split('\n')
    transcript = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 识别角色标记
        if line.startswith('User:') or line.startswith('用户:'):
            content = line.split(':', 1)[1].strip()
            transcript.append({"role": "user", "content": content})
        elif line.startswith('Assistant:') or line.startswith('助手:'):
            content = line.split(':', 1)[1].strip()
            transcript.append({"role": "assistant", "content": content})
        else:
            # 无角色标记，作为 assistant 内容
            transcript.append({"role": "assistant", "content": line})

    return transcript


@server.tool("save_knowledge")
async def save_knowledge(
    knowledge_points: list[Dict[str, Any]],
    session_id: str,
    graph_id: int = None
) -> MCPResult:
    """
    保存知识点到 Memory MCP

    Args:
        knowledge_points: 知识点列表
        session_id: 会话ID
        graph_id: 知识图谱ID（可选，默认使用默认图谱）

    Returns:
        MCPResult with:
        {
            "saved_count": 3,
            "knowledge_ids": ["knowledge_xxx", ...],
            "status": "completed"
        }
    """
    logger.info(f"保存知识点: {len(knowledge_points)} 个到图谱 {graph_id}")

    # 如果未指定 graph_id，获取默认图谱ID
    if graph_id is None:
        try:
            kg_storage = getattr(memory_manager, 'kg_storage', None)
            if kg_storage:
                # 查询名为"默认图谱"的图谱
                graphs = await kg_storage.list_graphs()
                default_graph = next((g for g in graphs if g['name'] == '默认图谱'), None)
                if default_graph:
                    graph_id = default_graph['id']
                    logger.info(f"使用默认图谱 ID: {graph_id}")
        except Exception as e:
            logger.warning(f"获取默认图谱失败: {e}，知识点将不关联图谱")

    # 发布事件
    await bus.publish({
        "type": "knowledge_save_requested",
        "session_id": session_id,
        "data": {"knowledge_points": knowledge_points, "graph_id": graph_id}
    })

    # 自动失效知识搜索缓存
    cache_manager.invalidate_pattern("search_knowledge:*")
    cache_manager.invalidate_pattern("get_knowledge_graph:*")
    cache_manager.invalidate_pattern("list_knowledge_graphs:*")
    logger.info("自动失效知识缓存")

    # 实际保存到 Memory Manager
    try:
        # 为每个知识点生成唯一ID（如果没有）
        from src.utils.id_generator import generate_knowledge_id
        for kp in knowledge_points:
            if not kp.get("id"):
                kp["id"] = generate_knowledge_id()
            if not kp.get("session_id"):
                kp["session_id"] = session_id
            # 添加 graph_id
            if graph_id:
                kp["graph_id"] = graph_id

        # 调用 Memory Manager 保存
        saved_ids = await memory_manager._save_knowledge_points(knowledge_points)

        logger.info(f"成功保存 {len(saved_ids)} 个知识点")

        return MCPResult(
            data={
                "saved_count": len(saved_ids),
                "knowledge_ids": saved_ids,
                "status": "completed",
                "message": f"已保存 {len(saved_ids)} 个知识点"
            }
        )
    except Exception as e:
        logger.error(f"保存知识点失败: {e}")
        return MCPResult(
            data={
                "saved_count": 0,
                "knowledge_ids": [],
                "status": "failed",
                "error": str(e)
            }
        )


@server.tool("delete_knowledge")
async def delete_knowledge(node_name: str) -> MCPResult:
    """
    删除知识点

    Args:
        node_name: 要删除的节点名称
    """
    logger.info(f"删除知识点: {node_name}")
    try:
        await memory_manager.delete_entities([node_name])
        return MCPResult(data={"status": "deleted", "node_name": node_name})
    except Exception as e:
        logger.error(f"删除失败: {e}")
        return MCPResult(data={"status": "failed", "error": str(e)})


@server.tool("track_project")
@cacheable(ttl_seconds=86400, scope="user")  # 1天用户级缓存
async def track_project(
    project_path: str,
    project_name: str = None,
    quick_mode: bool = True
) -> MCPResult:
    """
    追踪项目经验（快速入口，调用原子化工具）

    Args:
        project_path: 项目路径
        project_name: 可选的项目名称
        quick_mode: 快速模式（True=仅基础分析，False=完整分析）

    Returns:
        MCPResult with:
        {
            "project_id": "project_xxx",
            "framework": {...},
            "structure": {...},
            "dependencies": {...},
            "patterns": {...},  # 仅在 quick_mode=False 时返回
            "status": "completed"
        }

    Design Note:
        这是一个便捷工具，内部调用 4 个原子化工具：
        1. project/detect_framework - 检测框架
        2. project/scan_structure - 扫描结构
        3. project/analyze_dependencies - 分析依赖
        4. project/extract_patterns - 提取模式（仅在非快速模式）

        AI-First 架构：Skills 应该直接调用原子工具，而不是这个便捷工具。
        这个工具主要用于：
        - 快速原型验证
        - 手动测试
        - 向后兼容旧的集成
    """
    from src.utils.id_generator import generate_project_id
    import os

    project_id = generate_project_id()
    logger.info(f"追踪项目: {project_path} (quick_mode={quick_mode})")

    try:
        # 1. 调用 project/detect_framework
        framework_result = await detect_framework(project_path)
        framework_data = framework_result.data

        # 2. 调用 project/scan_structure
        structure_result = await scan_structure(project_path)
        structure_data = structure_result.data

        # 3. 调用 project/analyze_dependencies
        dependencies_result = await analyze_dependencies(project_path)
        dependencies_data = dependencies_result.data

        # 4. 调用 project/extract_patterns（仅在完整模式）
        patterns_data = None
        if not quick_mode:
            patterns_result = await extract_patterns(project_path, file_limit=20)
            patterns_data = patterns_result.data

        # 5. 组装结果
        tech_stack = []
        if dependencies_data.get("language") != "Unknown":
            tech_stack.append(dependencies_data["language"])
        if framework_data.get("framework") != "Unknown":
            tech_stack.append(framework_data["framework"])

        # 生成摘要
        highlights = []
        highlights.append(f"框架: {framework_data.get('framework', 'Unknown')}")
        highlights.append(f"语言: {dependencies_data.get('language', 'Unknown')}")
        highlights.append(f"依赖数量: {dependencies_data.get('dependency_count', 0)}")
        highlights.append(f"文件数量: {structure_data.get('file_stats', {}).get('total_files', 0)}")

        if patterns_data and not patterns_data.get("error"):
            naming = patterns_data.get("naming_convention", {})
            if naming:
                highlights.append(f"命名规范: {naming.get('files', 'unknown')}")

        # 6. 发布事件
        await bus.publish({
            "type": "project_track_requested",
            "project_id": project_id,
            "data": {
                "path": project_path,
                "name": project_name,
                "tech_stack": tech_stack,
                "framework": framework_data.get("framework")
            }
        })

        # 7. 返回结果
        result_data = {
            "project_id": project_id,
            "project_path": project_path,
            "project_name": project_name or os.path.basename(project_path),
            "framework": framework_data,
            "structure": structure_data,
            "dependencies": dependencies_data,
            "tech_stack": tech_stack,
            "highlights": highlights,
            "status": "completed",
            "mode": "quick" if quick_mode else "full"
        }

        # 仅在完整模式添加 patterns
        if patterns_data:
            result_data["patterns"] = patterns_data

        return MCPResult(data=result_data)

    except Exception as e:
        logger.error(f"项目追踪失败: {e}")
        return MCPResult(
            data={
                "project_id": project_id,
                "error": str(e),
                "status": "failed"
            }
        )


@server.tool("explore_technology")
@cacheable(ttl_seconds=3600, scope="public")  # 1小时公共缓存
async def explore_technology(
    topic: str,
    depth: str = "basic"
) -> MCPResult:
    """
    探索技术主题

    Args:
        topic: 技术主题
        depth: 探索深度 (basic, intermediate, advanced)

    Returns:
        MCPResult with:
        {
            "topic": "...",
            "learning_path": [...],
            "resources": [...],
            "status": "completed"
        }
    """
    logger.info(f"探索技术: {topic} (深度: {depth})")

    await bus.publish({
        "type": "tech_explore_requested",
        "data": {
            "topic": topic,
            "depth": depth
        }
    })

    # 从知识图谱中搜索相关技术内容
    try:
        # 搜索相关知识点
        search_result = await memory_manager.search_knowledge(topic)
        related_nodes = search_result.get("nodes", [])

        # 构建学习路径
        learning_path = []
        resources = []

        if related_nodes:
            # 从知识图谱中提取学习路径
            for i, node in enumerate(related_nodes[:5], 1):
                learning_path.append({
                    "step": i,
                    "title": node.get("name") or node.get("title", f"主题 {i}"),
                    "content": node.get("observations", [""])[0] if node.get("observations") else "",
                    "source": "knowledge_graph"
                })

            # 提取资源链接
            for node in related_nodes:
                observations = node.get("observations", [])
                for obs in observations:
                    if "http" in obs or "https" in obs:
                        resources.append({
                            "type": "参考资料",
                            "content": obs
                        })

        # 如果没有找到知识，返回基础建议
        if not learning_path:
            learning_path = [
                {
                    "step": 1,
                    "title": f"了解 {topic} 基础概念",
                    "content": f"建议先搜索 {topic} 的官方文档和入门教程",
                    "source": "suggestion"
                },
                {
                    "step": 2,
                    "title": f"实践 {topic}",
                    "content": "通过小项目实践所学知识",
                    "source": "suggestion"
                }
            ]

        return MCPResult(
            data={
                "topic": topic,
                "depth": depth,
                "learning_path": learning_path,
                "resources": resources[:10],  # 最多10个资源
                "related_count": len(related_nodes),
                "status": "completed"
            }
        )

    except Exception as e:
        logger.error(f"技术探索失败: {e}")
        return MCPResult(
            data={
                "topic": topic,
                "learning_path": [],
                "resources": [],
                "status": "failed",
                "error": str(e)
            }
        )


@server.tool("search_knowledge")
@cacheable(ttl_seconds=3600, scope="user")  # 1小时用户级缓存
async def search_knowledge(query: str) -> MCPResult:
    """
    语义搜索知识图谱

    Args:
        query: 搜索查询 (e.g. "如何实现 FastAPI 路由")

    Returns:
        MCPResult with:
        {
            "results": [...],
            "count": 5,
            "source": "memory_mcp"
        }
    """
    logger.info(f"搜索知识: {query}")

    result = await memory_manager.search_knowledge(query)

    return MCPResult(
        data={
            "results": result.get("nodes", []),
            "count": len(result.get("nodes", [])),
            "source": result.get("source", "unknown")
        }
    )


@server.tool("get_knowledge_graph")
@cacheable(ttl_seconds=3600, scope="user")  # 1小时用户级缓存
async def get_knowledge_graph(
    node_name: str = None,
    max_depth: int = 2
) -> MCPResult:
    """
    获取知识图谱（全图或子图）

    Args:
        node_name: 中心节点名称（None = 全图）
        max_depth: 关系深度（暂未实现）

    Returns:
        MCPResult with:
        {
            "entities": [...],
            "relations": [...],
            "source": "memory_mcp"
        }
    """
    logger.info(f"获取知识图谱: node={node_name}, depth={max_depth}")

    graph = await memory_manager.get_knowledge_graph(node_name)

    return MCPResult(
        data={
            "entities": graph.get("entities", []),
            "relations": graph.get("relations", []),
            "source": graph.get("source", "unknown")
        }
    )


@server.tool("ui_knowledge_graph")
async def ui_knowledge_graph(
    knowledge_ids: Optional[List[str]] = None,
    depth: int = 2
) -> MCPResult:
    """
    生成知识图谱可视化 UI

    Args:
        knowledge_ids: 起始节点 ID 列表 (None = 全图)
        depth: 子图深度 (1-3)

    Returns:
        MCPResult with UI template
    """
    from src.tools.ui_knowledge_graph import generate_knowledge_graph_ui

    logger.info(f"生成知识图谱 UI: ids={knowledge_ids}, depth={depth}")

    try:
        result = await generate_knowledge_graph_ui(
            knowledge_ids=knowledge_ids,
            depth=depth,
            memory_manager=memory_manager
        )

        # Load HTML template content
        from pathlib import Path
        template_html = ""
        if result.template_path:
            template_file = Path(result.template_path)
            if template_file.exists():
                template_html = template_file.read_text(encoding="utf-8")
            else:
                logger.warning(f"Template file not found: {result.template_path}")

        return MCPResult(
            data=result.template_data,
            meta={
                "io.modelcontextprotocol/uiTemplate": {
                    "templateId": result.template_id,
                    "template": template_html,
                    "data": result.template_data
                }
            }
        )
    except Exception as e:
        logger.error(f"生成知识图谱 UI 失败: {e}")
        return MCPResult(
            data={"error": str(e)}
        )


@server.tool("search_nodes")
@cacheable(ttl_seconds=3600, scope="user")  # 1小时用户级缓存
async def search_nodes(query: str) -> MCPResult:
    """
    搜索知识图谱节点（前端知识图谱组件专用）

    Args:
        query: 搜索关键词

    Returns:
        MCPResult with:
        [
            {
                "id": "node-id",
                "name": "节点名称",
                "type": "concept",
                "observations": ["观察1", "观察2"]
            }
        ]
    """
    logger.info(f"搜索节点: {query}")

    try:
        result = await memory_manager.search_knowledge(query)
        nodes = result.get("nodes", [])

        # 转换为前端期望的格式
        formatted_nodes = []
        for node in nodes:
            formatted_nodes.append({
                "id": node.get("name") or node.get("id"),
                "name": node.get("name", "Unknown"),
                "type": node.get("entityType", "concept").lower(),
                "observations": node.get("observations", [])
            })

        return MCPResult(data=formatted_nodes)
    except Exception as e:
        logger.error(f"搜索节点失败: {e}")
        return MCPResult(data=[])


@server.tool("open_nodes")
@cacheable(ttl_seconds=3600, scope="user")  # 1小时用户级缓存
async def open_nodes(names: List[str]) -> MCPResult:
    """
    获取指定节点的详细信息（前端知识图谱组件专用）

    Args:
        names: 节点名称列表

    Returns:
        MCPResult with:
        [
            {
                "id": "node-id",
                "name": "节点名称",
                "type": "concept",
                "observations": ["详细观察1", "详细观察2"]
            }
        ]
    """
    logger.info(f"获取节点详情: {names}")

    try:
        # 获取完整知识图谱
        graph = await memory_manager.get_knowledge_graph()
        entities = graph.get("entities", [])

        # 筛选指定名称的节点
        result_nodes = []
        for entity in entities:
            entity_name = entity.get("name")
            if entity_name in names:
                result_nodes.append({
                    "id": entity_name,
                    "name": entity_name,
                    "type": entity.get("entityType", "concept").lower(),
                    "observations": entity.get("observations", [])
                })

        return MCPResult(data=result_nodes)
    except Exception as e:
        logger.error(f"获取节点详情失败: {e}")
        return MCPResult(data=[])


# ============ 图谱管理工具 ============

@server.tool("create_knowledge_graph")
async def create_knowledge_graph_tool(
    name: str,
    description: str = ""
) -> MCPResult:
    """
    创建新的知识图谱

    Args:
        name: 图谱名称
        description: 图谱描述

    Returns:
        MCPResult with:
        {
            "success": bool,
            "graph": {
                "id": int,
                "name": str,
                "description": str,
                "created_at": str,
                "node_count": int
            }
        }
    """
    from src.tools.graph_management import create_knowledge_graph

    logger.info(f"创建知识图谱: {name}")

    # 获取知识图谱存储实例
    kg_storage = getattr(memory_manager, 'kg_storage', None)

    result = await create_knowledge_graph(
        name=name,
        description=description,
        kg_storage=kg_storage
    )

    return MCPResult(data=result)


@server.tool("list_knowledge_graphs")
@cacheable(ttl_seconds=60, scope="user")  # 1分钟缓存
async def list_knowledge_graphs_tool() -> MCPResult:
    """
    列出所有知识图谱

    Returns:
        MCPResult with:
        {
            "success": bool,
            "graphs": [
                {
                    "id": int,
                    "name": str,
                    "description": str,
                    "node_count": int,
                    "created_at": str
                }
            ]
        }
    """
    from src.tools.graph_management import list_knowledge_graphs

    logger.info("列出所有知识图谱")

    kg_storage = getattr(memory_manager, 'kg_storage', None)

    result = await list_knowledge_graphs(kg_storage=kg_storage)

    return MCPResult(data=result)


@server.tool("delete_knowledge_graph")
async def delete_knowledge_graph_tool(graph_id: int) -> MCPResult:
    """
    删除知识图谱

    Args:
        graph_id: 图谱ID

    Returns:
        MCPResult with:
        {
            "success": bool,
            "message": str
        }
    """
    from src.tools.graph_management import delete_knowledge_graph

    logger.info(f"删除知识图谱: {graph_id}")

    # 自动失效相关缓存
    cache_manager.invalidate_pattern("list_knowledge_graphs:*")
    cache_manager.invalidate_pattern("get_knowledge_graph:*")

    kg_storage = getattr(memory_manager, 'kg_storage', None)

    result = await delete_knowledge_graph(
        graph_id=graph_id,
        kg_storage=kg_storage
    )

    return MCPResult(data=result)


@server.tool("merge_knowledge_graphs")
async def merge_knowledge_graphs_tool(
    source_ids: List[int],
    target_name: str,
    target_description: str = ""
) -> MCPResult:
    """
    合并多个知识图谱

    Args:
        source_ids: 源图谱ID列表
        target_name: 目标图谱名称
        target_description: 目标图谱描述

    Returns:
        MCPResult with:
        {
            "success": bool,
            "graph": {
                "id": int,
                "name": str,
                "description": str,
                "created_at": str,
                "node_count": int
            }
        }
    """
    from src.tools.graph_management import merge_knowledge_graphs

    logger.info(f"合并知识图谱: {source_ids} -> {target_name}")

    # 自动失效相关缓存
    cache_manager.invalidate_pattern("list_knowledge_graphs:*")
    cache_manager.invalidate_pattern("get_knowledge_graph:*")

    kg_storage = getattr(memory_manager, 'kg_storage', None)

    result = await merge_knowledge_graphs(
        source_ids=source_ids,
        target_name=target_name,
        target_description=target_description,
        kg_storage=kg_storage
    )

    return MCPResult(data=result)


@server.tool("get_graph_data")
@cacheable(ttl_seconds=300, scope="user")  # 5分钟缓存
async def get_graph_data_tool(graph_id: int) -> MCPResult:
    """
    获取指定图谱的可视化数据

    Args:
        graph_id: 图谱ID

    Returns:
        MCPResult with:
        {
            "success": bool,
            "graph": {
                "nodes": [...],
                "edges": [...]
            }
        }
    """
    from src.tools.graph_management import get_knowledge_graph

    logger.info(f"获取图谱数据: {graph_id}")

    kg_storage = getattr(memory_manager, 'kg_storage', None)

    result = await get_knowledge_graph(
        graph_id=graph_id,
        kg_storage=kg_storage
    )

    return MCPResult(data=result)


@server.tool("knowledge/create_relation")
async def create_relation(
    from_entity: str,
    to_entity: str,
    relation_type: str
) -> MCPResult:
    """
    在知识图谱中建立关系（原子工具）

    Args:
        from_entity: 源实体名称
        to_entity: 目标实体名称
        relation_type: 关系类型 (uses/requires/related_to/belongs_to/implements/extends)

    Returns:
        MCPResult with:
        {
            "from": "FastAPI",
            "to": "Pydantic",
            "relation_type": "uses",
            "status": "created"
        }

    Examples:
        - 项目使用技术: create_relation("learning-system", "FastAPI", "uses")
        - 技术依赖: create_relation("FastAPI", "Pydantic", "requires")
        - 相关技术: create_relation("FastAPI", "Django", "related_to")
        - 模块归属: create_relation("auth_module", "backend", "belongs_to")
    """
    logger.info(f"创建关系: {from_entity} --{relation_type}--> {to_entity}")

    # 自动失效知识图谱缓存
    cache_manager.invalidate_pattern("get_knowledge_graph:*")
    cache_manager.invalidate_pattern("search_knowledge:*")

    try:
        success = await memory_manager.link_knowledge_nodes(
            from_node=from_entity,
            to_node=to_entity,
            relation_type=relation_type
        )

        if success:
            return MCPResult(
                data={
                    "from": from_entity,
                    "to": to_entity,
                    "relation_type": relation_type,
                    "status": "created",
                    "message": f"成功建立关系: {from_entity} --{relation_type}--> {to_entity}"
                }
            )
        else:
            return MCPResult(
                data={
                    "from": from_entity,
                    "to": to_entity,
                    "relation_type": relation_type,
                    "status": "failed",
                    "error": "MCP Memory not available or relation creation failed"
                }
            )

    except Exception as e:
        logger.error(f"创建关系失败: {e}")
        return MCPResult(
            data={
                "from": from_entity,
                "to": to_entity,
                "relation_type": relation_type,
                "status": "failed",
                "error": str(e)
            }
        )


# ============ 外部资源工具 (Context7 & Exa) ============

@server.tool("resource/query_docs")
@cacheable(ttl_seconds=3600, scope="public")  # 1小时公共缓存
async def query_docs(
    library: str,
    query: str
) -> MCPResult:
    """
    查询技术文档（集成 Context7 MCP）

    Args:
        library: 库名称 (e.g. "fastapi", "react", "django")
        query: 查询问题 (e.g. "如何实现身份验证")

    Returns:
        MCPResult with:
        {
            "library": "fastapi",
            "query": "如何实现身份验证",
            "answer": "...",
            "sources": [
                {"title": "...", "url": "..."}
            ]
        }

    Note:
        需要配置 Context7 MCP Server:
        - 安装: npm install -g @context7/mcp-server
        - 配置: 在 ~/.claude/config.json 中添加 context7 服务器
    """
    logger.info(f"查询文档: library={library}, query={query}")

    # 架构说明：
    # MCP Server 之间无法直接通信（设计原则：单一职责）
    # Context7 集成需要客户端协调：
    #   1. 客户端收到用户请求
    #   2. 客户端调用 mcp__plugin_ecc_context7__resolve-library-id(libraryName=library)
    #   3. 客户端调用 mcp__plugin_ecc_context7__query-docs(libraryId=result, query=query)
    #   4. 客户端将结果传递给本 Server 的 save_knowledge 保存

    try:
        answer = f"关于 {library} 的 {query}:\n\n"
        answer += "✓ Context7 集成已配置\n\n"
        answer += "客户端协调流程：\n"
        answer += f"1. 调用 context7.resolve-library-id(libraryName='{library}')\n"
        answer += f"2. 调用 context7.query-docs(libraryId=<result>, query='{query}')\n"
        answer += "3. 将结果保存到知识图谱\n\n"
        answer += "注意：此工具标记集成点，实际查询由客户端协调完成。"

        return MCPResult(
            data={
                "library": library,
                "query": query,
                "answer": answer,
                "sources": [],
                "status": "integration_marker",
                "message": "Client should orchestrate Context7 MCP calls",
                "integration": {
                    "mcp_server": "context7",
                    "tools": [
                        "mcp__plugin_ecc_context7__resolve-library-id",
                        "mcp__plugin_ecc_context7__query-docs"
                    ]
                }
            }
        )

    except Exception as e:
        logger.error(f"文档查询失败: {e}")
        return MCPResult(
            data={
                "library": library,
                "query": query,
                "answer": "",
                "sources": [],
                "status": "failed",
                "error": str(e)
            }
        )


@server.tool("resource/web_search")
@cacheable(ttl_seconds=3600, scope="public")  # 1小时公共缓存
async def web_search(
    query: str,
    result_count: int = 10
) -> MCPResult:
    """
    网络搜索（集成 Exa MCP）

    Args:
        query: 搜索查询
        result_count: 返回结果数量 (默认10)

    Returns:
        MCPResult with:
        {
            "query": "FastAPI best practices",
            "results": [
                {
                    "title": "...",
                    "url": "...",
                    "snippet": "...",
                    "published_date": "2024-01-01"
                }
            ],
            "total": 10
        }

    Note:
        需要配置 Exa MCP Server:
        - 安装: npm install -g @exa/mcp-server
        - 配置: 在 ~/.claude/config.json 中添加 exa 服务器
        - API Key: 需要 Exa API Key
    """
    logger.info(f"网络搜索: query={query}, count={result_count}")

    # 架构说明：
    # MCP Server 之间无法直接通信（设计原则：单一职责）
    # Exa 集成需要客户端协调：
    #   1. 客户端收到用户请求
    #   2. 客户端调用 mcp__plugin_ecc_exa__web_search_exa(query=query, numResults=result_count)
    #   3. 客户端将结果传递给本 Server 的 save_knowledge 保存

    try:
        return MCPResult(
            data={
                "query": query,
                "result_count": result_count,
                "results": [],
                "total": 0,
                "status": "integration_marker",
                "message": "Client should orchestrate Exa MCP calls",
                "integration": {
                    "mcp_server": "exa",
                    "tools": [
                        "mcp__plugin_ecc_exa__web_search_exa",
                        "mcp__plugin_ecc_exa__web_fetch_exa"
                    ],
                    "workflow": f"web_search_exa(query='{query}', numResults={result_count})"
                }
            }
        )

    except Exception as e:
        logger.error(f"网络搜索失败: {e}")
        return MCPResult(
            data={
                "query": query,
                "results": [],
                "total": 0,
                "status": "failed",
                "error": str(e)
            }
        )


# ============ 危险操作工具 (MRTR) ============

@server.tool("delete_knowledge")
async def delete_knowledge(
    knowledge_ids: list,
    request_state: str = None
) -> MCPResult:
    """
    删除知识节点（危险操作，需要二次确认）

    Args:
        knowledge_ids: 要删除的知识节点ID列表
        request_state: JWT token（第二轮请求时提供）

    Returns:
        第一轮：返回确认请求
        第二轮：返回删除结果
    """
    if not request_state:
        # 第一轮：返回确认请求
        logger.info(f"删除知识节点请求（第一轮）: {len(knowledge_ids)} 个节点")

        token = jwt_handler.generate_request_state(
            operation="delete_knowledge",
            params={"knowledge_ids": knowledge_ids}
        )

        return MCPResult(
            data={
                "message": f"⚠️ 将删除 {len(knowledge_ids)} 个知识节点，此操作不可逆",
                "knowledge_ids": knowledge_ids,
                "requires_confirmation": True
            },
            meta={
                "io.modelcontextprotocol/inputRequired": {
                    "requestState": token,
                    "fields": [
                        {
                            "name": "confirm",
                            "type": "boolean",
                            "label": "确认删除",
                            "required": True
                        },
                        {
                            "name": "archive_instead",
                            "type": "boolean",
                            "label": "归档而非删除",
                            "default": True
                        }
                    ]
                }
            }
        )

    # 第二轮：验证并执行
    try:
        payload = jwt_handler.verify_request_state(request_state)
        jwt_handler.verify_params_match(payload, {"knowledge_ids": knowledge_ids})

        logger.info(f"删除知识节点请求（第二轮）: JWT验证通过，执行删除...")

        # 执行删除
        deleted_count = await memory_manager.delete_nodes(knowledge_ids)

        # 自动失效相关缓存
        cache_manager.invalidate_pattern("search_knowledge:*")
        cache_manager.invalidate_pattern("get_knowledge_graph:*")
        logger.info("自动失效知识缓存")

        return MCPResult(
            data={
                "deleted_count": deleted_count,
                "status": "completed",
                "message": f"成功删除 {deleted_count} 个知识节点"
            }
        )

    except Exception as e:
        logger.error(f"删除知识节点失败: {e}")
        return MCPResult(
            data={
                "status": "failed",
                "error": str(e)
            }
        )


@server.tool("delete_project")
async def delete_project(
    project_id: str,
    request_state: str = None
) -> MCPResult:
    """
    删除项目（危险操作，需要二次确认）

    Args:
        project_id: 项目ID
        request_state: JWT token（第二轮请求时提供）

    Returns:
        第一轮：返回确认请求
        第二轮：返回删除结果
    """
    if not request_state:
        # 第一轮：返回确认请求
        logger.info(f"删除项目请求（第一轮）: project_id={project_id}")

        token = jwt_handler.generate_request_state(
            operation="delete_project",
            params={"project_id": project_id}
        )

        return MCPResult(
            data={
                "message": f"⚠️ 将删除项目 {project_id} 及其所有关联数据，此操作不可逆",
                "project_id": project_id,
                "requires_confirmation": True
            },
            meta={
                "io.modelcontextprotocol/inputRequired": {
                    "requestState": token,
                    "fields": [
                        {
                            "name": "confirm",
                            "type": "boolean",
                            "label": "确认删除项目",
                            "required": True
                        }
                    ]
                }
            }
        )

    # 第二轮：验证并执行
    try:
        payload = jwt_handler.verify_request_state(request_state)
        jwt_handler.verify_params_match(payload, {"project_id": project_id})

        logger.info(f"删除项目请求（第二轮）: JWT验证通过，执行删除...")

        # 删除项目相关的知识节点（从 Memory MCP）
        # 查找所有与该项目相关的知识节点
        deleted_count = 0
        try:
            # 搜索项目相关节点
            project_nodes = await memory_manager.search_knowledge(f"project_id:{project_id}")
            if project_nodes.get("nodes"):
                node_ids = [node.get("name") or node.get("id") for node in project_nodes["nodes"] if node.get("name") or node.get("id")]
                if node_ids:
                    deleted_count = await memory_manager.delete_nodes(node_ids)
                    logger.info(f"删除了 {deleted_count} 个项目相关节点")
        except Exception as e:
            logger.warning(f"删除项目节点失败: {e}")

        # 失效相关缓存
        cache_manager.invalidate_pattern(f"track_project:*{project_id}*")
        cache_manager.invalidate_pattern("search_knowledge:*")
        logger.info("自动失效项目相关缓存")

        return MCPResult(
            data={
                "status": "completed",
                "message": f"成功删除项目 {project_id}",
                "project_id": project_id,
                "deleted_nodes": deleted_count
            }
        )

    except Exception as e:
        logger.error(f"删除项目失败: {e}")
        return MCPResult(
            data={
                "status": "failed",
                "error": str(e)
            }
        )


@server.tool("rebuild_index")
async def rebuild_index(
    index_type: str = "all",
    request_state: str = None
) -> MCPResult:
    """
    重建索引（危险操作，需要二次确认）

    Args:
        index_type: 索引类型 (all/knowledge/sessions)
        request_state: JWT token（第二轮请求时提供）

    Returns:
        第一轮：返回确认请求
        第二轮：返回重建结果
    """
    if not request_state:
        # 第一轮：返回确认请求
        logger.info(f"重建索引请求（第一轮）: index_type={index_type}")

        token = jwt_handler.generate_request_state(
            operation="rebuild_index",
            params={"index_type": index_type}
        )

        return MCPResult(
            data={
                "message": f"⚠️ 将重建 {index_type} 索引，此操作可能耗时较长",
                "index_type": index_type,
                "requires_confirmation": True
            },
            meta={
                "io.modelcontextprotocol/inputRequired": {
                    "requestState": token,
                    "fields": [
                        {
                            "name": "confirm",
                            "type": "boolean",
                            "label": "确认重建索引",
                            "required": True
                        }
                    ]
                }
            }
        )

    # 第二轮：验证并执行
    try:
        payload = jwt_handler.verify_request_state(request_state)
        jwt_handler.verify_params_match(payload, {"index_type": index_type})

        logger.info(f"重建索引请求（第二轮）: JWT验证通过，执行重建...")

        # 重建索引逻辑
        rebuilt_items = 0

        if index_type in ["all", "knowledge"]:
            # 失效所有知识相关缓存，强制重新构建
            cache_manager.invalidate_pattern("search_knowledge:*")
            cache_manager.invalidate_pattern("get_knowledge_graph:*")
            rebuilt_items += 1
            logger.info("已失效知识索引缓存")

        if index_type in ["all", "sessions"]:
            # 失效会话相关缓存
            cache_manager.invalidate_pattern("analyze_session:*")
            rebuilt_items += 1
            logger.info("已失效会话索引缓存")

        if index_type == "all":
            # 全局缓存失效
            cache_manager.invalidate_pattern("track_project:*")
            rebuilt_items += 1
            logger.info("已失效项目索引缓存")

        return MCPResult(
            data={
                "status": "completed",
                "message": f"成功重建 {index_type} 索引",
                "index_type": index_type,
                "rebuilt_items": rebuilt_items
            }
        )

    except Exception as e:
        logger.error(f"重建索引失败: {e}")
        return MCPResult(
            data={
                "status": "failed",
                "error": str(e)
            }
        )


@server.tool("get_cache_stats")
async def get_cache_stats() -> MCPResult:
    """
    获取缓存统计信息

    Returns:
        MCPResult with:
        {
            "backend": "redis" | "memory",
            "redis_available": bool,
            "cache_hits": int,
            "cache_misses": int,
            "cache_sets": int,
            "hit_rate": float,
            "registered_tools": int,
            "invalidated_caches": int,
            "tools": {...}
        }
    """
    if cache_manager:
        stats = cache_manager.get_stats()
        logger.info(f"缓存统计: 命中率={stats.get('hit_rate', 0):.2%}, 后端={stats.get('backend', 'unknown')}")
        return MCPResult(data=stats)
    else:
        return MCPResult(
            data={
                "backend": "none",
                "error": "Cache manager not initialized"
            }
        )


# ============ Tasks 扩展 (长任务管理) ============

@server.tool("analyze_project_deep")
async def analyze_project_deep_tool(project_path: str) -> TaskHandleResult:
    """
    深度分析项目（长任务，5-10分钟）

    Args:
        project_path: 项目路径

    Returns:
        TaskHandleResult with task_id for progress tracking
    """
    from src.tasks.long_tasks import analyze_project_deep

    logger.info(f"启动项目深度分析: {project_path}")

    task_id = task_manager.create_task(
        "Deep Project Analysis",
        lambda tid, tmgr: analyze_project_deep(tid, tmgr, project_path),
        eta_seconds=600  # 预计10分钟
    )

    return TaskHandleResult(
        task_id=task_id,
        status="running",
        progress=0.0,
        message=f"正在分析项目: {project_path}",
        eta_seconds=600
    )


@server.tool("vectorize_knowledge_graph")
async def vectorize_knowledge_graph_tool(graph_size: int = 1000) -> TaskHandleResult:
    """
    知识图谱向量化（长任务，3-5分钟）

    Args:
        graph_size: 图谱节点数量

    Returns:
        TaskHandleResult with task_id for progress tracking
    """
    from src.tasks.long_tasks import vectorize_knowledge_graph

    logger.info(f"启动知识图谱向量化: {graph_size} 节点")

    task_id = task_manager.create_task(
        "Vectorize Knowledge Graph",
        lambda tid, tmgr: vectorize_knowledge_graph(tid, tmgr, graph_size),
        eta_seconds=300  # 预计5分钟
    )

    return TaskHandleResult(
        task_id=task_id,
        status="running",
        progress=0.0,
        message=f"正在向量化 {graph_size} 个节点",
        eta_seconds=300
    )


@server.tool("research_technology_deep")
async def research_technology_deep_tool(
    topic: str,
    depth: str = "comprehensive"
) -> TaskHandleResult:
    """
    深度技术调研（长任务，8-12分钟）

    Args:
        topic: 技术主题
        depth: 调研深度 (basic/intermediate/comprehensive)

    Returns:
        TaskHandleResult with task_id for progress tracking
    """
    from src.tasks.long_tasks import research_technology_deep

    logger.info(f"启动深度技术调研: {topic} (深度: {depth})")

    task_id = task_manager.create_task(
        "Deep Technology Research",
        lambda tid, tmgr: research_technology_deep(tid, tmgr, topic, depth),
        eta_seconds=720  # 预计12分钟
    )

    return TaskHandleResult(
        task_id=task_id,
        status="running",
        progress=0.0,
        message=f"正在深度调研: {topic}",
        eta_seconds=720
    )


@server.tool("tasks/get")
async def get_task_status(task_id: str) -> MCPResult:
    """
    查询任务状态

    Args:
        task_id: 任务ID (e.g. "task-a7b3c9d2")

    Returns:
        MCPResult with:
        {
            "taskId": "task-a7b3c9d2",
            "name": "Deep Project Analysis",
            "status": "running",
            "progress": 0.65,
            "message": "Analyzing architecture...",
            "etaSeconds": 120,
            "result": {...}  # 仅当 status=completed 时存在
        }
    """
    logger.info(f"查询任务状态: {task_id}")

    task = task_manager.get_task(task_id)

    if not task:
        raise MCPError(f"Task not found: {task_id}", code=-32001)

    return MCPResult(
        data=task.to_dict(),
        meta={
            "ttlMs": 5000 if task.status == "running" else 60000,  # 运行中5秒缓存，完成后1分钟
            "cacheScope": "user"
        }
    )


@server.tool("tasks/list")
async def list_tasks(
    status: str = None,
    limit: int = 100
) -> MCPResult:
    """
    列出所有任务

    Args:
        status: 可选状态过滤 (running, completed, failed, cancelled)
        limit: 最大返回数量 (默认100)

    Returns:
        MCPResult with:
        {
            "tasks": [...],
            "total": 15,
            "filtered": 3  # 应用过滤后的数量
        }
    """
    logger.info(f"列出任务: status={status}, limit={limit}")

    tasks = task_manager.list_tasks(status=status, limit=limit)
    task_dicts = [t.to_dict() for t in tasks]

    return MCPResult(
        data={
            "tasks": task_dicts,
            "total": len(task_manager.tasks),
            "filtered": len(task_dicts)
        },
        meta={
            "ttlMs": 10000,  # 10秒缓存
            "cacheScope": "user"
        }
    )


@server.tool("tasks/cancel")
async def cancel_task(task_id: str) -> MCPResult:
    """
    取消正在运行的任务

    Args:
        task_id: 任务ID

    Returns:
        MCPResult with:
        {
            "taskId": "task-a7b3c9d2",
            "status": "cancelled",
            "message": "Task cancellation requested"
        }
    """
    logger.info(f"取消任务: {task_id}")

    success = await task_manager.cancel_task(task_id)

    if not success:
        task = task_manager.get_task(task_id)
        if not task:
            raise MCPError(f"Task not found: {task_id}", code=-32001)
        else:
            raise MCPError(
                f"Cannot cancel task (status: {task.status})",
                code=-32002
            )

    return MCPResult(
        data={
            "taskId": task_id,
            "status": "cancelled",
            "message": "Task cancellation requested"
        }
    )


# ============ Cache Management ============

@server.tool("invalidate_cache")
async def invalidate_cache(
    patterns: list[str] = None,
    tools: list[str] = None
) -> MCPResult:
    """
    失效缓存

    用例：
    1. 知识更新后，失效相关搜索缓存
    2. 项目修改后，失效项目分析缓存
    3. 手动刷新缓存

    Args:
        patterns: 缓存键模式列表 (e.g. ["search_knowledge:*", "get_project:proj-001"])
        tools: 工具名称列表 (失效该工具的所有缓存)

    Returns:
        MCPResult with:
        {
            "invalidated_count": 15,
            "patterns": [...],
            "message": "Cache invalidated successfully"
        }
    """
    logger.info(f"失效缓存: patterns={patterns}, tools={tools}")

    invalidated_count = 0

    # 按模式失效
    if patterns:
        for pattern in patterns:
            cache_manager.invalidate_pattern(pattern)
            invalidated_count += 1

    # 按工具失效（失效该工具的所有可能缓存键）
    if tools:
        for tool_name in tools:
            # 工具级失效：假设缓存键格式为 "tool_name:*"
            cache_manager.invalidate_pattern(f"{tool_name}:*")
            invalidated_count += 1

    # 获取统计信息
    stats = cache_manager.get_stats()

    return MCPResult(
        data={
            "invalidated_count": invalidated_count,
            "patterns": patterns or [],
            "tools": tools or [],
            "message": f"Successfully invalidated {invalidated_count} cache patterns",
            "stats": stats
        }
    )


@server.tool("cache_stats")
async def cache_stats() -> MCPResult:
    """
    获取缓存统计信息

    Returns:
        MCPResult with:
        {
            "registered_tools": 8,
            "invalidated_caches": 3,
            "tools": {
                "search_knowledge": [3600, "user"],
                ...
            }
        }
    """
    logger.info("获取缓存统计")

    stats = cache_manager.get_stats()

    return MCPResult(
        data=stats,
        meta={
            "ttlMs": 10000,  # 10秒缓存
            "cacheScope": "user"
        }
    )


# ============ MCP Resources ============

@server.resource("knowledge://graph")
async def get_knowledge_graph() -> str:
    """获取知识图谱"""
    # TODO: 从 Memory MCP 读取知识图谱
    return "知识图谱数据 (待实现)"


@server.resource("sessions://list")
async def list_sessions() -> str:
    """列出所有会话"""
    # TODO: 从文件系统读取会话列表
    return "会话列表 (待实现)"


# ============ 生命周期管理 ============

async def startup():
    """启动时执行"""
    global session_analyzer, memory_manager, learning_coach, idle_detector
    global project_agent, interview_agent
    global nonce_store, jwt_handler, cache_manager
    global pg_knowledge_graph, llm_provider

    logger.info("=" * 50)
    logger.info("Learning System MCP Server 启动中...")
    logger.info(f"协议版本: MCP 2026-07-28")
    logger.info(f"项目根目录: {settings.project_root}")
    logger.info(f"数据目录: {settings.data_dir}")
    logger.info("=" * 50)

    # 启动事件总线
    await bus.start()
    logger.info("[OK] 事件总线已启动")

    # 初始化 Redis 缓存（如果启用）
    redis_cache = None
    if settings.redis_enabled:
        try:
            from src.storage.redis_cache import RedisCache
            redis_cache = await RedisCache.create(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password
            )
            # 健康检查
            if await redis_cache.health_check():
                logger.info(f"[OK] Redis 缓存已启用 ({settings.redis_host}:{settings.redis_port}/{settings.redis_db})")
            else:
                logger.warning("[WARN] Redis 健康检查失败，将使用内存缓存")
                redis_cache = None
        except Exception as e:
            logger.warning(f"[WARN] Redis 连接失败: {e}，将使用内存缓存")
            redis_cache = None
    else:
        logger.info("[INFO] Redis 缓存已禁用，使用内存缓存")

    # 初始化缓存管理器（传入 Redis 后端）
    cache_manager = CacheManager(redis_cache=redis_cache)
    await cache_manager.start_cleanup_task()
    logger.info("[OK] 缓存管理器已启动")

    # 初始化安全组件
    logger.info("[...] 安全组件初始化...")
    nonce_store = NonceStore(cleanup_interval_seconds=60)
    await nonce_store.start()
    logger.info("[OK] NonceStore 已启动")

    jwt_handler = JWTHandler(nonce_store)
    logger.info("[OK] JWTHandler 已初始化")

    # 初始化 Agents (6/6)
    logger.info("[...] Agents 初始化 (6/6)...")

    # 初始化 PostgreSQL 知识图谱 (优先初始化，MemoryManager 依赖)
    from src.storage.postgres_knowledge_graph import PostgresKnowledgeGraph
    from src.storage.local_knowledge_graph import LocalKnowledgeGraph
    from pathlib import Path

    global pg_knowledge_graph
    knowledge_graph = None

    # 尝试连接 PostgreSQL
    if settings.postgres_enabled:
        try:
            pg_knowledge_graph = PostgresKnowledgeGraph(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                deepseek_api_key=settings.deepseek_api_key
            )
            await pg_knowledge_graph.connect()
            knowledge_graph = pg_knowledge_graph
            logger.info("[OK] PostgreSQL KnowledgeGraph 已连接")
        except Exception as e:
            logger.warning(f"[WARN] PostgreSQL 连接失败: {e}，降级到 LocalKnowledgeGraph")

    # 降级到 LocalKnowledgeGraph
    if knowledge_graph is None:
        try:
            local_kg_path = Path(settings.data_dir) / "knowledge" / "graph.db"
            knowledge_graph = LocalKnowledgeGraph(local_kg_path)
            logger.info(f"[OK] LocalKnowledgeGraph 已初始化 ({local_kg_path})")
        except Exception as e:
            logger.warning(f"[WARN] LocalKnowledgeGraph 初始化失败: {e}，将使用内存存储")
            knowledge_graph = None

    session_analyzer = SessionAnalyzer("session_analyzer_001", bus)
    await session_analyzer.start()
    logger.info("[OK] SessionAnalyzer 已启动 (1/6)")

    memory_manager = MemoryManager(
        "memory_manager_001",
        bus,
        knowledge_graph=knowledge_graph,
        local_db_path=str(Path(settings.data_dir) / "knowledge" / "graph.db")
    )
    await memory_manager.start()
    logger.info("[OK] MemoryManager 已启动 (2/6)")

    learning_coach = LearningCoach("learning_coach_001", bus)
    await learning_coach.start()
    logger.info("[OK] LearningCoach 已启动 (3/6)")

    # 新增：ProjectAgent
    from src.agents.project_agent import ProjectAgent
    project_agent = ProjectAgent("project_agent_001", bus)
    await project_agent.start()
    logger.info("[OK] ProjectAgent 已启动 (4/6)")

    # 新增：InterviewAgent
    from src.agents.interview_agent import InterviewAgent
    interview_agent = InterviewAgent("interview_agent_001", bus, llm_provider=None)
    await interview_agent.start()
    logger.info("[OK] InterviewAgent 已启动 (5/6)")

    # 注意：ProjectAnalyzer 不是事件驱动 Agent，而是工具类，按需调用
    logger.info("[OK] ProjectAnalyzer (工具类，按需调用) (6/6)")

    # 初始化空闲检测器（测试用：60秒空闲阈值）
    idle_detector = IdleDetector(bus, idle_threshold_seconds=60, check_interval_seconds=10)
    await idle_detector.start()
    logger.info("[OK] IdleDetector 已启动")

    # 初始化 LLM Provider
    global llm_provider
    if settings.deepseek_api_key and settings.deepseek_api_key != "placeholder_key":
        try:
            from src.llm.factory import LLMProviderFactory
            llm_provider = LLMProviderFactory.create({
                "provider": "deepseek",
                "api_key": settings.deepseek_api_key,
                "model": "deepseek-chat",
                "base_url": settings.deepseek_base_url
            })
            logger.info("[OK] DeepSeek LLM Provider 已初始化")
        except Exception as e:
            logger.warning(f"[WARN] LLM Provider 初始化失败: {e}")
            llm_provider = None
    else:
        logger.info("[INFO] DeepSeek API Key 未配置，LLM 对话功能将不可用")


async def shutdown():
    """关闭时执行"""
    global session_analyzer, memory_manager, learning_coach, idle_detector
    global project_agent, interview_agent
    global nonce_store, jwt_handler, cache_manager

    logger.info("Learning System MCP Server 关闭中...")

    # 停止空闲检测器
    if idle_detector:
        await idle_detector.stop()
        logger.info("[OK] IdleDetector 已停止")

    # 停止 Agents
    if interview_agent:
        await interview_agent.stop()
        logger.info("[OK] InterviewAgent 已停止")

    if project_agent:
        await project_agent.stop()
        logger.info("[OK] ProjectAgent 已停止")

    if learning_coach:
        await learning_coach.stop()
        logger.info("[OK] LearningCoach 已停止")

    if memory_manager:
        await memory_manager.stop()
        logger.info("[OK] MemoryManager 已停止")

    if session_analyzer:
        await session_analyzer.stop()
        logger.info("[OK] SessionAnalyzer 已停止")

    # 停止安全组件
    if nonce_store:
        await nonce_store.stop()
        logger.info("[OK] NonceStore 已停止")

    # 停止缓存管理器
    if cache_manager:
        await cache_manager.stop_cleanup_task()
        # 关闭 Redis 连接
        if cache_manager.redis_cache:
            await cache_manager.redis_cache.close()
            logger.info("[OK] Redis 缓存已关闭")
        logger.info("[OK] 缓存管理器已停止")

    # 关闭 PostgreSQL 连接
    if pg_knowledge_graph:
        await pg_knowledge_graph.close()
        logger.info("[Stopped] PostgreSQL KnowledgeGraph 已关闭")

    # 停止事件总线
    await bus.stop()
    logger.info("[OK] 事件总线已停止")


async def main_loop():
    """主事件循环"""
    # 启动生命周期
    await startup()

    try:
        # 初始化 Hook 系统
        from src.storage import ObservationStore
        from src.hooks import SessionCaptureHook

        observation_store = ObservationStore()
        session_hook = SessionCaptureHook(observation_store)

        # 创建传输层（注入 Hook）
        transport = StdioTransport(hooks=[session_hook])

        logger.info("[START] MCP Server 已启动，等待客户端连接...")
        logger.info("[STDIO] 使用 stdio 传输层")
        logger.info("[HOOK] Hook 系统已启用（会话自动捕获）")
        logger.info("=" * 50)

        # 运行传输层（阻塞直到连接关闭）
        await transport.run(server)

    except KeyboardInterrupt:
        logger.info("收到中断信号，准备关闭...")
    except Exception as e:
        logger.error(f"服务器错误: {e}")
    finally:
        await shutdown()


# ============ 原子化项目分析工具 (AI-First 架构) ============

@server.tool("project/detect_framework")
async def detect_framework(project_path: str) -> MCPResult:
    """
    检测项目使用的框架（原子工具）

    Args:
        project_path: 项目根目录路径

    Returns:
        MCPResult with:
        {
            "framework": "FastAPI",
            "confidence": 0.9,
            "evidence": ["found @server.tool decorator", "fastapi in requirements.txt"]
        }
    """
    from src.tools.file_explorer import FileExplorer

    try:
        explorer = FileExplorer(project_path)

        # 1. 检测配置文件
        config_files = explorer.detect_config_files()

        framework = "Unknown"
        confidence = 0.0
        evidence = []

        # 2. Python 项目框架检测
        if 'python_pip' in config_files or 'python_poetry' in config_files:
            req_file = config_files.get('python_pip') or config_files.get('python_poetry')

            try:
                content = req_file.read_text(encoding='utf-8').lower()

                if 'fastapi' in content:
                    framework = "FastAPI"
                    confidence = 0.9
                    evidence.append("fastapi in dependencies")
                elif 'django' in content:
                    framework = "Django"
                    confidence = 0.85
                    evidence.append("django in dependencies")
                elif 'flask' in content:
                    framework = "Flask"
                    confidence = 0.85
                    evidence.append("flask in dependencies")
            except Exception as e:
                logger.warning(f"Failed to read requirements: {e}")

        # 3. Node.js 项目框架检测
        elif 'nodejs_npm' in config_files:
            pkg_file = config_files['nodejs_npm']

            try:
                import json
                pkg_data = json.loads(pkg_file.read_text(encoding='utf-8'))
                deps = {**pkg_data.get('dependencies', {}), **pkg_data.get('devDependencies', {})}

                if 'next' in deps:
                    framework = "Next.js"
                    confidence = 0.9
                    evidence.append("next in dependencies")
                elif 'nuxt' in deps:
                    framework = "Nuxt.js"
                    confidence = 0.9
                    evidence.append("nuxt in dependencies")
                elif 'react' in deps:
                    framework = "React"
                    confidence = 0.8
                    evidence.append("react in dependencies")
                elif 'vue' in deps:
                    framework = "Vue.js"
                    confidence = 0.8
                    evidence.append("vue in dependencies")
            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")

        return MCPResult(
            data={
                "framework": framework,
                "confidence": confidence,
                "evidence": evidence
            }
        )

    except Exception as e:
        logger.error(f"Framework detection failed: {e}")
        return MCPResult(
            data={
                "framework": "Unknown",
                "confidence": 0.0,
                "evidence": [],
                "error": str(e)
            }
        )


@server.tool("project/scan_structure")
async def scan_structure(project_path: str) -> MCPResult:
    """
    扫描项目目录结构（原子工具）

    Args:
        project_path: 项目根目录路径

    Returns:
        MCPResult with:
        {
            "directories": ["src", "tests", "docs"],
            "entry_points": ["server.py", "main.py"],
            "file_stats": {
                "total_files": 50,
                "python_files": 25,
                "total_lines": 2000
            }
        }
    """
    from src.tools.file_explorer import FileExplorer
    from pathlib import Path

    try:
        explorer = FileExplorer(project_path)

        # 1. 列出目录结构
        directories = explorer.list_directory(depth=2)

        # 2. 查找入口文件
        entry_points = explorer.find_entry_points()
        entry_points_str = [str(ep.relative_to(Path(project_path))) for ep in entry_points]

        # 3. 文件统计
        py_files = explorer.glob_files("**/*.py")
        file_stats = {
            "total_files": len(list(Path(project_path).rglob("*.*"))),
            "python_files": len(py_files),
        }

        # 统计代码行数
        total_lines = 0
        for py_file in py_files[:50]:  # 限制统计前50个文件，避免太慢
            try:
                content = explorer.read_file(str(Path(py_file).relative_to(Path(project_path))), max_lines=10000)
                total_lines += len(content.split('\n'))
            except:
                pass

        file_stats["total_lines"] = total_lines

        return MCPResult(
            data={
                "directories": directories,
                "entry_points": entry_points_str,
                "file_stats": file_stats
            }
        )

    except Exception as e:
        logger.error(f"Structure scan failed: {e}")
        return MCPResult(
            data={
                "directories": [],
                "entry_points": [],
                "file_stats": {},
                "error": str(e)
            }
        )


@server.tool("project/analyze_dependencies")
async def analyze_dependencies(project_path: str) -> MCPResult:
    """
    分析项目依赖（原子工具）

    Args:
        project_path: 项目根目录路径

    Returns:
        MCPResult with:
        {
            "language": "Python",
            "package_manager": "pip",
            "dependencies": [
                {"name": "fastapi", "version": "0.100.0"},
                {"name": "pydantic", "version": "2.0.0"}
            ],
            "dependency_count": 15
        }
    """
    from src.tools.file_explorer import FileExplorer
    from pathlib import Path

    try:
        explorer = FileExplorer(project_path)
        config_files = explorer.detect_config_files()

        language = "Unknown"
        package_manager = "Unknown"
        dependencies = []

        # Python 项目
        if 'python_pip' in config_files:
            language = "Python"
            package_manager = "pip"
            req_file = config_files['python_pip']

            try:
                lines = req_file.read_text(encoding='utf-8').splitlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '==' in line:
                            name, version = line.split('==', 1)
                            dependencies.append({"name": name.strip(), "version": version.strip()})
                        elif '>=' in line:
                            name, version = line.split('>=', 1)
                            dependencies.append({"name": name.strip(), "version": f">={version.strip()}"})
                        else:
                            dependencies.append({"name": line, "version": "latest"})
            except Exception as e:
                logger.warning(f"Failed to parse requirements.txt: {e}")

        elif 'python_poetry' in config_files:
            language = "Python"
            package_manager = "poetry"
            # TODO: 解析 pyproject.toml

        # Node.js 项目
        elif 'nodejs_npm' in config_files:
            language = "JavaScript/TypeScript"
            package_manager = "npm"
            pkg_file = config_files['nodejs_npm']

            try:
                import json
                pkg_data = json.loads(pkg_file.read_text(encoding='utf-8'))

                for name, version in pkg_data.get('dependencies', {}).items():
                    dependencies.append({"name": name, "version": version})

                for name, version in pkg_data.get('devDependencies', {}).items():
                    dependencies.append({"name": name, "version": version, "dev": True})
            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")

        return MCPResult(
            data={
                "language": language,
                "package_manager": package_manager,
                "dependencies": dependencies,
                "dependency_count": len(dependencies)
            }
        )

    except Exception as e:
        logger.error(f"Dependency analysis failed: {e}")
        return MCPResult(
            data={
                "language": "Unknown",
                "package_manager": "Unknown",
                "dependencies": [],
                "dependency_count": 0,
                "error": str(e)
            }
        )


@server.tool("project/extract_patterns")
async def extract_patterns(project_path: str, file_limit: int = 20) -> MCPResult:
    """
    提取项目代码模式（原子工具）

    Args:
        project_path: 项目根目录路径
        file_limit: 采样文件数量限制

    Returns:
        MCPResult with:
        {
            "naming_convention": {
                "files": "snake_case",
                "functions": "snake_case",
                "classes": "PascalCase"
            },
            "code_patterns": {
                "async_usage": 0.8,
                "type_hints": 0.6,
                "decorators": ["@server.tool", "@cacheable"]
            }
        }
    """
    from src.tools.file_explorer import FileExplorer
    from src.tools.pattern_matcher import PatternMatcher
    from pathlib import Path

    try:
        explorer = FileExplorer(project_path)
        matcher = PatternMatcher()

        # 1. 查找 Python 文件
        py_files = explorer.glob_files("**/*.py")[:file_limit]

        if not py_files:
            return MCPResult(
                data={
                    "naming_convention": {},
                    "code_patterns": {},
                    "message": "No Python files found"
                }
            )

        # 2. 分析命名规范
        naming = matcher.detect_naming_convention([Path(project_path) / f for f in py_files])

        # 3. 统计代码模式
        total_async = 0
        all_decorators = []

        for py_file in py_files[:10]:  # 限制分析前10个文件
            try:
                file_path = Path(project_path) / py_file

                # 统计 async
                async_count = matcher.count_async_patterns(file_path)
                total_async += async_count

                # 收集装饰器
                decorators = matcher.detect_decorators(file_path)
                all_decorators.extend(decorators)

            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")

        # 4. 统计装饰器频率
        from collections import Counter
        decorator_counts = Counter(all_decorators)
        top_decorators = [dec for dec, count in decorator_counts.most_common(10)]

        return MCPResult(
            data={
                "naming_convention": {
                    "files": naming,
                    "functions": naming,
                    "classes": "PascalCase" if naming == "snake_case" else "unknown"
                },
                "code_patterns": {
                    "async_usage": round(total_async / max(len(py_files), 1), 2),
                    "decorators": top_decorators
                }
            }
        )

    except Exception as e:
        logger.error(f"Pattern extraction failed: {e}")
        return MCPResult(
            data={
                "naming_convention": {},
                "code_patterns": {},
                "error": str(e)
            }
        )


@server.tool("project_analyze_status")
@cacheable(ttl_seconds=3600, scope="public")  # 1小时公共缓存
async def project_analyze_status(
    project_path: str,
    depth: int = 3,
    output_format: str = "json"
) -> MCPResult:
    """
    完整的项目状态分析，生成结构化报告
    整合框架检测、结构扫描、依赖分析和模式提取

    Args:
        project_path: 项目根目录路径
        depth: 目录扫描深度 (默认3)
        output_format: 输出格式 (json/markdown)

    Returns:
        MCPResult with:
        {
            "project_name": "learning-system",
            "summary": {
                "tech_stack": ["Python - FastAPI"],
                "complexity": "中等",
                "completion_percentage": 80,
                ...
            },
            "todos": [...],
            "learning_suggestions": [...],
            "analysis_phases": {...}
        }
    """
    from workflows.project_status_analyzer import ProjectStatusAnalyzer
    import os

    try:
        # 验证路径
        if not os.path.exists(project_path):
            return MCPResult(
                data={"error": f"项目路径不存在: {project_path}"}
            )

        # 构建工具注册表
        tools_registry = {
            "project/detect_framework": project_detect_framework,
            "project/scan_structure": project_scan_structure,
            "project/analyze_dependencies": project_analyze_dependencies,
            "project/extract_patterns": project_extract_patterns,
        }

        # 创建分析器并执行
        analyzer = ProjectStatusAnalyzer(tools_registry)
        report = await analyzer.analyze(project_path, depth, output_format)

        logger.info(f"项目分析完成: {project_path}")

        return MCPResult(data=report)

    except Exception as e:
        logger.error(f"项目状态分析失败: {e}")
        return MCPResult(
            data={
                "error": str(e),
                "project_path": project_path
            }
        )


@server.tool("chat")
async def chat_tool(
    message: str,
    session_id: str = None,
    skill_context: str = None
) -> MCPResult:
    """
    与 AI 对话，使用 DeepSeek LLM

    Args:
        message: 用户消息
        session_id: 可选的会话ID（用于上下文关联）
        skill_context: 可选的 Skill 文档内容（Markdown 格式）

    Returns:
        MCPResult with:
        {
            "response": "AI 的回答",
            "session_id": "session_xxx",
            "model": "deepseek-chat",
            "wait_confirm": false,  # 是否需要等待用户确认
            "confirm_data": null    # 需要确认的数据
        }
    """
    global llm_provider

    # 检查 LLM Provider 是否可用
    if llm_provider is None:
        return MCPResult(
            data={
                "error": "LLM Provider 未初始化，请检查 DEEPSEEK_API_KEY 配置",
                "response": "抱歉，AI 对话功能暂时不可用。请联系管理员配置 DeepSeek API Key。"
            }
        )

    try:
        # 生成会话ID
        if session_id is None:
            from src.utils.id_generator import generate_session_id
            session_id = generate_session_id()

        # 获取会话历史
        session_history = _get_session_history(session_id)

        # 构建系统提示词
        system_prompt = _build_system_prompt(skill_context)

        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # 添加会话历史
        messages.extend(session_history)

        # 添加当前用户消息
        messages.append({"role": "user", "content": message})

        # 调用 LLM
        logger.info(f"Chat request [session={session_id}]: {message[:50]}...")
        if skill_context:
            logger.info(f"Skill context attached: {len(skill_context)} chars")

        response = await llm_provider.chat(messages)

        logger.info(f"Chat response: {response[:50]}...")

        # 保存会话历史
        _save_to_session_history(session_id, message, response)

        # 检测是否需要等待用户确认（WAIT for user CONFIRM）
        wait_confirm, confirm_data = _detect_wait_confirm(response)

        result_data = {
            "response": response,
            "session_id": session_id,
            "model": "deepseek-chat",
            "wait_confirm": wait_confirm
        }

        if wait_confirm and confirm_data:
            result_data["confirm_data"] = confirm_data

        return MCPResult(data=result_data)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return MCPResult(
            data={
                "error": str(e),
                "response": f"抱歉，处理您的消息时出现错误: {str(e)}"
            }
        )


@server.tool("summarize_conversation")
async def summarize_conversation_tool(
    conversation_text: str,
    extraction_prompt: str = None
) -> MCPResult:
    """
    从对话中提取知识点

    Args:
        conversation_text: 完整的对话文本（格式：用户: 问题\\n助手: 回答）
        extraction_prompt: 可选的自定义提取提示词

    Returns:
        MCPResult with:
        {
            "knowledge_points": [
                {
                    "title": "知识点标题",
                    "content": "详细内容",
                    "tags": ["标签1", "标签2"],
                    "type": "concept|technology|method|tool"
                }
            ],
            "count": 3
        }
    """
    from src.tools.summarize_conversation import summarize_conversation

    try:
        logger.info(f"Summarizing conversation, text length: {len(conversation_text)}")
        result = await summarize_conversation(conversation_text, extraction_prompt)
        logger.info(f"Extraction result: {result.get('count', 0)} knowledge points")
        return MCPResult(data=result)

    except Exception as e:
        logger.error(f"Summarize conversation error: {e}", exc_info=True)
        return MCPResult(
            data={
                "knowledge_points": [],
                "count": 0,
                "error": str(e)
            }
        )


@server.tool("execute_skill")
async def execute_skill_tool(
    skill_name: str,
    context: Dict[str, Any]
) -> MCPResult:
    """
    执行预定义的 Skill 工作流

    Args:
        skill_name: Skill 名称（如 "summarize-knowledge"）
        context: 执行上下文（如对话历史）

    Returns:
        MCPResult with:
        {
            "skill": "summarize-knowledge",
            "status": "success|pending_confirmation|error",
            "phase": "Extract|Confirm|Store",
            "data": {...}  # 阶段特定的数据
        }

    Note:
        这是一个简化的 Skill 执行器，目前支持的 Skills：
        - summarize-knowledge: 知识总结工作流（Extract → Confirm → Store）

        对于需要用户确认的阶段，返回 status="pending_confirmation"
        前端应该显示确认对话框，用户确认后继续执行后续阶段
    """
    from src.tools.summarize_conversation import summarize_conversation

    try:
        logger.info(f"Executing skill: {skill_name}")

        if skill_name == "summarize-knowledge":
            # Phase 1: Extract（提取知识点）
            messages = context.get('messages', [])
            conversation_text = '\n\n'.join([
                f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
                for m in messages
                if m.get('role') in ['user', 'assistant']
            ])

            # 调用提取工具
            result = await summarize_conversation(conversation_text, None)

            if result.get('error'):
                return MCPResult(
                    data={
                        "skill": skill_name,
                        "status": "error",
                        "phase": "Extract",
                        "error": result['error']
                    }
                )

            # Phase 1 完成，返回待确认状态
            return MCPResult(
                data={
                    "skill": skill_name,
                    "status": "pending_confirmation",
                    "phase": "Confirm",
                    "knowledge_points": result.get('knowledge_points', []),
                    "count": result.get('count', 0),
                    "message": "知识点提取完成，等待用户确认"
                }
            )

        else:
            return MCPResult(
                data={
                    "skill": skill_name,
                    "status": "error",
                    "error": f"Unknown skill: {skill_name}. Available skills: summarize-knowledge"
                }
            )

    except Exception as e:
        logger.error(f"Execute skill error: {e}", exc_info=True)
        return MCPResult(
            data={
                "skill": skill_name,
                "status": "error",
                "error": str(e)
            }
        )


# ============ 文件系统工具 ============

@server.tool("read_file")
async def read_file_tool(
    file_path: str,
    encoding: str = "utf-8"
) -> MCPResult:
    """
    读取文件内容

    Args:
        file_path: 文件路径（相对或绝对路径）
        encoding: 文件编码，默认 utf-8

    Returns:
        MCPResult with:
        {
            "content": "文件内容",
            "path": "实际路径",
            "size": 1024,
            "lines": 50
        }
    """
    import os
    from pathlib import Path

    try:
        # 转换为绝对路径
        path = Path(file_path).resolve()

        # 安全检查：不允许读取敏感文件
        sensitive_patterns = ['.env', 'password', 'secret', 'token', 'key', '.pem', '.key']
        if any(pattern in str(path).lower() for pattern in sensitive_patterns):
            logger.warning(f"Blocked reading sensitive file: {path}")
            return MCPResult(
                data={
                    "error": "拒绝读取敏感文件（包含密钥、密码等）",
                    "path": str(path)
                }
            )

        # 检查文件是否存在
        if not path.exists():
            return MCPResult(
                data={
                    "error": f"文件不存在: {path}",
                    "path": str(path)
                }
            )

        if not path.is_file():
            return MCPResult(
                data={
                    "error": f"不是文件: {path}",
                    "path": str(path)
                }
            )

        # 读取文件
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()

        # 获取文件信息
        size = path.stat().st_size
        lines = len(content.splitlines())

        logger.info(f"Read file: {path} ({size} bytes, {lines} lines)")

        return MCPResult(
            data={
                "content": content,
                "path": str(path),
                "size": size,
                "lines": lines
            }
        )

    except UnicodeDecodeError:
        return MCPResult(
            data={
                "error": f"无法用 {encoding} 编码读取文件，可能是二进制文件",
                "path": str(path)
            }
        )
    except Exception as e:
        logger.error(f"Read file error: {e}", exc_info=True)
        return MCPResult(
            data={
                "error": str(e),
                "path": file_path
            }
        )


@server.tool("list_directory")
async def list_directory_tool(
    directory_path: str,
    max_depth: int = 1,
    show_hidden: bool = False
) -> MCPResult:
    """
    列出目录内容

    Args:
        directory_path: 目录路径
        max_depth: 最大递归深度（1=仅当前层，2=包含子目录）
        show_hidden: 是否显示隐藏文件

    Returns:
        MCPResult with:
        {
            "path": "目录路径",
            "items": [
                {"name": "file.py", "type": "file", "size": 1024},
                {"name": "subdir", "type": "directory", "items": [...]}
            ]
        }
    """
    import os
    from pathlib import Path

    try:
        path = Path(directory_path).resolve()

        if not path.exists():
            return MCPResult(
                data={
                    "error": f"目录不存在: {path}",
                    "path": str(path)
                }
            )

        if not path.is_dir():
            return MCPResult(
                data={
                    "error": f"不是目录: {path}",
                    "path": str(path)
                }
            )

        def scan_directory(dir_path: Path, current_depth: int) -> list:
            """递归扫描目录"""
            items = []

            try:
                for item in sorted(dir_path.iterdir()):
                    # 跳过隐藏文件
                    if not show_hidden and item.name.startswith('.'):
                        continue

                    item_data = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file"
                    }

                    if item.is_file():
                        item_data["size"] = item.stat().st_size
                    elif item.is_dir() and current_depth < max_depth:
                        # 递归扫描子目录
                        item_data["items"] = scan_directory(item, current_depth + 1)

                    items.append(item_data)
            except PermissionError:
                pass

            return items

        items = scan_directory(path, 1)

        logger.info(f"Listed directory: {path} ({len(items)} items)")

        return MCPResult(
            data={
                "path": str(path),
                "items": items,
                "count": len(items)
            }
        )

    except Exception as e:
        logger.error(f"List directory error: {e}", exc_info=True)
        return MCPResult(
            data={
                "error": str(e),
                "path": directory_path
            }
        )


@server.tool("search_files")
async def search_files_tool(
    directory_path: str,
    pattern: str,
    max_results: int = 50
) -> MCPResult:
    """
    搜索文件（支持通配符）

    Args:
        directory_path: 搜索目录
        pattern: 文件名模式（如 "*.py", "test_*.js"）
        max_results: 最大返回结果数

    Returns:
        MCPResult with:
        {
            "matches": [
                {"path": "path/to/file.py", "size": 1024},
                ...
            ],
            "count": 10
        }
    """
    from pathlib import Path

    try:
        path = Path(directory_path).resolve()

        if not path.exists() or not path.is_dir():
            return MCPResult(
                data={
                    "error": f"无效的目录: {path}",
                    "matches": [],
                    "count": 0
                }
            )

        # 使用 glob 搜索
        matches = []
        for match in path.rglob(pattern):
            if match.is_file():
                matches.append({
                    "path": str(match),
                    "name": match.name,
                    "size": match.stat().st_size
                })

                if len(matches) >= max_results:
                    break

        logger.info(f"Searched files in {path} with pattern '{pattern}': {len(matches)} matches")

        return MCPResult(
            data={
                "matches": matches,
                "count": len(matches),
                "pattern": pattern
            }
        )

    except Exception as e:
        logger.error(f"Search files error: {e}", exc_info=True)
        return MCPResult(
            data={
                "error": str(e),
                "matches": [],
                "count": 0
            }
        )


@server.tool("write_file")
async def write_file_tool(
    file_path: str,
    content: str,
    encoding: str = "utf-8",
    create_dirs: bool = True
) -> MCPResult:
    """
    写入文件

    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 文件编码，默认 utf-8
        create_dirs: 是否自动创建父目录

    Returns:
        MCPResult with:
        {
            "path": "实际路径",
            "size": 1024,
            "status": "created|updated"
        }
    """
    from pathlib import Path

    try:
        path = Path(file_path).resolve()

        # 检查是否已存在
        existed = path.exists()

        # 创建父目录
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)

        size = path.stat().st_size
        status = "updated" if existed else "created"

        logger.info(f"Wrote file: {path} ({size} bytes, {status})")

        return MCPResult(
            data={
                "path": str(path),
                "size": size,
                "status": status
            }
        )

    except Exception as e:
        logger.error(f"Write file error: {e}", exc_info=True)
        return MCPResult(
            data={
                "error": str(e),
                "path": file_path
            }
        )


@server.tool("get_file_info")
async def get_file_info_tool(
    file_path: str
) -> MCPResult:
    """
    获取文件或目录信息

    Args:
        file_path: 文件或目录路径

    Returns:
        MCPResult with:
        {
            "path": "实际路径",
            "type": "file|directory",
            "size": 1024,
            "created": "2024-01-01T00:00:00",
            "modified": "2024-01-01T00:00:00"
        }
    """
    from pathlib import Path
    from datetime import datetime

    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return MCPResult(
                data={
                    "error": f"路径不存在: {path}",
                    "path": str(path)
                }
            )

        stat = path.stat()

        return MCPResult(
            data={
                "path": str(path),
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size": stat.st_size if path.is_file() else None,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Get file info error: {e}", exc_info=True)
        return MCPResult(
            data={
                "error": str(e),
                "path": file_path
            }
        )


@server.tool("add_knowledge")
async def add_knowledge_tool(
    title: str,
    content: str,
    tags: list[str],
    entity_type: str = "concept"
) -> MCPResult:
    """
    添加单个知识点到知识图谱（封装工具，简化前端调用）

    Args:
        title: 知识点标题
        content: 详细内容
        tags: 标签列表
        entity_type: 实体类型（concept/technology/method/tool）

    Returns:
        MCPResult with:
        {
            "entity_name": "知识点标题",
            "status": "created",
            "observations_count": 2
        }
    """
    from src.storage.mcp_memory_adapter import mcp_memory_adapter

    try:
        # 构建 observations（内容 + 标签）
        observations = [content]
        if tags:
            observations.append(f"标签: {', '.join(tags)}")

        # 调用 create_entities
        await mcp_memory_adapter.create_entities([{
            "name": title,
            "entityType": entity_type,
            "observations": observations
        }])

        logger.info(f"Added knowledge: {title} (type={entity_type}, tags={len(tags)})")

        return MCPResult(
            data={
                "entity_name": title,
                "status": "created",
                "observations_count": len(observations)
            }
        )

    except Exception as e:
        logger.error(f"Add knowledge error: {e}", exc_info=True)
        return MCPResult(
            data={
                "error": str(e),
                "entity_name": title
            }
        )


def main():
    """入口函数"""
    # 配置日志
    import sys
    logger.remove()
    logger.add(
        sys.stderr,  # 日志输出到 stderr，避免污染 stdout 的 JSON-RPC 消息
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # 运行主循环
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("程序已退出")


if __name__ == "__main__":
    main()
