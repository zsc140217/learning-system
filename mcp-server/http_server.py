"""
MCP HTTP Server
Stateless HTTP transport following MCP 2026-07-28 specification

Usage:
    python http_server.py

Features:
- Stateless request/response (no session ID)
- MRTR (Multi Round-Trip Request) support
- Tasks extension for long-running operations
- MCP Apps UI templates
"""
import asyncio
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from config import settings
from src.protocol.http_transport import HTTPTransport
from src.bus.agent_bus import bus
from src.agents.session_analyzer import SessionAnalyzer
from src.agents.memory_manager import MemoryManager
from src.agents.learning_coach import LearningCoach
from src.triggers import IdleDetector
from src.security import JWTHandler, NonceStore
from src.tasks import task_manager
from src.cache import CacheManager

# ============ 导入已注册工具的 server 实例 ============
# 直接使用 server.py 中已经注册了所有工具的实例
from server import server

# 全局组件
session_analyzer = None
memory_manager = None
learning_coach = None
idle_detector = None
nonce_store = None
jwt_handler = None
cache_manager = None


async def startup():
    """启动时执行"""
    global session_analyzer, memory_manager, learning_coach, idle_detector
    global nonce_store, jwt_handler, cache_manager

    logger.info("=" * 60)
    logger.info("MCP HTTP Server 启动中...")
    logger.info(f"协议版本: MCP 2026-07-28 (无状态核心)")
    logger.info(f"传输层: HTTP + JSON-RPC")
    logger.info(f"监听地址: http://localhost:{settings.http_port}")
    logger.info(f"项目根目录: {settings.project_root}")
    logger.info(f"数据目录: {settings.data_dir}")
    logger.info("=" * 60)

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

    # 初始化空闲检测器
    idle_detector = IdleDetector(bus, idle_threshold_seconds=60, check_interval_seconds=10)
    await idle_detector.start()
    logger.info("[OK] IdleDetector 已启动")

    # 注入全局组件到 server.py 的模块级变量
    import server as server_module
    server_module.session_analyzer = session_analyzer
    server_module.memory_manager = memory_manager
    server_module.learning_coach = learning_coach
    server_module.idle_detector = idle_detector
    server_module.nonce_store = nonce_store
    server_module.jwt_handler = jwt_handler
    server_module.cache_manager = cache_manager

    logger.info("=" * 60)
    logger.info("[READY] HTTP Server 已就绪，等待客户端连接...")
    logger.info(f"[HEALTH] http://localhost:{settings.http_port}/health")
    logger.info(f"[JSONRPC] http://localhost:{settings.http_port}/jsonrpc")
    logger.info("=" * 60)


async def shutdown():
    """关闭时执行"""
    global session_analyzer, memory_manager, learning_coach, idle_detector
    global nonce_store, jwt_handler, cache_manager

    logger.info("MCP HTTP Server 关闭中...")

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

    # 停止缓存管理器
    if cache_manager:
        await cache_manager.stop()
        logger.info("[OK] CacheManager 已停止")

    # 停止事件总线
    await bus.stop()
    logger.info("[OK] 事件总线已停止")


def main():
    """入口函数"""
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # 创建 HTTP 传输层
    transport = HTTPTransport(server)
    app = transport.get_app()

    # 添加静态文件服务
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def root():
        """返回主页"""
        return FileResponse("static/index.html")

    # 注册生命周期事件
    @app.on_event("startup")
    async def on_startup():
        await startup()

    @app.on_event("shutdown")
    async def on_shutdown():
        await shutdown()

    # 启动 HTTP 服务器
    try:
        uvicorn.run(
            app,
            host=settings.http_host,
            port=settings.http_port,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，程序已退出")


if __name__ == "__main__":
    main()
