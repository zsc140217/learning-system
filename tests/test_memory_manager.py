"""
Tests for Memory Manager agent
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))

import asyncio
import pytest
from src.agents.memory_manager import MemoryManager
from src.bus.agent_bus import AgentBus


@pytest.mark.asyncio
async def test_memory_manager_initialization():
    """Test MemoryManager can be initialized"""
    bus = AgentBus()
    manager = MemoryManager("memory_001", bus)

    assert manager.agent_id == "memory_001"
    assert manager.bus == bus
    assert manager.is_running is False


@pytest.mark.asyncio
async def test_memory_manager_processes_knowledge_extracted_event():
    """Test MemoryManager processes knowledge.extracted events"""
    bus = AgentBus()
    manager = MemoryManager("memory_001", bus)

    results = []

    async def capture_result(event):
        results.append(event)

    await bus.start()
    await manager.start()

    # Subscribe to save results
    bus.subscribe("knowledge.saved", capture_result)

    # Publish knowledge extracted event
    await bus.publish({
        "type": "knowledge.extracted",
        "session_id": "sess_001",
        "knowledge_points": [
            {
                "id": "kp_001",
                "title": "Python Basics",
                "content": "Python is a programming language",
                "source": "session"
            }
        ]
    })

    # Wait for processing
    await asyncio.sleep(0.1)

    await bus.stop()
    await manager.stop()

    # Verify knowledge was saved
    assert len(results) >= 1
    assert results[0]["type"] == "knowledge.saved"
    assert "saved_count" in results[0]
    assert results[0]["saved_count"] == 1


@pytest.mark.asyncio
async def test_memory_manager_saves_multiple_knowledge_points():
    """Test MemoryManager saves multiple knowledge points"""
    bus = AgentBus()
    manager = MemoryManager("memory_001", bus)

    results = []

    async def capture_result(event):
        results.append(event)

    await bus.start()
    await manager.start()
    bus.subscribe("knowledge.saved", capture_result)

    # Publish multiple knowledge points
    await bus.publish({
        "type": "knowledge.extracted",
        "session_id": "sess_002",
        "knowledge_points": [
            {"id": "kp_001", "title": "Topic 1", "content": "Content 1", "source": "session"},
            {"id": "kp_002", "title": "Topic 2", "content": "Content 2", "source": "session"},
            {"id": "kp_003", "title": "Topic 3", "content": "Content 3", "source": "session"}
        ]
    })

    await asyncio.sleep(0.1)
    await bus.stop()
    await manager.stop()

    # Verify all knowledge points were saved
    assert len(results) >= 1
    assert results[0]["saved_count"] == 3


@pytest.mark.asyncio
async def test_memory_manager_handles_empty_knowledge_points():
    """Test MemoryManager handles empty knowledge points gracefully"""
    bus = AgentBus()
    manager = MemoryManager("memory_001", bus)

    results = []

    async def capture_result(event):
        results.append(event)

    await bus.start()
    await manager.start()
    bus.subscribe("knowledge.saved", capture_result)

    # Publish empty knowledge points
    await bus.publish({
        "type": "knowledge.extracted",
        "session_id": "sess_003",
        "knowledge_points": []
    })

    await asyncio.sleep(0.1)
    await bus.stop()
    await manager.stop()

    # Should handle gracefully (no save event or saved_count=0)
    if len(results) > 0:
        assert results[0]["saved_count"] == 0


@pytest.mark.asyncio
async def test_memory_manager_creates_entities_in_memory():
    """Test MemoryManager creates entities for knowledge points"""
    bus = AgentBus()
    manager = MemoryManager("memory_001", bus)

    await bus.start()
    await manager.start()

    # Publish knowledge point
    await bus.publish({
        "type": "knowledge.extracted",
        "session_id": "sess_004",
        "knowledge_points": [
            {
                "id": "kp_004",
                "title": "Async Programming",
                "content": "async/await enables asynchronous programming in Python",
                "source": "session",
                "session_id": "sess_004"
            }
        ]
    })

    await asyncio.sleep(0.1)
    await bus.stop()
    await manager.stop()

    # Verify entity was stored in memory
    assert len(manager._knowledge_store) > 0
    assert "kp_004" in manager._knowledge_store


@pytest.mark.asyncio
async def test_memory_manager_ignores_non_knowledge_events():
    """Test MemoryManager ignores events that are not knowledge.extracted"""
    bus = AgentBus()
    manager = MemoryManager("memory_001", bus)

    results = []

    async def capture_result(event):
        results.append(event)

    await bus.start()
    await manager.start()
    bus.subscribe("knowledge.saved", capture_result)

    # Publish non-knowledge event
    await bus.publish({
        "type": "other.event",
        "data": "irrelevant"
    })

    await asyncio.sleep(0.1)
    await bus.stop()
    await manager.stop()

    # Should not produce any results
    assert len(results) == 0
