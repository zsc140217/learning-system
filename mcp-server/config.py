"""
配置管理模块
加载环境变量和应用配置
"""
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # 项目路径
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent
    )

    # 数据目录
    data_dir: Path | None = Field(default=None)
    sessions_dir: Path | None = Field(default=None)
    projects_dir: Path | None = Field(default=None)
    knowledge_dir: Path | None = Field(default=None)

    # API配置
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-opus-5")

    # Memory MCP配置
    memory_mcp_host: str = Field(default="localhost")
    memory_mcp_port: int = Field(default=8080)

    # HTTP Server配置
    http_host: str = Field(default="0.0.0.0")
    http_port: int = Field(default=8080)

    # 测试配置
    test_project_path: Optional[str] = Field(default=None)

    # 日志配置
    log_level: str = Field(default="INFO")
    log_file: Optional[Path] = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 初始化数据目录
        if self.data_dir is None:
            self.data_dir = self.project_root / "data"

        if self.sessions_dir is None:
            self.sessions_dir = self.data_dir / "sessions"

        if self.projects_dir is None:
            self.projects_dir = self.data_dir / "projects"

        if self.knowledge_dir is None:
            self.knowledge_dir = self.data_dir / "knowledge"

        # 创建目录
        self._ensure_directories()

    def _ensure_directories(self):
        """确保所有必需的目录存在"""
        for directory in [
            self.data_dir,
            self.sessions_dir,
            self.projects_dir,
            self.knowledge_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
