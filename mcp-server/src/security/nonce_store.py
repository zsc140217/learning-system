"""
Nonce Store for preventing replay attacks.

Maintains an in-memory store of used nonces with automatic expiration.
"""

import asyncio
from datetime import datetime, timedelta, UTC
from typing import Dict
from loguru import logger


class NonceStore:
    """
    In-memory store for tracking used nonces to prevent replay attacks.

    Nonces are automatically cleaned up after expiration (default: 10 minutes).
    """

    def __init__(self, cleanup_interval_seconds: int = 60):
        """
        Initialize the nonce store.

        Args:
            cleanup_interval_seconds: How often to run cleanup (default: 60s)
        """
        self._used_nonces: Dict[str, datetime] = {}
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_task = None

    async def start(self):
        """Start the background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("NonceStore started")

    async def stop(self):
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("NonceStore stopped")

    def is_used(self, nonce: str) -> bool:
        """
        Check if a nonce has already been used.

        Args:
            nonce: The nonce to check

        Returns:
            True if the nonce has been used, False otherwise
        """
        return nonce in self._used_nonces

    def mark_used(self, nonce: str, expiry_minutes: int = 10):
        """
        Mark a nonce as used.

        Args:
            nonce: The nonce to mark as used
            expiry_minutes: How long to keep the nonce (default: 10 minutes)
        """
        expiry_time = datetime.now(UTC) + timedelta(minutes=expiry_minutes)
        self._used_nonces[nonce] = expiry_time
        logger.debug(f"Nonce marked as used: {nonce[:8]}... (expires at {expiry_time})")

    async def _cleanup_loop(self):
        """Background loop to clean up expired nonces."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in nonce cleanup loop: {e}")

    async def _cleanup_expired(self):
        """Remove expired nonces from the store."""
        now = datetime.now(UTC)
        expired = [nonce for nonce, expiry in self._used_nonces.items() if expiry < now]

        for nonce in expired:
            del self._used_nonces[nonce]

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired nonces")

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the nonce store.

        Returns:
            Dictionary with store statistics
        """
        return {
            "total_nonces": len(self._used_nonces),
            "cleanup_interval_seconds": self._cleanup_interval
        }
