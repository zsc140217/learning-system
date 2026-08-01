"""
Tests for base agent functionality
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))

import asyncio
import pytest
from src.agents.base_agent import BaseAgent
from src.bus.agent_bus import AgentBus


class TestAgent(BaseAgent):
    """Test agent implementation"""

    def __init__(self, agent_id: str, bus: AgentBus):
        super().__init__(agent_id, bus)
        self.processed_events = []

    async def process_event(self, event: dict) -> None:
        """Process test events"""
        self.processed_events.append(event)


@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent can be initialized with ID and bus"""
    bus = AgentBus()
    agent = TestAgent("test_agent", bus)

    assert agent.agent_id == "test_agent"
    assert agent.bus == bus
    assert agent.is_running is False


@pytest.mark.asyncio
async def test_agent_start_stop():
    """Test agent lifecycle management"""
    bus = AgentBus()
    agent = TestAgent("test_agent", bus)

    await bus.start()
    await agent.start()
    assert agent.is_running is True

    await agent.stop()
    assert agent.is_running is False
    await bus.stop()


@pytest.mark.asyncio
async def test_agent_subscribes_to_events():
    """Test agent can subscribe to events"""
    bus = AgentBus()
    agent = TestAgent("test_agent", bus)

    await bus.start()
    await agent.start()

    # Subscribe to test events
    await agent.subscribe("test.event")

    # Publish event
    await bus.publish({
        "type": "test.event",
        "data": "test_data"
    })

    # Wait for event processing (give the worker task time to process)
    await asyncio.sleep(0.1)

    await bus.stop()
    await agent.stop()

    # Verify event was received
    assert len(agent.processed_events) == 1
    assert agent.processed_events[0]["type"] == "test.event"
    assert agent.processed_events[0]["data"] == "test_data"


@pytest.mark.asyncio
async def test_agent_emit_event():
    """Test agent can emit events"""
    bus = AgentBus()
    agent = TestAgent("test_agent", bus)

    received_events = []

    async def handler(event):
        received_events.append(event)

    await bus.start()
    await agent.start()
    bus.subscribe("agent.output", handler)

    # Emit event from agent
    await agent.emit({
        "type": "agent.output",
        "data": "result"
    })

    # Wait for event processing
    await asyncio.sleep(0.1)

    await bus.stop()
    await agent.stop()

    # Verify event was published
    assert len(received_events) == 1
    assert received_events[0]["type"] == "agent.output"


@pytest.mark.asyncio
async def test_agent_multiple_subscriptions():
    """Test agent can subscribe to multiple event types"""
    bus = AgentBus()
    agent = TestAgent("test_agent", bus)

    await bus.start()
    await agent.start()

    # Subscribe to multiple event types
    await agent.subscribe("event.type1")
    await agent.subscribe("event.type2")

    # Publish different events
    await bus.publish({"type": "event.type1", "data": "data1"})
    await bus.publish({"type": "event.type2", "data": "data2"})
    await bus.publish({"type": "event.type3", "data": "data3"})  # Not subscribed

    # Wait for event processing
    await asyncio.sleep(0.1)

    await bus.stop()
    await agent.stop()

    # Verify only subscribed events were received
    assert len(agent.processed_events) == 2
    assert agent.processed_events[0]["type"] == "event.type1"
    assert agent.processed_events[1]["type"] == "event.type2"
