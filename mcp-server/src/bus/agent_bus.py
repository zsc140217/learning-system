"""
Agent事件总线
实现Agent之间的异步事件通信
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional
from loguru import logger


class AgentBus:
    """Agent事件总线"""

    def __init__(self):
        # 事件订阅者: {event_type: [handler1, handler2, ...]}
        self._subscribers: Dict[str, List[Callable]] = {}
        # 事件队列
        self._event_queue: asyncio.Queue = asyncio.Queue()
        # 运行标志
        self._running = False
        # 处理任务
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动事件总线"""
        if self._running:
            logger.warning("事件总线已经在运行")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())
        logger.info("事件总线已启动")

    async def stop(self):
        """停止事件总线"""
        if not self._running:
            return

        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("事件总线已停止")

    def subscribe(self, event_type: str, handler: Callable):
        """
        订阅事件

        Args:
            event_type: 事件类型 (如 'session_completed', 'knowledge_saved')
            handler: 事件处理函数 async def handler(event: dict)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)
        logger.debug(f"订阅事件: {event_type}, 处理器: {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅事件"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"取消订阅: {event_type}, 处理器: {handler.__name__}")
            except ValueError:
                pass

    async def publish(self, event: Dict[str, Any]):
        """
        发布事件

        Args:
            event: 事件数据，必须包含 'type' 字段
                {
                    "type": "session_completed",
                    "session_id": "session_1722518400_a7b3c9d2",
                    "data": {...}
                }
        """
        if "type" not in event:
            raise ValueError("事件必须包含 'type' 字段")

        await self._event_queue.put(event)
        logger.debug(f"发布事件: {event['type']}")

    async def _process_events(self):
        """处理事件队列"""
        logger.info("事件处理器已启动")

        while self._running:
            try:
                # 获取事件 (超时1秒)
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                # 分发事件
                await self._dispatch_event(event)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"处理事件失败: {e}", exc_info=True)

        logger.info("事件处理器已停止")

    async def _dispatch_event(self, event: Dict[str, Any]):
        """分发事件到订阅者"""
        event_type = event["type"]

        if event_type not in self._subscribers:
            logger.debug(f"无订阅者处理事件: {event_type}")
            return

        handlers = self._subscribers[event_type]
        logger.debug(f"分发事件 {event_type} 到 {len(handlers)} 个处理器")

        # 并发执行所有处理器
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(self._safe_call_handler(handler, event))
            tasks.append(task)

        # 等待所有处理器完成
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call_handler(self, handler: Callable, event: Dict[str, Any]):
        """安全调用处理器"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(
                f"处理器 {handler.__name__} 执行失败: {e}",
                exc_info=True
            )


# 全局事件总线实例
bus = AgentBus()
