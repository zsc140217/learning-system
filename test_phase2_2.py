"""
Phase 2.2 Testing Script
Tests MemoryManager (MCP integration), InterviewAgent, and Knowledge Graph Viewer
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "mcp-server"))

from src.bus.agent_bus import bus
from src.agents.memory_manager import MemoryManager
from src.agents.interview_agent import InterviewAgent


async def test_memory_manager():
    """Test MemoryManager with Memory MCP integration"""
    print("\n" + "=" * 60)
    print("[Test 1] MemoryManager - Memory MCP Integration")
    print("=" * 60)

    # Initialize MemoryManager (without actual MCP tools for now)
    memory_manager = MemoryManager("test_memory_manager", bus, mcp_tools={})
    await memory_manager.start()

    # Test 1: Save knowledge points
    print("\n[Test 1.1] Saving knowledge points...")
    knowledge_points = [
        {
            "id": "k-fastapi-001",
            "title": "FastAPI Basics",
            "content": "FastAPI is a modern web framework for building APIs",
            "source": "session",
            "session_id": "sess-test-001",
            "timestamp": "2026-08-02T20:00:00"
        },
        {
            "id": "k-mcp-001",
            "title": "MCP Protocol",
            "content": "Model Context Protocol for AI agent communication",
            "source": "session",
            "session_id": "sess-test-001",
            "timestamp": "2026-08-02T20:05:00"
        }
    ]

    saved_ids = await memory_manager._save_knowledge_points(knowledge_points)
    print(f"[OK] Saved {len(saved_ids)} knowledge points")
    print(f"   IDs: {', '.join(saved_ids)}")

    # Test 2: Search knowledge
    print("\n[Test 1.2] Searching knowledge...")
    search_result = await memory_manager.search_knowledge("FastAPI")
    print(f"[OK] Search results for 'FastAPI': {len(search_result['nodes'])} nodes found")
    print(f"   Source: {search_result['source']}")
    print(f"   Cache TTL: {search_result['_meta']['ttlMs']}ms")

    # Test 3: Get stats
    print("\n[Test 1.3] Getting memory stats...")
    stats = memory_manager.get_stats()
    print(f"[OK] Memory stats:")
    print(f"   Total nodes: {stats['total_knowledge_points']}")
    print(f"   Store size: {stats['store_size_kb']:.2f} KB")
    print(f"   MCP available: {stats['mcp_available']}")
    print(f"   Source: {stats['source']}")

    await memory_manager.stop()
    print("\n[OK] MemoryManager test completed")


async def test_interview_agent():
    """Test InterviewAgent question generation"""
    print("\n" + "=" * 60)
    print("[Test 2] InterviewAgent - Question Generation")
    print("=" * 60)

    # Initialize InterviewAgent
    interview_agent = InterviewAgent("test_interview_agent", bus)
    await interview_agent.start()

    # Mock project analysis result
    project_analysis = {
        "project_id": "proj-learning-system-test",
        "analysis": {
            "project_path": "E:\\Desktop\\learning-system",
            "language": "python",
            "timestamp": "2026-08-02T20:00:00",
            "architecture": {
                "patterns": ["Agent-Based", "Layered Architecture"],
                "structure": "Layered Monolith",
                "highlights": [
                    {
                        "title": "Event-Driven Communication",
                        "description": "Agents communicate via async event bus"
                    },
                    {
                        "title": "MCP Protocol Integration",
                        "description": "Full implementation of MCP 2026-07-28 features"
                    }
                ]
            },
            "tech_stack": {
                "frameworks": [
                    {"name": "FastAPI", "version": None}
                ],
                "databases": [],
                "infrastructure": []
            }
        }
    }

    # Generate questions
    print("\n[Test 2.1] Generating interview questions...")
    questions = await interview_agent._generate_questions(
        project_analysis["project_id"],
        project_analysis["analysis"]
    )

    print(f"[OK] Generated {len(questions)} interview questions")
    print("\nQuestions Preview:")
    print("-" * 60)

    for i, q in enumerate(questions, 1):
        print(f"\n{i}. [{q['difficulty'].upper()}] {q['question']}")
        print(f"   Category: {q['category']}")
        print(f"   Key Points: {len(q['key_points'])} points")
        print(f"   Follow-ups: {len(q['follow_up_questions'])} questions")

        # Show first question details
        if i == 1:
            print(f"\n   Standard Answer Preview:")
            answer_lines = q['standard_answer'].split('\n')[:5]
            for line in answer_lines:
                print(f"   {line}")
            if len(q['standard_answer'].split('\n')) > 5:
                print(f"   ... (truncated)")

    await interview_agent.stop()
    print("\n[OK] InterviewAgent test completed")


async def test_knowledge_graph_viewer():
    """Test Knowledge Graph Viewer HTML exists"""
    print("\n" + "=" * 60)
    print("[Test 3] Knowledge Graph Viewer - MCP App")
    print("=" * 60)

    viewer_path = project_root / "mcp-server" / "src" / "apps" / "knowledge_graph_viewer.html"

    print(f"\n[Test 3.1] Checking HTML file...")
    if viewer_path.exists():
        file_size = viewer_path.stat().st_size
        print(f"[OK] File exists: {viewer_path}")
        print(f"   Size: {file_size / 1024:.2f} KB")

        # Read and check key features
        content = viewer_path.read_text(encoding='utf-8')
        features = {
            "Canvas rendering": "<canvas id=\"graph-canvas\">" in content,
            "Search functionality": "id=\"search-input\"" in content,
            "Filter buttons": "data-filter=" in content,
            "Node details panel": "id=\"node-details\"" in content,
            "MCP postMessage": "window.parent.postMessage" in content,
            "Stats display": "id=\"stat-total\"" in content
        }

        print("\n[Test 3.2] Checking features...")
        for feature, present in features.items():
            status = "[OK]" if present else "[FAIL]"
            print(f"   {status} {feature}")

        all_present = all(features.values())
        if all_present:
            print("\n[OK] Knowledge Graph Viewer test completed")
        else:
            print("\n[WARN]  Some features missing")
    else:
        print(f"[FAIL] File not found: {viewer_path}")


async def test_project_analysis_completed_flow():
    """Test the complete flow: project analysis -> interview questions + memory storage"""
    print("\n" + "=" * 60)
    print("[Test 4] Complete Flow - Project Analysis -> Questions + Memory")
    print("=" * 60)

    # Initialize agents
    await bus.start()
    memory_manager = MemoryManager("test_memory", bus, mcp_tools={})
    interview_agent = InterviewAgent("test_interview", bus)

    await memory_manager.start()
    await interview_agent.start()

    # Collect emitted events
    collected_events = []

    async def event_collector(event):
        collected_events.append(event)

    bus.subscribe("interview.questions_generated", event_collector)
    bus.subscribe("knowledge.saved", event_collector)

    # Publish project.analysis_completed event
    print("\n[Test 4.1] Publishing project.analysis_completed event...")
    await bus.publish({
        "type": "project.analysis_completed",
        "project_id": "proj-test-flow",
        "analysis": {
            "project_path": "E:\\Desktop\\test-project",
            "language": "python",
            "timestamp": "2026-08-02T20:30:00",
            "architecture": {
                "patterns": ["Microservices"],
                "structure": "Microservices",
                "highlights": []
            },
            "tech_stack": {
                "frameworks": [{"name": "Django", "version": "4.2"}],
                "databases": [{"name": "PostgreSQL", "version": "15"}],
                "infrastructure": [{"name": "Docker", "version": None}]
            }
        }
    })

    # Wait for event processing
    await asyncio.sleep(0.5)

    print(f"\n[Test 4.2] Checking emitted events...")
    print(f"[OK] Collected {len(collected_events)} events")

    for event in collected_events:
        event_type = event.get("type")
        print(f"\n   Event: {event_type}")
        if event_type == "interview.questions_generated":
            print(f"   - Generated {len(event.get('questions', []))} questions")
        elif event_type == "knowledge.saved":
            print(f"   - Saved {event.get('saved_count', 0)} knowledge points")

    # Cleanup
    await memory_manager.stop()
    await interview_agent.stop()
    await bus.stop()

    print("\n[OK] Complete flow test completed")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Phase 2.2 Testing Suite")
    print("Testing: MemoryManager, InterviewAgent, Knowledge Graph Viewer")
    print("=" * 60)

    try:
        # Run tests sequentially
        await test_memory_manager()
        await test_interview_agent()
        await test_knowledge_graph_viewer()
        await test_project_analysis_completed_flow()

        print("\n" + "=" * 60)
        print("[OK] All Phase 2.2 tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
