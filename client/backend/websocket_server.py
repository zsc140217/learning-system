"""
WebSocket Server for Learning System Frontend
Handles real-time communication between React frontend and MCP backend
"""
import asyncio
import json
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger

from mcp_client import MCPClientPool
from mcp_http_client import MCPHTTPClient
from skill_manager import SkillManager
from skill_executor import SkillExecutor
from config import config

app = FastAPI(title="Learning System WebSocket Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

# Global components
mcp_client = None  # MCPHTTPClient instance
skill_manager = SkillManager(config.skills_dir)
skill_executor = None  # 延迟初始化


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def send_json(self, websocket: WebSocket, data: dict):
        """Send JSON message to specific client"""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def broadcast(self, data: dict):
        """Broadcast message to all clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Failed to broadcast: {e}")


manager = ConnectionManager()


@app.get("/")
async def root():
    return {
        "service": "Learning System WebSocket Server",
        "status": "running",
        "connections": len(manager.active_connections)
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for frontend communication"""
    await manager.connect(websocket)

    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle JSON-RPC 2.0 protocol
            if message.get("jsonrpc") == "2.0":
                request_id = message.get("id")
                method = message.get("method")
                params = message.get("params", {})

                logger.info(f"JSON-RPC Request: {method}")

                try:
                    if method == "tools/call":
                        tool_name = params.get("name")
                        arguments = params.get("arguments", {})

                        logger.info(f"Calling tool: {tool_name} with args: {arguments}")

                        # Call tool via MCP HTTP client
                        mcp_response = await mcp_client.call_tool(tool_name, arguments)

                        logger.info(f"MCP response keys: {list(mcp_response.keys())}")
                        logger.info(f"Has _meta in mcp_response: {'_meta' in mcp_response}")

                        # Build JSON-RPC response with _meta support
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": mcp_response.get("result", {})
                        }

                        # Forward _meta field if present
                        if "_meta" in mcp_response and mcp_response["_meta"]:
                            response["_meta"] = mcp_response["_meta"]
                            logger.info(f"Forwarding _meta with keys: {list(mcp_response['_meta'].keys())}")
                        else:
                            logger.warning("No _meta field found in mcp_response")

                        logger.info(f"Response keys: {list(response.keys())}")

                        # Send JSON-RPC response
                        await manager.send_json(websocket, response)

                    elif method == "tools/list":
                        # List tools
                        tools = await mcp_client.list_tools()

                        # Send JSON-RPC response
                        await manager.send_json(websocket, {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {"tools": tools}
                        })

                    elif method == "skills/execute":
                        # Execute a skill
                        skill_name = params.get("skill_name")
                        context = params.get("context", {})

                        logger.info(f"Executing skill: {skill_name}")

                        # Execute skill with progress updates
                        result = await skill_executor.execute_skill(skill_name, context)

                        # Convert result to dict
                        response_data = {
                            "skill_name": result.skill_name,
                            "success": result.success,
                            "phases": [
                                {
                                    "phase_name": phase.phase_name,
                                    "success": phase.success,
                                    "output": phase.output,
                                    "error": phase.error
                                }
                                for phase in result.phases
                            ],
                            "final_output": result.final_output,
                            "error": result.error
                        }

                        # Send JSON-RPC response
                        await manager.send_json(websocket, {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": response_data
                        })

                    elif method == "skills/list":
                        # List available skills
                        skills = skill_manager.list_skills()
                        skills_data = [
                            {
                                "name": skill.name,
                                "description": skill.description
                            }
                            for skill in skills
                        ]

                        await manager.send_json(websocket, {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {"skills": skills_data}
                        })

                    else:
                        # Unknown method
                        await manager.send_json(websocket, {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}"
                            }
                        })

                except Exception as e:
                    logger.error(f"JSON-RPC error: {e}")
                    await manager.send_json(websocket, {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    })

            # Handle legacy simple message format
            else:
                msg_type = message.get("type")
                logger.info(f"Legacy message: {msg_type}")

                if msg_type == "ping":
                    await manager.send_json(websocket, {"type": "pong"})
                else:
                    await manager.send_json(websocket, {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}"
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected normally")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.on_event("startup")
async def startup():
    global skill_executor, mcp_client

    logger.info("=" * 60)
    logger.info("Learning System WebSocket Server")
    logger.info("=" * 60)
    logger.info(f"Skills directory: {config.skills_dir}")
    logger.info("Server starting...")

    # Initialize MCP HTTP client
    logger.info("Initializing MCP HTTP client...")
    mcp_client = MCPHTTPClient(base_url="http://localhost:8080")
    logger.info("[OK] MCP HTTP client initialized")

    # Load skills
    logger.info("Loading skills...")
    skill_manager.load_skills()
    logger.info(f"[OK] Loaded {len(skill_manager.list_skills())} skills")

    # Initialize skill executor
    skill_executor = SkillExecutor(mcp_client, skill_manager)
    logger.info("[OK] Skill executor initialized")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Server shutting down...")
    if mcp_client:
        await mcp_client.close()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
