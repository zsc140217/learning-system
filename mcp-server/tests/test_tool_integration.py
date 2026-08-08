"""
集成测试 - 验证所有工具的真实实现
测试修复后的 17 个 MCP 工具
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.protocol import MCPServer, MCPResult
from src.agents.memory_manager import MemoryManager
from src.agents.session_analyzer import SessionAnalyzer
from src.agents.learning_coach import LearningCoach
from src.bus.agent_bus import bus
from src.cache import CacheManager
from src.security import JWTHandler, NonceStore
from src.tasks import task_manager


class IntegrationTestRunner:
    """集成测试运行器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name: str):
        """测试装饰器"""
        def decorator(func):
            async def wrapper():
                try:
                    print(f"\n🧪 测试: {name}")
                    await func()
                    print(f"  ✅ 通过")
                    self.passed += 1
                    self.results.append({"name": name, "status": "PASS"})
                except AssertionError as e:
                    print(f"  ❌ 失败: {e}")
                    self.failed += 1
                    self.results.append({"name": name, "status": "FAIL", "error": str(e)})
                except Exception as e:
                    print(f"  ⚠️  错误: {e}")
                    self.failed += 1
                    self.results.append({"name": name, "status": "ERROR", "error": str(e)})
            return wrapper
        return decorator

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("📊 测试摘要")
        print("="*60)
        print(f"  ✅ 通过: {self.passed}")
        print(f"  ❌ 失败: {self.failed}")
        print(f"  📈 通过率: {self.passed / (self.passed + self.failed) * 100:.1f}%")
        print("="*60)

        if self.failed > 0:
            print("\n❌ 失败的测试:")
            for result in self.results:
                if result["status"] != "PASS":
                    print(f"  - {result['name']}: {result.get('error', 'Unknown')}")


async def setup_test_env():
    """设置测试环境"""
    print("🔧 设置测试环境...")

    # 初始化全局组件
    global memory_manager, session_analyzer, learning_coach
    global cache_manager, jwt_handler, nonce_store

    memory_manager = MemoryManager("memory_manager", bus, {})
    session_analyzer = SessionAnalyzer("session_analyzer", bus)
    learning_coach = LearningCoach("learning_coach", bus)

    cache_manager = CacheManager()
    nonce_store = NonceStore()
    jwt_handler = JWTHandler("test-secret-key", nonce_store)

    # 启动 agents
    await memory_manager.start()
    await session_analyzer.start()
    await learning_coach.start()

    print("  ✅ 测试环境就绪\n")


async def run_tests():
    """运行所有集成测试"""
    runner = IntegrationTestRunner()

    # ============ P0: 核心功能测试 ============

    @runner.test("save_knowledge - 保存知识点")
    async def test_save_knowledge():
        # 导入工具函数
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from server import save_knowledge

        knowledge_points = [
            {
                "title": "FastAPI 路由",
                "content": "使用 @app.get() 装饰器定义路由",
                "category": "Backend",
                "source": "test"
            },
            {
                "title": "Python 异步",
                "content": "使用 async/await 语法",
                "category": "Python",
                "source": "test"
            }
        ]

        result = await save_knowledge(knowledge_points, "test_session_001")

        assert result.data["status"] == "completed", f"状态应为 completed，实际: {result.data['status']}"
        assert result.data["saved_count"] == 2, f"应保存 2 个，实际: {result.data['saved_count']}"
        assert len(result.data["knowledge_ids"]) == 2, f"应返回 2 个 ID，实际: {len(result.data['knowledge_ids'])}"
        assert all("knowledge_" in kid for kid in result.data["knowledge_ids"]), "ID 格式错误"

    @runner.test("search_knowledge - 搜索知识")
    async def test_search_knowledge():
        from server import search_knowledge

        # 搜索
        result = await search_knowledge("FastAPI")

        assert result.data["source"] in ["memory_mcp", "fallback"], f"来源错误: {result.data['source']}"
        assert "results" in result.data, "缺少 results 字段"
        assert "count" in result.data, "缺少 count 字段"

    @runner.test("delete_knowledge - 删除知识（第一轮确认）")
    async def test_delete_knowledge_round1():
        from server import delete_knowledge

        result = await delete_knowledge(
            knowledge_ids=["knowledge_test_001", "knowledge_test_002"],
            request_state=None
        )

        assert result.data["requires_confirmation"] == True, "应要求确认"
        assert "io.modelcontextprotocol/inputRequired" in result.meta, "缺少 inputRequired"
        assert "requestState" in result.meta["io.modelcontextprotocol/inputRequired"], "缺少 requestState"

    @runner.test("delete_knowledge - 删除知识（第二轮执行）")
    async def test_delete_knowledge_round2():
        from server import delete_knowledge

        # 生成测试 token
        token = jwt_handler.generate_request_state(
            operation="delete_knowledge",
            params={"knowledge_ids": ["knowledge_test_001"]}
        )

        result = await delete_knowledge(
            knowledge_ids=["knowledge_test_001"],
            request_state=token
        )

        assert result.data["status"] == "completed", f"状态应为 completed，实际: {result.data['status']}"
        assert "deleted_count" in result.data, "缺少 deleted_count 字段"

    @runner.test("explore_technology - 技术探索")
    async def test_explore_technology():
        from server import explore_technology

        result = await explore_technology("FastAPI", "basic")

        assert result.data["status"] == "completed", f"状态应为 completed，实际: {result.data['status']}"
        assert result.data["topic"] == "FastAPI", "主题不匹配"
        assert len(result.data["learning_path"]) > 0, "学习路径不能为空"
        assert "resources" in result.data, "缺少 resources 字段"

    @runner.test("track_project - 项目追踪")
    async def test_track_project():
        from server import track_project

        # 使用当前项目目录测试
        project_path = str(Path(__file__).parent.parent)

        result = await track_project(project_path, "test-project")

        assert result.data["status"] == "completed", f"状态应为 completed，实际: {result.data['status']}"
        assert "tech_stack" in result.data, "缺少 tech_stack 字段"
        assert "framework" in result.data, "缺少 framework 字段"

    # 运行所有测试
    await test_save_knowledge()
    await test_search_knowledge()
    await test_delete_knowledge_round1()
    await test_delete_knowledge_round2()
    await test_explore_technology()
    await test_track_project()

    # 打印摘要
    runner.print_summary()

    return runner.passed, runner.failed


async def main():
    """主函数"""
    print("="*60)
    print("🧪 Learning System MCP Server - 集成测试")
    print("="*60)

    # 设置测试环境
    await setup_test_env()

    # 运行测试
    passed, failed = await run_tests()

    # 返回退出码
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
