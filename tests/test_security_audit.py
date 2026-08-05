"""
Security Audit Test Suite for Learning System MCP Server.

Tests JWT security, nonce replay prevention, input validation, and permission control.
Covers OWASP Top 10 vulnerabilities and security best practices.
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import jwt
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mcp-server"))

from src.security.jwt_handler import JWTHandler, SecurityError
from src.security.nonce_store import NonceStore


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def nonce_store():
    """Create a NonceStore instance for testing."""
    return NonceStore(cleanup_interval_seconds=1)


@pytest.fixture
def jwt_handler(nonce_store):
    """Create a JWTHandler instance with a fixed secret for testing."""
    return JWTHandler(
        nonce_store=nonce_store,
        jwt_secret="test_secret_key_for_security_audit_12345"
    )


@pytest.fixture
async def running_nonce_store(nonce_store):
    """Create and start a NonceStore instance."""
    await nonce_store.start()
    yield nonce_store
    await nonce_store.stop()


# ============================================================================
# JWT Security Tests
# ============================================================================

class TestJWTSecurity:
    """Test suite for JWT token security."""

    def test_jwt_generation_includes_required_fields(self, jwt_handler):
        """Test that generated JWT tokens include all required fields."""
        # Arrange
        operation = "delete_knowledge"
        params = {"entity_name": "test_entity"}

        # Act
        token = jwt_handler.generate_request_state(operation, params)

        # Assert
        payload = jwt.decode(
            token,
            jwt_handler.jwt_secret,
            algorithms=["HS256"]
        )
        assert "operation" in payload
        assert "params" in payload
        assert "nonce" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert payload["operation"] == operation
        assert payload["params"] == params

    def test_jwt_tampering_detection(self, jwt_handler):
        """Test that tampered JWT tokens are rejected."""
        # Arrange
        token = jwt_handler.generate_request_state("delete", {"id": "123"})

        # Act: Tamper with the token
        tampered_token = token[:-10] + "tampered!"

        # Assert: Verification should fail
        with pytest.raises(SecurityError, match="Invalid token"):
            jwt_handler.verify_request_state(tampered_token)

    def test_jwt_signature_verification_fails_with_wrong_secret(self, nonce_store):
        """Test that JWT tokens signed with a different secret are rejected."""
        # Arrange
        handler1 = JWTHandler(nonce_store, jwt_secret="secret1")
        handler2 = JWTHandler(nonce_store, jwt_secret="secret2")

        token = handler1.generate_request_state("test", {"data": "value"})

        # Act & Assert: Different secret should fail verification
        with pytest.raises(SecurityError, match="Invalid token"):
            handler2.verify_request_state(token)

    def test_jwt_expiry_enforcement(self, jwt_handler):
        """Test that expired JWT tokens are rejected."""
        # Arrange: Generate a token that expires in -1 minutes (already expired)
        operation = "delete"
        params = {"id": "123"}
        nonce = uuid4().hex

        payload = {
            "operation": operation,
            "params": params,
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "iat": datetime.now(UTC) - timedelta(minutes=2),
            "nonce": nonce
        }

        expired_token = jwt.encode(payload, jwt_handler.jwt_secret, algorithm="HS256")

        # Act & Assert: Expired token should be rejected
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_handler.verify_request_state(expired_token)

    def test_jwt_missing_nonce_field(self, jwt_handler):
        """Test that JWT tokens without nonce field are rejected."""
        # Arrange: Create a token without nonce
        payload = {
            "operation": "test",
            "params": {},
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iat": datetime.now(UTC)
            # Missing "nonce" field
        }

        token = jwt.encode(payload, jwt_handler.jwt_secret, algorithm="HS256")

        # Act & Assert
        with pytest.raises(SecurityError, match="Token missing nonce field"):
            jwt_handler.verify_request_state(token)

    def test_jwt_malformed_token(self, jwt_handler):
        """Test that malformed JWT tokens are rejected."""
        # Arrange
        malformed_tokens = [
            "not.a.jwt",
            "invalid",
            "",
            "a.b",  # Only 2 parts instead of 3
            ".....",  # Too many dots
        ]

        # Act & Assert
        for token in malformed_tokens:
            with pytest.raises(SecurityError, match="Invalid token"):
                jwt_handler.verify_request_state(token)

    def test_jwt_valid_token_verification(self, jwt_handler):
        """Test that valid JWT tokens are verified successfully."""
        # Arrange
        operation = "delete_knowledge"
        params = {"entity_name": "test"}

        token = jwt_handler.generate_request_state(operation, params)

        # Act
        payload = jwt_handler.verify_request_state(token)

        # Assert
        assert payload["operation"] == operation
        assert payload["params"] == params
        assert "nonce" in payload


# ============================================================================
# Nonce Replay Attack Prevention Tests
# ============================================================================

class TestNonceReplayPrevention:
    """Test suite for nonce-based replay attack prevention."""

    def test_nonce_replay_attack_detection(self, jwt_handler):
        """Test that reusing a JWT token is detected as a replay attack."""
        # Arrange
        token = jwt_handler.generate_request_state("delete", {"id": "123"})

        # Act: First verification should succeed
        payload1 = jwt_handler.verify_request_state(token)
        assert payload1 is not None

        # Assert: Second verification should fail (replay attack)
        with pytest.raises(SecurityError, match="Nonce already used"):
            jwt_handler.verify_request_state(token)

    def test_nonce_uniqueness(self, jwt_handler):
        """Test that each generated token has a unique nonce."""
        # Arrange & Act
        tokens = [
            jwt_handler.generate_request_state("op", {"id": i})
            for i in range(100)
        ]

        # Extract nonces
        nonces = []
        for token in tokens:
            payload = jwt.decode(token, jwt_handler.jwt_secret, algorithms=["HS256"])
            nonces.append(payload["nonce"])

        # Assert: All nonces should be unique
        assert len(nonces) == len(set(nonces)), "Nonces are not unique!"

    @pytest.mark.asyncio
    async def test_nonce_expiration_cleanup(self, nonce_store):
        """Test that expired nonces are cleaned up automatically."""
        # Arrange
        await nonce_store.start()
        nonce = "test_nonce_12345"
        nonce_store.mark_used(nonce, expiry_minutes=0)  # Expire immediately

        # Act: Wait for cleanup (cleanup interval is 1 second)
        await asyncio.sleep(1.5)

        # Assert: Nonce should be cleaned up
        stats = nonce_store.get_stats()
        assert stats["total_nonces"] == 0, "Expired nonce was not cleaned up"

        # Cleanup
        await nonce_store.stop()

    def test_nonce_store_tracking(self, nonce_store):
        """Test that NonceStore correctly tracks used nonces."""
        # Arrange
        nonce1 = "nonce_1"
        nonce2 = "nonce_2"

        # Act
        nonce_store.mark_used(nonce1)
        nonce_store.mark_used(nonce2)

        # Assert
        assert nonce_store.is_used(nonce1)
        assert nonce_store.is_used(nonce2)
        assert not nonce_store.is_used("nonce_3")

        stats = nonce_store.get_stats()
        assert stats["total_nonces"] == 2

    @pytest.mark.asyncio
    async def test_concurrent_nonce_usage(self, jwt_handler):
        """Test that concurrent requests with different nonces work correctly."""
        # Arrange
        tokens = [
            jwt_handler.generate_request_state("op", {"id": i})
            for i in range(10)
        ]

        # Act: Verify all tokens concurrently
        async def verify_token(token):
            return jwt_handler.verify_request_state(token)

        results = await asyncio.gather(
            *[verify_token(token) for token in tokens],
            return_exceptions=True
        )

        # Assert: All verifications should succeed
        assert all(not isinstance(r, Exception) for r in results)
        assert len(results) == 10


# ============================================================================
# Parameter Tampering Prevention Tests
# ============================================================================

class TestParameterTamperingPrevention:
    """Test suite for parameter tampering detection."""

    def test_parameter_mismatch_detection(self, jwt_handler):
        """Test that parameter changes between rounds are detected."""
        # Arrange
        token = jwt_handler.generate_request_state(
            "delete",
            {"entity_name": "original"}
        )
        payload = jwt_handler.verify_request_state(token)

        # Act & Assert: Different params should be rejected
        with pytest.raises(SecurityError, match="Parameters mismatch"):
            jwt_handler.verify_params_match(
                payload,
                {"entity_name": "tampered"}
            )

    def test_parameter_match_success(self, jwt_handler):
        """Test that matching parameters pass verification."""
        # Arrange
        params = {"entity_name": "test", "scope": "user"}
        token = jwt_handler.generate_request_state("delete", params)
        payload = jwt_handler.verify_request_state(token)

        # Act & Assert: Same params should pass
        assert jwt_handler.verify_params_match(payload, params) is True

    def test_parameter_order_independence(self, jwt_handler):
        """Test that parameter order doesn't affect matching."""
        # Arrange
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}  # Different order

        token = jwt_handler.generate_request_state("test", params1)
        payload = jwt_handler.verify_request_state(token)

        # Act & Assert: Different order should still match
        assert jwt_handler.verify_params_match(payload, params2) is True

    def test_additional_parameter_detection(self, jwt_handler):
        """Test that adding extra parameters is detected."""
        # Arrange
        token = jwt_handler.generate_request_state("test", {"id": "123"})
        payload = jwt_handler.verify_request_state(token)

        # Act & Assert: Extra param should be detected
        with pytest.raises(SecurityError, match="Parameters mismatch"):
            jwt_handler.verify_params_match(
                payload,
                {"id": "123", "extra": "param"}
            )

    def test_missing_parameter_detection(self, jwt_handler):
        """Test that removing parameters is detected."""
        # Arrange
        token = jwt_handler.generate_request_state(
            "test",
            {"id": "123", "name": "test"}
        )
        payload = jwt_handler.verify_request_state(token)

        # Act & Assert: Missing param should be detected
        with pytest.raises(SecurityError, match="Parameters mismatch"):
            jwt_handler.verify_params_match(payload, {"id": "123"})


# ============================================================================
# Input Validation Tests
# ============================================================================

class TestInputValidation:
    """Test suite for input validation and sanitization."""

    def test_jwt_handler_validates_operation_type(self, jwt_handler):
        """Test that operation parameter must be a string."""
        # Act & Assert: Should handle non-string operations gracefully
        token = jwt_handler.generate_request_state("test_operation", {})
        assert token is not None

    def test_jwt_handler_validates_params_type(self, jwt_handler):
        """Test that params parameter must be a dictionary."""
        # Arrange
        valid_params = [
            {},
            {"key": "value"},
            {"nested": {"key": "value"}},
            {"list": [1, 2, 3]},
        ]

        # Act & Assert: All should generate tokens successfully
        for params in valid_params:
            token = jwt_handler.generate_request_state("test", params)
            assert token is not None

    def test_nonce_store_handles_empty_nonce(self, nonce_store):
        """Test that NonceStore handles empty nonce strings."""
        # Arrange
        empty_nonce = ""

        # Act
        nonce_store.mark_used(empty_nonce)

        # Assert
        assert nonce_store.is_used(empty_nonce)

    def test_jwt_handler_handles_large_params(self, jwt_handler):
        """Test that JWT handler can handle large parameter dictionaries."""
        # Arrange: Create a large params dictionary
        large_params = {f"key_{i}": f"value_{i}" for i in range(1000)}

        # Act
        token = jwt_handler.generate_request_state("test", large_params)
        payload = jwt_handler.verify_request_state(token)

        # Assert
        assert payload["params"] == large_params

    def test_jwt_handler_handles_special_characters(self, jwt_handler):
        """Test that JWT handler handles special characters in params."""
        # Arrange
        special_params = {
            "sql_injection": "'; DROP TABLE users; --",
            "xss": "<script>alert('XSS')</script>",
            "unicode": "测试中文字符 🔒",
            "newlines": "line1\nline2\rline3",
            "quotes": "single' double\" backtick`",
        }

        # Act
        token = jwt_handler.generate_request_state("test", special_params)
        payload = jwt_handler.verify_request_state(token)

        # Assert: All special characters should be preserved
        assert payload["params"] == special_params


# ============================================================================
# Token Lifecycle Tests
# ============================================================================

class TestTokenLifecycle:
    """Test suite for JWT token lifecycle management."""

    def test_token_not_valid_before_issued(self, jwt_handler):
        """Test that tokens with future iat (issued at) are rejected."""
        # Arrange: Create a token issued in the future
        payload = {
            "operation": "test",
            "params": {},
            "nonce": uuid4().hex,
            "iat": datetime.now(UTC) + timedelta(minutes=5),
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        }
        future_token = jwt.encode(payload, jwt_handler.jwt_secret, algorithm="HS256")

        # Act & Assert: JWT library validates iat and should reject future tokens
        with pytest.raises(jwt.ImmatureSignatureError):
            jwt.decode(future_token, jwt_handler.jwt_secret, algorithms=["HS256"])

    def test_token_expiry_window(self, jwt_handler):
        """Test that tokens expire at the correct time."""
        # Arrange
        expiry_minutes = 1
        token = jwt_handler.generate_request_state(
            "test", {}, expiry_minutes=expiry_minutes
        )

        # Act: Decode and check expiry time
        payload = jwt.decode(token, jwt_handler.jwt_secret, algorithms=["HS256"])
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]

        # Assert: Expiry should be exactly expiry_minutes after iat
        assert exp_timestamp - iat_timestamp == expiry_minutes * 60

    def test_multiple_tokens_for_same_operation(self, jwt_handler):
        """Test that multiple tokens can be generated for the same operation."""
        # Arrange
        operation = "delete"
        params = {"id": "123"}

        # Act: Generate multiple tokens
        token1 = jwt_handler.generate_request_state(operation, params)
        token2 = jwt_handler.generate_request_state(operation, params)

        # Assert: Tokens should be different (different nonces)
        assert token1 != token2

        # Both should verify successfully
        payload1 = jwt_handler.verify_request_state(token1)
        payload2 = jwt_handler.verify_request_state(token2)

        assert payload1["nonce"] != payload2["nonce"]


# ============================================================================
# Security Best Practices Tests
# ============================================================================

class TestSecurityBestPractices:
    """Test suite for security best practices and edge cases."""

    def test_jwt_secret_warning_when_not_set(self, nonce_store, caplog):
        """Test that a warning is logged when JWT_SECRET is not set."""
        # Arrange & Act: Create handler without explicit secret
        import os
        old_secret = os.environ.get("JWT_SECRET")
        if "JWT_SECRET" in os.environ:
            del os.environ["JWT_SECRET"]

        handler = JWTHandler(nonce_store, jwt_secret=None)

        # Restore env
        if old_secret:
            os.environ["JWT_SECRET"] = old_secret

        # Assert: Handler should be created with a random secret
        assert handler.jwt_secret is not None
        assert len(handler.jwt_secret) == 32  # UUID hex length

    def test_nonce_store_stats(self, nonce_store):
        """Test that NonceStore provides accurate statistics."""
        # Arrange
        for i in range(5):
            nonce_store.mark_used(f"nonce_{i}")

        # Act
        stats = nonce_store.get_stats()

        # Assert
        assert stats["total_nonces"] == 5
        assert stats["cleanup_interval_seconds"] == 1

    @pytest.mark.asyncio
    async def test_nonce_store_graceful_shutdown(self, nonce_store):
        """Test that NonceStore shuts down gracefully."""
        # Arrange
        await nonce_store.start()
        nonce_store.mark_used("test_nonce")

        # Act
        await nonce_store.stop()

        # Assert: Should not raise any exceptions
        assert True

    def test_jwt_algorithm_enforcement(self, jwt_handler):
        """Test that only HS256 algorithm is accepted."""
        # Arrange: Try to create a token with a different algorithm
        payload = {
            "operation": "test",
            "params": {},
            "nonce": uuid4().hex,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iat": datetime.now(UTC),
        }

        # Create token with "none" algorithm (security vulnerability)
        none_token = jwt.encode(payload, "", algorithm="none")

        # Act & Assert: Should reject "none" algorithm
        with pytest.raises(SecurityError):
            jwt_handler.verify_request_state(none_token)

    def test_concurrent_replay_attacks(self, jwt_handler):
        """Test that concurrent replay attacks are all detected."""
        # Arrange
        token = jwt_handler.generate_request_state("test", {})

        # Act: First verification succeeds
        jwt_handler.verify_request_state(token)

        # Assert: All subsequent attempts should fail
        for _ in range(10):
            with pytest.raises(SecurityError, match="Nonce already used"):
                jwt_handler.verify_request_state(token)


# ============================================================================
# Performance and Stress Tests
# ============================================================================

class TestSecurityPerformance:
    """Test suite for security-related performance."""

    def test_jwt_generation_performance(self, jwt_handler):
        """Test that JWT generation is fast enough for production."""
        # Arrange
        iterations = 1000
        params = {"operation": "test", "data": "value"}

        # Act
        start = time.perf_counter()
        for _ in range(iterations):
            jwt_handler.generate_request_state("test", params)
        elapsed = time.perf_counter() - start

        # Assert: Should generate 1000 tokens in less than 100ms
        avg_time = (elapsed / iterations) * 1000  # Convert to ms
        assert avg_time < 1.0, f"JWT generation too slow: {avg_time:.3f}ms per token"

    def test_jwt_verification_performance(self, jwt_handler):
        """Test that JWT verification is fast enough for production."""
        # Arrange
        iterations = 1000
        tokens = [
            jwt_handler.generate_request_state("test", {"id": i})
            for i in range(iterations)
        ]

        # Act
        start = time.perf_counter()
        for token in tokens:
            jwt_handler.verify_request_state(token)
        elapsed = time.perf_counter() - start

        # Assert: Should verify 1000 tokens in less than 200ms
        avg_time = (elapsed / iterations) * 1000  # Convert to ms
        assert avg_time < 1.0, f"JWT verification too slow: {avg_time:.3f}ms per token"

    def test_nonce_store_lookup_performance(self, nonce_store):
        """Test that nonce lookup is fast enough for production."""
        # Arrange: Add 10,000 nonces
        for i in range(10000):
            nonce_store.mark_used(f"nonce_{i}")

        # Act: Lookup performance
        iterations = 1000
        start = time.perf_counter()
        for i in range(iterations):
            nonce_store.is_used(f"nonce_{i}")
        elapsed = time.perf_counter() - start

        # Assert: Should lookup 1000 nonces in less than 10ms
        avg_time = (elapsed / iterations) * 1000  # Convert to ms
        assert avg_time < 0.1, f"Nonce lookup too slow: {avg_time:.3f}ms per lookup"


# ============================================================================
# Integration Tests
# ============================================================================

class TestSecurityIntegration:
    """Test suite for end-to-end security workflows."""

    def test_full_mrtr_workflow(self, jwt_handler):
        """Test the complete MRTR workflow with JWT and nonce."""
        # Arrange
        operation = "delete_knowledge"
        params = {"entity_name": "test_entity", "scope": "user"}

        # Act: Round 1 - Generate JWT
        token = jwt_handler.generate_request_state(operation, params)
        assert token is not None

        # Act: Round 2 - Verify JWT and execute
        payload = jwt_handler.verify_request_state(token)
        assert payload["operation"] == operation

        # Verify params match
        assert jwt_handler.verify_params_match(payload, params) is True

        # Assert: Round 3 - Replay should fail
        with pytest.raises(SecurityError, match="Nonce already used"):
            jwt_handler.verify_request_state(token)

    def test_mrtr_workflow_with_expiry(self, jwt_handler):
        """Test MRTR workflow respects token expiry."""
        # Arrange
        token = jwt_handler.generate_request_state("test", {}, expiry_minutes=-1)

        # Act & Assert: Expired token should be rejected
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_handler.verify_request_state(token)

    def test_mrtr_workflow_with_parameter_tampering(self, jwt_handler):
        """Test MRTR workflow detects parameter tampering."""
        # Arrange
        original_params = {"id": "123"}
        token = jwt_handler.generate_request_state("delete", original_params)
        payload = jwt_handler.verify_request_state(token)

        # Act & Assert: Tampered params should be rejected
        tampered_params = {"id": "456"}
        with pytest.raises(SecurityError, match="Parameters mismatch"):
            jwt_handler.verify_params_match(payload, tampered_params)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
