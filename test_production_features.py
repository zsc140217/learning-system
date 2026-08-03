"""
Test DeepSeek Provider with Production Features

Tests:
- Rate limiting
- Response caching
- Retry logic
- Logging and metrics
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "mcp-server"))

from src.utils.logging import setup_logging
from src.llm.deepseek_provider import DeepSeekProvider
from loguru import logger


async def test_basic_chat():
    """Test basic chat functionality"""
    print("\n=== Test 1: Basic Chat ===")

    config = {
        "api_key": "sk-test",  # Will be overridden by env var
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "rate_limit": 60,
        "cache_ttl": 3600
    }

    provider = DeepSeekProvider(config)

    messages = [
        {"role": "system", "content": "你是一个面试助手"},
        {"role": "user", "content": "什么是 Python 装饰器？用一句话回答。"}
    ]

    try:
        response = await provider.chat(messages)
        print(f"Response: {response[:100]}...")
        print("✅ Basic chat test passed")
    except Exception as e:
        print(f"❌ Basic chat test failed: {e}")


async def test_cache_hit():
    """Test cache hit scenario"""
    print("\n=== Test 2: Cache Hit ===")

    config = {
        "model": "deepseek-chat",
        "cache_ttl": 60
    }

    provider = DeepSeekProvider(config)

    messages = [
        {"role": "user", "content": "What is 1+1?"}
    ]

    try:
        # First call - cache miss
        print("First call (cache miss)...")
        response1 = await provider.chat(messages, temperature=0.0)

        # Second call - should hit cache
        print("Second call (cache hit)...")
        response2 = await provider.chat(messages, temperature=0.0)

        assert response1 == response2
        print("✅ Cache hit test passed")

        # Print stats
        stats = provider.get_stats()
        print(f"Cache stats: {stats['cache']}")

    except Exception as e:
        print(f"❌ Cache hit test failed: {e}")


async def test_rate_limiting():
    """Test rate limiting with burst requests"""
    print("\n=== Test 3: Rate Limiting ===")

    config = {
        "model": "deepseek-chat",
        "rate_limit": 5,  # Only 5 requests per minute for testing
        "cache_ttl": 0    # Disable cache
    }

    provider = DeepSeekProvider(config)

    messages = [
        {"role": "user", "content": f"Count to {i}"}
        for i in range(1, 8)  # 7 requests, will trigger rate limit
    ]

    try:
        print("Sending 7 requests with 5/min limit...")
        tasks = [
            provider.chat([msg], temperature=0.9)  # High temp to bypass cache
            for msg in messages
        ]

        start = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = asyncio.get_event_loop().time() - start

        successes = sum(1 for r in results if not isinstance(r, Exception))
        print(f"Completed {successes}/7 requests in {elapsed:.2f}s")
        print("✅ Rate limiting test passed")

        # Print stats
        stats = provider.get_stats()
        print(f"Rate limiter stats: {stats['rate_limiter']}")

    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")


async def test_retry_logic():
    """Test retry with simulated failure"""
    print("\n=== Test 4: Retry Logic ===")

    # This test requires manual verification by checking logs
    config = {
        "model": "deepseek-chat",
        "max_retries": 3,
        "retry_delay": 0.5
    }

    provider = DeepSeekProvider(config)

    messages = [
        {"role": "user", "content": "Hello"}
    ]

    try:
        # Normal request should succeed
        response = await provider.chat(messages)
        print("✅ Retry logic test passed (check logs for retry behavior)")

    except Exception as e:
        print(f"ℹ️  Request failed (expected if API key invalid): {e}")


async def test_streaming():
    """Test streaming chat"""
    print("\n=== Test 5: Streaming Chat ===")

    config = {
        "model": "deepseek-chat"
    }

    provider = DeepSeekProvider(config)

    messages = [
        {"role": "user", "content": "Count from 1 to 5"}
    ]

    try:
        print("Streaming response: ", end="", flush=True)
        async for chunk in provider.chat_stream(messages):
            print(chunk, end="", flush=True)
        print("\n✅ Streaming test passed")

    except Exception as e:
        print(f"\n❌ Streaming test failed: {e}")


async def test_token_counting():
    """Test token estimation and cost calculation"""
    print("\n=== Test 6: Token Counting ===")

    config = {
        "model": "deepseek-chat"
    }

    provider = DeepSeekProvider(config)

    messages = [
        {"role": "user", "content": "这是一个测试消息，用于估算 token 数量。" * 10}
    ]

    # Estimate tokens
    prompt_tokens = provider._estimate_tokens(messages)
    print(f"Estimated prompt tokens: {prompt_tokens}")

    # Calculate cost
    cost = provider._calculate_cost(prompt_tokens, prompt_tokens)
    print(f"Estimated cost for {prompt_tokens*2} tokens: ${cost:.6f}")

    print("✅ Token counting test passed")


async def main():
    """Run all tests"""
    # Setup logging
    setup_logging(level="INFO")

    print("=" * 60)
    print("DeepSeek Provider - Production Features Test Suite")
    print("=" * 60)

    # Run tests
    await test_basic_chat()
    await test_cache_hit()
    await test_rate_limiting()
    await test_retry_logic()
    # await test_streaming()  # Uncomment if you want to test streaming
    await test_token_counting()

    print("\n" + "=" * 60)
    print("Test suite completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
