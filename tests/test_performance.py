"""
Performance Benchmark Tests for MCP 2026 Implementation

Tests performance metrics for:
- Knowledge graph query speed
- Task execution concurrency
- Cache hit rate optimization
- Memory usage patterns

Author: Learning System Team
Date: 2026-08-04
"""

import asyncio
import time
import pytest
from datetime import datetime
from pathlib import Path
import sys
import statistics

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mcp-server"))

# Import MCP components
from src.tasks.task_manager import TaskManager
from src.cache.cache_manager import CacheManager
from src.agents.memory_manager import MemoryManager
from src.bus.agent_bus import AgentBus


class PerformanceBenchmark:
    """Performance benchmark runner"""

    def __init__(self):
        self.results = {}

    def measure_time(self, operation_name: str):
        """Context manager to measure execution time"""
        class TimeMeasure:
            def __init__(self, benchmark, name):
                self.benchmark = benchmark
                self.name = name
                self.start_time = None

            def __enter__(self):
                self.start_time = time.perf_counter()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                elapsed = time.perf_counter() - self.start_time
                if self.name not in self.benchmark.results:
                    self.benchmark.results[self.name] = []
                self.benchmark.results[self.name].append(elapsed)

        return TimeMeasure(self, operation_name)

    def get_stats(self, operation_name: str) -> dict:
        """Get statistics for an operation"""
        if operation_name not in self.results:
            return {}

        times = self.results[operation_name]
        return {
            "count": len(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "max": max(times),
            "total": sum(times)
        }

    def print_report(self):
        """Print performance report"""
        print("\n" + "=" * 70)
        print("PERFORMANCE BENCHMARK REPORT")
        print("=" * 70)

        for operation, times in self.results.items():
            stats = self.get_stats(operation)
            print(f"\n{operation}:")
            print(f"  Runs:    {stats['count']}")
            print(f"  Mean:    {stats['mean']*1000:.2f}ms")
            print(f"  Median:  {stats['median']*1000:.2f}ms")
            print(f"  StdDev:  {stats['stdev']*1000:.2f}ms")
            print(f"  Min:     {stats['min']*1000:.2f}ms")
            print(f"  Max:     {stats['max']*1000:.2f}ms")

        print("\n" + "=" * 70)


@pytest.fixture
def benchmark():
    """Create benchmark instance"""
    return PerformanceBenchmark()


@pytest.fixture
def task_manager():
    """Create task manager instance"""
    return TaskManager()


@pytest.fixture
def cache_manager():
    """Create cache manager instance"""
    return CacheManager()


@pytest.fixture
def memory_manager():
    """Create memory manager instance"""
    bus = AgentBus()
    manager = MemoryManager("memory-test", bus)
    return manager


class TestTaskManagerPerformance:
    """Test TaskManager performance"""

    @pytest.mark.asyncio
    async def test_task_creation_speed(self, task_manager, benchmark):
        """Test task creation performance"""

        async def dummy_task(task_id: str, mgr: TaskManager):
            await asyncio.sleep(0.01)

        # Warmup
        for _ in range(5):
            task_manager.create_task("warmup", dummy_task)

        # Benchmark
        for i in range(50):
            with benchmark.measure_time("task_creation"):
                task_id = task_manager.create_task(f"test-{i}", dummy_task)
                assert task_id is not None

        stats = benchmark.get_stats("task_creation")
        assert stats["mean"] < 0.01  # Should be under 10ms

        # Cleanup
        await asyncio.sleep(0.6)

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, task_manager, benchmark):
        """Test concurrent task execution performance"""

        async def test_task(task_id: str, mgr: TaskManager):
            mgr.update_progress(task_id, 0.5, "Processing")
            await asyncio.sleep(0.05)
            mgr.update_progress(task_id, 1.0, "Done")

        with benchmark.measure_time("concurrent_10_tasks"):
            task_ids = []
            for i in range(10):
                task_id = task_manager.create_task(f"concurrent-{i}", test_task)
                task_ids.append(task_id)

            # Wait for all to complete
            max_wait = 2.0
            start = time.time()
            while time.time() - start < max_wait:
                all_done = all(
                    task_manager.get_task(tid).status in ("completed", "failed")
                    for tid in task_ids
                )
                if all_done:
                    break
                await asyncio.sleep(0.01)

        stats = benchmark.get_stats("concurrent_10_tasks")
        # All 10 tasks should complete in parallel, not sequentially
        assert stats["mean"] < 0.15  # Should be under 150ms (not 10 * 50ms = 500ms)

    @pytest.mark.asyncio
    async def test_task_query_performance(self, task_manager, benchmark):
        """Test task query performance"""

        async def dummy_task(task_id: str, mgr: TaskManager):
            await asyncio.sleep(0.01)

        # Create 100 tasks
        task_ids = []
        for i in range(100):
            task_id = task_manager.create_task(f"query-test-{i}", dummy_task)
            task_ids.append(task_id)

        await asyncio.sleep(0.1)

        # Benchmark get_task
        for i in range(100):
            with benchmark.measure_time("task_get"):
                task = task_manager.get_task(task_ids[i])
                assert task is not None

        stats = benchmark.get_stats("task_get")
        assert stats["mean"] < 0.001  # Should be under 1ms

        # Benchmark list_tasks
        for _ in range(20):
            with benchmark.measure_time("task_list"):
                tasks = task_manager.list_tasks(status="running")

        stats = benchmark.get_stats("task_list")
        assert stats["mean"] < 0.01  # Should be under 10ms

        await asyncio.sleep(1.2)


class TestCacheManagerPerformance:
    """Test CacheManager performance"""

    def test_cache_registration_speed(self, cache_manager, benchmark):
        """Test cache registration performance"""

        for i in range(100):
            with benchmark.measure_time("cache_register"):
                cache_manager.register_tool(
                    f"test_tool_{i}",
                    ttl_seconds=3600,
                    scope="user"
                )

        stats = benchmark.get_stats("cache_register")
        assert stats["mean"] < 0.001  # Should be under 1ms

    def test_cache_invalidation_speed(self, cache_manager, benchmark):
        """Test cache invalidation performance"""

        # Register tools
        for i in range(100):
            cache_manager.register_tool(f"tool_{i}", 3600, "user")

        # Benchmark invalidation
        for i in range(100):
            with benchmark.measure_time("cache_invalidate"):
                cache_manager.invalidate([f"cache_key_{i}"])

        stats = benchmark.get_stats("cache_invalidate")
        assert stats["mean"] < 0.001  # Should be under 1ms

    def test_cache_pattern_matching_speed(self, cache_manager, benchmark):
        """Test cache pattern matching performance"""

        # Create many cache entries
        for i in range(200):
            cache_manager.invalidate([f"search_knowledge:{i}"])

        # Benchmark pattern invalidation
        for _ in range(20):
            with benchmark.measure_time("cache_pattern_invalidate"):
                cache_manager.invalidate_pattern("search_knowledge:*")

        stats = benchmark.get_stats("cache_pattern_invalidate")
        assert stats["mean"] < 0.01  # Should be under 10ms


class TestMemoryManagerPerformance:
    """Test MemoryManager performance with fallback store"""

    @pytest.mark.asyncio
    async def test_knowledge_save_speed(self, memory_manager, benchmark):
        """Test knowledge point save performance"""
        await memory_manager.start()

        knowledge_points = [
            {
                "title": f"Knowledge Point {i}",
                "content": f"Content for knowledge point {i}",
                "difficulty": 0.5,
                "tags": ["test", "benchmark"]
            }
            for i in range(50)
        ]

        for kp in knowledge_points:
            with benchmark.measure_time("knowledge_save"):
                # This will use fallback store since MCP is not available
                saved_ids = await memory_manager._save_knowledge_points([kp])
                assert len(saved_ids) == 1

        stats = benchmark.get_stats("knowledge_save")
        assert stats["mean"] < 0.01  # Should be under 10ms

    @pytest.mark.asyncio
    async def test_knowledge_search_speed(self, memory_manager, benchmark):
        """Test knowledge search performance"""
        await memory_manager.start()

        # Save some knowledge points
        knowledge_points = [
            {
                "title": f"FastAPI Tutorial {i}",
                "content": f"Content about FastAPI {i}",
                "difficulty": 0.5,
                "tags": ["python", "fastapi"]
            }
            for i in range(20)
        ]
        await memory_manager._save_knowledge_points(knowledge_points)

        # Benchmark search
        for i in range(20):
            with benchmark.measure_time("knowledge_search"):
                results = await memory_manager.search_knowledge(f"FastAPI {i}")

        stats = benchmark.get_stats("knowledge_search")
        assert stats["mean"] < 0.01  # Should be under 10ms


class TestEndToEndPerformance:
    """Test end-to-end workflow performance"""

    @pytest.mark.asyncio
    async def test_full_workflow_performance(self, benchmark):
        """Test complete workflow from session to knowledge storage"""

        bus = AgentBus()
        memory_manager = MemoryManager("memory-e2e", bus)
        await memory_manager.start()

        with benchmark.measure_time("e2e_workflow"):
            # Simulate session analysis event
            event = {
                "type": "knowledge.extracted",
                "session_id": "sess-perf-test",
                "knowledge_points": [
                    {
                        "title": "Performance Testing",
                        "content": "Testing system performance",
                        "difficulty": 0.6,
                        "tags": ["testing", "performance"]
                    }
                ],
                "relations": []
            }

            await memory_manager.process_event(event)

            # Wait for processing
            await asyncio.sleep(0.1)

        stats = benchmark.get_stats("e2e_workflow")
        assert stats["mean"] < 0.2  # Should be under 200ms

    @pytest.mark.asyncio
    async def test_system_responsiveness(self, benchmark):
        """Test overall system responsiveness under load"""

        bus = AgentBus()
        task_manager = TaskManager()
        cache_manager = CacheManager()

        async def load_test_task(task_id: str, mgr: TaskManager):
            for i in range(5):
                mgr.update_progress(task_id, i * 0.2, f"Step {i}")
                await asyncio.sleep(0.01)
            mgr.update_progress(task_id, 1.0, "Complete")

        with benchmark.measure_time("system_under_load"):
            # Create multiple concurrent tasks
            task_ids = []
            for i in range(20):
                task_id = task_manager.create_task(f"load-{i}", load_test_task)
                task_ids.append(task_id)

            # Register cache entries
            for i in range(50):
                cache_manager.register_tool(f"tool_{i}", 3600, "user")

            # Wait for tasks
            await asyncio.sleep(0.3)

            # Query tasks
            for tid in task_ids:
                task = task_manager.get_task(tid)
                assert task is not None

        stats = benchmark.get_stats("system_under_load")
        assert stats["mean"] < 0.5  # Should complete in under 500ms


@pytest.mark.asyncio
async def test_print_performance_report(benchmark, task_manager, cache_manager):
    """Final test to print complete performance report"""

    # Run a mix of operations
    async def test_task(task_id: str, mgr: TaskManager):
        await asyncio.sleep(0.02)

    # Task operations
    for i in range(30):
        with benchmark.measure_time("mixed_task_create"):
            task_manager.create_task(f"mixed-{i}", test_task)

    await asyncio.sleep(0.1)

    # Cache operations
    for i in range(30):
        with benchmark.measure_time("mixed_cache_ops"):
            cache_manager.register_tool(f"mixed_tool_{i}", 3600, "user")
            cache_manager.invalidate([f"cache_{i}"])

    # Print comprehensive report
    benchmark.print_report()

    # Performance targets
    assert benchmark.get_stats("mixed_task_create")["mean"] < 0.01
    assert benchmark.get_stats("mixed_cache_ops")["mean"] < 0.002

    await asyncio.sleep(0.7)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
