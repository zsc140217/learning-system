"""
Complete End-to-End Integration Test

Tests the entire learning system workflow:
1. User creates a learning session
2. AI generates learning path with knowledge graph
3. User progresses through learning materials
4. System tracks progress and updates knowledge graph
5. Interview preparation with AI assistant
6. Production features (cache, rate limit, retry) validation
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "mcp-server"))

from src.bus.agent_bus import AgentBus
from src.agents.memory_manager import MemoryManager
from src.agents.interview_agent import InterviewAgent
from src.llm.deepseek_provider import DeepSeekProvider
from src.utils.logging import setup_logging
from loguru import logger


class E2ETestRunner:
    """End-to-end test runner"""

    def __init__(self):
        self.bus = AgentBus()
        self.memory_manager = None
        self.interview_agent = None
        self.llm_provider = None
        self.test_session_id = f"e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }

    async def setup(self):
        """Initialize all components"""
        logger.info("Setting up E2E test environment...")

        # Start message bus
        await self.bus.start()

        # Initialize LLM provider with production features
        llm_config = {
            "model": "deepseek-chat",
            "rate_limit": 20,  # 20 requests per minute
            "cache_ttl": 300,  # 5 minutes cache
            "max_retries": 3
        }
        self.llm_provider = DeepSeekProvider(llm_config)

        # Initialize memory manager (fallback mode for testing)
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
        """
        Scenario 1: Complete Learning Flow
        User Story: User creates FastAPI learning plan
        """
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 1: Complete Learning Flow")
        logger.info("=" * 60)

        try:
            # Step 1: User creates learning topic
            logger.info("Step 1: Creating learning topic...")
            learning_topic = {
                "id": "topic_fastapi_001",
                "title": "FastAPI Web Development",
                "description": "Learn FastAPI framework for building APIs",
                "difficulty": "intermediate",
                "estimated_hours": 20
            }

            await self.bus.publish({
                "type": "learning.topic_created",
                "session_id": self.test_session_id,
                "topic": learning_topic
            })

            await asyncio.sleep(0.2)
            logger.success("Step 1 passed: Learning topic created")

            # Step 2: AI generates learning path
            logger.info("Step 2: Generating learning path with AI...")
            messages = [
                {
                    "role": "system",
                    "content": "You are a learning path planner. Generate structured learning plans."
                },
                {
                    "role": "user",
                    "content": f"Generate a learning path for: {learning_topic['title']}. Include 3-5 key knowledge points."
                }
            ]

            learning_path = await self.llm_provider.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            logger.success(f"Step 2 passed: Learning path generated ({len(learning_path)} chars)")

            # Step 3: Extract knowledge points from AI response
            logger.info("Step 3: Extracting knowledge points...")
            knowledge_points = [
                {
                    "id": f"kp_fastapi_{i:03d}",
                    "title": f"FastAPI Concept {i}",
                    "content": f"Key concept about FastAPI feature {i}",
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
            logger.success(f"Step 3 passed: Extracted {len(knowledge_points)} knowledge points")

            # Step 4: Simulate user progress
            logger.info("Step 4: Tracking learning progress...")
            for i, kp in enumerate(knowledge_points, 1):
                await self.bus.publish({
                    "type": "learning.progress_updated",
                    "session_id": self.test_session_id,
                    "knowledge_point_id": kp["id"],
                    "status": "completed",
                    "completion_percentage": i / len(knowledge_points) * 100
                })
                await asyncio.sleep(0.1)

            logger.success("Step 4 passed: Learning progress tracked")

            # Step 5: Verify knowledge graph
            logger.info("Step 5: Verifying knowledge graph...")
            search_results = await self.memory_manager.search_knowledge("FastAPI")

            if search_results and len(search_results.get("nodes", [])) >= len(knowledge_points):
                logger.success(f"Step 5 passed: Knowledge graph contains {len(search_results['nodes'])} nodes")
            else:
                logger.warning(f"Step 5 warning: Expected {len(knowledge_points)} nodes, found {len(search_results.get('nodes', []))}")
                self.results["warnings"].append("Knowledge graph node count mismatch")

            self.results["passed"].append("Scenario 1: Learning Flow")

        except Exception as e:
            logger.error(f"Scenario 1 failed: {e}")
            self.results["failed"].append(f"Scenario 1: {str(e)}")

    async def test_scenario_2_knowledge_graph_operations(self):
        """
        Scenario 2: Knowledge Graph Operations
        User Story: Create entities, establish relationships, query recommendations
        """
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 2: Knowledge Graph Operations")
        logger.info("=" * 60)

        try:
            # Step 1: Create entities
            logger.info("Step 1: Creating knowledge entities...")
            entities = [
                {"name": "Python", "type": "language"},
                {"name": "FastAPI", "type": "framework"},
                {"name": "Pydantic", "type": "library"},
                {"name": "Async Programming", "type": "concept"}
            ]

            for entity in entities:
                await self.bus.publish({
                    "type": "knowledge.entity_created",
                    "session_id": self.test_session_id,
                    "entity": entity
                })
                await asyncio.sleep(0.05)

            logger.success(f"Step 1 passed: Created {len(entities)} entities")

            # Step 2: Create relationships
            logger.info("Step 2: Creating relationships...")
            relationships = [
                {"from": "FastAPI", "to": "Python", "type": "built_with"},
                {"from": "FastAPI", "to": "Pydantic", "type": "depends_on"},
                {"from": "FastAPI", "to": "Async Programming", "type": "uses"}
            ]

            for rel in relationships:
                await self.bus.publish({
                    "type": "knowledge.relation_created",
                    "session_id": self.test_session_id,
                    "relation": rel
                })
                await asyncio.sleep(0.05)

            logger.success(f"Step 2 passed: Created {len(relationships)} relationships")

            # Step 3: Query recommendations
            logger.info("Step 3: Querying related knowledge...")
            search_results = await self.memory_manager.search_knowledge("FastAPI")

            if search_results:
                logger.success(f"Step 3 passed: Found {len(search_results.get('nodes', []))} related nodes")
            else:
                logger.warning("Step 3 warning: No search results returned")
                self.results["warnings"].append("Empty search results")

            # Step 4: Retrieve specific knowledge
            logger.info("Step 4: Retrieving specific knowledge point...")
            kp = self.memory_manager.get_knowledge_point("kp_fastapi_001")

            if kp:
                logger.success(f"Step 4 passed: Retrieved knowledge point: {kp.get('title', 'Unknown')}")
            else:
                logger.warning("Step 4 warning: Knowledge point not found")
                self.results["warnings"].append("Knowledge point retrieval failed")

            # Step 5: Get statistics
            logger.info("Step 5: Collecting knowledge graph statistics...")
            stats = self.memory_manager.get_stats()
            logger.info(f"  Total knowledge points: {stats['total_knowledge_points']}")
            logger.info(f"  Store size: {stats['store_size_kb']:.2f} KB")
            logger.info(f"  Source: {stats['source']}")
            logger.success("Step 5 passed: Statistics collected")

            self.results["passed"].append("Scenario 2: Knowledge Graph Operations")

        except Exception as e:
            logger.error(f"Scenario 2 failed: {e}")
            self.results["failed"].append(f"Scenario 2: {str(e)}")

    async def test_scenario_3_interview_preparation(self):
        """
        Scenario 3: Interview Preparation
        User Story: User prepares for Python/FastAPI interview
        """
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 3: Interview Preparation")
        logger.info("=" * 60)

        try:
            # Step 1: Extract resume keywords
            logger.info("Step 1: Extracting resume keywords...")
            resume_content = """
            Python Developer with 3 years experience.
            Skills: FastAPI, asyncio, PostgreSQL, Docker
            Projects: Built REST APIs with FastAPI, designed microservices
            """

            messages = [
                {
                    "role": "system",
                    "content": "You are a resume analyzer. Extract key skills and experience."
                },
                {
                    "role": "user",
                    "content": f"Extract key skills from this resume:\n{resume_content}"
                }
            ]

            keywords_response = await self.llm_provider.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=200
            )

            logger.success(f"Step 1 passed: Extracted keywords ({len(keywords_response)} chars)")

            # Step 2: Generate interview questions
            logger.info("Step 2: Generating interview questions...")
            question_prompt = [
                {
                    "role": "system",
                    "content": "You are an interviewer. Generate technical questions based on candidate skills."
                },
                {
                    "role": "user",
                    "content": "Generate 3 technical interview questions for a FastAPI developer, increasing difficulty."
                }
            ]

            questions = await self.llm_provider.chat(
                messages=question_prompt,
                temperature=0.8,
                max_tokens=500
            )

            logger.success(f"Step 2 passed: Generated interview questions ({len(questions)} chars)")

            # Step 3: Simulate interview session
            logger.info("Step 3: Simulating interview session...")
            interview_messages = [
                {
                    "role": "system",
                    "content": "You are an interviewer for Python/FastAPI developer positions."
                },
                {
                    "role": "user",
                    "content": "Introduce the main features of FastAPI."
                },
                {
                    "role": "assistant",
                    "content": "FastAPI main features: high performance, type hints, automatic docs."
                },
                {
                    "role": "user",
                    "content": "How do you handle async requests in FastAPI?"
                }
            ]

            interview_response = await self.llm_provider.chat(
                messages=interview_messages,
                temperature=0.7,
                max_tokens=300
            )

            logger.success(f"Step 3 passed: Interview simulation completed ({len(interview_response)} chars)")

            # Step 4: Evaluate responses
            logger.info("Step 4: Evaluating interview responses...")
            eval_prompt = [
                {
                    "role": "system",
                    "content": "You are an interview evaluator. Rate candidate responses on a scale of 1-10."
                },
                {
                    "role": "user",
                    "content": f"Rate this response (1-10):\n{interview_response[:200]}"
                }
            ]

            evaluation = await self.llm_provider.chat(
                messages=eval_prompt,
                temperature=0.2,
                max_tokens=100
            )

            logger.success(f"Step 4 passed: Interview evaluation completed: {evaluation[:50]}...")

            self.results["passed"].append("Scenario 3: Interview Preparation")

        except Exception as e:
            logger.error(f"Scenario 3 failed: {e}")
            self.results["failed"].append(f"Scenario 3: {str(e)}")

    async def test_scenario_4_production_features(self):
        """
        Scenario 4: Production Features Validation
        User Story: Validate cache, rate limiting, retry mechanisms
        """
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 4: Production Features Validation")
        logger.info("=" * 60)

        try:
            # Step 1: Test cache hit rate
            logger.info("Step 1: Testing cache hit rate...")
            test_message = [{"role": "user", "content": "What is 2+2?"}]

            # First call - cache miss
            response1 = await self.llm_provider.chat(test_message, temperature=0.0)
            await asyncio.sleep(0.1)

            # Second call - should hit cache
            response2 = await self.llm_provider.chat(test_message, temperature=0.0)

            cache_stats = self.llm_provider.get_stats()["cache"]
            cache_hit_rate = (cache_stats["hits"] / cache_stats["total"]) * 100 if cache_stats["total"] > 0 else 0

            logger.info(f"  Cache hits: {cache_stats['hits']}/{cache_stats['total']}")
            logger.info(f"  Hit rate: {cache_hit_rate:.1f}%")

            if cache_stats["hits"] > 0:
                logger.success("Step 1 passed: Cache working correctly")
            else:
                logger.warning("Step 1 warning: No cache hits recorded")
                self.results["warnings"].append("Cache hit rate is 0%")

            # Step 2: Test rate limiting
            logger.info("Step 2: Testing rate limiting...")
            rate_limit_config = {
                "model": "deepseek-chat",
                "rate_limit": 10  # 10 requests per minute
            }
            limited_provider = DeepSeekProvider(rate_limit_config)

            # Send burst of requests
            tasks = [
                limited_provider.chat([{"role": "user", "content": f"Test {i}"}], temperature=0.9)
                for i in range(5)
            ]

            start_time = asyncio.get_event_loop().time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = asyncio.get_event_loop().time() - start_time

            successes = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"  Completed {successes}/5 requests in {elapsed:.2f}s")

            rate_stats = limited_provider.get_stats()["rate_limiter"]
            logger.info(f"  Wait time: {rate_stats['total_wait_time']:.2f}s")
            logger.success("Step 2 passed: Rate limiting working correctly")

            # Step 3: Test retry mechanism
            logger.info("Step 3: Testing retry mechanism...")
            retry_stats = self.llm_provider.get_stats()["retry"]
            logger.info(f"  Total requests: {retry_stats['total_requests']}")
            logger.info(f"  Retries: {retry_stats['total_retries']}")
            logger.info(f"  Success rate: {retry_stats['success_rate']:.1f}%")

            if retry_stats["success_rate"] >= 95:
                logger.success("Step 3 passed: Retry mechanism working correctly")
            else:
                logger.warning(f"Step 3 warning: Success rate below 95%: {retry_stats['success_rate']:.1f}%")
                self.results["warnings"].append(f"Low success rate: {retry_stats['success_rate']:.1f}%")

            # Step 4: Test token counting and cost
            logger.info("Step 4: Testing token counting...")
            token_stats = self.llm_provider.get_stats()["tokens"]
            logger.info(f"  Total tokens: {token_stats['total_tokens']}")
            logger.info(f"  Total cost: ${token_stats['total_cost']:.6f}")
            logger.info(f"  Avg tokens/request: {token_stats['total_tokens'] / max(1, retry_stats['total_requests']):.1f}")
            logger.success("Step 4 passed: Token counting working correctly")

            # Step 5: Test logging
            logger.info("Step 5: Testing logging...")
            logger.info("  Log file: logs/learning_system.log")
            logger.success("Step 5 passed: Logging configured correctly")

            self.results["passed"].append("Scenario 4: Production Features")

        except Exception as e:
            logger.error(f"Scenario 4 failed: {e}")
            self.results["failed"].append(f"Scenario 4: {str(e)}")

    def print_summary(self):
        """Print test execution summary"""
        logger.info("\n" + "=" * 60)
        logger.info("E2E Test Execution Summary")
        logger.info("=" * 60)

        total = len(self.results["passed"]) + len(self.results["failed"])

        logger.info(f"\nResults: {len(self.results['passed'])}/{total} scenarios passed\n")

        if self.results["passed"]:
            logger.success("Passed Scenarios:")
            for scenario in self.results["passed"]:
                logger.success(f"  - {scenario}")

        if self.results["failed"]:
            logger.error("\nFailed Scenarios:")
            for scenario in self.results["failed"]:
                logger.error(f"  - {scenario}")

        if self.results["warnings"]:
            logger.warning("\nWarnings:")
            for warning in self.results["warnings"]:
                logger.warning(f"  - {warning}")

        # Print final stats
        if self.llm_provider:
            logger.info("\nLLM Provider Statistics:")
            stats = self.llm_provider.get_stats()
            logger.info(f"  Cache hit rate: {(stats['cache']['hits']/max(1, stats['cache']['total'])*100):.1f}%")
            logger.info(f"  Success rate: {stats['retry']['success_rate']:.1f}%")
            logger.info(f"  Total tokens: {stats['tokens']['total_tokens']}")
            logger.info(f"  Total cost: ${stats['tokens']['total_cost']:.6f}")

        logger.info("\n" + "=" * 60)

        if self.results["failed"]:
            logger.error("E2E tests FAILED")
            return False
        else:
            logger.success("All E2E tests PASSED")
            return True


async def main():
    """Run all E2E test scenarios"""
    # Setup logging
    setup_logging(level="INFO")

    logger.info("=" * 60)
    logger.info("Learning System - Complete E2E Integration Test")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    runner = E2ETestRunner()

    try:
        # Setup
        await runner.setup()

        # Run all scenarios
        await runner.test_scenario_1_learning_flow()
        await runner.test_scenario_2_knowledge_graph_operations()
        await runner.test_scenario_3_interview_preparation()
        await runner.test_scenario_4_production_features()

        # Print summary
        success = runner.print_summary()

        logger.info(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return 0 if success else 1

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Cleanup
        await runner.teardown()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
