"""
Idle Detector - 检测客户端空闲状态并触发学习巩固
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger


class IdleDetector:
    """
    监听客户端活动，检测空闲状态

    工作原理:
    1. 记录每次 Tool 调用的时间戳
    2. 如果超过阈值（默认 30 分钟）无活动，触发 idle 事件
    3. 发布事件到事件总线，由其他 Agent 处理
    """

    def __init__(
        self,
        bus,
        idle_threshold_seconds: int = 1800,  # 30 分钟
        check_interval_seconds: int = 60      # 1 分钟检查一次
    ):
        self.bus = bus
        self.idle_threshold = timedelta(seconds=idle_threshold_seconds)
        self.check_interval = check_interval_seconds

        self.last_activity_time: Optional[datetime] = None
        self.is_idle: bool = False
        self.check_task: Optional[asyncio.Task] = None
        self.session_data: Dict[str, Any] = {}

        logger.info(
            f"IdleDetector 初始化 - 空闲阈值: {idle_threshold_seconds}s "
            f"({idle_threshold_seconds/60:.1f}分钟)"
        )

    async def start(self):
        """启动空闲检测循环"""
        logger.info("IdleDetector 启动")
        self.check_task = asyncio.create_task(self._check_loop())

    async def stop(self):
        """停止空闲检测"""
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
        logger.info("IdleDetector 已停止")

    def record_activity(self, activity_type: str, metadata: Dict[str, Any] = None):
        """
        记录活动

        Args:
            activity_type: 活动类型 (tool_call, resource_read, etc.)
            metadata: 额外的元数据
        """
        now = datetime.now()
        self.last_activity_time = now

        # 如果之前是空闲状态，现在恢复活跃
        if self.is_idle:
            logger.info("客户端恢复活跃")
            self.is_idle = False
            self.session_data = {}  # 清空会话数据

        # 累积会话数据
        if metadata:
            tool_name = metadata.get("tool_name")
            if tool_name:
                if "tool_calls" not in self.session_data:
                    self.session_data["tool_calls"] = []
                self.session_data["tool_calls"].append({
                    "tool": tool_name,
                    "timestamp": now.isoformat()
                })

        logger.debug(f"记录活动: {activity_type}")

    async def _check_loop(self):
        """定期检查空闲状态"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_idle_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"空闲检测错误: {e}")

    async def _check_idle_status(self):
        """检查当前是否空闲"""
        if self.last_activity_time is None:
            return

        now = datetime.now()
        time_since_last_activity = now - self.last_activity_time

        # 如果超过阈值且当前不是空闲状态
        if time_since_last_activity > self.idle_threshold and not self.is_idle:
            logger.info(
                f"检测到空闲状态 - 距离上次活动: "
                f"{time_since_last_activity.total_seconds():.0f}秒"
            )
            self.is_idle = True
            await self._trigger_idle_event()

    async def _trigger_idle_event(self):
        """触发空闲事件"""
        event = {
            "type": "client.idle",
            "timestamp": datetime.now().isoformat(),
            "last_activity": self.last_activity_time.isoformat() if self.last_activity_time else None,
            "session_data": self.session_data
        }

        logger.info("发布 client.idle 事件")
        await self.bus.publish(event)

    def get_idle_duration(self) -> Optional[timedelta]:
        """
        获取当前空闲时长

        Returns:
            空闲时长，如果没有活动记录则返回 None
        """
        if self.last_activity_time is None:
            return None

        return datetime.now() - self.last_activity_time
