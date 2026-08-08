"""
Project Analyzer Sub-Agent

使用 DeepSeek API + project-deep-analyzer Skill 进行深度项目分析。

核心思路（学习 ECC）：
1. 读取 Skill 文档（方法论）
2. 注册工具到 DeepSeek（FileExplorer, PatternMatcher）
3. 构建 Prompt：Skill + 项目路径
4. DeepSeek 自主执行 6 个阶段
5. 返回结构化 JSON

这是一个独立的子 Agent，在隔离的上下文中执行，不污染主对话。
"""
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging

from ..llm.deepseek_client import DeepSeekClient
from ..tools.file_explorer import FileExplorer
from ..tools.pattern_matcher import PatternMatcher

logger = logging.getLogger(__name__)


class ProjectAnalyzer:
    """
    项目深度分析器（Sub-Agent 模式）

    工作流程：
    1. 加载 project-deep-analyzer Skill
    2. 注册工具（FileExplorer, PatternMatcher）
    3. 调用 DeepSeek API（带工具调用）
    4. DeepSeek 按照 Skill 自主分析
    5. 返回结构化 JSON
    """

    SKILL_PATH = Path(__file__).parent / "prompts" / "project_deep_analyzer_skill.md"

    def __init__(self, project_path: str):
        """
        初始化项目分析器

        Args:
            project_path: 项目根目录路径
        """
        self.project_path = Path(project_path).resolve()

        if not self.project_path.exists():
            raise ValueError(f"Project path does not exist: {self.project_path}")

        # 初始化工具
        self.file_explorer = FileExplorer(str(self.project_path))
        self.pattern_matcher = PatternMatcher()

        # 初始化 DeepSeek 客户端
        self.deepseek_client = DeepSeekClient()

        logger.info(f"ProjectAnalyzer initialized for {self.project_path}")

    async def analyze(self, deep_analysis: bool = True) -> Dict[str, Any]:
        """
        执行完整的项目分析

        Args:
            deep_analysis: 是否启用深度分析（Phase 4, Phase 6 需要 LLM）

        Returns:
            分析结果字典
        """
        logger.info(f"Starting project analysis (deep={deep_analysis})")

        try:
            # 1. 读取 Skill 文档
            skill_content = self._load_skill()
            logger.info(f"Loaded skill document: {len(skill_content)} chars")

            # 2. 注册工具
            self._register_tools()
            logger.info("Tools registered to DeepSeek")

            # 3. 构建 Prompt
            prompt = self._build_prompt(skill_content, deep_analysis)
            logger.info("Prompt built")

            # 4. 调用 DeepSeek API
            logger.info("Calling DeepSeek API with tools...")
            response = await self.deepseek_client.chat_with_tools(
                prompt=prompt,
                max_iterations=20  # 允许多轮工具调用
            )

            # 5. 解析响应
            result = self._parse_response(response)
            logger.info(f"Analysis completed in {response.get('iterations', 0)} iterations")

            return result

        except Exception as e:
            logger.error(f"Error during project analysis: {e}", exc_info=True)
            return {
                "error": str(e),
                "project_path": str(self.project_path),
                "status": "failed"
            }
        finally:
            # 清理资源
            await self.deepseek_client.close()

    def _load_skill(self) -> str:
        """加载 Skill 文档"""
        if not self.SKILL_PATH.exists():
            raise FileNotFoundError(f"Skill file not found: {self.SKILL_PATH}")

        return self.SKILL_PATH.read_text(encoding='utf-8')

    def _register_tools(self):
        """注册工具到 DeepSeek"""

        # 1. FileExplorer 工具
        self.deepseek_client.register_tool(
            name="glob_files",
            func=self.file_explorer.glob_files,
            spec={
                "name": "glob_files",
                "description": "Find files matching a glob pattern (e.g., '**/*.py', 'requirements.txt')",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern to match files"
                        }
                    },
                    "required": ["pattern"]
                }
            }
        )

        self.deepseek_client.register_tool(
            name="read_file",
            func=self.file_explorer.read_file,
            spec={
                "name": "read_file",
                "description": "Read file content with optional line limit",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to project root"
                        },
                        "max_lines": {
                            "type": "integer",
                            "description": "Maximum number of lines to read (default: 100)",
                            "default": 100
                        }
                    },
                    "required": ["path"]
                }
            }
        )

        self.deepseek_client.register_tool(
            name="list_directory",
            func=self.file_explorer.list_directory,
            spec={
                "name": "list_directory",
                "description": "List directory structure up to specified depth",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "depth": {
                            "type": "integer",
                            "description": "Directory depth to list (default: 2)",
                            "default": 2
                        }
                    }
                }
            }
        )

        self.deepseek_client.register_tool(
            name="detect_config_files",
            func=self.file_explorer.detect_config_files,
            spec={
                "name": "detect_config_files",
                "description": "Detect common configuration files (package.json, requirements.txt, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        )

        self.deepseek_client.register_tool(
            name="find_entry_points",
            func=self.file_explorer.find_entry_points,
            spec={
                "name": "find_entry_points",
                "description": "Find likely entry point files (main.py, server.py, index.js, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        )

        # 2. PatternMatcher 工具
        def detect_decorators_wrapper(file_path: str):
            """Wrapper to convert string path to Path object"""
            return self.pattern_matcher.detect_decorators(Path(self.project_path) / file_path)

        self.deepseek_client.register_tool(
            name="detect_decorators",
            func=detect_decorators_wrapper,
            spec={
                "name": "detect_decorators",
                "description": "Detect decorators in a Python file (@app.route, @server.tool, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Python file path relative to project root"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        )

        def detect_imports_wrapper(file_path: str):
            """Wrapper to convert string path to Path object"""
            return self.pattern_matcher.detect_imports(Path(self.project_path) / file_path)

        self.deepseek_client.register_tool(
            name="detect_imports",
            func=detect_imports_wrapper,
            spec={
                "name": "detect_imports",
                "description": "Detect import statements in a Python file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Python file path relative to project root"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        )

        def count_async_patterns_wrapper(file_path: str):
            """Wrapper to convert string path to Path object"""
            return self.pattern_matcher.count_async_patterns(Path(self.project_path) / file_path)

        self.deepseek_client.register_tool(
            name="count_async_patterns",
            func=count_async_patterns_wrapper,
            spec={
                "name": "count_async_patterns",
                "description": "Count async/await patterns in a Python file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Python file path relative to project root"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        )

    def _build_prompt(self, skill_content: str, deep_analysis: bool) -> str:
        """构建 Prompt"""

        prompt = f"""You are a professional code analyst. Your task is to analyze a project following the methodology defined in the skill document below.

# Skill Document: project-deep-analyzer

{skill_content}

---

# Your Task

Analyze the project at: {self.project_path}

## Instructions

1. Follow the 6-phase workflow defined in the skill document
2. Use the provided tools to explore the project:
   - glob_files: Find files matching patterns
   - read_file: Read file content (limit to 50-100 lines for efficiency)
   - list_directory: Get directory structure
   - detect_config_files: Find configuration files
   - find_entry_points: Find entry point files
   - detect_decorators: Find Python decorators
   - detect_imports: Find Python imports
   - count_async_patterns: Count async/await usage

3. For each phase, output your findings in structured format

4. Phase 4 (Execution Path Tracing) and Phase 6 (Learning Path Generation) require deeper reasoning:
   - Trace actual code execution paths
   - Identify design patterns in use
   - Generate learning-oriented insights

5. Deep analysis mode: {'ENABLED' if deep_analysis else 'DISABLED'}
   {'- Perform full Phase 4 and Phase 6 analysis' if deep_analysis else '- Skip Phase 4, provide basic Phase 6'}

## Output Format

Your final output MUST be valid JSON with this structure:

```json
{{
  "project_overview": {{
    "name": "string",
    "purpose": "string",
    "tech_stack": ["array"],
    "architecture": "string"
  }},
  "phases": {{
    "phase1_reconnaissance": {{ ... }},
    "phase2_architecture": {{ ... }},
    "phase3_entry_points": {{ ... }},
    "phase4_execution_flow": {{ ... }},
    "phase5_conventions": {{ ... }},
    "phase6_learning_path": {{
      "key_concepts": [...],
      "learning_path": [...],
      "interview_highlights": [...]
    }}
  }}
}}
```

Begin analysis now. Use tools to explore, then provide your JSON report.
"""

        return prompt

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析 DeepSeek 响应"""

        content = response.get("content", "")

        if not content:
            return {
                "error": "Empty response from DeepSeek",
                "raw_response": response
            }

        # 尝试提取 JSON
        try:
            # 如果响应是 Markdown 代码块包裹的 JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                # 假设整个响应是 JSON
                json_str = content.strip()

            result = json.loads(json_str)
            result["analysis_metadata"] = {
                "iterations": response.get("iterations", 0),
                "model": "deepseek-chat",
                "project_path": str(self.project_path)
            }

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {e}")
            return {
                "error": "Failed to parse JSON response",
                "raw_content": content,
                "parse_error": str(e)
            }
