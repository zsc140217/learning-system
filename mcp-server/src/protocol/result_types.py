"""
MCP Result Types
Defines result types with _meta field support for MCP 2026-07-28
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class MCPError(Exception):
    """MCP Protocol Error"""
    def __init__(self, message: str, code: int = -32000):
        self.message = message
        self.code = code
        super().__init__(message)


@dataclass
class MCPResult:
    """
    Base MCP Result with _meta support

    Usage:
        result = MCPResult(
            data={"status": "ok"},
            meta={"ttlMs": 3600000, "cacheScope": "user"}
        )
    """
    data: Any
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_jsonrpc(self, request_id: int | str) -> Dict[str, Any]:
        """
        Convert to JSON-RPC 2.0 response format

        Returns:
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {...},
                "_meta": {...}
            }
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": self.data
        }

        if self.meta:
            response["_meta"] = self.meta

        return response


class InputRequiredResult:
    """
    MRTR (Multi-Round Trip Request) Result
    Server requests user input with optional JWT-signed state

    Usage:
        result = InputRequiredResult(
            message="Confirm deletion of 3 knowledge nodes",
            fields=[
                {"name": "confirm", "type": "boolean", "label": "Confirm Delete"},
                {"name": "archive", "type": "boolean", "default": True}
            ],
            request_state="eyJhbGc..."  # JWT token
        )
    """
    def __init__(
        self,
        message: str,
        fields: List[Dict[str, Any]] = None,
        request_state: Optional[str] = None,
        data: Any = None
    ):
        self.message = message
        self.fields = fields or []
        self.request_state = request_state
        self.data = data or {}

        # Build meta
        self.meta = {
            "io.modelcontextprotocol/inputRequired": {
                "message": self.message,
                "fields": self.fields
            }
        }

        if self.request_state:
            self.meta["io.modelcontextprotocol/inputRequired"]["requestState"] = self.request_state

    def to_jsonrpc(self, request_id: int | str) -> Dict[str, Any]:
        """Convert to JSON-RPC response"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": self.data,
            "_meta": self.meta
        }
        return response


class TaskHandleResult:
    """
    Tasks Extension Result
    Returns a handle for long-running background tasks

    Usage:
        result = TaskHandleResult(
            task_id="task-a7b3c9d2",
            status="running",
            progress=0.0,
            message="Analysis started...",
            eta_seconds=600
        )
    """
    def __init__(
        self,
        task_id: str,
        status: str,
        progress: float,
        message: Optional[str] = None,
        eta_seconds: Optional[int] = None,
        result: Any = None,
        error: Optional[str] = None
    ):
        self.task_id = task_id
        self.status = status
        self.progress = progress
        self.message = message
        self.eta_seconds = eta_seconds
        self.result = result
        self.error = error

        # Build task data
        task_data = {
            "taskId": self.task_id,
            "status": self.status,
            "progress": self.progress
        }

        if self.message:
            task_data["message"] = self.message

        if self.eta_seconds:
            task_data["etaSeconds"] = self.eta_seconds

        if self.result:
            task_data["result"] = self.result

        if self.error:
            task_data["error"] = self.error

        self.meta = {
            "io.modelcontextprotocol/taskHandle": task_data
        }

        self.data = task_data

    def to_jsonrpc(self, request_id: int | str) -> Dict[str, Any]:
        """Convert to JSON-RPC response"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": self.data,
            "_meta": self.meta
        }
        return response


class UITemplateResult:
    """
    MCP Apps Result
    Returns UI template for interactive client rendering

    Usage:
        result = UITemplateResult(
            template_id="com.learning-system.session-summary",
            template_path="/path/to/template.html",
            template_data={
                "session_id": "session_001",
                "knowledge_points": [...]
            }
        )
    """
    def __init__(
        self,
        template_id: str,
        template_path: str,
        template_data: Dict[str, Any] = None
    ):
        self.template_id = template_id
        self.template_path = template_path
        self.template_data = template_data or {}

        self.meta = {
            "io.modelcontextprotocol/uiTemplate": {
                "templateId": self.template_id,
                "templatePath": self.template_path,
                "data": self.template_data
            }
        }

        self.data = self.template_data

    def to_jsonrpc(self, request_id: int | str) -> Dict[str, Any]:
        """Convert to JSON-RPC response"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": self.data,
            "_meta": self.meta
        }
        return response
