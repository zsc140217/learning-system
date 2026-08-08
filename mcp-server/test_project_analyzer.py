"""
测试 project_analyze_status 工具
"""
import asyncio
import sys
import os

# 添加项目路径到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflows.project_status_analyzer import ProjectStatusAnalyzer


async def mock_tool(result_data):
    """模拟 MCP 工具返回"""
    class MockResult:
        def __init__(self, data):
            self.data = data

    async def tool(**kwargs):
        return MockResult(result_data)

    return tool


async def test_analyzer():
    """测试分析器"""

    # 模拟工具返回
    tools_registry = {
        "project/detect_framework": await mock_tool({
            "framework": "FastAPI",
            "language": "Python",
            "confidence": 0.95,
            "version": "3.10+",
            "entry_points": ["server.py"]
        }),
        "project/scan_structure": await mock_tool({
            "directories": ["mcp-server/", "client/", "docs/", "tests/"],
            "key_files": ["server.py", "requirements.txt", "CLAUDE.md"],
            "config_files": ["config.py"]
        }),
        "project/analyze_dependencies": await mock_tool({
            "dependencies": [
                {"name": "fastapi", "version": "0.100.0", "type": "core"},
                {"name": "pydantic", "version": "2.0.0", "type": "core"},
                {"name": "pytest", "version": "7.0.0", "type": "dev"}
            ],
            "total_count": 25
        }),
        "project/extract_patterns": await mock_tool({
            "patterns": [
                {"type": "decorator", "usage": "@server.tool", "count": 20},
                {"type": "async", "usage": "async/await", "count": 30}
            ],
            "conventions": {
                "naming": "snake_case",
                "async_usage": "high"
            }
        })
    }

    # 创建分析器
    analyzer = ProjectStatusAnalyzer(tools_registry)

    # 执行分析（使用当前项目路径）
    project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    print(f"测试项目路径: {project_path}\n")

    # JSON 格式测试
    print("=" * 50)
    print("测试 JSON 格式输出")
    print("=" * 50)

    result = await analyzer.analyze(project_path, depth=3, output_format="json")

    print(f"\n项目名称: {result['project_name']}")
    print(f"项目路径: {result['project_path']}")

    summary = result.get('summary', {})
    print(f"\n摘要:")
    print(f"  - 技术栈: {summary.get('tech_stack')}")
    print(f"  - 复杂度: {summary.get('complexity')}")
    print(f"  - 完成度: {summary.get('completion_percentage')}%")
    print(f"  - 依赖数量: {summary.get('total_dependencies')}")
    print(f"  - 测试: {'YES' if summary.get('has_tests') else 'NO'}")
    print(f"  - 文档: {'YES' if summary.get('has_documentation') else 'NO'}")

    todos = result.get('todos', [])
    print(f"\n待办事项 ({len(todos)} 项):")
    for todo in todos[:3]:  # 只显示前3项
        print(f"  - [{todo['priority']}] {todo['task']}")

    suggestions = result.get('learning_suggestions', [])
    print(f"\n学习建议 ({len(suggestions)} 项):")
    for suggestion in suggestions[:2]:  # 只显示前2项
        print(f"  - {suggestion['level']}: {suggestion['topic']} ({suggestion['estimated_time']})")

    # Markdown 格式测试
    print("\n" + "=" * 50)
    print("测试 Markdown 格式输出")
    print("=" * 50)

    result_md = await analyzer.analyze(project_path, depth=3, output_format="markdown")
    markdown = result_md.get('markdown', '')

    # 只显示前500字符
    print(f"\nMarkdown 输出 (前500字符):\n")
    print(markdown[:500])
    print("...\n")

    print("OK - Test completed")


if __name__ == "__main__":
    asyncio.run(test_analyzer())
