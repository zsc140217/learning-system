"""
Secure Storage Extension with OAuth 2.0 Support

Demonstrates OAuth 2.0 authorization flow and encrypted token storage.
This extension shows how to implement secure storage for sensitive credentials.
"""

import os
import json
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import logging

from .base_extension import Extension

logger = logging.getLogger(__name__)


class SecureStorageExtension(Extension):
    """
    Extension for secure storage with OAuth 2.0 support.

    Features:
    - OAuth 2.0 authorization flow simulation
    - Encrypted token storage
    - Automatic token refresh
    - Secure credential management

    Note: This is a demonstration implementation for educational purposes.
    Production usage would require proper OAuth provider integration.
    """

    def __init__(self):
        super().__init__()
        self._storage_path = os.path.join(os.path.expanduser("~"), ".learning-system", "secure_storage.enc")
        self._encryption_key = self._get_or_create_key()
        self._cipher = Fernet(self._encryption_key)

    @property
    def extension_id(self) -> str:
        return "io.learning-system.storage.secure"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "Secure Storage with OAuth"

    @property
    def description(self) -> str:
        return "Secure storage for OAuth tokens and sensitive credentials with encryption"

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "oauth2_flow": True,
            "token_refresh": True,
            "encrypted_storage": True,
            "supported_grant_types": ["authorization_code", "client_credentials"],
            "encryption_algorithm": "Fernet (AES-128-CBC)"
        }

    def register_tools(self, server: Any):
        """Register secure storage tools with the MCP server."""

        @server.tool("oauth_initiate")
        async def oauth_initiate(
            provider: str,
            client_id: str,
            scopes: list
        ) -> Dict[str, Any]:
            """
            Initiate OAuth 2.0 authorization flow.

            Args:
                provider: OAuth provider name (e.g., "github", "google")
                client_id: OAuth client ID
                scopes: List of requested scopes

            Returns:
                Authorization URL and state for CSRF protection
            """
            try:
                auth_info = self._initiate_oauth_flow(provider, client_id, scopes)

                return {
                    "provider": provider,
                    "authorization_url": auth_info["auth_url"],
                    "state": auth_info["state"],
                    "expires_at": auth_info["expires_at"],
                    "instructions": "User must visit authorization_url to grant permissions"
                }
            except Exception as e:
                logger.error(f"Failed to initiate OAuth flow: {e}")
                return {"error": str(e)}

        @server.tool("oauth_complete")
        async def oauth_complete(
            provider: str,
            authorization_code: str,
            state: str
        ) -> Dict[str, Any]:
            """
            Complete OAuth 2.0 authorization flow and store tokens securely.

            Args:
                provider: OAuth provider name
                authorization_code: Authorization code from callback
                state: State parameter for CSRF validation

            Returns:
                Success status and token metadata
            """
            try:
                token_info = self._complete_oauth_flow(
                    provider,
                    authorization_code,
                    state
                )

                # Store tokens securely
                self._store_token(provider, token_info)

                return {
                    "provider": provider,
                    "status": "success",
                    "token_type": token_info["token_type"],
                    "expires_in": token_info["expires_in"],
                    "scopes": token_info.get("scope", "").split()
                }
            except Exception as e:
                logger.error(f"Failed to complete OAuth flow: {e}")
                return {"error": str(e)}

        @server.tool("oauth_refresh_token")
        async def refresh_token(provider: str) -> Dict[str, Any]:
            """
            Refresh OAuth 2.0 access token.

            Args:
                provider: OAuth provider name

            Returns:
                New token metadata
            """
            try:
                new_token = self._refresh_token(provider)

                return {
                    "provider": provider,
                    "status": "refreshed",
                    "expires_in": new_token["expires_in"],
                    "refreshed_at": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return {"error": str(e)}

        @server.tool("secure_store_credential")
        async def store_credential(
            service: str,
            credential_type: str,
            credential_data: Dict[str, str]
        ) -> Dict[str, Any]:
            """
            Store credentials securely with encryption.

            Args:
                service: Service name (e.g., "database", "api")
                credential_type: Type of credential (e.g., "api_key", "password")
                credential_data: Credential key-value pairs

            Returns:
                Storage confirmation
            """
            try:
                self._store_secure_credential(service, credential_type, credential_data)

                return {
                    "service": service,
                    "credential_type": credential_type,
                    "status": "stored",
                    "encrypted": True
                }
            except Exception as e:
                logger.error(f"Failed to store credential: {e}")
                return {"error": str(e)}

        @server.tool("secure_retrieve_credential")
        async def retrieve_credential(
            service: str,
            credential_type: str
        ) -> Dict[str, Any]:
            """
            Retrieve stored credentials securely.

            Args:
                service: Service name
                credential_type: Type of credential

            Returns:
                Decrypted credential data
            """
            try:
                credential_data = self._retrieve_secure_credential(service, credential_type)

                if credential_data is None:
                    return {"error": "Credential not found"}

                return {
                    "service": service,
                    "credential_type": credential_type,
                    "data": credential_data,
                    "status": "retrieved"
                }
            except Exception as e:
                logger.error(f"Failed to retrieve credential: {e}")
                return {"error": str(e)}

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        key_file = os.path.join(os.path.expanduser("~"), ".learning-system", "encryption.key")

        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()

        # Create new key
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)

        logger.info("Created new encryption key")
        return key

    def _initiate_oauth_flow(
        self,
        provider: str,
        client_id: str,
        scopes: list
    ) -> Dict[str, Any]:
        """Simulate OAuth 2.0 authorization initiation."""
        import secrets

        state = secrets.token_urlsafe(32)

        # Provider-specific authorization URLs (demo)
        auth_urls = {
            "github": f"https://github.com/login/oauth/authorize?client_id={client_id}&scope={','.join(scopes)}&state={state}",
            "google": f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&scope={' '.join(scopes)}&state={state}&response_type=code",
        }

        auth_url = auth_urls.get(provider, f"https://{provider}.com/oauth/authorize")

        return {
            "auth_url": auth_url,
            "state": state,
            "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }

    def _complete_oauth_flow(
        self,
        provider: str,
        authorization_code: str,
        state: str
    ) -> Dict[str, Any]:
        """
        Simulate OAuth 2.0 token exchange.

        Note: In production, this would make HTTP requests to the OAuth provider.
        """
        # Simulate token response
        token_info = {
            "access_token": f"demo_access_token_{provider}_{authorization_code[:8]}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": f"demo_refresh_token_{provider}_{authorization_code[:8]}",
            "scope": "read write",
            "created_at": datetime.utcnow().isoformat()
        }

        return token_info

    def _refresh_token(self, provider: str) -> Dict[str, Any]:
        """Refresh OAuth token."""
        # Retrieve stored token
        stored_token = self._retrieve_token(provider)

        if not stored_token:
            raise ValueError(f"No token found for provider: {provider}")

        # Simulate token refresh
        new_token = {
            "access_token": f"refreshed_access_token_{provider}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "created_at": datetime.utcnow().isoformat()
        }

        # Update stored token
        stored_token.update(new_token)
        self._store_token(provider, stored_token)

        return new_token

    def _store_token(self, provider: str, token_info: Dict[str, Any]) -> None:
        """Store OAuth token with encryption."""
        storage = self._load_storage()

        if "oauth_tokens" not in storage:
            storage["oauth_tokens"] = {}

        storage["oauth_tokens"][provider] = token_info
        self._save_storage(storage)

        logger.info(f"Stored OAuth token for provider: {provider}")

    def _retrieve_token(self, provider: str) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth token."""
        storage = self._load_storage()
        return storage.get("oauth_tokens", {}).get(provider)

    def _store_secure_credential(
        self,
        service: str,
        credential_type: str,
        credential_data: Dict[str, str]
    ) -> None:
        """Store credential with encryption."""
        storage = self._load_storage()

        if "credentials" not in storage:
            storage["credentials"] = {}

        key = f"{service}:{credential_type}"
        storage["credentials"][key] = credential_data
        self._save_storage(storage)

        logger.info(f"Stored credential for {service} ({credential_type})")

    def _retrieve_secure_credential(
        self,
        service: str,
        credential_type: str
    ) -> Optional[Dict[str, str]]:
        """Retrieve credential with decryption."""
        storage = self._load_storage()
        key = f"{service}:{credential_type}"
        return storage.get("credentials", {}).get(key)

    def _load_storage(self) -> Dict[str, Any]:
        """Load and decrypt storage."""
        if not os.path.exists(self._storage_path):
            return {}

        try:
            with open(self._storage_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self._cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to load storage: {e}")
            return {}

    def _save_storage(self, storage: Dict[str, Any]) -> None:
        """Encrypt and save storage."""
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)

        data = json.dumps(storage).encode('utf-8')
        encrypted_data = self._cipher.encrypt(data)

        with open(self._storage_path, 'wb') as f:
            f.write(encrypted_data)

    def on_disable(self) -> None:
        """Cleanup on disable."""
        super().on_disable()
        logger.info("Secure storage extension disabled. Encrypted data preserved.")
