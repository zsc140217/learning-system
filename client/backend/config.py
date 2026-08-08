"""
客户端配置管理
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """MCP Server 配置"""
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    cwd: Optional[str] = None
    env: dict[str, str] = Field(default_factory=dict)


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = "deepseek"  # deepseek | claude | openai
    api_key: str
    model: str = "deepseek-chat"
    base_url: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7


class ClientConfig(BaseModel):
    """客户端配置"""
    # MCP Server 配置
    mcp_server: MCPServerConfig

    # LLM 配置
    llm: LLMConfig

    # 路径配置
    skills_dir: Path = Field(default_factory=lambda: Path("skills"))
    data_dir: Path = Field(default_factory=lambda: Path("data"))

    # WebSocket 配置
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765

    # 任务轮询配置
    task_poll_interval: float = 2.0  # 秒
    task_timeout: float = 600.0  # 秒

    @classmethod
    def from_env(cls) -> "ClientConfig":
        """从环境变量加载配置"""
        mcp_server_path = Path(__file__).parent.parent.parent / "mcp-server"

        return cls(
            mcp_server=MCPServerConfig(
                name="learning-system",
                command="python",
                args=["server.py"],
                cwd=str(mcp_server_path),
                env={
                    "PYTHONPATH": str(mcp_server_path),
                    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", ""),
                }
            ),
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "deepseek"),
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                model=os.getenv("LLM_MODEL", "deepseek-chat"),
            )
        )


# 全局配置实例
config = ClientConfig.from_env()
