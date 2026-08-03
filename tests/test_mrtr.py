"""
Tests for MRTR (Multi-Round Trip Request) implementation.

Tests JWT generation, verification, nonce replay attack prevention,
and dangerous operation confirmation flow.
"""

import sys
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
import jwt as pyjwt

from src.security import JWTHandler, NonceStore
from src.security.jwt_handler import SecurityError


@pytest_asyncio.fixture
async def nonce_store():
    """Create and start a nonce store for testing."""
    store = NonceStore(cleanup_interval_seconds=1)
    await store.start()
    yield store
    await store.stop()


@pytest_asyncio.fixture
def jwt_handler(nonce_store):
    """Create a JWT handler with test secret."""
    return JWTHandler(nonce_store, jwt_secret="test_secret_key_123")


class TestNonceStore:
    """Test nonce store functionality."""

    @pytest.mark.asyncio
    async def test_nonce_marking_and_checking(self, nonce_store):
        """Test marking and checking nonces."""
        nonce = "test_nonce_001"

        # Initially not used
        assert not nonce_store.is_used(nonce)

        # Mark as used
        nonce_store.mark_used(nonce)

        # Now should be used
        assert nonce_store.is_used(nonce)

    @pytest.mark.asyncio
    async def test_nonce_expiry(self, nonce_store):
        """Test that nonces expire after the specified time."""
        nonce = "test_nonce_002"

        # Mark with 0.05 minute (3 seconds) expiry
        nonce_store.mark_used(nonce, expiry_minutes=0.05)
        assert nonce_store.is_used(nonce)

        # Wait for cleanup to run
        await asyncio.sleep(4)

        # Should be cleaned up now
        assert not nonce_store.is_used(nonce)

    @pytest.mark.asyncio
    async def test_nonce_store_stats(self, nonce_store):
        """Test nonce store statistics."""
        nonce_store.mark_used("nonce_1")
        nonce_store.mark_used("nonce_2")
        nonce_store.mark_used("nonce_3")

        stats = nonce_store.get_stats()
        assert stats["total_nonces"] == 3
        assert stats["cleanup_interval_seconds"] == 1


class TestJWTHandler:
    """Test JWT handler functionality."""

    def test_generate_request_state(self, jwt_handler):
        """Test JWT token generation."""
        operation = "delete_knowledge"
        params = {"knowledge_ids": ["k-001", "k-002"]}

        token = jwt_handler.generate_request_state(operation, params)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode without verification to check structure
        decoded = pyjwt.decode(token, options={"verify_signature": False})
        assert decoded["operation"] == operation
        assert decoded["params"] == params
        assert "nonce" in decoded
        assert "exp" in decoded
        assert "iat" in decoded

    def test_verify_request_state_success(self, jwt_handler, nonce_store):
        """Test successful JWT verification."""
        operation = "delete_project"
        params = {"project_id": "proj-001"}

        # Generate token
        token = jwt_handler.generate_request_state(operation, params)

        # Verify token
        payload = jwt_handler.verify_request_state(token)

        assert payload["operation"] == operation
        assert payload["params"] == params
        assert "nonce" in payload

        # Nonce should now be marked as used
        assert nonce_store.is_used(payload["nonce"])

    def test_verify_request_state_replay_attack(self, jwt_handler):
        """Test that replay attacks are prevented."""
        operation = "rebuild_index"
        params = {"index_type": "all"}

        # Generate and verify token once
        token = jwt_handler.generate_request_state(operation, params)
        jwt_handler.verify_request_state(token)

        # Try to use the same token again (replay attack)
        with pytest.raises(SecurityError, match="Nonce already used"):
            jwt_handler.verify_request_state(token)

    def test_verify_request_state_expired_token(self, jwt_handler):
        """Test that expired tokens are rejected."""
        # Generate token with very short expiry
        token = jwt_handler.generate_request_state(
            "delete_knowledge",
            {"knowledge_ids": ["k-001"]},
            expiry_minutes=-1  # Already expired
        )

        # Should raise ExpiredSignatureError
        with pytest.raises(pyjwt.ExpiredSignatureError):
            jwt_handler.verify_request_state(token)

    def test_verify_request_state_invalid_token(self, jwt_handler):
        """Test that invalid tokens are rejected."""
        # Completely invalid token
        with pytest.raises(SecurityError, match="Invalid token"):
            jwt_handler.verify_request_state("invalid_token_xyz")

    def test_verify_request_state_tampered_token(self, jwt_handler):
        """Test that tampered tokens are rejected."""
        # Generate valid token
        token = jwt_handler.generate_request_state(
            "delete_knowledge",
            {"knowledge_ids": ["k-001"]}
        )

        # Tamper with the token (change last character)
        tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")

        # Should fail verification
        with pytest.raises(SecurityError, match="Invalid token"):
            jwt_handler.verify_request_state(tampered_token)

    def test_verify_params_match_success(self, jwt_handler):
        """Test parameter matching validation."""
        params = {"knowledge_ids": ["k-001", "k-002"]}
        token = jwt_handler.generate_request_state("delete_knowledge", params)
        payload = jwt_handler.verify_request_state(token)

        # Should succeed with matching params
        assert jwt_handler.verify_params_match(payload, params)

    def test_verify_params_match_failure(self, jwt_handler):
        """Test that parameter tampering is detected."""
        original_params = {"knowledge_ids": ["k-001", "k-002"]}
        token = jwt_handler.generate_request_state("delete_knowledge", original_params)
        payload = jwt_handler.verify_request_state(token)

        # Try with different params
        tampered_params = {"knowledge_ids": ["k-999"]}

        with pytest.raises(SecurityError, match="Parameters mismatch"):
            jwt_handler.verify_params_match(payload, tampered_params)


class TestMRTRFlow:
    """Test complete MRTR flow."""

    @pytest.mark.asyncio
    async def test_complete_delete_knowledge_flow(self, jwt_handler):
        """Test the complete two-round flow for delete_knowledge."""
        knowledge_ids = ["k-001", "k-002", "k-003"]

        # Round 1: Generate request state
        token = jwt_handler.generate_request_state(
            operation="delete_knowledge",
            params={"knowledge_ids": knowledge_ids}
        )

        # Simulate user confirmation
        # Round 2: Verify and execute
        payload = jwt_handler.verify_request_state(token)

        # Verify params match
        jwt_handler.verify_params_match(
            payload,
            {"knowledge_ids": knowledge_ids}
        )

        # If we got here, verification succeeded
        assert payload["operation"] == "delete_knowledge"
        assert payload["params"]["knowledge_ids"] == knowledge_ids

    @pytest.mark.asyncio
    async def test_mrtr_flow_with_parameter_change(self, jwt_handler):
        """Test that changing parameters between rounds fails."""
        # Round 1: Generate token with original params
        original_ids = ["k-001", "k-002"]
        token = jwt_handler.generate_request_state(
            operation="delete_knowledge",
            params={"knowledge_ids": original_ids}
        )

        # Round 2: Try to verify with different params
        changed_ids = ["k-999"]  # Attacker changed the params

        payload = jwt_handler.verify_request_state(token)

        # Should fail parameter verification
        with pytest.raises(SecurityError, match="Parameters mismatch"):
            jwt_handler.verify_params_match(
                payload,
                {"knowledge_ids": changed_ids}
            )

    @pytest.mark.asyncio
    async def test_mrtr_flow_timeout(self, jwt_handler):
        """Test that expired tokens cannot be used."""
        # Generate token with very short expiry
        token = jwt_handler.generate_request_state(
            operation="delete_project",
            params={"project_id": "proj-001"},
            expiry_minutes=0.01  # 0.6 seconds
        )

        # Wait for token to expire
        await asyncio.sleep(1)

        # Should fail with expired token
        with pytest.raises(pyjwt.ExpiredSignatureError):
            jwt_handler.verify_request_state(token)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
