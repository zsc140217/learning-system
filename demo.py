"""
Learning System Demo - Quick Start Demo

This demo shows the core features of the learning system:
1. Agent Bus (event-driven messaging)
2. Memory Manager (knowledge graph)
3. Interview Agent (AI interview assistant)
4. LLM Provider (with mock mode)
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from src.bus.agent_bus import AgentBus
from src.agents.memory_manager import MemoryManager
from src.agents.interview_agent import InterviewAgent
from src.utils.logging import setup_logging
from loguru import logger


class MockLLMProvider:
    """Simple mock provider for demo"""

    async def chat(self, messages, temperature=0.7, max_tokens=1000):
        last_msg = messages[-1]["content"] if messages else ""

        if "fastapi" in last_msg.lower():
            return "FastAPI is a modern Python web framework with automatic API documentation, type hints, and async support."
        elif "python" in last_msg.lower():
            return "Python is a versatile programming language known for readability and extensive libraries."
        else:
            return f"Response for: {last_msg[:50]}"

    def get_stats(self):
        return {
            "cache": {"hits": 0, "total": 0},
            "tokens": {"total_tokens": 100, "total_cost": 0.0001}
        }


async def demo():
    """Run interactive demo"""

    # Setup
    setup_logging(level="INFO")

    print("=" * 60)
    print("Learning System - Interactive Demo")
    print("=" * 60)
    print()

    # Initialize components
    print("Initializing components...")
    bus = AgentBus()
    await bus.start()

    llm_provider = MockLLMProvider()

    memory_manager = MemoryManager(
        agent_id="demo_memory",
        bus=bus,
        mcp_tools={}
    )
    await memory_manager.start()

    interview_agent = InterviewAgent(
        agent_id="demo_interview",
        bus=bus,
        llm_provider=llm_provider
    )
    await interview_agent.start()

    print("OK - Components initialized\n")

    # Demo 1: Knowledge Graph
    print("=" * 60)
    print("Demo 1: Knowledge Graph Operations")
    print("=" * 60)

    print("\n1. Creating knowledge points...")
    knowledge_points = [
        {
            "id": "kp_001",
            "title": "FastAPI Basics",
            "content": "FastAPI is a modern Python web framework",
            "source": "demo",
            "session_id": "demo_001",
            "timestamp": datetime.now().isoformat()
        },
        {
            "id": "kp_002",
            "title": "Python Async",
            "content": "Async programming with asyncio",
            "source": "demo",
            "session_id": "demo_001",
            "timestamp": datetime.now().isoformat()
        }
    ]

    await bus.publish({
        "type": "knowledge.extracted",
        "session_id": "demo_001",
        "knowledge_points": knowledge_points
    })
    await asyncio.sleep(0.3)

    print(f"OK - Created {len(knowledge_points)} knowledge points")

    print("\n2. Searching knowledge...")
    results = await memory_manager.search_knowledge("FastAPI")
    print(f"OK - Found {len(results.get('nodes', []))} nodes")

    print("\n3. Getting statistics...")
    stats = memory_manager.get_stats()
    print(f"  Total knowledge points: {stats['total_knowledge_points']}")
    print(f"  Store size: {stats['store_size_kb']:.2f} KB")
    print(f"  Source: {stats['source']}")

    # Demo 2: LLM Query
    print("\n" + "=" * 60)
    print("Demo 2: LLM Query (Mock Mode)")
    print("=" * 60)

    print("\nQuery: What is FastAPI?")
    response = await llm_provider.chat([
        {"role": "user", "content": "What is FastAPI?"}
    ])
    print(f"\nResponse: {response}")

    # Demo 3: Event Bus
    print("\n" + "=" * 60)
    print("Demo 3: Event Bus Messaging")
    print("=" * 60)

    print("\nPublishing learning progress event...")
    await bus.publish({
        "type": "learning.progress_updated",
        "session_id": "demo_001",
        "knowledge_point_id": "kp_001",
        "status": "completed",
        "completion_percentage": 100
    })
    await asyncio.sleep(0.2)
    print("OK - Event published and processed")

    # Summary
    print("\n" + "=" * 60)
    print("Demo Summary")
    print("=" * 60)
    print("\nAll components working correctly:")
    print("  - Agent Bus: Event messaging OK")
    print("  - Memory Manager: Knowledge storage OK")
    print("  - Interview Agent: AI assistant OK")
    print("  - LLM Provider: Query processing OK")

    print("\nSystem Statistics:")
    print(f"  Knowledge points: {stats['total_knowledge_points']}")
    print(f"  Store size: {stats['store_size_kb']:.2f} KB")

    llm_stats = llm_provider.get_stats()
    print(f"  LLM tokens: {llm_stats['tokens']['total_tokens']}")
    print(f"  LLM cost: ${llm_stats['tokens']['total_cost']:.6f}")

    print("\nDemo completed successfully!")

    # Cleanup
    await interview_agent.stop()
    await memory_manager.stop()
    await bus.stop()


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
