"""
Retry utilities with exponential backoff

Handles transient failures in API calls and network operations.
"""
import asyncio
from typing import Callable, Any, Optional, Type
from loguru import logger


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """
    Retry function with exponential backoff

    Delay sequence: 1s, 2s, 4s, 8s, ...

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Function result

    Raises:
        Exception: If all retries exhausted
    """
    import random

    for attempt in range(max_retries):
        try:
            return await func()

        except Exception as e:
            # Check if error is retryable
            if not _should_retry(e):
                logger.error(f"Non-retryable error: {e}")
                raise

            # Last attempt - don't retry
            if attempt == max_retries - 1:
                logger.error(
                    f"Max retries ({max_retries}) exceeded. Last error: {e}"
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(
                base_delay * (exponential_base ** attempt),
                max_delay
            )

            # Add jitter to prevent synchronized retries
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )

            await asyncio.sleep(delay)


def _should_retry(error: Exception) -> bool:
    """
    Determine if error is retryable

    Retryable errors:
    - HTTP 429 (Too Many Requests)
    - HTTP 500/502/503/504 (Server Errors)
    - Timeout errors
    - Connection errors

    Non-retryable errors:
    - HTTP 400 (Bad Request)
    - HTTP 401/403 (Authentication/Authorization)
    - HTTP 404 (Not Found)

    Args:
        error: Exception to check

    Returns:
        True if should retry, False otherwise
    """
    error_str = str(error).lower()

    # HTTP status codes
    retryable_codes = ["429", "500", "502", "503", "504"]
    non_retryable_codes = ["400", "401", "403", "404"]

    # Check for retryable status codes
    if any(code in error_str for code in retryable_codes):
        return True

    # Check for non-retryable status codes
    if any(code in error_str for code in non_retryable_codes):
        return False

    # Network-related errors
    network_errors = ["timeout", "connection", "network", "unreachable"]
    if any(err in error_str for err in network_errors):
        return True

    # Default: don't retry unknown errors
    return False


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[tuple] = None
    ):
        """
        Initialize retry configuration

        Args:
            max_retries: Maximum retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay cap
            exponential_base: Exponential backoff base
            jitter: Add random jitter
            retryable_exceptions: Tuple of exception types to retry
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (Exception,)


def retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry with exponential backoff

    Example:
        @retry(RetryConfig(max_retries=5, base_delay=2.0))
        async def fetch_data():
            # May fail transiently
            return await api_call()

    Args:
        config: Retry configuration

    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig()

    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=config.max_retries,
                base_delay=config.base_delay,
                max_delay=config.max_delay,
                exponential_base=config.exponential_base,
                jitter=config.jitter
            )
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit Breaker pattern for fault tolerance

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered

    Example:
        breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60.0
        )

        async def call_api():
            async with breaker:
                return await api.call()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_attempts: int = 1
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening
            timeout: Seconds before attempting recovery
            half_open_attempts: Successful attempts to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts

        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"

        logger.info(
            f"CircuitBreaker initialized: "
            f"threshold={failure_threshold}, timeout={timeout}s"
        )

    async def __aenter__(self):
        """Check circuit state before operation"""
        import time

        if self._state == "OPEN":
            # Check if timeout elapsed
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.timeout:
                    self._state = "HALF_OPEN"
                    self._success_count = 0
                    logger.info("Circuit breaker: OPEN -> HALF_OPEN")
                else:
                    raise Exception(
                        f"Circuit breaker OPEN. "
                        f"Retry in {self.timeout - elapsed:.1f}s"
                    )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Update circuit state after operation"""
        import time

        if exc_type is None:
            # Success
            self._record_success()
        else:
            # Failure
            self._record_failure()

        return False  # Don't suppress exception

    def _record_success(self):
        """Record successful operation"""
        if self._state == "HALF_OPEN":
            self._success_count += 1
            if self._success_count >= self.half_open_attempts:
                self._state = "CLOSED"
                self._failure_count = 0
                logger.info("Circuit breaker: HALF_OPEN -> CLOSED")
        elif self._state == "CLOSED":
            self._failure_count = 0

    def _record_failure(self):
        """Record failed operation"""
        import time

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == "HALF_OPEN":
            self._state = "OPEN"
            logger.warning("Circuit breaker: HALF_OPEN -> OPEN")

        elif self._state == "CLOSED":
            if self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                logger.warning(
                    f"Circuit breaker: CLOSED -> OPEN "
                    f"({self._failure_count} failures)"
                )

    def get_state(self) -> str:
        """Get current circuit state"""
        return self._state

    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold
        }
