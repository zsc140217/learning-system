"""
Task 1.6 & 1.7: 空闲触发系统和端到端集成测试
测试完整的知识图谱工作流：会话分析 -> 知识提取 -> 图谱存储 -> 空闲触发
"""
import sys
from pathlib import Path

# 添加 mcp-server 到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime

from src.bus.agent_bus import AgentBus
from src.agents.session_analyzer import SessionAnalyzer
from src.agents.memory_manager import MemoryManager
from src.agents.learning_coach import LearningCoach
from src.triggers.idle_detector import IdleDetector
from src.storage.mcp_memory_adapter import MCPMemoryAdapter


@pytest_asyncio.fixture
async def event_bus():
    """创建事件总线"""
    bus = AgentBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest_asyncio.fixture
async def session_analyzer(event_bus):
    """创建 SessionAnalyzer"""
    analyzer = SessionAnalyzer("test_analyzer", event_bus)
    await analyzer.start()
    yield analyzer
    await analyzer.stop()


@pytest_asyncio.fixture
async def memory_manager(event_bus):
    """创建 MemoryManager"""
    manager = MemoryManager("test_manager", event_bus)
    await manager.start()
    yield manager
    await manager.stop()


@pytest_asyncio.fixture
async def learning_coach(event_bus):
    """创建 LearningCoach"""
    coach = LearningCoach("test_coach", event_bus)
    await coach.start()
    yield coach
    await coach.stop()


@pytest_asyncio.fixture
async def idle_detector(event_bus):
    """创建 IdleDetector（短阈值用于测试）"""
    detector = IdleDetector(event_bus, idle_threshold_seconds=2, check_interval_seconds=1)
    await detector.start()
    yield detector
    await detector.stop()


# ============ Task 1.7: 端到端集成测试 ============

@pytest.mark.asyncio
async def test_e2e_session_to_knowledge_graph(
    event_bus,
    session_analyzer,
    memory_manager
):
    """
    端到端测试：会话分析 -> 知识提取 -> 知识图谱存储

    流程：
    1. 发布 session.completed 事件
    2. SessionAnalyzer 提取知识点和关系
    3. MemoryManager 保存到知识图谱
    """
    # 准备测试会话数据
    session_id = "test_session_001"
    transcript = [
        {"role": "user", "content": "什么是 FastAPI？"},
        {"role": "assistant", "content": "FastAPI 是一个现代、快速的 Python Web 框架，基于标准 Python 类型提示构建 API。"},
        {"role": "user", "content": "如何实现依赖注入？"},
        {"role": "assistant", "content": "FastAPI 使用 Depends 函数实现依赖注入，可以在路由函数的参数中声明依赖。"}
    ]

    # 收集发布的事件
    captured_events = []

    async def capture_events(event):
        captured_events.append(event)

    event_bus.subscribe("knowledge.extracted", capture_events)
    event_bus.subscribe("knowledge.saved", capture_events)

    # 1. 发布 session.completed 事件
    await event_bus.publish({
        "type": "session.completed",
        "session_id": session_id,
        "transcript": transcript
    })

    # 等待事件处理
    await asyncio.sleep(0.5)

    # 2. 验证 knowledge.extracted 事件
    extracted_events = [e for e in captured_events if e["type"] == "knowledge.extracted"]
    assert len(extracted_events) == 1

    extracted_event = extracted_events[0]
    knowledge_points = extracted_event["knowledge_points"]
    relations = extracted_event["relations"]

    # 验证知识点提取
    assert len(knowledge_points) >= 2  # 至少提取了2个知识点
    assert all("title" in kp for kp in knowledge_points)
    assert all("content" in kp for kp in knowledge_points)

    # 验证关系推断
    assert len(relations) >= 1  # 至少有1个关系
    assert all("from" in r and "to" in r and "relationType" in r for r in relations)

    # 3. 验证 knowledge.saved 事件
    saved_events = [e for e in captured_events if e["type"] == "knowledge.saved"]
    assert len(saved_events) == 1

    saved_event = saved_events[0]
    assert saved_event["saved_count"] >= 2
    assert saved_event["relations_count"] >= 1

    print(f"✅ 端到端测试通过:")
    print(f"   - 提取知识点: {len(knowledge_points)} 个")
    print(f"   - 推断关系: {len(relations)} 个")
    print(f"   - 保存成功: {saved_event['saved_count']} 个节点, {saved_event['relations_count']} 个关系")


@pytest.mark.asyncio
async def test_e2e_idle_trigger_workflow(
    event_bus,
    session_analyzer,
    memory_manager,
    learning_coach,
    idle_detector
):
    """
    端到端测试：空闲触发 -> 学习巩固

    流程：
    1. 记录若干活动
    2. 等待空闲检测（2秒阈值）
    3. LearningCoach 收到空闲事件并触发巩固
    """
    # 收集发布的事件
    captured_events = []

    async def capture_events(event):
        captured_events.append(event)

    event_bus.subscribe("client.idle", capture_events)
    event_bus.subscribe("learning.consolidation_triggered", capture_events)

    # 1. 模拟用户活动
    idle_detector.record_activity("tool_call", {"tool_name": "analyze_session"})
    await asyncio.sleep(0.5)

    idle_detector.record_activity("tool_call", {"tool_name": "search_knowledge"})
    await asyncio.sleep(0.5)

    idle_detector.record_activity("tool_call", {"tool_name": "get_knowledge_graph"})

    # 2. 等待空闲检测（阈值 2秒 + 检查间隔 1秒）
    print("⏳ 等待空闲触发（3秒）...")
    await asyncio.sleep(3.5)

    # 3. 验证 client.idle 事件
    idle_events = [e for e in captured_events if e["type"] == "client.idle"]
    assert len(idle_events) >= 1, "应该触发至少1次空闲事件"

    idle_event = idle_events[0]
    assert "session_data" in idle_event
    assert "tool_calls" in idle_event["session_data"]
    assert len(idle_event["session_data"]["tool_calls"]) == 3

    # 4. 验证 learning.consolidation_triggered 事件
    consolidation_events = [e for e in captured_events if e["type"] == "learning.consolidation_triggered"]
    assert len(consolidation_events) >= 1, "应该触发至少1次巩固事件"

    consolidation_event = consolidation_events[0]
    assert "session_analysis" in consolidation_event
    assert "suggestions" in consolidation_event

    analysis = consolidation_event["session_analysis"]
    suggestions = consolidation_event["suggestions"]

    assert analysis["total_calls"] == 3
    assert analysis["unique_tools"] == 3
    assert len(suggestions) >= 1

    print(f"✅ 空闲触发测试通过:")
    print(f"   - 记录活动: {analysis['total_calls']} 次")
    print(f"   - 触发空闲事件: {len(idle_events)} 次")
    print(f"   - 生成建议: {len(suggestions)} 条")
    for suggestion in suggestions:
        print(f"     * [{suggestion['priority']}] {suggestion['message']}")


@pytest.mark.asyncio
async def test_idle_detector_cooldown(event_bus, learning_coach):
    """测试 LearningCoach 的冷却机制"""
    detector = IdleDetector(event_bus, idle_threshold_seconds=1, check_interval_seconds=0.5)
    await detector.start()

    captured_events = []

    async def capture_events(event):
        captured_events.append(event)

    event_bus.subscribe("learning.consolidation_triggered", capture_events)

    # 第一次活动 -> 空闲 -> 触发
    detector.record_activity("tool_call", {"tool_name": "test"})
    await asyncio.sleep(2)

    # 第二次活动 -> 空闲 -> 应该被冷却拦截
    detector.record_activity("tool_call", {"tool_name": "test"})
    await asyncio.sleep(2)

    await detector.stop()

    # 应该只触发1次（第二次被冷却拦截）
    consolidation_count = len([e for e in captured_events if e["type"] == "learning.consolidation_triggered"])
    assert consolidation_count == 1, f"预期触发1次，实际触发{consolidation_count}次"

    print("✅ 冷却机制测试通过 - 频繁空闲不会重复触发")


@pytest.mark.asyncio
async def test_mcp_memory_integration_with_relations():
    """测试 MCP Memory 关系功能是否正常工作"""
    adapter = MCPMemoryAdapter()

    # 检查可用性
    if not adapter.is_available():
        pytest.skip("MCP Memory 不可用，跳过测试")

    # 创建知识节点
    entities = [
        {
            "name": "FastAPI 路由",
            "entityType": "knowledge",
            "observations": ["FastAPI 使用装饰器 @app.get() 定义路由"]
        },
        {
            "name": "Python 装饰器",
            "entityType": "knowledge",
            "observations": ["装饰器是一种高阶函数，用于修改函数行为"]
        }
    ]

    result = await adapter.create_entities(entities)
    assert result["status"] == "success"
    assert result["created_count"] == 2

    # 建立关系
    relations = [
        {
            "from": "FastAPI 路由",
            "to": "Python 装饰器",
            "relationType": "requires"
        }
    ]

    result = await adapter.create_relations(relations)
    assert result["status"] == "success"
    assert result["created_count"] == 1

    # 读取图谱验证关系
    graph = await adapter.read_graph()
    assert len(graph["entities"]) >= 2
    assert len(graph["relations"]) >= 1

    relation_types = [r["relationType"] for r in graph["relations"]]
    assert "requires" in relation_types

    print("✅ MCP Memory 关系功能测试通过")
    print(f"   - 创建节点: {len(entities)} 个")
    print(f"   - 创建关系: {len(relations)} 个")
    print(f"   - 图谱包含: {len(graph['entities'])} 节点, {len(graph['relations'])} 关系")


# ============ 性能测试 ============

@pytest.mark.asyncio
async def test_performance_large_session(event_bus, session_analyzer, memory_manager):
    """性能测试：处理大型会话（50轮对话）"""
    session_id = "large_session_001"

    # 生成大型会话数据
    transcript = []
    for i in range(50):
        transcript.append({"role": "user", "content": f"问题 {i+1}"})
        transcript.append({"role": "assistant", "content": f"这是关于技术点 {i+1} 的详细回答..." * 10})

    start_time = datetime.now()

    # 发布事件
    await event_bus.publish({
        "type": "session.completed",
        "session_id": session_id,
        "transcript": transcript
    })

    # 等待处理完成
    await asyncio.sleep(1)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"✅ 大型会话性能测试:")
    print(f"   - 会话大小: {len(transcript)} 轮对话")
    print(f"   - 处理时间: {duration:.2f} 秒")
    print(f"   - 性能指标: {'通过' if duration < 2 else '⚠️ 超时'}")

    assert duration < 2, f"处理时间 {duration:.2f}s 超过 2s 阈值"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
