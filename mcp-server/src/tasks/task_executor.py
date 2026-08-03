"""
Task Executor
Provides reusable task execution patterns and utilities
"""

import asyncio
from typing import Callable, Any, Optional, List
from datetime import datetime, timedelta

from loguru import logger

from .task_manager import TaskManager


class TaskExecutor:
    """
    Reusable task execution patterns

    Provides common patterns for:
    - Multi-stage tasks with progress tracking
    - Timeout control
    - Retry logic
    - Error recovery
    """

    @staticmethod
    async def execute_with_timeout(
        executor: Callable,
        task_id: str,
        task_mgr: TaskManager,
        timeout_seconds: int
    ):
        """
        Execute task with timeout

        Args:
            executor: Async executor function
            task_id: Task ID
            task_mgr: TaskManager instance
            timeout_seconds: Timeout in seconds
        """
        try:
            await asyncio.wait_for(
                executor(task_id, task_mgr),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            task_mgr.fail_task(
                task_id,
                f"Task timed out after {timeout_seconds} seconds",
                "Timeout exceeded"
            )
            logger.error(f"Task {task_id} timed out")

    @staticmethod
    async def execute_with_retry(
        executor: Callable,
        task_id: str,
        task_mgr: TaskManager,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Execute task with retry logic

        Args:
            executor: Async executor function
            task_id: Task ID
            task_mgr: TaskManager instance
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        for attempt in range(max_retries):
            try:
                await executor(task_id, task_mgr)
                return  # Success
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Task {task_id} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    task_mgr.update_progress(
                        task_id,
                        task_mgr.tasks[task_id].progress,
                        f"Retry {attempt + 1}/{max_retries} after error: {str(e)[:50]}"
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    task_mgr.fail_task(
                        task_id,
                        f"Failed after {max_retries} attempts: {e}",
                        "Maximum retries exceeded"
                    )
                    logger.error(f"Task {task_id} failed after {max_retries} attempts")
                    raise

    @staticmethod
    async def execute_multi_stage(
        task_id: str,
        task_mgr: TaskManager,
        stages: List[tuple[str, float, Callable]]
    ):
        """
        Execute multi-stage task with automatic progress tracking

        Args:
            task_id: Task ID
            task_mgr: TaskManager instance
            stages: List of (stage_name, progress_weight, stage_executor)
                    progress_weight should sum to 1.0 across all stages

        Example:
            stages = [
                ("Scanning files", 0.2, scan_files),
                ("Parsing code", 0.3, parse_code),
                ("Analyzing", 0.5, analyze)
            ]
        """
        total_progress = 0.0

        for stage_name, weight, stage_func in stages:
            task_mgr.update_progress(
                task_id,
                total_progress,
                f"Starting: {stage_name}"
            )
            logger.debug(f"Task {task_id} stage: {stage_name}")

            try:
                # Execute stage
                result = await stage_func(task_id, task_mgr)

                # Update progress
                total_progress += weight
                task_mgr.update_progress(
                    task_id,
                    total_progress,
                    f"Completed: {stage_name}"
                )

            except Exception as e:
                task_mgr.fail_task(
                    task_id,
                    f"Failed at stage '{stage_name}': {e}",
                    f"Stage failed: {stage_name}"
                )
                raise

        # Final completion
        task_mgr.update_progress(task_id, 1.0, "All stages completed")

    @staticmethod
    def create_staged_executor(stages: List[tuple[str, float, Callable]]) -> Callable:
        """
        Create a staged executor function

        Args:
            stages: List of (stage_name, progress_weight, stage_executor)

        Returns:
            Async executor function compatible with TaskManager.create_task()
        """
        async def executor(task_id: str, task_mgr: TaskManager):
            await TaskExecutor.execute_multi_stage(task_id, task_mgr, stages)

        return executor

    @staticmethod
    async def execute_batch(
        task_id: str,
        task_mgr: TaskManager,
        items: List[Any],
        processor: Callable,
        batch_size: int = 10,
        stage_name: str = "Processing items"
    ):
        """
        Execute batch processing with progress tracking

        Args:
            task_id: Task ID
            task_mgr: TaskManager instance
            items: List of items to process
            processor: Async function to process each item
            batch_size: Number of items to process concurrently
            stage_name: Name for progress messages
        """
        total = len(items)
        processed = 0

        for i in range(0, total, batch_size):
            batch = items[i:i + batch_size]

            # Process batch concurrently
            await asyncio.gather(*[processor(item) for item in batch])

            processed += len(batch)
            progress = processed / total

            task_mgr.update_progress(
                task_id,
                progress,
                f"{stage_name}: {processed}/{total} items"
            )

            logger.debug(f"Task {task_id} processed {processed}/{total} items")


class TaskTimeout:
    """Task timeout utilities"""

    @staticmethod
    def calculate_eta(
        started_at: datetime,
        current_progress: float,
        target_progress: float = 1.0
    ) -> Optional[int]:
        """
        Calculate estimated time remaining

        Args:
            started_at: Task start time
            current_progress: Current progress (0.0 to 1.0)
            target_progress: Target progress (default 1.0)

        Returns:
            Estimated seconds remaining, or None if cannot calculate
        """
        if current_progress <= 0:
            return None

        elapsed = (datetime.utcnow() - started_at).total_seconds()
        remaining_progress = target_progress - current_progress

        if remaining_progress <= 0:
            return 0

        # Linear extrapolation
        eta_seconds = int((elapsed / current_progress) * remaining_progress)

        return eta_seconds


class TaskTemplates:
    """
    Pre-built task templates for common operations
    """

    @staticmethod
    async def simple_delay_task(
        task_id: str,
        task_mgr: TaskManager,
        delay_seconds: float = 5.0,
        stages: int = 5
    ):
        """
        Simple delay task for testing (simulates multi-stage work)

        Args:
            task_id: Task ID
            task_mgr: TaskManager instance
            delay_seconds: Total delay time
            stages: Number of stages to simulate
        """
        stage_delay = delay_seconds / stages

        for stage in range(stages):
            progress = (stage + 1) / stages
            task_mgr.update_progress(
                task_id,
                progress,
                f"Stage {stage + 1}/{stages}"
            )
            await asyncio.sleep(stage_delay)

        task_mgr.complete_task(
            task_id,
            {"message": f"Completed after {delay_seconds}s"},
            "Task completed successfully"
        )

    @staticmethod
    async def file_processing_task(
        task_id: str,
        task_mgr: TaskManager,
        file_paths: List[str],
        processor: Callable
    ):
        """
        File processing task template

        Args:
            task_id: Task ID
            task_mgr: TaskManager instance
            file_paths: List of file paths to process
            processor: Async function to process each file
        """
        total = len(file_paths)
        results = []

        for i, file_path in enumerate(file_paths):
            task_mgr.update_progress(
                task_id,
                (i + 1) / total,
                f"Processing: {file_path}"
            )

            try:
                result = await processor(file_path)
                results.append({"file": file_path, "result": result, "status": "ok"})
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
                results.append({"file": file_path, "error": str(e), "status": "error"})

        task_mgr.complete_task(
            task_id,
            {"processed": len(results), "results": results},
            f"Processed {len(results)} files"
        )
