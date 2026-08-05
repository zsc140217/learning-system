"""
Extension Manager

Manages MCP extensions lifecycle and capability negotiation.
"""

from typing import Dict, Any, List, Optional, Set
import logging
from .base_extension import Extension

logger = logging.getLogger(__name__)


class ExtensionManager:
    """
    Manages extension registration, capability negotiation, and lifecycle.

    Workflow:
    1. Extensions are registered during server startup
    2. Client sends capabilities during handshake
    3. Manager negotiates and enables matching extensions
    4. Extensions register their tools with the server
    """

    def __init__(self):
        self.extensions: Dict[str, Extension] = {}
        self.enabled_extensions: Set[str] = set()
        self._server = None

    def register(self, extension: Extension) -> None:
        """
        Register an extension with the manager.

        Args:
            extension: Extension instance to register

        Raises:
            ValueError: If extension ID already registered
        """
        ext_id = extension.extension_id

        if ext_id in self.extensions:
            logger.warning(f"Extension already registered: {ext_id}")
            return

        self.extensions[ext_id] = extension
        logger.info(
            f"Registered extension: {ext_id} v{extension.version} - {extension.display_name}"
        )

    def unregister(self, extension_id: str) -> None:
        """
        Unregister an extension.

        Args:
            extension_id: Extension ID to unregister
        """
        if extension_id in self.enabled_extensions:
            self.disable_extension(extension_id)

        if extension_id in self.extensions:
            del self.extensions[extension_id]
            logger.info(f"Unregistered extension: {extension_id}")

    def negotiate_capabilities(
        self, client_capabilities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Negotiate capabilities with client and enable matching extensions.

        Args:
            client_capabilities: Client-declared capabilities
                Example: {
                    "extensions": {
                        "io.learning-system.analyzer.python": {
                            "version": "1.0.0"
                        }
                    }
                }

        Returns:
            Dictionary of enabled extensions with their capabilities
        """
        client_extensions = client_capabilities.get("extensions", {})
        enabled = {}

        for ext_id, client_ext_info in client_extensions.items():
            if ext_id not in self.extensions:
                logger.warning(f"Client requested unknown extension: {ext_id}")
                continue

            extension = self.extensions[ext_id]

            # Version compatibility check (simple for now)
            client_version = client_ext_info.get("version", "1.0.0")
            if not self._is_version_compatible(extension.version, client_version):
                logger.warning(
                    f"Version mismatch for {ext_id}: "
                    f"server={extension.version}, client={client_version}"
                )
                continue

            # Enable extension if negotiation succeeds
            if self._server:
                self.enable_extension(ext_id, self._server)
                enabled[ext_id] = {
                    "version": extension.version,
                    "capabilities": extension.get_capabilities(),
                }

        logger.info(
            f"Capability negotiation complete. Enabled {len(enabled)} extensions."
        )
        return enabled

    def enable_extension(self, extension_id: str, server: Any) -> bool:
        """
        Enable a specific extension.

        Args:
            extension_id: Extension ID to enable
            server: MCP server instance

        Returns:
            True if enabled successfully, False otherwise
        """
        if extension_id not in self.extensions:
            logger.error(f"Cannot enable unknown extension: {extension_id}")
            return False

        if extension_id in self.enabled_extensions:
            logger.info(f"Extension already enabled: {extension_id}")
            return True

        extension = self.extensions[extension_id]

        try:
            extension.enable(server)
            self.enabled_extensions.add(extension_id)
            logger.info(f"Extension enabled: {extension_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable extension {extension_id}: {e}")
            return False

    def disable_extension(self, extension_id: str) -> bool:
        """
        Disable a specific extension.

        Args:
            extension_id: Extension ID to disable

        Returns:
            True if disabled successfully, False otherwise
        """
        if extension_id not in self.enabled_extensions:
            logger.warning(f"Extension not enabled: {extension_id}")
            return False

        extension = self.extensions[extension_id]

        try:
            extension.disable()
            self.enabled_extensions.remove(extension_id)
            logger.info(f"Extension disabled: {extension_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable extension {extension_id}: {e}")
            return False

    def get_extension(self, extension_id: str) -> Optional[Extension]:
        """
        Get extension by ID.

        Args:
            extension_id: Extension ID

        Returns:
            Extension instance or None if not found
        """
        return self.extensions.get(extension_id)

    def list_extensions(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all registered extensions.

        Args:
            enabled_only: If True, only return enabled extensions

        Returns:
            List of extension metadata dictionaries
        """
        extensions = self.extensions.values()

        if enabled_only:
            extensions = [
                ext for ext in extensions if ext.extension_id in self.enabled_extensions
            ]

        return [ext.get_metadata() for ext in extensions]

    def set_server(self, server: Any) -> None:
        """
        Set the MCP server instance for extensions.

        Args:
            server: MCP server instance
        """
        self._server = server

    def _is_version_compatible(
        self, server_version: str, client_version: str
    ) -> bool:
        """
        Check if server and client versions are compatible.

        Simple implementation: major version must match.

        Args:
            server_version: Server extension version (semver)
            client_version: Client extension version (semver)

        Returns:
            True if compatible
        """
        try:
            server_major = int(server_version.split(".")[0])
            client_major = int(client_version.split(".")[0])
            return server_major == client_major
        except (ValueError, IndexError):
            logger.warning(
                f"Invalid version format: server={server_version}, client={client_version}"
            )
            return False

    def shutdown(self) -> None:
        """Disable all extensions and cleanup."""
        logger.info("Shutting down extension manager...")

        for ext_id in list(self.enabled_extensions):
            self.disable_extension(ext_id)

        logger.info("Extension manager shutdown complete")
