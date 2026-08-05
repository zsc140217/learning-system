"""
简易 Web 客户端 - HTTP API 层
提供 REST API 接口给浏览器调用
"""
import asyncio
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
from loguru import logger

# 导入 MCP Server
from server import (
    server,
    session_analyzer,
    memory_manager,
    learning_coach,
    startup as mcp_startup
)

app = FastAPI(title="Learning System Web Client")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


# ============ Request/Response Models ============

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tools_used: list[str] = []


class AnalyzeRequest(BaseModel):
    session_data: str
    session_id: Optional[str] = None


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"


# ============ DeepSeek API ============

async def call_deepseek(
    messages: list[Dict[str, str]],
    tools: Optional[list[Dict]] = None
) -> Dict[str, Any]:
    """调用 DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="DEEPSEEK_API_KEY 未配置"
        )

    async with httpx.AsyncClient() as client:
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30.0
        )

        if response.status_code != 200:
            logger.error(f"DeepSeek API 错误: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"DeepSeek API 调用失败: {response.text}"
            )

        return response.json()


# ============ MCP Tools Definition ============

def get_mcp_tools() -> list[Dict]:
    """获取 MCP 工具定义（OpenAI 格式）"""
    return [
        {
            "type": "function",
            "function": {
                "name": "analyze_session",
                "description": "分析会话内容，提取知识点",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_data": {
                            "type": "string",
                            "description": "会话内容（Markdown 格式）"
                        }
                    },
                    "required": ["session_data"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": "搜索知识图谱",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_knowledge",
                "description": "添加知识到知识图谱",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "知识内容"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "标签列表"
                        }
                    },
                    "required": ["content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "tasks_list",
                "description": "列出所有任务",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "tasks_create",
                "description": "创建新任务",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "任务标题"
                        },
                        "description": {
                            "type": "string",
                            "description": "任务描述"
                        }
                    },
                    "required": ["title", "description"]
                }
            }
        }
    ]


# ============ Tool Execution ============

async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """执行 MCP 工具"""
    tool_func = server.tools.get(tool_name)
    if not tool_func:
        raise HTTPException(
            status_code=404,
            detail=f"工具 {tool_name} 不存在"
        )

    try:
        result = await tool_func(**arguments)
        return result.data if hasattr(result, 'data') else result
    except Exception as e:
        logger.error(f"工具执行失败: {tool_name} - {e}")
        raise HTTPException(
            status_code=500,
            detail=f"工具执行失败: {str(e)}"
        )


# ============ API Endpoints ============

@app.on_event("startup")
async def startup_event():
    """启动时初始化 MCP Server"""
    logger.info("初始化 MCP Server...")
    await mcp_startup()
    logger.info("MCP Server 已就绪")


@app.get("/")
async def root():
    """返回前端页面"""
    return FileResponse("static/index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口
    支持工具调用（自动调用 MCP 工具）
    """
    messages = [
        {
            "role": "system",
            "content": "你是一个学习助手，帮助用户管理学习内容、知识图谱和任务。"
        },
        {
            "role": "user",
            "content": request.message
        }
    ]

    tools_used = []
    max_iterations = 5

    for _ in range(max_iterations):
        # 调用 DeepSeek
        response = await call_deepseek(messages, tools=get_mcp_tools())

        choice = response["choices"][0]
        message = choice["message"]

        # 如果没有工具调用，返回结果
        if not message.get("tool_calls"):
            return ChatResponse(
                reply=message["content"],
                session_id=request.session_id or "default",
                tools_used=tools_used
            )

        # 执行工具调用
        messages.append(message)

        for tool_call in message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            arguments = eval(tool_call["function"]["arguments"])

            logger.info(f"执行工具: {tool_name} - {arguments}")
            tools_used.append(tool_name)

            # 执行 MCP 工具
            result = await execute_tool(tool_name, arguments)

            # 添加工具结果到消息
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_name,
                "content": str(result)
            })

    # 超过最大迭代次数
    return ChatResponse(
        reply="抱歉，处理超时。请简化您的请求。",
        session_id=request.session_id or "default",
        tools_used=tools_used
    )


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    """分析会话内容"""
    result = await execute_tool(
        "analyze_session",
        {
            "session_data": request.session_data,
            "session_id": request.session_id
        }
    )
    return result


@app.get("/api/tasks")
async def list_tasks():
    """列出所有任务"""
    result = await execute_tool("tasks_list", {})
    return result


@app.post("/api/tasks")
async def create_task(request: TaskCreateRequest):
    """创建任务"""
    result = await execute_tool(
        "tasks_create",
        {
            "title": request.title,
            "description": request.description,
            "priority": request.priority
        }
    )
    return result


@app.get("/api/knowledge/search")
async def search_knowledge(query: str):
    """搜索知识"""
    result = await execute_tool("search_knowledge", {"query": query})
    return result


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "mcp_tools": len(server.tools),
        "deepseek_configured": bool(DEEPSEEK_API_KEY)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
