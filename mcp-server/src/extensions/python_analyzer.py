"""
Python Code Analyzer Extension

Analyzes Python source code for:
- Decorator patterns (FastAPI, Django, Flask)
- Type hints and annotations
- Async/await patterns
- Framework detection
"""

import ast
import os
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from .base_extension import Extension

logger = logging.getLogger(__name__)


class PythonAnalyzerExtension(Extension):
    """
    Extension for analyzing Python code structure and patterns.

    Capabilities:
    - Detect web frameworks (FastAPI, Django, Flask)
    - Extract decorator usage
    - Analyze type hints
    - Identify async/await patterns
    """

    @property
    def extension_id(self) -> str:
        return "io.learning-system.analyzer.python"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "Python Code Analyzer"

    @property
    def description(self) -> str:
        return "Analyzes Python code for decorators, type hints, and framework patterns"

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "analyze_decorators": True,
            "detect_framework": ["FastAPI", "Django", "Flask"],
            "extract_type_hints": True,
            "analyze_async_patterns": True,
            "supported_python_versions": ["3.8", "3.9", "3.10", "3.11", "3.12"]
        }

    def register_tools(self, server: Any):
        """Register Python analysis tools with the MCP server."""

        @server.tool("analyze_python_decorators")
        async def analyze_decorators(file_path: str) -> Dict[str, Any]:
            """
            Analyze decorator usage in a Python file.

            Args:
                file_path: Path to Python file

            Returns:
                Dictionary with decorator analysis results
            """
            try:
                decorators = self._extract_decorators(file_path)

                return {
                    "file": file_path,
                    "decorators": decorators,
                    "decorator_count": len(decorators),
                    "frameworks_detected": self._detect_frameworks(decorators)
                }
            except Exception as e:
                logger.error(f"Failed to analyze decorators in {file_path}: {e}")
                return {"error": str(e)}

        @server.tool("detect_python_framework")
        async def detect_framework(project_path: str) -> Dict[str, Any]:
            """
            Detect Python web framework used in project.

            Args:
                project_path: Path to project directory

            Returns:
                Dictionary with framework detection results
            """
            try:
                framework_info = self._detect_project_framework(project_path)

                return {
                    "project_path": project_path,
                    "framework": framework_info["framework"],
                    "confidence": framework_info["confidence"],
                    "evidence": framework_info["evidence"]
                }
            except Exception as e:
                logger.error(f"Failed to detect framework in {project_path}: {e}")
                return {"error": str(e)}

        @server.tool("extract_python_type_hints")
        async def extract_type_hints(file_path: str) -> Dict[str, Any]:
            """
            Extract type hints from a Python file.

            Args:
                file_path: Path to Python file

            Returns:
                Dictionary with type hint analysis
            """
            try:
                type_hints = self._extract_type_hints(file_path)

                return {
                    "file": file_path,
                    "functions_with_hints": type_hints["functions"],
                    "classes_with_hints": type_hints["classes"],
                    "coverage": type_hints["coverage"]
                }
            except Exception as e:
                logger.error(f"Failed to extract type hints from {file_path}: {e}")
                return {"error": str(e)}

        @server.tool("analyze_python_async")
        async def analyze_async_patterns(file_path: str) -> Dict[str, Any]:
            """
            Analyze async/await usage in a Python file.

            Args:
                file_path: Path to Python file

            Returns:
                Dictionary with async pattern analysis
            """
            try:
                async_info = self._analyze_async_patterns(file_path)

                return {
                    "file": file_path,
                    "async_functions": async_info["async_functions"],
                    "await_expressions": async_info["await_expressions"],
                    "async_comprehensions": async_info["async_comprehensions"]
                }
            except Exception as e:
                logger.error(f"Failed to analyze async patterns in {file_path}: {e}")
                return {"error": str(e)}

    def _extract_decorators(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract all decorators from a Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=file_path)

        decorators = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    decorator_info = {
                        "target": node.name,
                        "target_type": "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class",
                        "decorator": ast.unparse(decorator),
                        "line": decorator.lineno
                    }
                    decorators.append(decorator_info)

        return decorators

    def _detect_frameworks(self, decorators: List[Dict[str, Any]]) -> List[str]:
        """Detect frameworks based on decorator patterns."""
        frameworks = set()

        for dec in decorators:
            decorator_str = dec["decorator"]

            # FastAPI patterns
            if any(x in decorator_str for x in ["app.get", "app.post", "app.put", "app.delete", "APIRouter"]):
                frameworks.add("FastAPI")

            # Django patterns
            if any(x in decorator_str for x in ["login_required", "permission_required", "csrf_exempt"]):
                frameworks.add("Django")

            # Flask patterns
            if any(x in decorator_str for x in ["app.route", "blueprint.route"]):
                frameworks.add("Flask")

        return list(frameworks)

    def _detect_project_framework(self, project_path: str) -> Dict[str, Any]:
        """Detect framework by analyzing project structure and imports."""
        evidence = []
        framework_scores = {"FastAPI": 0, "Django": 0, "Flask": 0}

        # Check requirements.txt
        req_file = os.path.join(project_path, "requirements.txt")
        if os.path.exists(req_file):
            with open(req_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                if "fastapi" in content:
                    framework_scores["FastAPI"] += 3
                    evidence.append("fastapi in requirements.txt")
                if "django" in content:
                    framework_scores["Django"] += 3
                    evidence.append("django in requirements.txt")
                if "flask" in content:
                    framework_scores["Flask"] += 3
                    evidence.append("flask in requirements.txt")

        # Check for Django-specific files
        if os.path.exists(os.path.join(project_path, "manage.py")):
            framework_scores["Django"] += 2
            evidence.append("manage.py found")

        if os.path.exists(os.path.join(project_path, "settings.py")):
            framework_scores["Django"] += 1
            evidence.append("settings.py found")

        # Determine winner
        max_score = max(framework_scores.values())
        if max_score == 0:
            return {"framework": "Unknown", "confidence": 0.0, "evidence": []}

        detected = [fw for fw, score in framework_scores.items() if score == max_score][0]
        confidence = min(max_score / 5.0, 1.0)

        return {
            "framework": detected,
            "confidence": confidence,
            "evidence": evidence
        }

    def _extract_type_hints(self, file_path: str) -> Dict[str, Any]:
        """Extract type hint information from a Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=file_path)

        functions_with_hints = []
        classes_with_hints = []
        total_functions = 0
        hinted_functions = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1
                has_hints = node.returns is not None or any(
                    arg.annotation is not None for arg in node.args.args
                )

                if has_hints:
                    hinted_functions += 1
                    functions_with_hints.append({
                        "name": node.name,
                        "line": node.lineno,
                        "return_type": ast.unparse(node.returns) if node.returns else None,
                        "param_types": [
                            ast.unparse(arg.annotation) if arg.annotation else None
                            for arg in node.args.args
                        ]
                    })

            elif isinstance(node, ast.ClassDef):
                # Check if class has type-hinted attributes
                has_hints = any(
                    isinstance(item, ast.AnnAssign) for item in node.body
                )
                if has_hints:
                    classes_with_hints.append({
                        "name": node.name,
                        "line": node.lineno
                    })

        coverage = hinted_functions / total_functions if total_functions > 0 else 0.0

        return {
            "functions": functions_with_hints,
            "classes": classes_with_hints,
            "coverage": round(coverage, 2)
        }

    def _analyze_async_patterns(self, file_path: str) -> Dict[str, Any]:
        """Analyze async/await usage patterns."""
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=file_path)

        async_functions = []
        await_expressions = []
        async_comprehensions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                async_functions.append({
                    "name": node.name,
                    "line": node.lineno
                })

            elif isinstance(node, ast.Await):
                await_expressions.append({
                    "expression": ast.unparse(node.value),
                    "line": node.lineno
                })

            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                if any(isinstance(gen, ast.comprehension) and gen.is_async for gen in node.generators):
                    async_comprehensions.append({
                        "type": node.__class__.__name__,
                        "line": node.lineno
                    })

        return {
            "async_functions": async_functions,
            "await_expressions": await_expressions,
            "async_comprehensions": async_comprehensions
        }
