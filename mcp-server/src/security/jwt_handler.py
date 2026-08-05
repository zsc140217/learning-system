"""
JWT Handler for MRTR (Multi-Round Trip Request) implementation.

Provides JWT-based request state management with nonce-based replay attack prevention.
"""

import os
from datetime import datetime, timedelta, UTC
from typing import Any, Dict
from uuid import uuid4

import jwt
from loguru import logger

from .nonce_store import NonceStore


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


class JWTHandler:
    """
    JWT-based request state handler for dangerous operations.

    Implements the MRTR pattern:
    1. First request: generate JWT token with operation params
    2. Second request: verify JWT token and execute operation
    """

    def __init__(self, nonce_store: NonceStore, jwt_secret: str = None):
        """
        Initialize the JWT handler.

        Args:
            nonce_store: NonceStore instance for replay attack prevention
            jwt_secret: Secret key for JWT signing (defaults to env var or random)
        """
        self.nonce_store = nonce_store
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET") or uuid4().hex

        if not jwt_secret and not os.getenv("JWT_SECRET"):
            logger.warning(
                "JWT_SECRET not set, using random key. "
                "This means tokens won't survive server restarts!"
            )

    def generate_request_state(
        self,
        operation: str,
        params: Dict[str, Any],
        expiry_minutes: int = 5
    ) -> str:
        """
        Generate a JWT token for the first round of MRTR.

        Args:
            operation: The operation name (e.g., "delete_knowledge")
            params: The operation parameters
            expiry_minutes: Token expiry time (default: 5 minutes)

        Returns:
            JWT token string
        """
        nonce = uuid4().hex
        payload = {
            "operation": operation,
            "params": params,
            "exp": datetime.now(UTC) + timedelta(minutes=expiry_minutes),
            "iat": datetime.now(UTC),
            "nonce": nonce
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        logger.debug(
            f"Generated JWT for operation '{operation}' "
            f"(nonce: {nonce[:8]}..., expires in {expiry_minutes} minutes)"
        )

        return token

    def verify_request_state(self, token: str) -> Dict[str, Any]:
        """
        Verify a JWT token from the second round of MRTR.

        Args:
            token: The JWT token to verify

        Returns:
            Decoded payload with operation and params

        Raises:
            SecurityError: If token is invalid, expired, or nonce is reused
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is malformed
        """
        try:
            # Decode and verify signature
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"]
            )

            # Check nonce for replay attack
            nonce = payload.get("nonce")
            if not nonce:
                raise SecurityError("Token missing nonce field")

            if self.nonce_store.is_used(nonce):
                logger.warning(f"Replay attack detected! Nonce already used: {nonce[:8]}...")
                raise SecurityError("Nonce already used (replay attack detected)")

            # Mark nonce as used
            self.nonce_store.mark_used(nonce, expiry_minutes=10)

            logger.debug(f"JWT verified successfully for operation '{payload.get('operation')}'")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token: {e}")
            raise SecurityError(f"Invalid token: {e}")

    def verify_params_match(
        self,
        payload: Dict[str, Any],
        current_params: Dict[str, Any]
    ) -> bool:
        """
        Verify that the params in the JWT match the current request params.

        This prevents parameter tampering between the first and second round.

        Args:
            payload: Decoded JWT payload
            current_params: Current request parameters

        Returns:
            True if params match

        Raises:
            SecurityError: If params don't match
        """
        original_params = payload.get("params", {})

        if original_params != current_params:
            logger.warning(
                f"Parameter mismatch detected! "
                f"Original: {original_params}, Current: {current_params}"
            )
            raise SecurityError(
                "Parameters mismatch between first and second request. "
                "This may indicate a tampering attempt."
            )

        return True
