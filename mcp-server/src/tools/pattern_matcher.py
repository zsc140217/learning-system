"""
PatternMatcher Tool - 代码模式匹配工具

模拟 ECC 的 Grep 功能，用于代码模式识别
"""
from pathlib import Path
from typing import List, Dict, Set
import re
import ast
import logging

logger = logging.getLogger(__name__)


class PatternMatcher:
    """代码模式匹配工具，提供类似 ECC Grep 的功能"""

    def __init__(self):
        """初始化 PatternMatcher"""
        pass

    def search_pattern(self, pattern: str, files: List[Path]) -> Dict[str, List[Dict]]:
        """
        在多个文件中搜索正则表达式模式

        Args:
            pattern: 正则表达式模式
            files: 要搜索的文件列表

        Returns:
            文件路径 -> 匹配结果列表的映射
        """
        results = {}
        regex = re.compile(pattern)

        for file_path in files:
            matches = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append({
                                'line_number': line_num,
                                'line': line.strip(),
                                'file': str(file_path)
                            })

                if matches:
                    results[str(file_path)] = matches

            except Exception as e:
                logger.debug(f"Error searching {file_path}: {e}")

        logger.info(f"Pattern '{pattern}' found in {len(results)} files")
        return results

    def detect_decorators(self, file_path: Path) -> List[str]:
        """
        检测 Python 文件中的装饰器

        Args:
            file_path: Python 文件路径

        Returns:
            装饰器列表，如 ['@server.tool', '@app.route']
        """
        decorators = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用 AST 解析
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for decorator in node.decorator_list:
                        # 提取装饰器名称
                        if isinstance(decorator, ast.Name):
                            decorators.append(f"@{decorator.id}")
                        elif isinstance(decorator, ast.Attribute):
                            # 处理 @app.route 形式
                            parts = []
                            current = decorator
                            while isinstance(current, ast.Attribute):
                                parts.insert(0, current.attr)
                                current = current.value
                            if isinstance(current, ast.Name):
                                parts.insert(0, current.id)
                            decorators.append(f"@{'.'.join(parts)}")
                        elif isinstance(decorator, ast.Call):
                            # 处理 @app.route('/path') 形式
                            if isinstance(decorator.func, ast.Attribute):
                                parts = []
                                current = decorator.func
                                while isinstance(current, ast.Attribute):
                                    parts.insert(0, current.attr)
                                    current = current.value
                                if isinstance(current, ast.Name):
                                    parts.insert(0, current.id)
                                decorators.append(f"@{'.'.join(parts)}")

        except Exception as e:
            logger.debug(f"Error parsing decorators in {file_path}: {e}")

        # 去重
        decorators = list(set(decorators))
        logger.debug(f"Found {len(decorators)} decorators in {file_path.name}")
        return decorators

    def detect_imports(self, file_path: Path) -> Dict[str, List[str]]:
        """
        检测 Python 文件中的 import 语句

        Args:
            file_path: Python 文件路径

        Returns:
            导入类型 -> 模块列表的映射
        """
        imports = {
            'standard': [],  # 标准库
            'third_party': [],  # 第三方库
            'local': []  # 本地模块
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        self._categorize_import(module, imports)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split('.')[0]
                        self._categorize_import(module, imports)

        except Exception as e:
            logger.debug(f"Error parsing imports in {file_path}: {e}")

        return imports

    def _categorize_import(self, module: str, imports: Dict[str, List[str]]):
        """将 import 分类到标准库、第三方库或本地模块"""
        # Python 标准库常见模块
        stdlib_modules = {
            'os', 'sys', 're', 'json', 'time', 'datetime', 'logging',
            'pathlib', 'typing', 'collections', 'itertools', 'functools',
            'asyncio', 'threading', 'multiprocessing', 'subprocess',
            'http', 'urllib', 'email', 'unittest', 'sqlite3'
        }

        if module in stdlib_modules:
            if module not in imports['standard']:
                imports['standard'].append(module)
        elif module.startswith('.') or module == 'src':
            if module not in imports['local']:
                imports['local'].append(module)
        else:
            if module not in imports['third_party']:
                imports['third_party'].append(module)

    def detect_naming_convention(self, files: List[Path]) -> Dict[str, str]:
        """
        检测项目的命名规范

        Args:
            files: 要分析的文件列表

        Returns:
            命名类型 -> 规范的映射
        """
        # 统计不同命名风格的出现次数
        file_naming = {'snake_case': 0, 'kebab-case': 0, 'PascalCase': 0, 'camelCase': 0}
        function_naming = {'snake_case': 0, 'camelCase': 0}
        class_naming = {'PascalCase': 0, 'snake_case': 0}

        # 分析文件命名
        for file_path in files:
            name = file_path.stem  # 不含扩展名的文件名
            if '_' in name and name.islower():
                file_naming['snake_case'] += 1
            elif '-' in name and name.islower():
                file_naming['kebab-case'] += 1
            elif name[0].isupper():
                file_naming['PascalCase'] += 1
            elif name[0].islower() and any(c.isupper() for c in name[1:]):
                file_naming['camelCase'] += 1

        # 分析函数和类命名（仅 Python 文件）
        py_files = [f for f in files if f.suffix == '.py']
        for file_path in py_files[:10]:  # 只分析前 10 个文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        name = node.name
                        if '_' in name:
                            function_naming['snake_case'] += 1
                        elif name[0].islower() and any(c.isupper() for c in name[1:]):
                            function_naming['camelCase'] += 1

                    elif isinstance(node, ast.ClassDef):
                        name = node.name
                        if name[0].isupper():
                            class_naming['PascalCase'] += 1
                        elif '_' in name:
                            class_naming['snake_case'] += 1

            except Exception as e:
                logger.debug(f"Error analyzing {file_path}: {e}")

        # 确定主导风格
        conventions = {
            'files': max(file_naming, key=file_naming.get) if sum(file_naming.values()) > 0 else 'unknown',
            'functions': max(function_naming, key=function_naming.get) if sum(function_naming.values()) > 0 else 'unknown',
            'classes': max(class_naming, key=class_naming.get) if sum(class_naming.values()) > 0 else 'unknown'
        }

        logger.info(f"Detected conventions: {conventions}")
        return conventions

    def count_async_patterns(self, file_path: Path) -> Dict[str, int]:
        """
        统计异步模式的使用

        Args:
            file_path: Python 文件路径

        Returns:
            异步模式统计
        """
        stats = {
            'async_functions': 0,
            'await_count': 0,
            'async_with': 0,
            'async_for': 0
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    stats['async_functions'] += 1
                elif isinstance(node, ast.Await):
                    stats['await_count'] += 1
                elif isinstance(node, ast.AsyncWith):
                    stats['async_with'] += 1
                elif isinstance(node, ast.AsyncFor):
                    stats['async_for'] += 1

        except Exception as e:
            logger.debug(f"Error analyzing async patterns in {file_path}: {e}")

        return stats

    def detect_error_handling_style(self, files: List[Path]) -> str:
        """
        检测错误处理风格

        Args:
            files: Python 文件列表

        Returns:
            错误处理风格描述
        """
        try_except_count = 0
        with_logging_count = 0

        for file_path in files[:10]:  # 分析前 10 个文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Try):
                        try_except_count += 1
                        # 检查是否有 logging
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                if isinstance(child.func, ast.Attribute):
                                    if child.func.attr in ['error', 'exception', 'warning']:
                                        with_logging_count += 1
                                        break

            except Exception:
                pass

        if try_except_count > 0:
            if with_logging_count / try_except_count > 0.5:
                return "try/except with logging"
            else:
                return "try/except"
        else:
            return "unknown"
