"""
项目状态分析工具
整合多个项目分析工具，生成结构化的项目状态报告
"""
import os
from typing import Dict, Any, List
from pathlib import Path


class ProjectStatusAnalyzer:
    """项目状态分析器，整合 project/* 工具生成综合报告"""

    def __init__(self, tools_registry: Dict[str, Any]):
        """
        初始化分析器

        Args:
            tools_registry: MCP工具注册表，包含所有可调用的工具
        """
        self.tools = tools_registry

    async def analyze(
        self,
        project_path: str,
        depth: int = 3,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        执行完整的项目分析

        Args:
            project_path: 项目根目录路径
            depth: 目录扫描深度
            output_format: 输出格式 (json/markdown)

        Returns:
            结构化的项目分析报告
        """
        # 验证项目路径
        if not os.path.exists(project_path):
            raise ValueError(f"项目路径不存在: {project_path}")

        report = {
            "project_path": project_path,
            "project_name": Path(project_path).name,
            "analysis_phases": {}
        }

        # Phase 1: 框架检测
        framework_result = await self._detect_framework(project_path)
        report["analysis_phases"]["framework_detection"] = framework_result

        # Phase 2: 结构扫描
        structure_result = await self._scan_structure(project_path, depth)
        report["analysis_phases"]["structure_scan"] = structure_result

        # Phase 3: 依赖分析
        dependencies_result = await self._analyze_dependencies(project_path)
        report["analysis_phases"]["dependencies_analysis"] = dependencies_result

        # Phase 4: 代码模式提取
        patterns_result = await self._extract_patterns(project_path)
        report["analysis_phases"]["pattern_extraction"] = patterns_result

        # 生成综合报告
        summary = self._generate_summary(report)
        report["summary"] = summary

        # 生成待办事项
        todos = self._generate_todos(report)
        report["todos"] = todos

        # 生成学习建议
        learning_suggestions = self._generate_learning_suggestions(report)
        report["learning_suggestions"] = learning_suggestions

        # 格式化输出
        if output_format == "markdown":
            return {"markdown": self._format_as_markdown(report)}

        return report

    async def _detect_framework(self, project_path: str) -> Dict[str, Any]:
        """调用 project/detect_framework 工具"""
        tool = self.tools.get("project/detect_framework")
        if not tool:
            return {"error": "工具未找到: project/detect_framework"}

        try:
            result = await tool(project_path=project_path)
            return result.data if hasattr(result, 'data') else result
        except Exception as e:
            return {"error": f"框架检测失败: {str(e)}"}

    async def _scan_structure(self, project_path: str, depth: int) -> Dict[str, Any]:
        """调用 project/scan_structure 工具"""
        tool = self.tools.get("project/scan_structure")
        if not tool:
            return {"error": "工具未找到: project/scan_structure"}

        try:
            result = await tool(project_path=project_path, depth=depth)
            return result.data if hasattr(result, 'data') else result
        except Exception as e:
            return {"error": f"结构扫描失败: {str(e)}"}

    async def _analyze_dependencies(self, project_path: str) -> Dict[str, Any]:
        """调用 project/analyze_dependencies 工具"""
        tool = self.tools.get("project/analyze_dependencies")
        if not tool:
            return {"error": "工具未找到: project/analyze_dependencies"}

        try:
            result = await tool(project_path=project_path)
            return result.data if hasattr(result, 'data') else result
        except Exception as e:
            return {"error": f"依赖分析失败: {str(e)}"}

    async def _extract_patterns(self, project_path: str) -> Dict[str, Any]:
        """调用 project/extract_patterns 工具"""
        tool = self.tools.get("project/extract_patterns")
        if not tool:
            return {"error": "工具未找到: project/extract_patterns"}

        try:
            result = await tool(
                project_path=project_path,
                focus=["decorators", "async", "inheritance", "patterns"]
            )
            return result.data if hasattr(result, 'data') else result
        except Exception as e:
            return {"error": f"模式提取失败: {str(e)}"}

    def _generate_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """生成项目摘要"""
        framework_data = report["analysis_phases"].get("framework_detection", {})
        structure_data = report["analysis_phases"].get("structure_scan", {})
        dependencies_data = report["analysis_phases"].get("dependencies_analysis", {})

        # 技术栈提取
        tech_stack = []
        if framework_data.get("framework"):
            tech_stack.append(f"{framework_data.get('language', 'Unknown')} - {framework_data['framework']}")

        # 计算复杂度
        total_deps = dependencies_data.get("total_count", 0)
        complexity = "简单" if total_deps < 10 else "中等" if total_deps < 30 else "复杂"

        # 完成度估算
        directories = structure_data.get("directories", [])
        has_tests = any("test" in str(d).lower() for d in directories)
        has_docs = any("docs" in str(d).lower() or "doc" in str(d).lower() for d in directories)

        completion_score = 0
        if framework_data.get("confidence", 0) > 0.7:
            completion_score += 30
        if has_tests:
            completion_score += 30
        if has_docs:
            completion_score += 20
        if total_deps > 0:
            completion_score += 20

        return {
            "project_name": report["project_name"],
            "tech_stack": tech_stack,
            "complexity": complexity,
            "completion_percentage": min(completion_score, 100),
            "framework_confidence": framework_data.get("confidence", 0),
            "total_dependencies": total_deps,
            "has_tests": has_tests,
            "has_documentation": has_docs
        }

    def _generate_todos(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据分析结果生成待办事项"""
        todos = []

        summary = report.get("summary", {})
        structure_data = report["analysis_phases"].get("structure_scan", {})

        # 检查测试覆盖
        if not summary.get("has_tests"):
            todos.append({
                "priority": "high",
                "category": "测试",
                "task": "添加测试框架和单元测试",
                "reason": "项目缺少测试目录"
            })

        # 检查文档
        if not summary.get("has_documentation"):
            todos.append({
                "priority": "medium",
                "category": "文档",
                "task": "创建项目文档和README",
                "reason": "项目缺少文档目录"
            })

        # 检查框架置信度
        if summary.get("framework_confidence", 0) < 0.7:
            todos.append({
                "priority": "high",
                "category": "架构",
                "task": "明确项目技术栈和入口点",
                "reason": f"框架检测置信度低 ({summary.get('framework_confidence', 0):.2f})"
            })

        # 检查配置文件
        key_files = structure_data.get("key_files", [])
        if not any("requirements.txt" in str(f) or "package.json" in str(f) for f in key_files):
            todos.append({
                "priority": "high",
                "category": "配置",
                "task": "添加依赖管理文件",
                "reason": "未找到 requirements.txt 或 package.json"
            })

        # 依赖复杂度警告
        if summary.get("total_dependencies", 0) > 50:
            todos.append({
                "priority": "low",
                "category": "优化",
                "task": "审查依赖树，移除不必要的依赖",
                "reason": f"依赖数量较多 ({summary.get('total_dependencies')})"
            })

        return todos

    def _generate_learning_suggestions(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成学习建议"""
        suggestions = []

        framework_data = report["analysis_phases"].get("framework_detection", {})
        patterns_data = report["analysis_phases"].get("pattern_extraction", {})
        dependencies_data = report["analysis_phases"].get("dependencies_analysis", {})

        framework = framework_data.get("framework")
        language = framework_data.get("language")

        # 基础学习路径
        if framework and language:
            suggestions.append({
                "level": "基础",
                "topic": f"{language} 和 {framework} 基础",
                "resources": [
                    f"官方文档: {framework}",
                    f"{language} 最佳实践"
                ],
                "estimated_time": "1-2周"
            })

        # 核心依赖学习
        core_deps = dependencies_data.get("dependencies", [])
        if core_deps:
            core_libs = [dep["name"] for dep in core_deps[:3] if dep.get("type") == "core"]
            if core_libs:
                suggestions.append({
                    "level": "进阶",
                    "topic": "核心依赖库深入",
                    "resources": core_libs,
                    "estimated_time": "2-3周"
                })

        # 设计模式学习
        patterns = patterns_data.get("patterns", [])
        if patterns:
            pattern_types = list(set([p.get("type") for p in patterns if p.get("type")]))
            if pattern_types:
                suggestions.append({
                    "level": "高级",
                    "topic": "项目中的设计模式",
                    "resources": [
                        f"学习 {', '.join(pattern_types)} 模式",
                        "阅读项目代码实现"
                    ],
                    "estimated_time": "1-2周"
                })

        # 面试准备
        suggestions.append({
            "level": "面试准备",
            "topic": "STAR 法则项目陈述",
            "resources": [
                "准备项目背景和目标",
                "梳理技术难点和解决方案",
                "总结项目亮点和成果"
            ],
            "estimated_time": "3-5天"
        })

        return suggestions

    def _format_as_markdown(self, report: Dict[str, Any]) -> str:
        """将报告格式化为 Markdown"""
        md_lines = []

        # 标题
        md_lines.append(f"# 项目分析报告: {report['project_name']}\n")
        md_lines.append(f"**项目路径**: `{report['project_path']}`\n")

        # 摘要
        summary = report.get("summary", {})
        md_lines.append("## 项目摘要\n")
        md_lines.append(f"- **技术栈**: {', '.join(summary.get('tech_stack', ['未知']))}")
        md_lines.append(f"- **复杂度**: {summary.get('complexity', 'N/A')}")
        md_lines.append(f"- **完成度**: {summary.get('completion_percentage', 0)}%")
        md_lines.append(f"- **依赖数量**: {summary.get('total_dependencies', 0)}")
        md_lines.append(f"- **测试覆盖**: {'[YES] 存在' if summary.get('has_tests') else '[NO] 缺失'}")
        md_lines.append(f"- **文档**: {'[YES] 存在' if summary.get('has_documentation') else '[NO] 缺失'}\n")

        # 待办事项
        todos = report.get("todos", [])
        if todos:
            md_lines.append("## 待办事项\n")
            for todo in todos:
                priority_mark = {"high": "[HIGH]", "medium": "[MID]", "low": "[LOW]"}.get(todo["priority"], "[?]")
                md_lines.append(f"{priority_mark} **[{todo['category']}]** {todo['task']}")
                md_lines.append(f"   - 原因: {todo['reason']}\n")

        # 学习建议
        suggestions = report.get("learning_suggestions", [])
        if suggestions:
            md_lines.append("## 学习路径\n")
            for i, suggestion in enumerate(suggestions, 1):
                md_lines.append(f"### {i}. {suggestion['topic']} ({suggestion['level']})\n")
                md_lines.append(f"**预计时间**: {suggestion['estimated_time']}\n")
                md_lines.append("**资源**:")
                for resource in suggestion.get("resources", []):
                    md_lines.append(f"- {resource}")
                md_lines.append("")

        return "\n".join(md_lines)
