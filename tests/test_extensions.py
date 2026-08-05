"""
Tests for MCP Extensions Framework

Tests cover:
- Extension registration and lifecycle
- Capability negotiation
- Tool registration
- Python analyzer
- TypeScript analyzer
- Secure storage with OAuth
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))

from src.extensions.base_extension import Extension
from src.extensions.extension_manager import ExtensionManager
from src.extensions.python_analyzer import PythonAnalyzerExtension
from src.extensions.typescript_analyzer import TypeScriptAnalyzerExtension
from src.extensions.secure_storage import SecureStorageExtension


class TestExtensionManager:
    """Test ExtensionManager functionality."""

    def test_register_extension(self):
        """Test registering an extension."""
        manager = ExtensionManager()
        extension = PythonAnalyzerExtension()

        manager.register(extension)

        assert extension.extension_id in manager.extensions
        assert manager.extensions[extension.extension_id] == extension

    def test_duplicate_registration(self):
        """Test duplicate registration warning."""
        manager = ExtensionManager()
        extension = PythonAnalyzerExtension()

        manager.register(extension)
        manager.register(extension)  # Should log warning but not fail

        assert len(manager.extensions) == 1

    def test_capability_negotiation(self):
        """Test capability negotiation with client."""
        manager = ExtensionManager()
        python_ext = PythonAnalyzerExtension()
        ts_ext = TypeScriptAnalyzerExtension()

        manager.register(python_ext)
        manager.register(ts_ext)

        # Mock server
        mock_server = Mock()
        manager.set_server(mock_server)

        # Client requests Python analyzer only
        client_caps = {
            "extensions": {
                "io.learning-system.analyzer.python": {"version": "1.0.0"}
            }
        }

        enabled = manager.negotiate_capabilities(client_caps)

        assert "io.learning-system.analyzer.python" in enabled
        assert "io.learning-system.analyzer.typescript" not in enabled

    def test_version_compatibility(self):
        """Test version compatibility checking."""
        manager = ExtensionManager()

        # Same major version - compatible
        assert manager._is_version_compatible("1.2.3", "1.5.0")

        # Different major version - incompatible
        assert not manager._is_version_compatible("1.0.0", "2.0.0")

        # Invalid version format
        assert not manager._is_version_compatible("invalid", "1.0.0")

    def test_enable_disable_extension(self):
        """Test enabling and disabling extensions."""
        manager = ExtensionManager()
        extension = PythonAnalyzerExtension()
        manager.register(extension)

        mock_server = Mock()

        # Enable
        result = manager.enable_extension(extension.extension_id, mock_server)
        assert result is True
        assert extension.extension_id in manager.enabled_extensions
        assert extension.is_enabled

        # Disable
        result = manager.disable_extension(extension.extension_id)
        assert result is True
        assert extension.extension_id not in manager.enabled_extensions
        assert not extension.is_enabled

    def test_list_extensions(self):
        """Test listing extensions."""
        manager = ExtensionManager()
        python_ext = PythonAnalyzerExtension()
        ts_ext = TypeScriptAnalyzerExtension()

        manager.register(python_ext)
        manager.register(ts_ext)

        # List all
        all_extensions = manager.list_extensions()
        assert len(all_extensions) == 2

        # Enable one
        mock_server = Mock()
        manager.set_server(mock_server)
        manager.enable_extension(python_ext.extension_id, mock_server)

        # List enabled only
        enabled_only = manager.list_extensions(enabled_only=True)
        assert len(enabled_only) == 1
        assert enabled_only[0]["id"] == python_ext.extension_id


class TestPythonAnalyzer:
    """Test Python analyzer extension."""

    def test_metadata(self):
        """Test extension metadata."""
        ext = PythonAnalyzerExtension()

        assert ext.extension_id == "io.learning-system.analyzer.python"
        assert ext.version == "1.0.0"
        assert ext.display_name == "Python Code Analyzer"
        assert "decorators" in ext.description.lower()

    def test_capabilities(self):
        """Test extension capabilities."""
        ext = PythonAnalyzerExtension()
        caps = ext.get_capabilities()

        assert caps["analyze_decorators"] is True
        assert "FastAPI" in caps["detect_framework"]
        assert caps["extract_type_hints"] is True

    @pytest.mark.asyncio
    async def test_analyze_decorators(self):
        """Test decorator analysis."""
        ext = PythonAnalyzerExtension()

        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/users")
async def get_users():
    return []

@app.post("/users")
async def create_user():
    pass
""")
            test_file = f.name

        try:
            decorators = ext._extract_decorators(test_file)

            assert len(decorators) == 2
            assert decorators[0]["target"] == "get_users"
            assert decorators[0]["target_type"] == "function"
            assert "app.get" in decorators[0]["decorator"]

            frameworks = ext._detect_frameworks(decorators)
            assert "FastAPI" in frameworks
        finally:
            os.unlink(test_file)

    @pytest.mark.asyncio
    async def test_extract_type_hints(self):
        """Test type hint extraction."""
        ext = PythonAnalyzerExtension()

        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from typing import Dict, List

def process_data(name: str, count: int) -> Dict[str, int]:
    return {name: count}

def no_hints(data):
    return data
""")
            test_file = f.name

        try:
            hints = ext._extract_type_hints(test_file)

            assert len(hints["functions"]) == 1  # Only process_data has hints
            assert hints["functions"][0]["name"] == "process_data"
            assert hints["functions"][0]["return_type"] == "Dict[str, int]"
            assert hints["coverage"] == 0.5  # 1 out of 2 functions
        finally:
            os.unlink(test_file)

    @pytest.mark.asyncio
    async def test_detect_framework(self):
        """Test framework detection."""
        ext = PythonAnalyzerExtension()

        # Create test project structure
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create requirements.txt
            req_file = os.path.join(tmpdir, "requirements.txt")
            with open(req_file, 'w') as f:
                f.write("fastapi==0.95.0\nuvicorn==0.21.1\n")

            result = ext._detect_project_framework(tmpdir)

            assert result["framework"] == "FastAPI"
            assert result["confidence"] > 0.5
            assert "fastapi in requirements.txt" in result["evidence"]


class TestTypeScriptAnalyzer:
    """Test TypeScript analyzer extension."""

    def test_metadata(self):
        """Test extension metadata."""
        ext = TypeScriptAnalyzerExtension()

        assert ext.extension_id == "io.learning-system.analyzer.typescript"
        assert ext.version == "1.0.0"
        assert "TypeScript" in ext.display_name

    def test_capabilities(self):
        """Test extension capabilities."""
        ext = TypeScriptAnalyzerExtension()
        caps = ext.get_capabilities()

        assert caps["detect_react_components"] is True
        assert "React" in caps["detect_framework"]
        assert caps["analyze_hooks"] is True

    @pytest.mark.asyncio
    async def test_detect_components(self):
        """Test React component detection."""
        ext = TypeScriptAnalyzerExtension()

        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False) as f:
            f.write("""
import React from 'react';

const UserProfile = ({ userId }: { userId: string }) => {
    return <div>{userId}</div>;
};

function Dashboard() {
    return <div>Dashboard</div>;
}

class OldComponent extends React.Component {
    render() {
        return <div>Old</div>;
    }
}
""")
            test_file = f.name

        try:
            components = ext._detect_react_components(test_file)

            assert len(components) == 3
            assert components[0]["name"] == "UserProfile"
            assert components[0]["type"] == "functional"
            assert components[2]["type"] == "class"
        finally:
            os.unlink(test_file)

    @pytest.mark.asyncio
    async def test_analyze_hooks(self):
        """Test hooks analysis."""
        ext = TypeScriptAnalyzerExtension()

        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False) as f:
            f.write("""
import { useState, useEffect } from 'react';

function useCustomHook() {
    const [data, setData] = useState(null);

    useEffect(() => {
        // fetch data
    }, []);

    return data;
}
""")
            test_file = f.name

        try:
            hooks_info = ext._analyze_hooks(test_file)

            assert len(hooks_info["hooks"]) == 2  # useState, useEffect
            assert len(hooks_info["custom_hooks"]) == 1
            assert hooks_info["custom_hooks"][0]["name"] == "useCustomHook"
        finally:
            os.unlink(test_file)

    @pytest.mark.asyncio
    async def test_extract_interfaces(self):
        """Test interface extraction."""
        ext = TypeScriptAnalyzerExtension()

        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write("""
export interface User {
    id: string;
    name: string;
}

type UserId = string;

enum Status {
    ACTIVE,
    INACTIVE
}
""")
            test_file = f.name

        try:
            types_info = ext._extract_interfaces(test_file)

            assert len(types_info["interfaces"]) == 1
            assert types_info["interfaces"][0]["name"] == "User"
            assert types_info["interfaces"][0]["exported"] is True

            assert len(types_info["types"]) == 1
            assert types_info["types"][0]["name"] == "UserId"

            assert len(types_info["enums"]) == 1
            assert types_info["enums"][0]["name"] == "Status"
        finally:
            os.unlink(test_file)


class TestSecureStorage:
    """Test secure storage extension."""

    def test_metadata(self):
        """Test extension metadata."""
        ext = SecureStorageExtension()

        assert ext.extension_id == "io.learning-system.storage.secure"
        assert ext.version == "1.0.0"
        assert "OAuth" in ext.display_name

    def test_capabilities(self):
        """Test extension capabilities."""
        ext = SecureStorageExtension()
        caps = ext.get_capabilities()

        assert caps["oauth2_flow"] is True
        assert caps["token_refresh"] is True
        assert caps["encrypted_storage"] is True

    def test_encryption_key_creation(self):
        """Test encryption key management."""
        ext = SecureStorageExtension()

        # Key should be created
        assert ext._encryption_key is not None
        assert len(ext._encryption_key) > 0

    def test_oauth_flow_initiation(self):
        """Test OAuth flow initiation."""
        ext = SecureStorageExtension()

        auth_info = ext._initiate_oauth_flow("github", "test_client_id", ["read", "write"])

        assert "auth_url" in auth_info
        assert "state" in auth_info
        assert "expires_at" in auth_info
        assert "github" in auth_info["auth_url"]

    def test_secure_credential_storage(self):
        """Test secure credential storage and retrieval."""
        ext = SecureStorageExtension()

        # Store credential
        test_cred = {"username": "admin", "password": "secret"}
        ext._store_secure_credential("database", "password", test_cred)

        # Retrieve credential
        retrieved = ext._retrieve_secure_credential("database", "password")

        assert retrieved == test_cred

    def test_token_storage_and_retrieval(self):
        """Test OAuth token storage."""
        ext = SecureStorageExtension()

        token_info = {
            "access_token": "test_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }

        # Store token
        ext._store_token("github", token_info)

        # Retrieve token
        retrieved = ext._retrieve_token("github")

        assert retrieved["access_token"] == "test_token"
        assert retrieved["token_type"] == "Bearer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
