"""
任务管理器（客户端）
处理 MCP 2026 的 Tasks 特性（长任务）
"""
import asyncio
from typing import Dict, Callable, Any, Optional
from datetime import datetime


class TaskManager:
    """
    任务管理器（客户端侧）

    职责：
    1. 检测工具返回的 taskHandle
    2. 后台轮询任务状态
    3. 通知 UI 更新进度
    4. 完成后返回结果

    使用示例：
    result = await mcp.call_tool("analyze_project_deep", {...})
    if result.get("_mcp_feature") == "task":
        task_id = result["_task_data"]["task_id"]
        await task_manager.track_task(task_id, ui_callback)
    """

    def __init__(self, mcp_client, poll_interval: float = 2.0, timeout: float = 600.0):
        self.mcp_client = mcp_client
        self.poll_interval = poll_interval  # 轮询间隔（秒）
        self.timeout = timeout  # 超时时间（秒）
        self.active_tasks: Dict[str, asyncio.Task] = {}

    async def track_task(
        self,
        task_id: str,
        state_manager,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        追踪任务

        Args:
            task_id: 任务 ID
            state_manager: 状态管理器（用于更新任务状态）
            callback: UI 回调函数（用于更新进度条）
        """
        # 创建后台任务
        background_task = asyncio.create_task(
            self._poll_task(task_id, state_manager, callback)
        )
        self.active_tasks[task_id] = background_task

        # 等待完成
        try:
            result = await background_task
            return result
        finally:
            self.active_tasks.pop(task_id, None)

    async def _poll_task(
        self,
        task_id: str,
        state_manager,
        callback: Optional[Callable[[Dict[str, Any]], None]]
    ):
        """轮询任务状态"""
        start_time = datetime.now()

        while True:
            # 检查超时
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > self.timeout:
                state_manager.update_task(
                    task_id,
                    status="failed",
                    error="Task timeout"
                )
                if callback:
                    callback({
                        "task_id": task_id,
                        "status": "failed",
                        "error": "Task timeout"
                    })
                raise TimeoutError(f"Task {task_id} timeout after {self.timeout}s")

            # 查询状态
            try:
                status = await self.mcp_client.get_task_status(task_id)

                # 更新状态管理器
                state_manager.update_task(
                    task_id,
                    status=status.get("status"),
                    progress=status.get("progress", 0),
                )

                # 通知 UI
                if callback:
                    callback(status)

                # 检查是否完成
                if status.get("status") == "completed":
                    state_manager.update_task(
                        task_id,
                        status="completed",
                        result=status.get("result")
                    )
                    return status.get("result")

                elif status.get("status") == "failed":
                    state_manager.update_task(
                        task_id,
                        status="failed",
                        error=status.get("error")
                    )
                    raise RuntimeError(f"Task failed: {status.get('error')}")

            except Exception as e:
                print(f"[TaskManager] Error polling task {task_id}: {e}")
                state_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e)
                )
                raise

            # 等待下次轮询
            await asyncio.sleep(self.poll_interval)

    async def cancel_task(self, task_id: str, state_manager):
        """取消任务"""
        # 取消后台任务
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            self.active_tasks.pop(task_id)

        # 通知 MCP Server
        try:
            await self.mcp_client.cancel_task(task_id)
        except Exception as e:
            print(f"[TaskManager] Error cancelling task {task_id}: {e}")

        # 更新状态
        state_manager.update_task(task_id, status="cancelled")

    def get_active_tasks(self) -> list[str]:
        """获取所有活跃任务"""
        return list(self.active_tasks.keys())
