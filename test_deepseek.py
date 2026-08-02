"""
Test DeepSeek Provider Integration
测试 DeepSeek LLM Provider 集成
"""
import asyncio
import sys
import os

# Add mcp-server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp-server'))

from src.llm import LLMProviderFactory


async def test_deepseek_provider():
    """Test DeepSeek provider creation and chat"""
    print("=" * 60)
    print("Test 1: DeepSeek Provider Creation")
    print("=" * 60)

    # Test 1: Create DeepSeek provider
    config = {
        "provider": "deepseek",
        "api_key": "sk-1c9d612d9af44212a26f48525e5faf79",
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 100
    }

    try:
        provider = LLMProviderFactory.create(config)
        print(f"[OK] Provider created: {provider.get_provider_name()}")
        print(f"[OK] Model: {provider.get_model_name()}")
    except Exception as e:
        print(f"[FAIL] Provider creation failed: {e}")
        return False

    # Test 2: List providers
    print("\n" + "=" * 60)
    print("Test 2: Available Providers")
    print("=" * 60)

    providers = LLMProviderFactory.list_providers()
    print(f"[OK] Available providers: {providers}")
    assert "deepseek" in providers, "DeepSeek not in provider list"

    # Test 3: Simple chat
    print("\n" + "=" * 60)
    print("Test 3: Simple Chat Request")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "Say 'Hello from DeepSeek!' and nothing else."}
    ]

    try:
        response = await provider.chat(messages)
        print(f"[OK] Response received: {response[:100]}...")
        assert len(response) > 0, "Empty response"
    except Exception as e:
        print(f"[FAIL] Chat request failed: {e}")
        return False

    # Test 4: Streaming chat
    print("\n" + "=" * 60)
    print("Test 4: Streaming Chat Request")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "Count from 1 to 3, one number per line."}
    ]

    try:
        print("[OK] Streaming response: ", end="", flush=True)
        async for chunk in provider.chat_stream(messages):
            print(chunk, end="", flush=True)
        print()  # New line
    except Exception as e:
        print(f"\n[FAIL] Streaming request failed: {e}")
        return False

    return True


async def test_interview_agent_with_deepseek():
    """Test InterviewAgent with DeepSeek provider"""
    print("\n" + "=" * 60)
    print("Test 5: InterviewAgent with DeepSeek")
    print("=" * 60)

    from src.bus.agent_bus import bus
    from src.agents.interview_agent import InterviewAgent
    from src.llm import LLMProviderFactory

    # Create DeepSeek provider
    config = {
        "provider": "deepseek",
        "api_key": "sk-1c9d612d9af44212a26f48525e5faf79",
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 200
    }

    provider = LLMProviderFactory.create(config)

    # Create InterviewAgent with DeepSeek
    interview_agent = InterviewAgent(
        "test-interview",
        bus,
        llm_provider=provider
    )

    await interview_agent.start()

    # Simulate project analysis data
    project_id = "test-project"
    analysis = {
        "project_path": "E:/Desktop/learning-system",
        "name": "learning-system",
        "language": "python",
        "tech_stack": {
            "frameworks": [
                {"name": "FastAPI", "version": "0.100.0"}
            ],
            "databases": [
                {"name": "SQLite", "version": "3.0"}
            ],
            "other": [
                {"name": "MCP", "description": "Model Context Protocol"}
            ]
        },
        "architecture": {
            "style": "Layered Monolith",
            "patterns": ["Event-Driven", "Dependency Injection"],
            "highlights": [
                {
                    "title": "Multi-agent architecture",
                    "description": "Event-driven communication between ProjectAgent, InterviewAgent, and MemoryManager"
                },
                {
                    "title": "MCP protocol integration",
                    "description": "Implements Model Context Protocol for LLM integration"
                }
            ]
        }
    }

    # Generate questions
    result = await interview_agent._generate_questions(project_id, analysis)

    print(f"[OK] Generated {len(result)} questions")

    # Check first question
    if result:
        q = result[0]
        print(f"\n[OK] Sample Question:")
        print(f"  ID: {q['id']}")
        print(f"  Question: {q['question'][:80]}...")
        print(f"  Answer Source: {q.get('answer_source', 'unknown')}")
        print(f"  Answer Length: {len(q.get('answer', ''))} chars")

        if q.get('answer_source') == 'llm':
            print(f"  [SUCCESS] LLM-enhanced answer detected!")
        else:
            print(f"  [INFO] Using template answer (LLM not called)")

    await interview_agent.stop()

    return True


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DeepSeek Provider Integration Tests")
    print("=" * 60 + "\n")

    try:
        # Test 1-4: Provider tests
        success = await test_deepseek_provider()

        if not success:
            print("\n[FAIL] Provider tests failed")
            return

        # Test 5: InterviewAgent integration
        success = await test_interview_agent_with_deepseek()

        if not success:
            print("\n[FAIL] InterviewAgent integration failed")
            return

        print("\n" + "=" * 60)
        print("All Tests Passed!")
        print("=" * 60)
        print("\nDeepSeek provider is successfully integrated!")
        print("You can now use it in your learning system.")

    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
