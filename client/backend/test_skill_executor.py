"""
测试 Skill 执行引擎
验证 codebase-onboarding skill 的解析和执行
"""
import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from skill_manager import SkillManager
from skill_executor import SkillExecutor


class MockMCPClient:
    """模拟 MCP 客户端用于测试"""

    async def call_tool(self, tool_name: str, arguments: dict):
        """模拟工具调用"""
        print(f"\n[MockMCPClient] call_tool({tool_name}, {arguments})")

        # 模拟不同工具的返回值
        if tool_name == "project/detect_framework":
            return {
                "framework": "FastAPI",
                "confidence": 0.9,
                "language": "Python",
                "version": "3.10+",
                "entry_points": ["server.py", "main.py"]
            }

        elif tool_name == "project/scan_structure":
            return {
                "directories": ["src/", "tests/", "docs/", "client/"],
                "key_files": ["server.py", "requirements.txt", "CLAUDE.md"],
                "config_files": ["pyproject.toml", "pytest.ini"]
            }

        elif tool_name == "project/analyze_dependencies":
            return {
                "dependencies": [
                    {"name": "fastapi", "version": "0.100.0", "type": "core"},
                    {"name": "pydantic", "version": "2.0.0", "type": "core"},
                    {"name": "pytest", "version": "7.0.0", "type": "dev"}
                ],
                "total_count": 15
            }

        elif tool_name == "project/extract_patterns":
            return {
                "patterns": [
                    {
                        "type": "decorator",
                        "usage": "@server.tool",
                        "count": 8,
                        "files": ["server.py"]
                    },
                    {
                        "type": "async",
                        "usage": "async/await",
                        "count": 15,
                        "files": ["server.py", "mcp_client.py"]
                    }
                ],
                "conventions": {
                    "naming": "snake_case",
                    "async_usage": "high",
                    "type_hints": "partial"
                }
            }

        else:
            return {"error": f"Unknown tool: {tool_name}"}


async def test_skill_parsing():
    """测试 Skill 解析"""
    print("=" * 60)
    print("Test 1: Skill Parsing")
    print("=" * 60)

    # 初始化 SkillManager
    skills_dir = Path(__file__).parent.parent.parent / "mcp-server" / "skills"
    skill_manager = SkillManager(skills_dir)
    skill_manager.load_skills()

    # 获取 codebase-onboarding skill
    skill = skill_manager.get_skill("codebase-onboarding")
    if not skill:
        print("ERROR: codebase-onboarding skill not found!")
        return False

    print(f"\nLoaded skill: {skill.name}")
    print(f"Description: {skill.description}")

    # 初始化 SkillExecutor
    mock_client = MockMCPClient()
    executor = SkillExecutor(mock_client, skill_manager)

    # 解析 Phases
    phases = executor._parse_phases(skill.content)
    print(f"\nParsed {len(phases)} phases:")
    for i, phase in enumerate(phases, 1):
        print(f"  {i}. {phase['name']}")
        print(f"     Steps: {len(phase['steps'])}")

    return True


async def test_skill_execution():
    """测试 Skill 执行"""
    print("\n" + "=" * 60)
    print("Test 2: Skill Execution")
    print("=" * 60)

    # 初始化组件
    skills_dir = Path(__file__).parent.parent.parent / "mcp-server" / "skills"
    skill_manager = SkillManager(skills_dir)
    skill_manager.load_skills()

    mock_client = MockMCPClient()
    executor = SkillExecutor(mock_client, skill_manager)

    # 执行 Skill
    context = {
        "project_path": "E:\\Desktop\\learning-system"
    }

    print(f"\n[Executing] codebase-onboarding skill...")
    print(f"Context: {context}\n")

    result = await executor.execute_skill("codebase-onboarding", context)

    # 显示结果
    print("\n" + "=" * 60)
    print("Execution Result")
    print("=" * 60)

    print(f"\nSkill: {result.skill_name}")
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")

    print(f"\nPhases ({len(result.phases)}):")
    for phase in result.phases:
        print(f"\n  Phase: {phase.phase_name}")
        print(f"  Success: {phase.success}")
        if phase.error:
            print(f"  Error: {phase.error}")
        print(f"  Output keys: {list(phase.output.keys())}")

    if result.success:
        print("\nAll phases completed successfully!")
        return True
    else:
        print("\nExecution failed!")
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Skill Executor Test Suite")
    print("=" * 60)

    # 测试 1: Skill 解析
    test1_pass = await test_skill_parsing()

    # 测试 2: Skill 执行
    test2_pass = await test_skill_execution()

    # 汇总结果
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Test 1 (Skill Parsing): {'PASS' if test1_pass else 'FAIL'}")
    print(f"Test 2 (Skill Execution): {'PASS' if test2_pass else 'FAIL'}")

    if test1_pass and test2_pass:
        print("\nAll tests passed!")
        return 0
    else:
        print("\nSome tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
