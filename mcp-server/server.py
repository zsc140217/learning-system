"""
Learning System MCP Server
基于FastMCP实现的MCP 2026-07-28服务器
"""
import asyncio
from typing import Any, Dict

from fastmcp import FastMCP
from loguru import logger

from config import settings
from src.bus.agent_bus import bus
from src.agents.session_analyzer import SessionAnalyzer
from src.agents.memory_manager import MemoryManager


# 创建FastMCP实例
mcp = FastMCP("Learning System")

# 全局Agents
session_analyzer = None
memory_manager = None


# ============ MCP Tools ============

@mcp.tool()
async def analyze_session(
    session_data: str,
    session_id: str | None = None
) -> Dict[str, Any]:
    """
    分析会话内容，提取知识点

    Args:
        session_data: 会话内容 (Markdown格式)
        session_id: 可选的会话ID，不提供则自动生成

    Returns:
        {
            "session_id": "session_1722518400_a7b3c9d2",
            "knowledge_points": [
                {
                    "title": "...",
                    "content": "...",
                    "tags": [...]
                }
            ],
            "status": "completed"
        }
    """
    from src.utils.id_generator import generate_session_id

    if session_id is None:
        session_id = generate_session_id()

    logger.info(f"分析会话: {session_id}")

    # 解析会话内容为transcript格式
    # 简单实现：按行解析 Markdown，提取用户/助手对话
    transcript = _parse_session_data(session_data)

    # 发布session.completed事件（SessionAnalyzer会处理）
    await bus.publish({
        "type": "session.completed",
        "session_id": session_id,
        "transcript": transcript
    })

    # 等待SessionAnalyzer处理（实际应该订阅knowledge.extracted事件）
    # 这里简化处理，直接返回状态
    await asyncio.sleep(0.2)  # 给Agent时间处理

    return {
        "session_id": session_id,
        "status": "completed",
        "message": "Session analysis triggered. Knowledge points will be extracted."
    }


def _parse_session_data(session_data: str) -> list[Dict[str, str]]:
    """
    解析会话数据为transcript格式

    Args:
        session_data: Markdown格式的会话内容

    Returns:
        transcript列表
    """
    # 简单实现：按换行符分割，提取问答对
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
            # 无角色标记，作为assistant内容
            transcript.append({"role": "assistant", "content": line})

    return transcript


@mcp.tool()
async def save_knowledge(
    knowledge_points: list[Dict[str, Any]],
    session_id: str
) -> Dict[str, Any]:
    """
    保存知识点到Memory MCP

    Args:
        knowledge_points: 知识点列表
        session_id: 会话ID

    Returns:
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

    # TODO: 实际实现Memory Manager逻辑
    return {
        "saved_count": len(knowledge_points),
        "knowledge_ids": [],
        "status": "pending"
    }


@mcp.tool()
async def track_project(
    project_path: str,
    project_name: str | None = None
) -> Dict[str, Any]:
    """
    追踪项目经验

    Args:
        project_path: 项目路径
        project_name: 可选的项目名称

    Returns:
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

    # TODO: 实际实现Project Tracker逻辑
    return {
        "project_id": project_id,
        "highlights": [],
        "status": "pending"
    }


@mcp.tool()
async def explore_technology(
    topic: str,
    depth: str = "basic"
) -> Dict[str, Any]:
    """
    探索技术主题

    Args:
        topic: 技术主题
        depth: 探索深度 (basic, intermediate, advanced)

    Returns:
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

    # TODO: 实际实现Tech Explorer逻辑
    return {
        "topic": topic,
        "learning_path": [],
        "resources": [],
        "status": "pending"
    }


# ============ MCP Resources ============

@mcp.resource("knowledge://graph")
async def get_knowledge_graph() -> str:
    """获取知识图谱"""
    # TODO: 从Memory MCP读取知识图谱
    return "知识图谱数据 (待实现)"


@mcp.resource("sessions://list")
async def list_sessions() -> str:
    """列出所有会话"""
    # TODO: 从文件系统读取会话列表
    return "会话列表 (待实现)"


# ============ 启动和关闭 ============

async def startup():
    """启动时执行"""
    global session_analyzer, memory_manager

    logger.info("=" * 50)
    logger.info("Learning System MCP Server 启动中...")
    logger.info(f"项目根目录: {settings.project_root}")
    logger.info(f"数据目录: {settings.data_dir}")
    logger.info("=" * 50)

    # 启动事件总线
    await bus.start()
    logger.info("✅ 事件总线已启动")

    # 初始化Agents
    logger.info("⏳ Agents初始化...")

    session_analyzer = SessionAnalyzer("session_analyzer_001", bus)
    await session_analyzer.start()
    logger.info("✅ SessionAnalyzer 已启动")

    memory_manager = MemoryManager("memory_manager_001", bus)
    await memory_manager.start()
    logger.info("✅ MemoryManager 已启动")


async def shutdown():
    """关闭时执行"""
    global session_analyzer, memory_manager

    logger.info("Learning System MCP Server 关闭中...")

    # 停止Agents
    if memory_manager:
        await memory_manager.stop()
        logger.info("✅ MemoryManager 已停止")

    if session_analyzer:
        await session_analyzer.stop()
        logger.info("✅ SessionAnalyzer 已停止")

    # 停止事件总线
    await bus.stop()
    logger.info("✅ 事件总线已停止")


def main():
    """主入口"""
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # 注册生命周期钩子
    mcp.add_startup_handler(startup)
    mcp.add_shutdown_handler(shutdown)

    # 运行服务器
    logger.info("启动 MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
