"""
Tests for Tasks Extension (Phase 2)
Tests task manager, executor, and task query tools
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from src.tasks import TaskManager, TaskState, TaskExecutor, TaskTimeout, TaskTemplates


class TestTaskManager:
    """测试 TaskManager 核心功能"""

    @pytest.fixture
    def task_manager(self):
        """创建 TaskManager 实例"""
        return TaskManager()

    @pytest.mark.asyncio
    async def test_create_simple_task(self, task_manager):
        """测试创建简单任务"""
        async def simple_executor(task_id: str, task_mgr: TaskManager):
            task_mgr.update_progress(task_id, 0.5, "Half done")
            await asyncio.sleep(0.1)
            task_mgr.complete_task(task_id, {"result": "success"})

        task_id = task_manager.create_task("Simple Task", simple_executor)

        assert task_id.startswith("task-")
        assert task_id in task_manager.tasks

        # 等待任务完成
        await asyncio.sleep(0.2)

        task = task_manager.get_task(task_id)
        assert task.status == "completed"
        assert task.progress == 1.0
        assert task.result["result"] == "success"

    @pytest.mark.asyncio
    async def test_task_progress_tracking(self, task_manager):
        """测试任务进度追踪"""
        progress_updates = []

        async def tracked_executor(task_id: str, task_mgr: TaskManager):
            for i in range(5):
                progress = (i + 1) / 5
                task_mgr.update_progress(task_id, progress, f"Stage {i+1}/5")
                progress_updates.append(progress)
                await asyncio.sleep(0.05)

        task_id = task_manager.create_task("Tracked Task", tracked_executor)
        await asyncio.sleep(0.3)

        assert len(progress_updates) == 5
        assert progress_updates[-1] == 1.0

        task = task_manager.get_task(task_id)
        assert task.status == "completed"

    @pytest.mark.asyncio
    async def test_task_failure(self, task_manager):
        """测试任务失败处理"""
        async def failing_executor(task_id: str, task_mgr: TaskManager):
            task_mgr.update_progress(task_id, 0.3, "Working...")
            await asyncio.sleep(0.05)
            raise ValueError("Intentional failure")

        task_id = task_manager.create_task("Failing Task", failing_executor)
        await asyncio.sleep(0.15)

        task = task_manager.get_task(task_id)
        assert task.status == "failed"
        assert "Intentional failure" in task.error

    @pytest.mark.asyncio
    async def test_task_cancellation(self, task_manager):
        """测试任务取消"""
        async def long_executor(task_id: str, task_mgr: TaskManager):
            for i in range(10):
                task_mgr.update_progress(task_id, i / 10, f"Stage {i+1}/10")
                await asyncio.sleep(0.1)

        task_id = task_manager.create_task("Long Task", long_executor)
        await asyncio.sleep(0.15)  # 让任务运行一会儿

        # 取消任务
        success = await task_manager.cancel_task(task_id)
        assert success is True

        await asyncio.sleep(0.1)

        task = task_manager.get_task(task_id)
        assert task.status == "cancelled"

    @pytest.mark.asyncio
    async def test_list_tasks_with_filter(self, task_manager):
        """测试任务列表和过滤"""
        # 创建多个任务
        async def quick_task(task_id: str, task_mgr: TaskManager):
            await asyncio.sleep(0.05)

        async def failing_task(task_id: str, task_mgr: TaskManager):
            raise RuntimeError("Test error")

        task_id_1 = task_manager.create_task("Task 1", quick_task)
        task_id_2 = task_manager.create_task("Task 2", quick_task)
        task_id_3 = task_manager.create_task("Task 3", failing_task)

        await asyncio.sleep(0.15)

        # 测试无过滤
        all_tasks = task_manager.list_tasks()
        assert len(all_tasks) == 3

        # 测试状态过滤
        completed_tasks = task_manager.list_tasks(status="completed")
        assert len(completed_tasks) == 2

        failed_tasks = task_manager.list_tasks(status="failed")
        assert len(failed_tasks) == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks(self, task_manager):
        """测试清理旧任务"""
        async def quick_task(task_id: str, task_mgr: TaskManager):
            await asyncio.sleep(0.01)

        # 创建任务
        task_id = task_manager.create_task("Old Task", quick_task)
        await asyncio.sleep(0.05)

        # 手动设置完成时间为25小时前
        task = task_manager.get_task(task_id)
        task.completed_at = datetime.utcnow() - timedelta(hours=25)

        # 清理旧任务
        task_manager.cleanup_old_tasks(max_age_hours=24)

        # 任务应该被删除
        assert task_manager.get_task(task_id) is None


class TestTaskExecutor:
    """测试 TaskExecutor 工具类"""

    @pytest.fixture
    def task_manager(self):
        return TaskManager()

    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self, task_manager):
        """测试超时控制 - 成功情况"""
        async def quick_executor(task_id: str, task_mgr: TaskManager):
            await asyncio.sleep(0.05)
            task_mgr.complete_task(task_id, {"status": "ok"})

        task_id = task_manager.create_task("Timeout Test", lambda tid, tmgr: TaskExecutor.execute_with_timeout(
            quick_executor, tid, tmgr, timeout_seconds=1
        ))

        await asyncio.sleep(0.1)

        task = task_manager.get_task(task_id)
        assert task.status == "completed"

    @pytest.mark.asyncio
    async def test_execute_with_timeout_exceeded(self, task_manager):
        """测试超时控制 - 超时情况"""
        async def slow_executor(task_id: str, task_mgr: TaskManager):
            await asyncio.sleep(2)

        task_id = task_manager.create_task("Slow Task", lambda tid, tmgr: TaskExecutor.execute_with_timeout(
            slow_executor, tid, tmgr, timeout_seconds=0.1
        ))

        await asyncio.sleep(0.2)

        task = task_manager.get_task(task_id)
        assert task.status == "failed"
        assert "timed out" in task.error.lower()

    @pytest.mark.asyncio
    async def test_execute_multi_stage(self, task_manager):
        """测试多阶段任务执行"""
        stage_results = []

        async def stage1(task_id: str, task_mgr: TaskManager):
            stage_results.append("stage1")
            await asyncio.sleep(0.05)

        async def stage2(task_id: str, task_mgr: TaskManager):
            stage_results.append("stage2")
            await asyncio.sleep(0.05)

        async def stage3(task_id: str, task_mgr: TaskManager):
            stage_results.append("stage3")
            await asyncio.sleep(0.05)

        stages = [
            ("Stage 1", 0.3, stage1),
            ("Stage 2", 0.4, stage2),
            ("Stage 3", 0.3, stage3),
        ]

        task_id = task_manager.create_task(
            "Multi-Stage Task",
            lambda tid, tmgr: TaskExecutor.execute_multi_stage(tid, tmgr, stages)
        )

        await asyncio.sleep(0.25)

        task = task_manager.get_task(task_id)
        assert task.status == "completed"
        assert stage_results == ["stage1", "stage2", "stage3"]

    @pytest.mark.asyncio
    async def test_execute_batch(self, task_manager):
        """测试批量处理"""
        processed_items = []

        async def item_processor(item):
            processed_items.append(item)
            await asyncio.sleep(0.01)

        items = list(range(10))

        async def batch_executor(task_id: str, task_mgr: TaskManager):
            await TaskExecutor.execute_batch(
                task_id, task_mgr, items, item_processor, batch_size=3
            )

        task_id = task_manager.create_task("Batch Task", batch_executor)
        await asyncio.sleep(0.2)

        task = task_manager.get_task(task_id)
        assert task.status == "completed"
        assert len(processed_items) == 10


class TestTaskTimeout:
    """测试 TaskTimeout 工具类"""

    def test_calculate_eta(self):
        """测试 ETA 计算"""
        started_at = datetime.utcnow() - timedelta(seconds=10)

        # 当前进度 50%，预计还需 10 秒
        eta = TaskTimeout.calculate_eta(started_at, 0.5)
        assert 9 <= eta <= 11  # 允许一点误差

        # 当前进度 10%，预计还需 90 秒
        eta = TaskTimeout.calculate_eta(started_at, 0.1)
        assert 85 <= eta <= 95

        # 当前进度 0%，无法计算
        eta = TaskTimeout.calculate_eta(started_at, 0.0)
        assert eta is None

        # 当前进度 100%，剩余 0 秒
        eta = TaskTimeout.calculate_eta(started_at, 1.0)
        assert eta == 0


class TestTaskTemplates:
    """测试 TaskTemplates 预置模板"""

    @pytest.fixture
    def task_manager(self):
        return TaskManager()

    @pytest.mark.asyncio
    async def test_simple_delay_task(self, task_manager):
        """测试延迟任务模板"""
        task_id = task_manager.create_task(
            "Delay Test",
            lambda tid, tmgr: TaskTemplates.simple_delay_task(tid, tmgr, delay_seconds=0.2, stages=4)
        )

        # 等待任务完成
        await asyncio.sleep(0.3)

        task = task_manager.get_task(task_id)
        assert task.status == "completed"
        assert task.result["message"] == "Completed after 0.2s"

    @pytest.mark.asyncio
    async def test_file_processing_task(self, task_manager):
        """测试文件处理任务模板"""
        processed_files = []

        async def mock_processor(file_path: str):
            processed_files.append(file_path)
            await asyncio.sleep(0.02)
            return {"size": 100}

        file_paths = ["file1.txt", "file2.txt", "file3.txt"]

        task_id = task_manager.create_task(
            "File Processing",
            lambda tid, tmgr: TaskTemplates.file_processing_task(tid, tmgr, file_paths, mock_processor)
        )

        await asyncio.sleep(0.15)

        task = task_manager.get_task(task_id)
        assert task.status == "completed"
        assert task.result["processed"] == 3
        assert len(processed_files) == 3


class TestTaskState:
    """测试 TaskState 数据类"""

    def test_task_state_to_dict(self):
        """测试 TaskState 转换为字典"""
        now = datetime.utcnow()
        task = TaskState(
            task_id="task-test123",
            name="Test Task",
            status="running",
            progress=0.65,
            created_at=now,
            message="Processing...",
            eta_seconds=120
        )

        data = task.to_dict()

        assert data["taskId"] == "task-test123"
        assert data["name"] == "Test Task"
        assert data["status"] == "running"
        assert data["progress"] == 0.65
        assert data["message"] == "Processing..."
        assert data["etaSeconds"] == 120
        assert "createdAt" in data
        assert "updatedAt" in data


# ============ 集成测试 ============

class TestTasksIntegration:
    """测试任务系统集成"""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self):
        """测试完整任务生命周期"""
        task_mgr = TaskManager()

        # 创建任务
        async def lifecycle_task(task_id: str, task_mgr: TaskManager):
            task_mgr.update_progress(task_id, 0.2, "Stage 1")
            await asyncio.sleep(0.05)
            task_mgr.update_progress(task_id, 0.5, "Stage 2")
            await asyncio.sleep(0.05)
            task_mgr.update_progress(task_id, 0.8, "Stage 3")
            await asyncio.sleep(0.05)
            task_mgr.complete_task(task_id, {"final": "result"}, "Done")

        task_id = task_mgr.create_task("Lifecycle Task", lifecycle_task, eta_seconds=1)

        # 检查初始状态
        task = task_mgr.get_task(task_id)
        assert task.status == "running"
        assert task.progress == 0.0

        # 等待部分完成
        await asyncio.sleep(0.1)
        task = task_mgr.get_task(task_id)
        assert task.progress > 0.2

        # 等待完全完成
        await asyncio.sleep(0.15)
        task = task_mgr.get_task(task_id)
        assert task.status == "completed"
        assert task.progress == 1.0
        assert task.result["final"] == "result"
        assert task.message == "Done"

        # 测试任务列表
        tasks = task_mgr.list_tasks(status="completed")
        assert len(tasks) == 1
        assert tasks[0].task_id == task_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
