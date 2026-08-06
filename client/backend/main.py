"""
Learning System 客户端主程序
Phase 2-3 实现
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional

from state import ClientStateManager
from config import config
from mcp_client import MCPClient, MCPClientPool
from skill_manager import SkillManager
from task_manager import TaskManager
from mrtr_handler import MRTRHandler, ConsoleUICallback


class LearningSystemClient:
    """
    Learning System 客户端

    整合所有组件：
    - StateManager: 会话状态管理
    - MCPClient: MCP 协议通信
    - SkillManager: Skill 文档管理
    - TaskManager: 长任务处理
    - MRTRHandler: 二次确认处理
    """

    def __init__(self):
        # 状态管理
        self.state = ClientStateManager()

        # MCP 客户端池
        self.mcp_pool = MCPClientPool()

        # Skill 管理器
        self.skills = SkillManager(config.skills_dir)

        # Skill 执行引擎（延迟初始化）
        self.skill_executor: Optional[SkillExecutor] = None

        # 任务管理器（延迟初始化）
        self.task_manager: Optional[TaskManager] = None

        # MRTR 处理器（延迟初始化）
        self.mrtr_handler: Optional[MRTRHandler] = None

        # UI 回调
        self.ui_callback = ConsoleUICallback()

    async def start(self):
        """启动客户端"""
        print("=" * 60)
        print("Learning System Client - Phase 2-3")
        print("=" * 60)

        # 1. 启动 MCP Server
        print("\n[1] Starting MCP Server...")
        mcp_client = MCPClient(
            command=config.mcp_server.command,
            args=config.mcp_server.args,
            cwd=config.mcp_server.cwd,
            env=config.mcp_server.env
        )
        await self.mcp_pool.add_client("learning-system", mcp_client)

        # 初始化管理器
        self.task_manager = TaskManager(
            mcp_client,
            poll_interval=config.task_poll_interval,
            timeout=config.task_timeout
        )
        self.mrtr_handler = MRTRHandler(mcp_client)
        self.skill_executor = SkillExecutor(mcp_client, self.skills)

        # 2. 加载 Skills
        print("[2] Loading Skills...")
        self.skills.load_skills()

        if self.skills.list_skills():
            print(f"   Loaded {len(self.skills.list_skills())} skills:")
            for skill in self.skills.list_skills():
                print(f"   - {skill.name}: {skill.description}")
        else:
            print("   No skills found (you can add them later)")

        # 3. 列出可用工具
        print("\n[3] Available MCP Tools:")
        tools = await mcp_client.list_tools()
        for tool in tools[:10]:  # 只显示前10个
            print(f"   - {tool.get('name')}: {tool.get('description', 'No description')}")
        if len(tools) > 10:
            print(f"   ... and {len(tools) - 10} more tools")

        print("\n" + "=" * 60)
        print("Client started successfully!")
        print("=" * 60)
        print()

    async def stop(self):
        """停止客户端"""
        print("\n[Stopping] Shutting down...")
        await self.mcp_pool.stop_all()
        print("[Stopped] Client stopped")

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 工具（高级封装）

        自动处理：
        1. 上下文注入（session_id, user_id, project_id）
        2. MRTR 二次确认
        3. Tasks 长任务轮询
        4. Apps UI 组件（暂时只打印）
        """
        # 构建上下文
        context = self.state.build_tool_context()

        # 调用工具
        result = await self.mcp_pool.call_tool(
            "learning-system",
            tool_name,
            arguments,
            context
        )

        # 处理 MRTR
        if result.get("_mcp_feature") == "mrtr":
            result = await self.mrtr_handler.handle(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                state_manager=self.state,
                ui_callback=self.ui_callback.show_confirmation
            )

        # 处理 Tasks
        if result.get("_mcp_feature") == "task":
            task_data = result.get("_task_data", {})
            task_id = task_data.get("task_id")

            if task_id:
                print(f"\n[Task] Long task started: {task_id}")
                print(f"[Task] Estimated duration: {task_data.get('estimatedDuration', 'unknown')}s")

                # 添加到状态管理器
                self.state.add_task(task_id, tool_name)

                # 后台轮询
                def progress_callback(status):
                    progress = status.get("progress", 0)
                    print(f"[Task] Progress: {progress:.1f}%", end="\r")

                result = await self.task_manager.track_task(
                    task_id,
                    self.state,
                    progress_callback
                )
                print(f"\n[Task] Completed!")

        # 处理 Apps
        if result.get("_mcp_feature") == "app":
            app_data = result.get("_app_data", {})
            print("\n[MCP App] UI component returned:")
            print(f"  Template: {len(app_data.get('template', ''))} characters")
            print("  (In a real client, this would be rendered in an iframe)")

        return result

    async def execute_skill(self, skill_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Skill

        Args:
            skill_name: Skill 名称
            context: 执行上下文 (如 project_path)

        Returns:
            SkillExecutionResult 转换为字典
        """
        if not self.skill_executor:
            return {"error": "SkillExecutor not initialized"}

        result = await self.skill_executor.execute_skill(skill_name, context)

        # 转换为字典
        return {
            "skill_name": result.skill_name,
            "success": result.success,
            "phases": [
                {
                    "phase_name": phase.phase_name,
                    "success": phase.success,
                    "output": phase.output,
                    "error": phase.error
                }
                for phase in result.phases
            ],
            "final_output": result.final_output,
            "error": result.error
        }

    async def interactive_loop(self):
        """交互式循环（控制台版本）"""
        print("\n" + "=" * 60)
        print("Interactive Mode")
        print("Commands:")
        print("  /analyze <path>  - Analyze a project (using codebase-onboarding skill)")
        print("  /search <query>  - Search knowledge graph")
        print("  /skills          - List available skills")
        print("  /tools           - List available tools")
        print("  /state           - Show current state")
        print("  /quit            - Exit")
        print("=" * 60)

        while True:
            try:
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                # 命令处理
                if user_input == "/quit":
                    break

                elif user_input == "/tools":
                    tools = await self.mcp_pool.get_client("learning-system").list_tools()
                    print(f"\nAvailable tools ({len(tools)}):")
                    for tool in tools:
                        print(f"  - {tool.get('name')}")

                elif user_input == "/skills":
                    skills = self.skills.list_skills()
                    print(f"\nAvailable skills ({len(skills)}):")
                    for skill in skills:
                        print(f"  - {skill.name}: {skill.description}")

                elif user_input == "/state":
                    summary = self.state.get_state_summary()
                    print("\nCurrent state:")
                    for key, value in summary.items():
                        print(f"  {key}: {value}")

                elif user_input.startswith("/analyze "):
                    project_path = user_input[9:].strip()
                    print(f"\n[Analyzing] {project_path} using codebase-onboarding skill...")

                    # 设置当前项目
                    self.state.set_current_project(project_path)

                    # 执行 codebase-onboarding skill
                    result = await self.execute_skill("codebase-onboarding", {
                        "project_path": project_path
                    })

                    print("\n[Result]")
                    if result.get("success"):
                        print("Skill executed successfully!")
                        print(f"\nPhases completed: {len(result.get('phases', []))}")
                        for phase in result.get('phases', []):
                            print(f"\n  Phase: {phase['phase_name']}")
                            print(f"  Success: {phase['success']}")
                            if phase.get('error'):
                                print(f"  Error: {phase['error']}")

                        print("\n[Final Output]")
                        print(json.dumps(result.get('final_output', {}), indent=2, ensure_ascii=False))
                    else:
                        print(f"Skill failed: {result.get('error')}")
                        print(result)

                elif user_input.startswith("/search "):
                    query = user_input[8:].strip()
                    print(f"\n[Searching] {query}...")

                    result = await self.call_tool("search_knowledge", {
                        "query": query,
                        "limit": 5
                    })

                    print("\n[Results]")
                    if "nodes" in result:
                        for node in result["nodes"]:
                            print(f"  - {node.get('name')}: {node.get('entity_type')}")
                    else:
                        print(result)

                else:
                    print("Unknown command. Type /quit to exit.")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Type /quit to exit.")
            except Exception as e:
                print(f"\n[Error] {e}")


async def main():
    """主函数"""
    client = LearningSystemClient()

    try:
        # 启动客户端
        await client.start()

        # 进入交互式循环
        await client.interactive_loop()

    finally:
        # 停止客户端
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
