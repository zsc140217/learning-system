"""
Rate Limiter for API calls

Implements Token Bucket algorithm to prevent API rate limit errors.
"""
import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger


class RateLimiter:
    """
    Token Bucket Rate Limiter

    Prevents exceeding API rate limits by throttling requests.

    Example:
        limiter = RateLimiter(max_requests=60, time_window=60.0)

        async def make_request():
            await limiter.acquire()
            # Make API call

    DeepSeek API limits:
    - Free tier: 60 requests/minute
    - Pro tier: 300 requests/minute
    """

    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = asyncio.Lock()

        logger.info(
            f"RateLimiter initialized: {max_requests} req/{time_window}s"
        )

    async def acquire(self) -> None:
        """
        Acquire permission to make a request

        Blocks if rate limit would be exceeded, waits until a slot is available.
        """
        async with self._lock:
            now = datetime.now()

            # Remove expired requests
            cutoff = now - timedelta(seconds=self.time_window)
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            # Check if rate limit exceeded
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest = self.requests[0]
                wait_until = oldest + timedelta(seconds=self.time_window)
                wait_seconds = (wait_until - now).total_seconds()

                logger.warning(
                    f"Rate limit reached ({len(self.requests)}/{self.max_requests}), "
                    f"waiting {wait_seconds:.2f}s"
                )

                await asyncio.sleep(wait_seconds)

                # Remove expired after waiting
                now = datetime.now()
                cutoff = now - timedelta(seconds=self.time_window)
                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()

            # Record this request
            self.requests.append(now)

            logger.debug(
                f"Request acquired: {len(self.requests)}/{self.max_requests} slots used"
            )

    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics

        Returns:
            Dict with current usage stats
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.time_window)

        # Count active requests
        active = sum(1 for req in self.requests if req > cutoff)

        return {
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "active_requests": active,
            "available_slots": self.max_requests - active,
            "utilization": active / self.max_requests if self.max_requests > 0 else 0
        }


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive Rate Limiter that adjusts based on API responses

    Automatically backs off when receiving 429 errors,
    and gradually increases rate when successful.
    """

    def __init__(
        self,
        initial_max_requests: int,
        time_window: float,
        min_requests: int = 10,
        max_requests_ceiling: int = 300
    ):
        """
        Initialize adaptive rate limiter

        Args:
            initial_max_requests: Starting max requests
            time_window: Time window in seconds
            min_requests: Minimum requests (safety floor)
            max_requests_ceiling: Maximum requests (hard ceiling)
        """
        super().__init__(initial_max_requests, time_window)
        self.min_requests = min_requests
        self.max_requests_ceiling = max_requests_ceiling
        self.consecutive_successes = 0
        self.consecutive_failures = 0

    def report_success(self) -> None:
        """Report successful API call - gradually increase rate"""
        self.consecutive_successes += 1
        self.consecutive_failures = 0

        # Increase rate after 10 consecutive successes
        if self.consecutive_successes >= 10:
            old_max = self.max_requests
            self.max_requests = min(
                int(self.max_requests * 1.1),
                self.max_requests_ceiling
            )

            if self.max_requests != old_max:
                logger.info(
                    f"Rate limit increased: {old_max} -> {self.max_requests} req/{self.time_window}s"
                )

            self.consecutive_successes = 0

    def report_rate_limit_error(self) -> None:
        """Report 429 rate limit error - immediately reduce rate"""
        self.consecutive_failures += 1
        self.consecutive_successes = 0

        old_max = self.max_requests
        self.max_requests = max(
            int(self.max_requests * 0.5),
            self.min_requests
        )

        logger.warning(
            f"Rate limit error detected! Reduced: {old_max} -> {self.max_requests} req/{self.time_window}s"
        )
