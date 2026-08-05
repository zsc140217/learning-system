"""
Task Manager
Manages long-running background tasks with progress tracking
"""

import asyncio
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import uuid4

from loguru import logger


@dataclass
class TaskState:
    """Task state representation"""
    task_id: str
    name: str
    status: str  # running, completed, failed, cancelled
    progress: float  # 0.0 to 1.0
    created_at: datetime
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    message: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    eta_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "taskId": self.task_id,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

        if self.started_at:
            data["startedAt"] = self.started_at.isoformat()

        if self.completed_at:
            data["completedAt"] = self.completed_at.isoformat()

        if self.message:
            data["message"] = self.message

        if self.eta_seconds is not None:
            data["etaSeconds"] = self.eta_seconds

        if self.result is not None:
            data["result"] = self.result

        if self.error:
            data["error"] = self.error

        return data


class TaskManager:
    """
    Task Manager for long-running background operations

    Features:
    - Async task execution
    - Progress tracking
    - Status management
    - Error handling
    - Timeout control

    Usage:
        task_mgr = TaskManager()

        async def my_task(task_id: str, task_mgr: TaskManager):
            task_mgr.update_progress(task_id, 0.5, "Processing...")
            await asyncio.sleep(2)
            task_mgr.tasks[task_id].result = {"data": "result"}

        task_id = task_mgr.create_task("My Task", my_task)
        await asyncio.sleep(3)
        state = task_mgr.get_task(task_id)
    """

    def __init__(self, max_concurrent_tasks: int = 50):
        self.tasks: Dict[str, TaskState] = {}
        self._task_futures: Dict[str, asyncio.Task] = {}
        self._max_concurrent = max_concurrent_tasks
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        logger.info(f"TaskManager initialized (max_concurrent={max_concurrent_tasks})")

    def create_task(
        self,
        name: str,
        executor: Callable,
        eta_seconds: Optional[int] = None
    ) -> str:
        """
        Create and start a new background task

        Args:
            name: Human-readable task name
            executor: Async function to execute (task_id, task_mgr) -> None
            eta_seconds: Estimated time to completion

        Returns:
            task_id: Unique task identifier
        """
        task_id = f"task-{uuid4().hex[:8]}"
        now = datetime.now(UTC)

        self.tasks[task_id] = TaskState(
            task_id=task_id,
            name=name,
            status="running",
            progress=0.0,
            created_at=now,
            started_at=now,
            eta_seconds=eta_seconds
        )

        # Start background task with concurrency control
        future = asyncio.create_task(self._execute_task_with_limit(task_id, executor))
        self._task_futures[task_id] = future

        logger.info(f"Task created: {task_id} ({name})")
        return task_id

    async def _execute_task_with_limit(self, task_id: str, executor: Callable):
        """Execute task with concurrency limit"""
        async with self._semaphore:
            await self._execute_task(task_id, executor)

    async def _execute_task(self, task_id: str, executor: Callable):
        """
        Execute task in background with error handling

        Args:
            task_id: Task ID
            executor: Async executor function
        """
        try:
            logger.debug(f"Task {task_id} started")
            await executor(task_id, self)

            # Mark as completed if not already
            if self.tasks[task_id].status == "running":
                self.tasks[task_id].status = "completed"
                self.tasks[task_id].progress = 1.0
                self.tasks[task_id].completed_at = datetime.now(UTC)
                self.tasks[task_id].updated_at = datetime.now(UTC)
                logger.info(f"Task {task_id} completed successfully")

        except asyncio.CancelledError:
            self.tasks[task_id].status = "cancelled"
            self.tasks[task_id].completed_at = datetime.now(UTC)
            self.tasks[task_id].updated_at = datetime.now(UTC)
            logger.warning(f"Task {task_id} cancelled")

        except Exception as e:
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].error = str(e)
            self.tasks[task_id].completed_at = datetime.now(UTC)
            self.tasks[task_id].updated_at = datetime.now(UTC)
            logger.error(f"Task {task_id} failed: {e}")

        finally:
            # Cleanup future reference
            if task_id in self._task_futures:
                del self._task_futures[task_id]

    def update_progress(
        self,
        task_id: str,
        progress: float,
        message: Optional[str] = None,
        eta_seconds: Optional[int] = None
    ):
        """
        Update task progress

        Args:
            task_id: Task ID
            progress: Progress value (0.0 to 1.0)
            message: Optional status message
            eta_seconds: Optional updated ETA
        """
        if task_id not in self.tasks:
            logger.warning(f"Attempted to update non-existent task: {task_id}")
            return

        task = self.tasks[task_id]
        task.progress = max(0.0, min(1.0, progress))
        task.updated_at = datetime.now(UTC)

        if message:
            task.message = message

        if eta_seconds is not None:
            task.eta_seconds = eta_seconds

        logger.debug(f"Task {task_id} progress: {progress:.1%} - {message or 'no message'}")

    def complete_task(
        self,
        task_id: str,
        result: Any = None,
        message: Optional[str] = None
    ):
        """
        Mark task as completed with result

        Args:
            task_id: Task ID
            result: Task result data
            message: Optional completion message
        """
        if task_id not in self.tasks:
            logger.warning(f"Attempted to complete non-existent task: {task_id}")
            return

        task = self.tasks[task_id]
        task.status = "completed"
        task.progress = 1.0
        task.result = result
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)

        if message:
            task.message = message

        logger.info(f"Task {task_id} marked as completed")

    def fail_task(
        self,
        task_id: str,
        error: str,
        message: Optional[str] = None
    ):
        """
        Mark task as failed with error

        Args:
            task_id: Task ID
            error: Error message
            message: Optional failure message
        """
        if task_id not in self.tasks:
            logger.warning(f"Attempted to fail non-existent task: {task_id}")
            return

        task = self.tasks[task_id]
        task.status = "failed"
        task.error = error
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)

        if message:
            task.message = message

        logger.error(f"Task {task_id} marked as failed: {error}")

    def get_task(self, task_id: str) -> Optional[TaskState]:
        """
        Get task state by ID

        Args:
            task_id: Task ID

        Returns:
            TaskState or None if not found
        """
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list[TaskState]:
        """
        List all tasks, optionally filtered by status

        Args:
            status: Optional status filter (running, completed, failed, cancelled)
            limit: Maximum number of tasks to return

        Returns:
            List of TaskState objects
        """
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        # Sort by creation time, newest first
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks[:limit]

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task

        Args:
            task_id: Task ID

        Returns:
            True if task was cancelled, False if not found or already completed
        """
        if task_id not in self.tasks:
            logger.warning(f"Attempted to cancel non-existent task: {task_id}")
            return False

        task = self.tasks[task_id]

        if task.status != "running":
            logger.info(f"Task {task_id} is not running (status: {task.status})")
            return False

        # Cancel the asyncio task
        if task_id in self._task_futures:
            future = self._task_futures[task_id]
            future.cancel()
            logger.info(f"Task {task_id} cancellation requested")
            return True

        return False

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        Remove old completed/failed tasks

        Args:
            max_age_hours: Maximum age in hours to keep
        """
        now = datetime.now(UTC)
        to_remove = []

        for task_id, task in self.tasks.items():
            if task.status in ("completed", "failed", "cancelled"):
                age_hours = (now - task.completed_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]
            logger.debug(f"Cleaned up old task: {task_id}")

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks")

    def get_stats(self) -> dict:
        """Get task manager statistics"""
        running = sum(1 for t in self.tasks.values() if t.status == "running")
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        failed = sum(1 for t in self.tasks.values() if t.status == "failed")

        return {
            "total_tasks": len(self.tasks),
            "running": running,
            "completed": completed,
            "failed": failed,
            "max_concurrent": self._max_concurrent,
            "available_slots": self._semaphore._value
        }


# Global task manager instance
task_manager = TaskManager()
