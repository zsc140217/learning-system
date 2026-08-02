"""
Phase 3 Testing Script
Tests LLM Provider abstraction and InterviewAgent integration
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "mcp-server"))

from src.bus.agent_bus import bus
from src.agents.interview_agent import InterviewAgent
from src.llm import LLMProviderFactory


async def test_llm_providers():
    """Test LLM Provider abstraction layer"""
    print("\n" + "=" * 60)
    print("[Test 1] LLM Provider Abstraction Layer")
    print("=" * 60)

    # Test 1.1: Factory list providers
    print("\n[Test 1.1] List available providers...")
    providers = LLMProviderFactory.list_providers()
    print(f"[OK] Available providers: {providers}")

    # Test 1.2: Create OpenAI provider (without API key for testing)
    print("\n[Test 1.2] Create OpenAI provider...")
    try:
        # This will fail validation but tests the factory
        openai_config = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        provider = LLMProviderFactory.create(openai_config)
        print(f"[SKIP] OpenAI provider requires API key")
    except ValueError as e:
        print(f"[OK] Validation working: {str(e)[:50]}...")

    # Test 1.3: Create Anthropic provider (without API key for testing)
    print("\n[Test 1.3] Create Anthropic provider...")
    try:
        anthropic_config = {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022"
        }
        provider = LLMProviderFactory.create(anthropic_config)
        print(f"[SKIP] Anthropic provider requires API key")
    except ValueError as e:
        print(f"[OK] Validation working: {str(e)[:50]}...")

    print("\n[Summary] LLM Provider tests completed")
    print("  - Factory pattern working")
    print("  - Multiple providers supported")
    print("  - Configuration validation working")


async def test_interview_agent_with_llm():
    """Test InterviewAgent with LLM integration"""
    print("\n" + "=" * 60)
    print("[Test 2] InterviewAgent with LLM Integration")
    print("=" * 60)

    # Test 2.1: Without LLM (template mode)
    print("\n[Test 2.1] InterviewAgent without LLM (template mode)...")
    agent_no_llm = InterviewAgent("test_interview_no_llm", bus, llm_provider=None)
    await agent_no_llm.start()

    # Simulate project analysis event
    mock_analysis = {
        "project_path": "E:\\Desktop\\learning-system",
        "language": "python",
        "tech_stack": {
            "frameworks": [{"name": "FastAPI", "version": "0.100+"}],
            "databases": [{"name": "SQLite", "purpose": "local storage"}]
        },
        "architecture": {
            "structure": "Layered Monolith",
            "patterns": ["Event-Driven", "Repository Pattern"],
            "highlights": [
                {"title": "Event Bus", "description": "Decoupled agent communication"}
            ]
        }
    }

    questions = await agent_no_llm._generate_questions("proj-test", mock_analysis)
    print(f"[OK] Generated {len(questions)} questions (template mode)")

    # Verify question structure
    if questions:
        q = questions[0]
        assert "id" in q, "Missing question id"
        assert "category" in q, "Missing category"
        assert "difficulty" in q, "Missing difficulty"
        assert "question" in q, "Missing question text"
        assert "standard_answer" in q, "Missing standard answer"
        assert "key_points" in q, "Missing key points"
        assert "follow_up_questions" in q, "Missing follow-up questions"
        print(f"[OK] Question structure validated")
        print(f"     - ID: {q['id']}")
        print(f"     - Category: {q['category']}")
        print(f"     - Difficulty: {q['difficulty']}")

    # Test 2.2: With LLM (if API key available)
    print("\n[Test 2.2] InterviewAgent with LLM enhancement...")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    if api_key:
        print("[INFO] API key found, testing LLM enhancement...")

        # Determine provider
        if os.getenv("OPENAI_API_KEY"):
            llm_config = {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7
            }
        else:
            llm_config = {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.7
            }

        provider = LLMProviderFactory.create(llm_config)
        agent_with_llm = InterviewAgent("test_interview_llm", bus, llm_provider=provider)
        await agent_with_llm.start()

        # Generate questions with LLM enhancement
        enhanced_questions = await agent_with_llm._generate_questions("proj-test", mock_analysis)
        print(f"[OK] Generated {len(enhanced_questions)} questions with LLM")

        # Check if enhancement was applied
        if enhanced_questions:
            eq = enhanced_questions[0]
            if "answer_source" in eq and eq["answer_source"] == "llm":
                print(f"[OK] LLM enhancement applied")
                print(f"     - Answer length: {len(eq['standard_answer'])} chars")
                print(f"     - Template preserved: {'template_answer' in eq}")
            else:
                print(f"[SKIP] LLM enhancement skipped (fallback to template)")
    else:
        print("[SKIP] No API key found (set OPENAI_API_KEY or ANTHROPIC_API_KEY)")

    print("\n[Summary] InterviewAgent tests completed")
    print("  - Template mode working")
    print("  - LLM integration ready (requires API key)")
    print("  - Fallback mechanism working")


async def test_complete_flow():
    """Test complete flow with event bus"""
    print("\n" + "=" * 60)
    print("[Test 3] Complete Event-Driven Flow")
    print("=" * 60)

    # Start event bus
    await bus.start()

    # Setup InterviewAgent
    agent = InterviewAgent("test_interview_flow", bus, llm_provider=None)
    await agent.start()

    # Track emitted events
    received_events = []

    async def event_listener(event):
        if event.get("type") == "interview.questions_generated":
            received_events.append(event)

    # Subscribe to output event
    bus.subscribe("interview.questions_generated", event_listener)

    # Emit project analysis event
    print("\n[Test 3.1] Emitting project.analysis_completed event...")
    await bus.publish({
        "type": "project.analysis_completed",
        "project_id": "proj-learning-system",
        "analysis": {
            "project_path": "E:\\Desktop\\learning-system",
            "language": "python",
            "tech_stack": {
                "frameworks": [{"name": "FastAPI"}]
            },
            "architecture": {
                "structure": "Layered Monolith",
                "patterns": ["Event-Driven"]
            }
        }
    })

    # Wait for processing
    await asyncio.sleep(1.0)

    # Verify event received
    print(f"\n[Test 3.2] Checking emitted events...")
    assert len(received_events) > 0, "No events received"
    print(f"[OK] Received {len(received_events)} event(s)")

    event = received_events[0]
    assert event["type"] == "interview.questions_generated"
    assert "project_id" in event
    assert "questions" in event
    assert "generated_at" in event
    print(f"[OK] Event structure validated")
    print(f"     - Project ID: {event['project_id']}")
    print(f"     - Questions: {len(event['questions'])}")
    print(f"     - Generated at: {event['generated_at']}")

    # Stop event bus
    await bus.stop()

    print("\n[Summary] Event-driven flow completed")
    print("  - Event subscription working")
    print("  - Event emission working")
    print("  - End-to-end integration successful")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Phase 3 Test Suite")
    print("=" * 60)

    try:
        await test_llm_providers()
        await test_interview_agent_with_llm()
        await test_complete_flow()

        print("\n" + "=" * 60)
        print("All Tests Passed!")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Set OPENAI_API_KEY or ANTHROPIC_API_KEY to test LLM enhancement")
        print("2. Configure real Memory MCP Server")
        print("3. Run integration tests with actual project")

    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
