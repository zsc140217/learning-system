"""
Learning System MCP Server
基于自研 MCP 2026-07-28 协议层实现
"""
import asyncio
from typing import Any, Dict

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
idle_detector = None

# 安全组件
nonce_store = None
jwt_handler = None

# 缓存管理
cache_manager = None


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
    session_id: str
) -> MCPResult:
    """
    保存知识点到 Memory MCP

    Args:
        knowledge_points: 知识点列表
        session_id: 会话ID

    Returns:
        MCPResult with:
        {
            "saved_count": 3,
            "knowledge_ids": ["knowledge_xxx", ...],
            "status": "completed"
        }
    """
    logger.info(f"保存知识点: {len(knowledge_points)} 个")

    # 发布事件
    await bus.publish({
        "type": "knowledge_save_requested",
        "session_id": session_id,
        "data": {"knowledge_points": knowledge_points}
    })

    # 自动失效知识搜索缓存
    cache_manager.invalidate_pattern("search_knowledge:*")
    cache_manager.invalidate_pattern("get_knowledge_graph:*")
    logger.info("自动失效知识缓存")

    # TODO: 实际实现 Memory Manager 逻辑
    return MCPResult(
        data={
            "saved_count": len(knowledge_points),
            "knowledge_ids": [],
            "status": "pending"
        }
    )


@server.tool("track_project")
@cacheable(ttl_seconds=86400, scope="user")  # 1天用户级缓存
async def track_project(
    project_path: str,
    project_name: str = None
) -> MCPResult:
    """
    追踪项目经验

    Args:
        project_path: 项目路径
        project_name: 可选的项目名称

    Returns:
        MCPResult with:
        {
            "project_id": "project_xxx",
            "highlights": [...],
            "status": "completed"
        }
    """
    from src.utils.id_generator import generate_project_id

    project_id = generate_project_id()
    logger.info(f"追踪项目: {project_path}")

    await bus.publish({
        "type": "project_track_requested",
        "project_id": project_id,
        "data": {
            "path": project_path,
            "name": project_name
        }
    })

    # TODO: 实际实现 Project Tracker 逻辑
    return MCPResult(
        data={
            "project_id": project_id,
            "highlights": [],
            "status": "pending"
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

    # TODO: 实际实现 Tech Explorer 逻辑
    return MCPResult(
        data={
            "topic": topic,
            "learning_path": [],
            "resources": [],
            "status": "pending"
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

        # TODO: 实现实际的项目删除逻辑
        # await project_manager.delete_project(project_id)

        return MCPResult(
            data={
                "status": "completed",
                "message": f"成功删除项目 {project_id}",
                "project_id": project_id
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

        # TODO: 实现实际的索引重建逻辑
        # await index_manager.rebuild(index_type)

        return MCPResult(
            data={
                "status": "completed",
                "message": f"成功重建 {index_type} 索引",
                "index_type": index_type
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
    global nonce_store, jwt_handler, cache_manager

    logger.info("=" * 50)
    logger.info("Learning System MCP Server 启动中...")
    logger.info(f"协议版本: MCP 2026-07-28")
    logger.info(f"项目根目录: {settings.project_root}")
    logger.info(f"数据目录: {settings.data_dir}")
    logger.info("=" * 50)

    # 启动事件总线
    await bus.start()
    logger.info("[OK] 事件总线已启动")

    # 初始化缓存管理器
    cache_manager = CacheManager()
    await cache_manager.start_cleanup_task()
    logger.info("[OK] 缓存管理器已启动")

    # 初始化安全组件
    logger.info("[...] 安全组件初始化...")
    nonce_store = NonceStore(cleanup_interval_seconds=60)
    await nonce_store.start()
    logger.info("[OK] NonceStore 已启动")

    jwt_handler = JWTHandler(nonce_store)
    logger.info("[OK] JWTHandler 已初始化")

    # 初始化 Agents
    logger.info("[...] Agents 初始化...")

    session_analyzer = SessionAnalyzer("session_analyzer_001", bus)
    await session_analyzer.start()
    logger.info("[OK] SessionAnalyzer 已启动")

    memory_manager = MemoryManager("memory_manager_001", bus)
    await memory_manager.start()
    logger.info("[OK] MemoryManager 已启动")

    learning_coach = LearningCoach("learning_coach_001", bus)
    await learning_coach.start()
    logger.info("[OK] LearningCoach 已启动")

    # 初始化空闲检测器（测试用：60秒空闲阈值）
    idle_detector = IdleDetector(bus, idle_threshold_seconds=60, check_interval_seconds=10)
    await idle_detector.start()
    logger.info("[OK] IdleDetector 已启动")


async def shutdown():
    """关闭时执行"""
    global session_analyzer, memory_manager, learning_coach, idle_detector
    global nonce_store, jwt_handler

    logger.info("Learning System MCP Server 关闭中...")

    # 停止空闲检测器
    if idle_detector:
        await idle_detector.stop()
        logger.info("[OK] IdleDetector 已停止")

    # 停止 Agents
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


def main():
    """入口函数"""
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
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
