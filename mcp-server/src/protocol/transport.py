"""
MCP Transport Layer
Implements stdio and SSE transports for MCP protocol
"""

import sys
import json
import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional, List
from abc import ABC, abstractmethod


class Transport(ABC):
    """Base transport interface"""

    @abstractmethod
    async def read_message(self) -> Dict[str, Any]:
        """Read incoming message"""
        pass

    @abstractmethod
    async def write_message(self, message: Dict[str, Any]):
        """Write outgoing message"""
        pass

    @abstractmethod
    async def close(self):
        """Close transport"""
        pass


class StdioTransport(Transport):
    """
    Standard I/O Transport
    Reads from stdin, writes to stdout (MCP standard transport)

    Message format: JSON lines
    """

    def __init__(self, hooks: Optional[List] = None):
        self.stdin_reader = None
        self.stdout_writer = None
        self._closed = False
        self.hooks = hooks or []

    async def start(self):
        """Initialize stdio streams"""
        loop = asyncio.get_event_loop()

        # Create async readers/writers for stdin/stdout
        self.stdin_reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self.stdin_reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    async def read_message(self) -> Dict[str, Any]:
        """
        Read JSON-RPC message from stdin

        Returns:
            Parsed JSON message dict

        Raises:
            EOFError: If stdin is closed
        """
        if self._closed:
            raise EOFError("Transport closed")

        if not self.stdin_reader:
            await self.start()

        try:
            # Read line from stdin
            line = await self.stdin_reader.readline()

            if not line:
                raise EOFError("stdin closed")

            # Parse JSON
            message = json.loads(line.decode('utf-8'))
            return message

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    async def write_message(self, message: Dict[str, Any]):
        """
        Write JSON-RPC message to stdout

        Args:
            message: Message dict to serialize
        """
        if self._closed:
            return

        # Serialize to JSON
        json_str = json.dumps(message, ensure_ascii=False)

        # Write to stdout with newline
        sys.stdout.write(json_str + '\n')
        sys.stdout.flush()

    async def close(self):
        """Close transport"""
        self._closed = True

    async def run(self, server):
        """
        Run message loop with hook support

        Args:
            server: MCPServer instance to handle requests
        """
        await self.start()

        try:
            while not self._closed:
                # Read request
                request_data = await self.read_message()

                # Create hook context
                from ..hooks import HookContext
                context = HookContext(request=request_data)

                # Pre-request hooks
                for hook in self.hooks:
                    await hook.on_request(context)

                # Handle request
                try:
                    response_data = await server.handle_request(request_data)
                    context.response = response_data
                except Exception as e:
                    context.error = e
                    raise

                # Post-response hooks
                for hook in self.hooks:
                    await hook.on_response(context)

                # Write response
                await self.write_message(response_data)

        except EOFError:
            pass
        except Exception as e:
            import sys
            print(f"Transport error: {e}", file=sys.stderr)
        finally:
            await self.close()


class SSETransport(Transport):
    """
    Server-Sent Events (SSE) Transport
    For HTTP-based MCP connections

    Format:
        Client -> Server: HTTP POST with JSON body
        Server -> Client: SSE stream with JSON events
    """

    def __init__(self, request_queue: asyncio.Queue, response_callback: Callable[[Dict], Awaitable]):
        """
        Args:
            request_queue: Queue for incoming HTTP requests
            response_callback: Async function to send SSE events
        """
        self.request_queue = request_queue
        self.response_callback = response_callback
        self._closed = False

    async def read_message(self) -> Dict[str, Any]:
        """
        Read message from HTTP request queue

        Returns:
            Parsed JSON message dict
        """
        if self._closed:
            raise EOFError("Transport closed")

        message = await self.request_queue.get()
        return message

    async def write_message(self, message: Dict[str, Any]):
        """
        Write message as SSE event

        Args:
            message: Message dict to send
        """
        if self._closed:
            return

        await self.response_callback(message)

    async def close(self):
        """Close transport"""
        self._closed = True
