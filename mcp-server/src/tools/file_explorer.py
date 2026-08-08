"""
FileExplorer Tool - 文件系统探索工具

模拟 ECC 的 Glob + Read 功能，用于项目结构分析
"""
from pathlib import Path
from typing import List, Dict, Optional
import fnmatch
import logging

logger = logging.getLogger(__name__)


class FileExplorer:
    """文件系统探索工具，提供类似 ECC Glob/Read 的功能"""

    def __init__(self, root_path: str):
        """
        初始化 FileExplorer

        Args:
            root_path: 项目根目录路径
        """
        self.root = Path(root_path).resolve()
        if not self.root.exists():
            raise ValueError(f"Project path does not exist: {root_path}")

        # 默认忽略的目录
        self.ignore_dirs = {
            'node_modules', 'vendor', '.git', 'dist', 'build',
            '__pycache__', '.next', 'venv', 'env', '.venv',
            '.pytest_cache', '.mypy_cache', 'htmlcov'
        }

    def glob_files(self, pattern: str) -> List[Path]:
        """
        查找匹配模式的文件

        Args:
            pattern: glob 模式，如 "**/*.py", "requirements.txt"

        Returns:
            匹配的文件路径列表
        """
        try:
            # 使用 Path.rglob 进行递归搜索
            if "**" in pattern:
                files = list(self.root.rglob(pattern.replace("**/", "")))
            else:
                files = list(self.root.glob(pattern))

            # 过滤掉忽略目录中的文件
            filtered = []
            for f in files:
                if f.is_file() and not any(
                    ignored in f.parts for ignored in self.ignore_dirs
                ):
                    filtered.append(f)

            logger.debug(f"Glob pattern '{pattern}' found {len(filtered)} files")
            return filtered

        except Exception as e:
            logger.error(f"Error in glob_files: {e}")
            return []

    def read_file(self, path: Path, max_lines: int = 100) -> str:
        """
        读取文件内容（前 N 行）

        Args:
            path: 文件路径（Path 对象或字符串）
            max_lines: 最大读取行数，0 表示读取全部

        Returns:
            文件内容字符串
        """
        # 确保 path 是 Path 对象
        if isinstance(path, str):
            path = Path(path)

        try:
            with open(path, 'r', encoding='utf-8') as f:
                if max_lines == 0:
                    content = f.read()
                else:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line)
                    content = ''.join(lines)

            logger.debug(f"Read {len(content)} chars from {path.name}")
            return content

        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    if max_lines == 0:
                        content = f.read()
                    else:
                        lines = [f.readline() for _ in range(max_lines)]
                        content = ''.join(lines)
                return content
            except Exception as e:
                logger.error(f"Failed to read {path}: {e}")
                return ""

        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
            return ""

    def list_directory(self, depth: int = 2) -> List[str]:
        """
        列出目录结构（只看前 N 层）

        Args:
            depth: 目录深度

        Returns:
            目录路径列表（相对于根目录）
        """
        dirs = []

        def walk_depth(current_path: Path, current_depth: int):
            if current_depth > depth:
                return

            try:
                for item in current_path.iterdir():
                    # 跳过隐藏文件和忽略目录
                    if item.name.startswith('.') or item.name in self.ignore_dirs:
                        continue

                    if item.is_dir():
                        rel_path = item.relative_to(self.root)
                        dirs.append(str(rel_path))
                        walk_depth(item, current_depth + 1)

            except PermissionError:
                pass

        walk_depth(self.root, 1)
        logger.debug(f"Listed {len(dirs)} directories (depth={depth})")
        return sorted(dirs)

    def detect_config_files(self) -> Dict[str, Path]:
        """
        检测项目配置文件

        Returns:
            配置文件类型 -> 路径的映射
        """
        config_patterns = {
            'python_pip': ['requirements.txt', 'Pipfile', 'pyproject.toml'],
            'python_poetry': ['poetry.lock'],
            'nodejs_npm': ['package.json', 'package-lock.json'],
            'nodejs_yarn': ['yarn.lock'],
            'nodejs_pnpm': ['pnpm-lock.yaml'],
            'go': ['go.mod', 'go.sum'],
            'rust': ['Cargo.toml', 'Cargo.lock'],
            'java_maven': ['pom.xml'],
            'java_gradle': ['build.gradle', 'build.gradle.kts'],
            'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
            'git': ['.gitignore', '.gitattributes'],
            'ci_github': ['.github/workflows'],
            'env': ['.env', '.env.example', '.env.local']
        }

        detected = {}

        for config_type, patterns in config_patterns.items():
            for pattern in patterns:
                # 直接在根目录查找
                candidate = self.root / pattern
                if candidate.exists():
                    detected[config_type] = candidate
                    break

        logger.info(f"Detected {len(detected)} config file types")
        return detected

    def find_entry_points(self) -> List[Path]:
        """
        查找可能的入口文件

        Returns:
            入口文件路径列表
        """
        entry_patterns = [
            'main.py', 'main.ts', 'main.go', 'main.rs',
            'index.js', 'index.ts', 'index.html',
            'app.py', 'app.js', 'server.py', 'server.js',
            'manage.py',  # Django
            '__main__.py'
        ]

        # 特殊目录
        special_dirs = ['cmd', 'src/main']

        entry_points = []

        # 在根目录和 src/ 目录查找
        search_dirs = [self.root, self.root / 'src', self.root / 'mcp-server']

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for pattern in entry_patterns:
                candidate = search_dir / pattern
                if candidate.exists() and candidate.is_file():
                    entry_points.append(candidate)

        # 查找特殊目录
        for special in special_dirs:
            special_path = self.root / special
            if special_path.exists() and special_path.is_dir():
                # 查找该目录下的 main.* 文件
                for entry_file in special_path.glob('main.*'):
                    if entry_file.is_file():
                        entry_points.append(entry_file)

        # 去重
        entry_points = list(set(entry_points))
        logger.info(f"Found {len(entry_points)} entry points")
        return entry_points

    def get_file_statistics(self, extension: str = ".py") -> Dict[str, int]:
        """
        获取文件统计信息

        Args:
            extension: 文件扩展名

        Returns:
            统计信息字典
        """
        files = self.glob_files(f"**/*{extension}")

        total_lines = 0
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    total_lines += sum(1 for _ in file)
            except:
                pass

        return {
            'total_files': len(files),
            'total_lines': total_lines,
            'avg_lines_per_file': total_lines // len(files) if files else 0
        }
