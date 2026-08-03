"""Tests for the Hook system."""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import sys

# Add mcp-server to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))

from src.hooks import Hook, HookContext, SessionCaptureHook
from src.storage import ObservationStore


@pytest_asyncio.fixture
async def temp_observation_store(tmp_path):
    """Create a temporary observation store for testing."""
    store_path = tmp_path / "test_observations.jsonl"
    store = ObservationStore(str(store_path))
    yield store
    # Cleanup
    await store.clear()


@pytest.mark.asyncio
async def test_hook_context_creation():
    """Test HookContext dataclass creation."""
    request = {"method": "tools/call", "params": {"name": "test_tool"}}

    context = HookContext(request=request)

    assert context.request == request
    assert context.response is None
    assert context.error is None
    assert context.timestamp is None


@pytest.mark.asyncio
async def test_session_capture_hook_on_request(temp_observation_store):
    """Test SessionCaptureHook records timestamp on request."""
    hook = SessionCaptureHook(temp_observation_store)
    context = HookContext(request={"method": "test"})

    await hook.on_request(context)

    assert context.timestamp is not None
    assert isinstance(context.timestamp, float)


@pytest.mark.asyncio
async def test_session_capture_hook_on_response(temp_observation_store):
    """Test SessionCaptureHook records observation on response."""
    hook = SessionCaptureHook(temp_observation_store)

    # Simulate request-response cycle
    context = HookContext(
        request={"method": "tools/call", "params": {"name": "test_tool"}},
        response={"result": {"status": "ok"}},
        timestamp=1234567890.0
    )

    await hook.on_response(context)

    # Verify observation was written
    observations = await temp_observation_store.read_all()
    assert len(observations) == 1

    obs = observations[0]
    assert obs["type"] == "mcp_interaction"
    assert obs["request"]["method"] == "tools/call"
    assert obs["response"]["success"] is True
    assert obs["error"] is None
    assert "duration_ms" in obs


@pytest.mark.asyncio
async def test_session_capture_hook_records_error(temp_observation_store):
    """Test SessionCaptureHook records errors."""
    hook = SessionCaptureHook(temp_observation_store)

    error = ValueError("Test error")
    context = HookContext(
        request={"method": "tools/call"},
        error=error,
        timestamp=1234567890.0
    )

    await hook.on_response(context)

    observations = await temp_observation_store.read_all()
    assert len(observations) == 1
    assert observations[0]["error"] == "Test error"


@pytest.mark.asyncio
async def test_session_capture_hook_truncates_large_responses(temp_observation_store):
    """Test SessionCaptureHook truncates large response payloads."""
    hook = SessionCaptureHook(temp_observation_store)

    # Create a large response
    large_data = {"data": "x" * 2000}
    context = HookContext(
        request={"method": "test"},
        response={"result": large_data},
        timestamp=1234567890.0
    )

    await hook.on_response(context)

    observations = await temp_observation_store.read_all()
    obs = observations[0]

    # Response should be truncated
    assert "_summary" in obs["response"]["result"]
    assert obs["response"]["result"]["_summary"] == "Large response truncated"
    assert "_size" in obs["response"]["result"]


@pytest.mark.asyncio
async def test_multiple_hooks_in_sequence(temp_observation_store):
    """Test multiple hooks can be chained."""
    hook1 = SessionCaptureHook(temp_observation_store)
    hook2 = SessionCaptureHook(temp_observation_store)

    context = HookContext(
        request={"method": "test"},
        response={"result": "ok"},
        timestamp=1234567890.0
    )

    # Simulate hook chain
    await hook1.on_response(context)
    await hook2.on_response(context)

    # Both hooks should have written observations
    observations = await temp_observation_store.read_all()
    assert len(observations) == 2
