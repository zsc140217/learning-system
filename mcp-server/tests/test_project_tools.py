"""
项目分析工具单元测试
测试 project/* 原子化工具
"""
import pytest
import asyncio
from pathlib import Path
import sys
import os

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.file_explorer import FileExplorer
from src.tools.pattern_matcher import PatternMatcher


class TestProjectDetectFramework:
    """测试 project/detect_framework 工具"""

    @pytest.fixture
    def test_project_path(self):
        """返回测试项目路径"""
        return str(project_root)

    @pytest.mark.asyncio
    async def test_detect_fastapi_framework(self, test_project_path):
        """测试检测 FastAPI 框架"""
        explorer = FileExplorer(test_project_path)
        config_files = explorer.detect_config_files()

        # 检查是否检测到 requirements.txt
        assert 'python_pip' in config_files or 'python_poetry' in config_files

        # 读取依赖文件
        if 'python_pip' in config_files:
            req_file = config_files['python_pip']
            content = req_file.read_text(encoding='utf-8').lower()

            # 检查是否包含 fastapi
            assert 'fastapi' in content or 'fastmcp' in content

    @pytest.mark.asyncio
    async def test_detect_unknown_framework(self, tmp_path):
        """测试检测未知框架"""
        # 创建空项目目录
        explorer = FileExplorer(str(tmp_path))
        config_files = explorer.detect_config_files()

        # 空项目应该没有配置文件
        assert len(config_files) == 0


class TestProjectScanStructure:
    """测试 project/scan_structure 工具"""

    @pytest.fixture
    def test_project_path(self):
        """返回测试项目路径"""
        return str(project_root)

    @pytest.mark.asyncio
    async def test_scan_directory_structure(self, test_project_path):
        """测试扫描目录结构"""
        explorer = FileExplorer(test_project_path)
        directories = explorer.list_directory(depth=2)

        # 检查是否返回了目录列表
        assert isinstance(directories, list)
        assert len(directories) > 0

        # 检查是否包含 src 目录
        assert any('src' in d for d in directories)

    @pytest.mark.asyncio
    async def test_find_entry_points(self, test_project_path):
        """测试查找入口文件"""
        explorer = FileExplorer(test_project_path)
        entry_points = explorer.find_entry_points()

        # 检查是否找到了入口文件
        assert len(entry_points) > 0

        # 检查是否包含 server.py
        entry_names = [ep.name for ep in entry_points]
        assert 'server.py' in entry_names or 'main.py' in entry_names

    @pytest.mark.asyncio
    async def test_glob_python_files(self, test_project_path):
        """测试查找 Python 文件"""
        explorer = FileExplorer(test_project_path)
        py_files = explorer.glob_files("**/*.py")

        # 检查是否找到了 Python 文件
        assert len(py_files) > 0

        # 检查是否包含 server.py
        file_names = [f.name for f in py_files]
        assert 'server.py' in file_names


class TestProjectAnalyzeDependencies:
    """测试 project/analyze_dependencies 工具"""

    @pytest.fixture
    def test_project_path(self):
        """返回测试项目路径"""
        return str(project_root)

    @pytest.mark.asyncio
    async def test_analyze_python_dependencies(self, test_project_path):
        """测试分析 Python 依赖"""
        explorer = FileExplorer(test_project_path)
        config_files = explorer.detect_config_files()

        if 'python_pip' in config_files:
            req_file = config_files['python_pip']
            lines = req_file.read_text(encoding='utf-8').splitlines()

            dependencies = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '==' in line:
                        name, version = line.split('==', 1)
                        dependencies.append({"name": name.strip(), "version": version.strip()})

            # 检查是否解析到依赖
            assert len(dependencies) > 0

            # 检查是否包含核心依赖
            dep_names = [d['name'] for d in dependencies]
            assert any('fastmcp' in name.lower() or 'fastapi' in name.lower() for name in dep_names)


class TestProjectExtractPatterns:
    """测试 project/extract_patterns 工具"""

    @pytest.fixture
    def test_project_path(self):
        """返回测试项目路径"""
        return str(project_root)

    @pytest.mark.asyncio
    async def test_detect_naming_convention(self, test_project_path):
        """测试检测命名规范"""
        explorer = FileExplorer(test_project_path)
        matcher = PatternMatcher()

        py_files = explorer.glob_files("**/*.py")[:20]

        if py_files:
            naming = matcher.detect_naming_convention([Path(test_project_path) / f for f in py_files])

            # 检查命名规范（返回字典）
            assert isinstance(naming, dict)
            assert 'files' in naming
            assert 'functions' in naming
            assert 'classes' in naming

    @pytest.mark.asyncio
    async def test_count_async_patterns(self, test_project_path):
        """测试统计异步模式"""
        explorer = FileExplorer(test_project_path)
        matcher = PatternMatcher()

        # 测试 server.py 文件
        server_file = Path(test_project_path) / 'server.py'
        if server_file.exists():
            async_stats = matcher.count_async_patterns(server_file)

            # server.py 应该包含异步函数（返回字典）
            assert isinstance(async_stats, dict)
            assert 'async_functions' in async_stats
            assert async_stats['async_functions'] > 0

    @pytest.mark.asyncio
    async def test_detect_decorators(self, test_project_path):
        """测试检测装饰器"""
        explorer = FileExplorer(test_project_path)
        matcher = PatternMatcher()

        # 测试 server.py 文件
        server_file = Path(test_project_path) / 'server.py'
        if server_file.exists():
            decorators = matcher.detect_decorators(server_file)

            # server.py 应该包含装饰器
            assert len(decorators) > 0

            # 检查是否包含 @server.tool
            assert any('@server.tool' in dec for dec in decorators)


class TestFileExplorer:
    """测试 FileExplorer 工具类"""

    @pytest.fixture
    def test_project_path(self):
        """返回测试项目路径"""
        return str(project_root)

    def test_detect_config_files(self, test_project_path):
        """测试检测配置文件"""
        explorer = FileExplorer(test_project_path)
        config_files = explorer.detect_config_files()

        # 检查是否检测到配置文件
        assert isinstance(config_files, dict)
        assert len(config_files) > 0

        # 检查是否检测到 Python 配置
        assert 'python_pip' in config_files or 'python_poetry' in config_files

    def test_read_file_with_limit(self, test_project_path):
        """测试限制行数读取文件"""
        explorer = FileExplorer(test_project_path)

        # 读取 server.py 前 10 行
        content = explorer.read_file('server.py', max_lines=10)

        # 检查是否读取成功
        assert isinstance(content, str)
        assert len(content) > 0

        # 检查行数限制（读取10行，split后可能有11个元素因为最后一个\n）
        lines = content.split('\n')
        assert len(lines) <= 11  # 允许最后一个空行

    def test_list_directory(self, test_project_path):
        """测试列出目录"""
        explorer = FileExplorer(test_project_path)
        directories = explorer.list_directory(depth=1)

        # 检查是否返回了目录列表
        assert isinstance(directories, list)
        assert len(directories) > 0


class TestPatternMatcher:
    """测试 PatternMatcher 工具类"""

    @pytest.fixture
    def test_project_path(self):
        """返回测试项目路径"""
        return str(project_root)

    def test_detect_imports(self, test_project_path):
        """测试检测 import 语句"""
        matcher = PatternMatcher()
        server_file = Path(test_project_path) / 'server.py'

        if server_file.exists():
            imports = matcher.detect_imports(server_file)

            # 检查是否检测到 import（返回字典）
            assert isinstance(imports, dict)
            assert 'standard' in imports
            assert 'third_party' in imports
            assert 'local' in imports

            # 检查是否包含 asyncio（在标准库中）
            assert 'asyncio' in imports['standard']


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
