"""事件总线测试"""
import sys
from pathlib import Path
import pytest
import asyncio

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))


@pytest.mark.asyncio
async def test_bus_start_stop():
    """测试总线启动和停止"""
    from src.bus.agent_bus import AgentBus
    
    bus = AgentBus()
    
    await bus.start()
    assert bus._running is True
    
    await bus.stop()
    assert bus._running is False


@pytest.mark.asyncio
async def test_subscribe_and_publish():
    """测试订阅和发布"""
    from src.bus.agent_bus import AgentBus
    
    bus = AgentBus()
    await bus.start()
    
    # 订阅事件
    received_events = []
    
    async def handler(event):
        received_events.append(event)
    
    bus.subscribe("test_event", handler)
    
    # 发布事件
    test_event = {
        "type": "test_event",
        "data": {"message": "hello"}
    }
    
    await bus.publish(test_event)
    
    # 等待事件处理
    await asyncio.sleep(0.5)
    
    # 验证
    assert len(received_events) == 1
    assert received_events[0]["type"] == "test_event"
    assert received_events[0]["data"]["message"] == "hello"
    
    await bus.stop()


@pytest.mark.asyncio
async def test_multiple_subscribers():
    """测试多个订阅者"""
    from src.bus.agent_bus import AgentBus
    
    bus = AgentBus()
    await bus.start()
    
    received_count = [0, 0]
    
    async def handler1(event):
        received_count[0] += 1
    
    async def handler2(event):
        received_count[1] += 1
    
    bus.subscribe("test_event", handler1)
    bus.subscribe("test_event", handler2)
    
    await bus.publish({"type": "test_event", "data": {}})
    await asyncio.sleep(0.5)
    
    assert received_count[0] == 1
    assert received_count[1] == 1
    
    await bus.stop()


@pytest.mark.asyncio
async def test_unsubscribe():
    """测试取消订阅"""
    from src.bus.agent_bus import AgentBus
    
    bus = AgentBus()
    await bus.start()
    
    received_events = []
    
    async def handler(event):
        received_events.append(event)
    
    bus.subscribe("test_event", handler)
    
    # 发布第一个事件
    await bus.publish({"type": "test_event", "data": {"seq": 1}})
    await asyncio.sleep(0.5)
    
    # 取消订阅
    bus.unsubscribe("test_event", handler)
    
    # 发布第二个事件
    await bus.publish({"type": "test_event", "data": {"seq": 2}})
    await asyncio.sleep(0.5)
    
    # 只应收到第一个事件
    assert len(received_events) == 1
    assert received_events[0]["data"]["seq"] == 1
    
    await bus.stop()


@pytest.mark.asyncio
async def test_event_without_type_raises_error():
    """测试没有type字段的事件抛出异常"""
    from src.bus.agent_bus import AgentBus
    
    bus = AgentBus()
    await bus.start()
    
    with pytest.raises(ValueError, match="事件必须包含 'type' 字段"):
        await bus.publish({"data": {}})
    
    await bus.stop()
