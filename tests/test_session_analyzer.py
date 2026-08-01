"""
Tests for Session Analyzer agent
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))

import asyncio
import pytest
from src.agents.session_analyzer import SessionAnalyzer
from src.bus.agent_bus import AgentBus


@pytest.mark.asyncio
async def test_session_analyzer_initialization():
    """Test SessionAnalyzer can be initialized"""
    bus = AgentBus()
    analyzer = SessionAnalyzer("analyzer_001", bus)

    assert analyzer.agent_id == "analyzer_001"
    assert analyzer.bus == bus
    assert analyzer.is_running is False


@pytest.mark.asyncio
async def test_session_analyzer_processes_session_completed_event():
    """Test SessionAnalyzer processes session_completed events"""
    bus = AgentBus()
    analyzer = SessionAnalyzer("analyzer_001", bus)

    results = []

    async def capture_result(event):
        results.append(event)

    await bus.start()
    await analyzer.start()

    # Subscribe to analysis results
    bus.subscribe("knowledge.extracted", capture_result)

    # Publish session completed event
    await bus.publish({
        "type": "session.completed",
        "session_id": "sess_001",
        "transcript": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."}
        ]
    })

    # Wait for processing
    await asyncio.sleep(0.1)

    await bus.stop()
    await analyzer.stop()

    # Verify knowledge was extracted
    assert len(results) >= 1
    assert results[0]["type"] == "knowledge.extracted"
    assert "knowledge_points" in results[0]


@pytest.mark.asyncio
async def test_session_analyzer_extracts_knowledge_points():
    """Test SessionAnalyzer extracts knowledge points from transcript"""
    bus = AgentBus()
    analyzer = SessionAnalyzer("analyzer_001", bus)

    results = []

    async def capture_result(event):
        results.append(event)

    await bus.start()
    await analyzer.start()
    bus.subscribe("knowledge.extracted", capture_result)

    # Publish session with technical content
    await bus.publish({
        "type": "session.completed",
        "session_id": "sess_002",
        "transcript": [
            {"role": "user", "content": "Explain async/await in Python"},
            {"role": "assistant", "content": "async/await is used for asynchronous programming. The async keyword defines a coroutine function."}
        ]
    })

    await asyncio.sleep(0.1)
    await bus.stop()
    await analyzer.stop()

    # Verify knowledge points were extracted
    assert len(results) >= 1
    knowledge_points = results[0]["knowledge_points"]
    assert isinstance(knowledge_points, list)
    assert len(knowledge_points) > 0


@pytest.mark.asyncio
async def test_session_analyzer_handles_empty_transcript():
    """Test SessionAnalyzer handles empty transcripts gracefully"""
    bus = AgentBus()
    analyzer = SessionAnalyzer("analyzer_001", bus)

    results = []

    async def capture_result(event):
        results.append(event)

    await bus.start()
    await analyzer.start()
    bus.subscribe("knowledge.extracted", capture_result)

    # Publish session with empty transcript
    await bus.publish({
        "type": "session.completed",
        "session_id": "sess_003",
        "transcript": []
    })

    await asyncio.sleep(0.1)
    await bus.stop()
    await analyzer.stop()

    # Should handle gracefully (either no result or empty knowledge_points)
    if len(results) > 0:
        assert results[0]["knowledge_points"] == []


@pytest.mark.asyncio
async def test_session_analyzer_ignores_non_session_events():
    """Test SessionAnalyzer ignores events that are not session.completed"""
    bus = AgentBus()
    analyzer = SessionAnalyzer("analyzer_001", bus)

    results = []

    async def capture_result(event):
        results.append(event)

    await bus.start()
    await analyzer.start()
    bus.subscribe("knowledge.extracted", capture_result)

    # Publish non-session event
    await bus.publish({
        "type": "other.event",
        "data": "irrelevant"
    })

    await asyncio.sleep(0.1)
    await bus.stop()
    await analyzer.stop()

    # Should not produce any results
    assert len(results) == 0
