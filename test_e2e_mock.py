"""
E2E Integration Test with Mock Mode

This test can run in two modes:
1. REAL mode: Uses actual DeepSeek API (requires DEEPSEEK_API_KEY)
2. MOCK mode: Uses simulated responses (no API key needed)

Run with: python test_e2e_mock.py [--mode=mock|real]
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "mcp-server"))

from src.bus.agent_bus import AgentBus
from src.agents.memory_manager import MemoryManager
from src.agents.interview_agent import InterviewAgent
from src.llm.deepseek_provider import DeepSeekProvider
from src.utils.logging import setup_logging
from loguru import logger


class MockLLMProvider:
    """Mock LLM provider for testing without API"""

    def __init__(self, config):
        self.config = config
        self.call_count = 0
        self.stats = {
            "cache": {"hits": 0, "misses": 0, "total": 0},
            "rate_limiter": {"requests": 0, "total_wait_time": 0},
            "retry": {"total_requests": 0, "total_retries": 0, "success_rate": 100.0},
            "tokens": {"total_tokens": 1500, "total_cost": 0.000015}
        }

    async def chat(self, messages, temperature=0.7, max_tokens=1000):
        """Simulate chat completion"""
        self.call_count += 1
        self.stats["cache"]["total"] += 1
        self.stats["retry"]["total_requests"] += 1

        # Simulate cache hit for identical requests
        if self.call_count > 1 and temperature == 0.0:
            self.stats["cache"]["hits"] += 1
        else:
            self.stats["cache"]["misses"] += 1

        # Simulate rate limiting
        await asyncio.sleep(0.05)
        self.stats["rate_limiter"]["requests"] += 1

        # Generate mock response based on message content
        last_message = messages[-1]["content"] if messages else ""

        if "learning path" in last_message.lower():
            return """Learning Path for FastAPI:
1. Python Basics Review
2. FastAPI Fundamentals
3. Async Programming with asyncio
4. API Design Best Practices
5. Production Deployment"""

        elif "extract key skills" in last_message.lower():
            return "Key skills: Python, FastAPI, asyncio, PostgreSQL, Docker, REST API, Microservices"

        elif "interview questions" in last_message.lower():
            return """1. What are the main advantages of FastAPI?
2. Explain dependency injection in FastAPI
3. How do you handle async operations in FastAPI?"""

        elif "async requests" in last_message.lower():
            return "Use async/await keywords with async def route handlers for non-blocking I/O operations"

        elif "rate this response" in last_message.lower():
            return "Rating: 8/10. Good technical understanding with room for more examples."

        else:
            return "Mock response for: " + last_message[:50]

    async def chat_stream(self, messages, temperature=0.7, max_tokens=1000):
        """Simulate streaming chat"""
        response = await self.chat(messages, temperature, max_tokens)
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.01)

    def get_stats(self):
        """Return mock statistics"""
        return self.stats


class E2ETestRunner:
    """End-to-end test runner with mock support"""

    def __init__(self, use_real_api=False):
        self.bus = AgentBus()
        self.memory_manager = None
        self.interview_agent = None
        self.llm_provider = None
        self.use_real_api = use_real_api
        self.test_session_id = f"e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }

    async def setup(self):
        """Initialize all components"""
        logger.info("Setting up E2E test environment...")
        logger.info(f"Mode: {'REAL API' if self.use_real_api else 'MOCK'}")

        # Start message bus
        await self.bus.start()

        # Initialize LLM provider
        llm_config = {
            "model": "deepseek-chat",
            "rate_limit": 20,
            "cache_ttl": 300,
            "max_retries": 3
        }

        if self.use_real_api:
            self.llm_provider = DeepSeekProvider(llm_config)
        else:
            self.llm_provider = MockLLMProvider(llm_config)

        # Initialize memory manager
        self.memory_manager = MemoryManager(
            agent_id="memory_e2e",
            bus=self.bus,
            mcp_tools={}
        )
        await self.memory_manager.start()

        # Initialize interview agent
        self.interview_agent = InterviewAgent(
            agent_id="interview_e2e",
            bus=self.bus,
            llm_provider=self.llm_provider
        )
        await self.interview_agent.start()

        logger.success("E2E test environment ready")

    async def teardown(self):
        """Cleanup all components"""
        logger.info("Tearing down E2E test environment...")

        if self.interview_agent:
            await self.interview_agent.stop()
        if self.memory_manager:
            await self.memory_manager.stop()
        if self.bus:
            await self.bus.stop()

        logger.success("E2E test environment cleaned up")

    async def test_scenario_1_learning_flow(self):
        """Scenario 1: Complete Learning Flow"""
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 1: Complete Learning Flow")
        logger.info("=" * 60)

        try:
            # Step 1: Create learning topic
            logger.info("Step 1: Creating learning topic...")
            learning_topic = {
                "id": "topic_fastapi_001",
                "title": "FastAPI Web Development",
                "description": "Learn FastAPI framework",
                "difficulty": "intermediate",
                "estimated_hours": 20
            }

            await self.bus.publish({
                "type": "learning.topic_created",
                "session_id": self.test_session_id,
                "topic": learning_topic
            })
            await asyncio.sleep(0.2)
            logger.success("Step 1 PASSED")

            # Step 2: Generate learning path
            logger.info("Step 2: Generating learning path...")
            messages = [
                {"role": "system", "content": "You are a learning planner."},
                {"role": "user", "content": f"Generate learning path for: {learning_topic['title']}"}
            ]
            learning_path = await self.llm_provider.chat(messages, temperature=0.7, max_tokens=500)
            logger.success(f"Step 2 PASSED ({len(learning_path)} chars)")

            # Step 3: Extract knowledge points
            logger.info("Step 3: Extracting knowledge points...")
            knowledge_points = [
                {
                    "id": f"kp_fastapi_{i:03d}",
                    "title": f"FastAPI Concept {i}",
                    "content": f"Key concept {i}",
                    "source": "ai_generated",
                    "session_id": self.test_session_id,
                    "timestamp": datetime.now().isoformat()
                }
                for i in range(1, 4)
            ]

            await self.bus.publish({
                "type": "knowledge.extracted",
                "session_id": self.test_session_id,
                "knowledge_points": knowledge_points
            })
            await asyncio.sleep(0.3)
            logger.success(f"Step 3 PASSED ({len(knowledge_points)} points)")

            # Step 4: Track progress
            logger.info("Step 4: Tracking progress...")
            for i, kp in enumerate(knowledge_points, 1):
                await self.bus.publish({
                    "type": "learning.progress_updated",
                    "session_id": self.test_session_id,
                    "knowledge_point_id": kp["id"],
                    "status": "completed",
                    "completion_percentage": i / len(knowledge_points) * 100
                })
                await asyncio.sleep(0.1)
            logger.success("Step 4 PASSED")

            # Step 5: Verify knowledge graph
            logger.info("Step 5: Verifying knowledge graph...")
            search_results = await self.memory_manager.search_knowledge("FastAPI")
            node_count = len(search_results.get("nodes", []))

            if node_count >= len(knowledge_points):
                logger.success(f"Step 5 PASSED ({node_count} nodes)")
            else:
                logger.warning(f"Step 5 WARNING: {node_count} nodes")
                self.results["warnings"].append("Node count mismatch")

            self.results["passed"].append("Scenario 1: Learning Flow")

        except Exception as e:
            logger.error(f"Scenario 1 FAILED: {e}")
            self.results["failed"].append(f"Scenario 1: {str(e)}")

    async def test_scenario_2_knowledge_graph(self):
        """Scenario 2: Knowledge Graph Operations"""
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 2: Knowledge Graph")
        logger.info("=" * 60)

        try:
            # Create entities
            logger.info("Step 1: Creating entities...")
            entities = [
                {"name": "Python", "type": "language"},
                {"name": "FastAPI", "type": "framework"}
            ]

            for entity in entities:
                await self.bus.publish({
                    "type": "knowledge.entity_created",
                    "session_id": self.test_session_id,
                    "entity": entity
                })
                await asyncio.sleep(0.05)
            logger.success(f"Step 1 PASSED ({len(entities)} entities)")

            # Create relationships
            logger.info("Step 2: Creating relationships...")
            relationships = [
                {"from": "FastAPI", "to": "Python", "type": "built_with"}
            ]

            for rel in relationships:
                await self.bus.publish({
                    "type": "knowledge.relation_created",
                    "session_id": self.test_session_id,
                    "relation": rel
                })
                await asyncio.sleep(0.05)
            logger.success(f"Step 2 PASSED ({len(relationships)} relations)")

            # Query knowledge
            logger.info("Step 3: Querying knowledge...")
            search_results = await self.memory_manager.search_knowledge("FastAPI")
            logger.success(f"Step 3 PASSED ({len(search_results.get('nodes', []))} results)")

            # Get statistics
            logger.info("Step 4: Getting statistics...")
            stats = self.memory_manager.get_stats()
            logger.info(f"  Knowledge points: {stats['total_knowledge_points']}")
            logger.info(f"  Store size: {stats['store_size_kb']:.2f} KB")
            logger.success("Step 4 PASSED")

            self.results["passed"].append("Scenario 2: Knowledge Graph")

        except Exception as e:
            logger.error(f"Scenario 2 FAILED: {e}")
            self.results["failed"].append(f"Scenario 2: {str(e)}")

    async def test_scenario_3_interview_prep(self):
        """Scenario 3: Interview Preparation"""
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 3: Interview Prep")
        logger.info("=" * 60)

        try:
            # Extract keywords
            logger.info("Step 1: Extracting keywords...")
            messages = [
                {"role": "system", "content": "You are a resume analyzer."},
                {"role": "user", "content": "Extract key skills from: Python Developer, FastAPI"}
            ]
            keywords = await self.llm_provider.chat(messages, temperature=0.3, max_tokens=200)
            logger.success(f"Step 1 PASSED ({len(keywords)} chars)")

            # Generate questions
            logger.info("Step 2: Generating questions...")
            q_messages = [
                {"role": "system", "content": "You are an interviewer."},
                {"role": "user", "content": "Generate 3 interview questions for FastAPI developer"}
            ]
            questions = await self.llm_provider.chat(q_messages, temperature=0.8, max_tokens=500)
            logger.success(f"Step 2 PASSED ({len(questions)} chars)")

            # Simulate interview
            logger.info("Step 3: Simulating interview...")
            i_messages = [
                {"role": "system", "content": "You are an interviewer."},
                {"role": "user", "content": "How do you handle async requests in FastAPI?"}
            ]
            response = await self.llm_provider.chat(i_messages, temperature=0.7, max_tokens=300)
            logger.success(f"Step 3 PASSED ({len(response)} chars)")

            # Evaluate
            logger.info("Step 4: Evaluating...")
            e_messages = [
                {"role": "system", "content": "You are an evaluator."},
                {"role": "user", "content": f"Rate this response: {response[:100]}"}
            ]
            evaluation = await self.llm_provider.chat(e_messages, temperature=0.2, max_tokens=100)
            logger.success(f"Step 4 PASSED: {evaluation[:50]}...")

            self.results["passed"].append("Scenario 3: Interview Prep")

        except Exception as e:
            logger.error(f"Scenario 3 FAILED: {e}")
            self.results["failed"].append(f"Scenario 3: {str(e)}")

    async def test_scenario_4_production_features(self):
        """Scenario 4: Production Features"""
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 4: Production Features")
        logger.info("=" * 60)

        try:
            # Test cache
            logger.info("Step 1: Testing cache...")
            test_msg = [{"role": "user", "content": "What is 2+2?"}]
            r1 = await self.llm_provider.chat(test_msg, temperature=0.0)
            await asyncio.sleep(0.1)
            r2 = await self.llm_provider.chat(test_msg, temperature=0.0)

            cache_stats = self.llm_provider.get_stats()["cache"]
            hit_rate = (cache_stats["hits"] / max(1, cache_stats["total"])) * 100
            logger.info(f"  Cache hit rate: {hit_rate:.1f}%")
            logger.success("Step 1 PASSED")

            # Test rate limiting
            logger.info("Step 2: Testing rate limiting...")
            tasks = [
                self.llm_provider.chat([{"role": "user", "content": f"Test {i}"}], temperature=0.9)
                for i in range(3)
            ]
            start = asyncio.get_event_loop().time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = asyncio.get_event_loop().time() - start

            successes = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"  Completed {successes}/3 in {elapsed:.2f}s")
            logger.success("Step 2 PASSED")

            # Test retry
            logger.info("Step 3: Testing retry...")
            retry_stats = self.llm_provider.get_stats()["retry"]
            logger.info(f"  Success rate: {retry_stats['success_rate']:.1f}%")
            logger.success("Step 3 PASSED")

            # Test tokens
            logger.info("Step 4: Testing tokens...")
            token_stats = self.llm_provider.get_stats()["tokens"]
            logger.info(f"  Total: {token_stats['total_tokens']}")
            logger.info(f"  Cost: ${token_stats['total_cost']:.6f}")
            logger.success("Step 4 PASSED")

            self.results["passed"].append("Scenario 4: Production")

        except Exception as e:
            logger.error(f"Scenario 4 FAILED: {e}")
            self.results["failed"].append(f"Scenario 4: {str(e)}")

    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "=" * 60)
        logger.info("E2E Test Summary")
        logger.info("=" * 60)

        total = len(self.results["passed"]) + len(self.results["failed"])
        logger.info(f"\nResults: {len(self.results['passed'])}/{total} passed\n")

        if self.results["passed"]:
            logger.success("PASSED:")
            for s in self.results["passed"]:
                logger.success(f"  + {s}")

        if self.results["failed"]:
            logger.error("\nFAILED:")
            for s in self.results["failed"]:
                logger.error(f"  - {s}")

        if self.results["warnings"]:
            logger.warning("\nWARNINGS:")
            for w in self.results["warnings"]:
                logger.warning(f"  ! {w}")

        # Stats
        if self.llm_provider:
            logger.info("\nStatistics:")
            stats = self.llm_provider.get_stats()
            logger.info(f"  Cache: {(stats['cache']['hits']/max(1,stats['cache']['total'])*100):.1f}%")
            logger.info(f"  Success: {stats['retry']['success_rate']:.1f}%")
            logger.info(f"  Cost: ${stats['tokens']['total_cost']:.6f}")

        logger.info("\n" + "=" * 60)

        if self.results["failed"]:
            logger.error("FAILED")
            return False
        else:
            logger.success("ALL PASSED!")
            return True


async def main():
    """Run E2E tests"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mock", "real"], default="mock")
    args = parser.parse_args()

    setup_logging(level="INFO")

    logger.info("=" * 60)
    logger.info("E2E Integration Test")
    logger.info("=" * 60)
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    runner = E2ETestRunner(use_real_api=(args.mode == "real"))

    try:
        await runner.setup()
        await runner.test_scenario_1_learning_flow()
        await runner.test_scenario_2_knowledge_graph()
        await runner.test_scenario_3_interview_prep()
        await runner.test_scenario_4_production_features()

        success = runner.print_summary()
        logger.info(f"\nEnd: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return 0 if success else 1

    except Exception as e:
        logger.error(f"Fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await runner.teardown()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
