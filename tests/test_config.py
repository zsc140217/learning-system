"""配置模块测试"""
import sys
from pathlib import Path
import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))


def test_import_settings():
    """测试配置导入"""
    from config import settings
    
    assert settings is not None
    assert settings.project_root.exists()
    assert settings.data_dir.exists()


def test_data_directories_created():
    """测试数据目录创建"""
    from config import settings
    
    assert settings.sessions_dir.exists()
    assert settings.projects_dir.exists()
    assert settings.knowledge_dir.exists()


def test_default_values():
    """测试默认配置值"""
    from config import settings
    
    assert settings.anthropic_model == "claude-opus-5"
    assert settings.log_level == "INFO"
    assert settings.memory_mcp_host == "localhost"
    assert settings.memory_mcp_port == 8080
