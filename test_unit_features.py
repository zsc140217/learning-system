"""
Test Production Features - Unit Tests (No API Key Required)

Tests internal mechanisms:
- Rate limiter logic
- Cache behavior
- Token estimation
- Cost calculation
"""
import asyncio
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "mcp-server"))

from src.utils.logging import setup_logging
from src.utils.rate_limiter import RateLimiter
from src.utils.llm_cache import LLMCache
from src.utils.retry import retry_with_backoff, _should_retry
from loguru import logger


async def test_rate_limiter():
    """Test rate limiter logic"""
    print("\n=== Test 1: Rate Limiter ===")

    limiter = RateLimiter(max_requests=3, time_window=2.0)

    # First 3 requests should pass immediately
    start = asyncio.get_event_loop().time()
    for i in range(3):
        await limiter.acquire()
        print(f"Request {i+1} acquired")

    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 0.5, "First 3 requests should be immediate"
    print(f"First 3 requests: {elapsed:.2f}s ✅")

    # 4th request should wait ~2 seconds
    print("4th request (should wait)...")
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed >= 1.5, "4th request should wait"
    print(f"4th request waited: {elapsed:.2f}s ✅")

    # Get stats
    stats = limiter.get_stats()
    print(f"Stats: {stats}")
    print("✅ Rate limiter test passed")


async def test_cache():
    """Test cache behavior"""
    print("\n=== Test 2: LLM Cache ===")

    cache = LLMCache(ttl_seconds=60, max_size=100)

    messages = [{"role": "user", "content": "Hello"}]
    model = "deepseek-chat"
    temperature = 0.7

    # Cache miss
    result = cache.get(messages, model, temperature)
    assert result is None, "Should be cache miss"
    print("Cache miss ✅")

    # Set cache
    cache.set(messages, model, temperature, "Hello, world!")
    print("Cache set ✅")

    # Cache hit
    result = cache.get(messages, model, temperature)
    assert result == "Hello, world!", "Should be cache hit"
    print("Cache hit ✅")

    # Different temperature = different key
    result = cache.get(messages, model, 0.8)
    assert result is None, "Different temperature should miss"
    print("Different temperature cache miss ✅")

    # Get stats
    stats = cache.get_stats()
    print(f"Stats: {stats}")
    assert stats["hits"] == 1
    assert stats["misses"] == 2
    assert stats["hit_rate"] == 1/3
    print("✅ Cache test passed")


async def test_cache_expiration():
    """Test cache expiration"""
    print("\n=== Test 3: Cache Expiration ===")

    cache = LLMCache(ttl_seconds=1, max_size=100)  # 1 second TTL

    messages = [{"role": "user", "content": "Test"}]
    cache.set(messages, "model", 0.7, "Response")

    # Should hit immediately
    result = cache.get(messages, "model", 0.7)
    assert result == "Response"
    print("Immediate hit ✅")

    # Wait for expiration
    print("Waiting 1.5 seconds for expiration...")
    await asyncio.sleep(1.5)

    # Should miss after expiration
    result = cache.get(messages, "model", 0.7)
    assert result is None
    print("Expired cache miss ✅")
    print("✅ Cache expiration test passed")


async def test_retry_error_detection():
    """Test retry error classification"""
    print("\n=== Test 4: Retry Error Detection ===")

    # Retryable errors
    retryable_errors = [
        Exception("HTTP 429 Too Many Requests"),
        Exception("HTTP 500 Internal Server Error"),
        Exception("HTTP 503 Service Unavailable"),
        Exception("Connection timeout"),
        Exception("Network unreachable")
    ]

    for error in retryable_errors:
        assert _should_retry(error), f"Should retry: {error}"
        print(f"✅ Retryable: {error}")

    # Non-retryable errors
    non_retryable_errors = [
        Exception("HTTP 400 Bad Request"),
        Exception("HTTP 401 Unauthorized"),
        Exception("HTTP 403 Forbidden"),
        Exception("HTTP 404 Not Found")
    ]

    for error in non_retryable_errors:
        assert not _should_retry(error), f"Should NOT retry: {error}"
        print(f"❌ Non-retryable: {error}")

    print("✅ Error detection test passed")


async def test_retry_backoff():
    """Test exponential backoff"""
    print("\n=== Test 5: Retry with Backoff ===")

    attempt_count = 0

    async def failing_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception("Connection timeout")  # Retryable error
        return "Success"

    start = asyncio.get_event_loop().time()
    result = await retry_with_backoff(
        failing_function,
        max_retries=3,
        base_delay=0.5,
        jitter=False
    )
    elapsed = asyncio.get_event_loop().time() - start

    assert result == "Success"
    assert attempt_count == 3
    # Should have delays: 0.5s + 1.0s = 1.5s
    assert elapsed >= 1.4, f"Expected ~1.5s, got {elapsed:.2f}s"
    print(f"Retried {attempt_count} times in {elapsed:.2f}s ✅")
    print("✅ Retry backoff test passed")


async def test_token_estimation():
    """Test token estimation logic"""
    print("\n=== Test 6: Token Estimation ===")

    from src.llm.deepseek_provider import DeepSeekProvider

    config = {
        "api_key": "fake",
        "model": "deepseek-chat"
    }

    provider = DeepSeekProvider(config)

    # Test cases
    test_cases = [
        ([{"role": "user", "content": "Hello"}], 1),  # ~1 token
        ([{"role": "user", "content": "This is a test message"}], 6),  # ~6 tokens
        ([{"role": "user", "content": "A" * 100}], 25),  # 100 chars = ~25 tokens
    ]

    for messages, expected_range in test_cases:
        tokens = provider._estimate_tokens(messages)
        print(f"Messages: {messages[0]['content'][:30]}... -> {tokens} tokens")
        # Allow some variance
        assert tokens >= expected_range - 5 and tokens <= expected_range + 5

    print("✅ Token estimation test passed")


async def test_cost_calculation():
    """Test cost calculation"""
    print("\n=== Test 7: Cost Calculation ===")

    from src.llm.deepseek_provider import DeepSeekProvider

    config = {
        "api_key": "fake",
        "model": "deepseek-chat"
    }

    provider = DeepSeekProvider(config)

    # Test cases
    test_cases = [
        (1000, 1000, 0.00042),     # 1K tokens: $0.14/1M * 1K + $0.28/1M * 1K
        (10000, 10000, 0.0042),    # 10K tokens
        (100000, 100000, 0.042),   # 100K tokens
    ]

    for prompt_tokens, completion_tokens, expected_cost in test_cases:
        cost = provider._calculate_cost(prompt_tokens, completion_tokens)
        print(f"{prompt_tokens} + {completion_tokens} tokens -> ${cost:.6f}")
        assert abs(cost - expected_cost) < 0.00001

    print("✅ Cost calculation test passed")


async def main():
    """Run all tests"""
    # Setup logging
    setup_logging(level="INFO")

    print("=" * 60)
    print("Production Features - Unit Tests")
    print("=" * 60)

    # Run tests
    await test_rate_limiter()
    await test_cache()
    await test_cache_expiration()
    await test_retry_error_detection()
    await test_retry_backoff()
    await test_token_estimation()
    await test_cost_calculation()

    print("\n" + "=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
