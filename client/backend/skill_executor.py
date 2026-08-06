"""
Skill 执行引擎
解析 Skill Phase 并编排 MCP 工具调用
"""
import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class PhaseResult:
    """Phase 执行结果"""
    phase_name: str
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class SkillExecutionResult:
    """Skill 执行结果"""
    skill_name: str
    success: bool
    phases: List[PhaseResult]
    final_output: Dict[str, Any]
    error: Optional[str] = None


class SkillExecutor:
    """
    Skill 执行引擎

    职责:
    1. 解析 Skill 中的 Phase
    2. 提取工具调用指令
    3. 按顺序执行 Phase
    4. 聚合结果
    """

    def __init__(self, mcp_client, skill_manager):
        self.mcp_client = mcp_client
        self.skill_manager = skill_manager

    async def execute_skill(self, skill_name: str, context: Dict[str, Any]) -> SkillExecutionResult:
        """
        执行 Skill

        Args:
            skill_name: Skill 名称
            context: 执行上下文 (如 project_path)

        Returns:
            SkillExecutionResult
        """
        skill = self.skill_manager.get_skill(skill_name)
        if not skill:
            return SkillExecutionResult(
                skill_name=skill_name,
                success=False,
                phases=[],
                final_output={},
                error=f"Skill '{skill_name}' not found"
            )

        print(f"[SkillExecutor] Executing skill: {skill_name}")

        # 解析 Phase
        phases = self._parse_phases(skill.content)
        if not phases:
            return SkillExecutionResult(
                skill_name=skill_name,
                success=False,
                phases=[],
                final_output={},
                error="No phases found in skill"
            )

        # 执行每个 Phase
        phase_results = []
        aggregated_data = {}

        for phase in phases:
            print(f"[SkillExecutor] Executing Phase: {phase['name']}")

            try:
                phase_result = await self._execute_phase(phase, context, aggregated_data)
                phase_results.append(phase_result)

                if phase_result.success:
                    # 聚合数据供后续 Phase 使用
                    aggregated_data[phase['name']] = phase_result.output
                else:
                    # Phase 失败，停止执行
                    print(f"[SkillExecutor] Phase failed: {phase_result.error}")
                    return SkillExecutionResult(
                        skill_name=skill_name,
                        success=False,
                        phases=phase_results,
                        final_output=aggregated_data,
                        error=f"Phase '{phase['name']}' failed: {phase_result.error}"
                    )
            except Exception as e:
                print(f"[SkillExecutor] Phase error: {e}")
                phase_results.append(PhaseResult(
                    phase_name=phase['name'],
                    success=False,
                    output={},
                    error=str(e)
                ))
                return SkillExecutionResult(
                    skill_name=skill_name,
                    success=False,
                    phases=phase_results,
                    final_output=aggregated_data,
                    error=f"Phase '{phase['name']}' error: {e}"
                )

        # 所有 Phase 成功
        return SkillExecutionResult(
            skill_name=skill_name,
            success=True,
            phases=phase_results,
            final_output=aggregated_data,
            error=None
        )

    def _parse_phases(self, skill_content: str) -> List[Dict[str, Any]]:
        """
        解析 Skill 中的 Phase

        格式:
        ### Phase 1: 快速侦查
        **目标**: ...
        **步骤**:
        1. **检测框架**
           调用工具: project/detect_framework
           输入: {"project_path": "<用户提供的路径>"}
        """
        phases = []

        # 使用正则表达式匹配 Phase
        phase_pattern = r'###\s*Phase\s+\d+:\s*([^\n]+)\n(.*?)(?=###\s*Phase\s+\d+:|$)'
        matches = re.finditer(phase_pattern, skill_content, re.DOTALL)

        for match in matches:
            phase_name = match.group(1).strip()
            phase_content = match.group(2).strip()

            # 提取步骤
            steps = self._parse_steps(phase_content)

            phases.append({
                'name': phase_name,
                'content': phase_content,
                'steps': steps
            })

        return phases

    def _parse_steps(self, phase_content: str) -> List[Dict[str, Any]]:
        """
        解析 Phase 中的步骤

        格式:
        1. **检测框架**
           调用工具: project/detect_framework
           输入: {"project_path": "<用户提供的路径>"}
        """
        steps = []

        # 匹配步骤编号和名称
        step_pattern = r'\d+\.\s*\*\*([^*]+)\*\*\s*(.*?)(?=\d+\.\s*\*\*|$)'
        matches = re.finditer(step_pattern, phase_content, re.DOTALL)

        for match in matches:
            step_name = match.group(1).strip()
            step_content = match.group(2).strip()

            # 提取工具调用
            tool_call = self._extract_tool_call(step_content)

            steps.append({
                'name': step_name,
                'content': step_content,
                'tool_call': tool_call
            })

        return steps

    def _extract_tool_call(self, step_content: str) -> Optional[Dict[str, Any]]:
        """
        提取工具调用信息

        格式:
        调用工具: project/detect_framework
        输入: {"project_path": "<用户提供的路径>"}
        """
        # 匹配 "调用工具:"
        tool_match = re.search(r'调用工具:\s*([^\n]+)', step_content)
        if not tool_match:
            return None

        tool_name = tool_match.group(1).strip()

        # 匹配 "输入:" 后的 JSON
        input_match = re.search(r'输入:\s*({[^}]+})', step_content, re.DOTALL)
        tool_input = {}
        if input_match:
            try:
                # 解析 JSON（可能包含模板变量）
                input_str = input_match.group(1).strip()
                tool_input = json.loads(input_str)
            except json.JSONDecodeError:
                # JSON 包含模板变量，暂时保留原始字符串
                tool_input = {"_raw": input_str}

        return {
            'tool_name': tool_name,
            'input': tool_input
        }

    async def _execute_phase(
        self,
        phase: Dict[str, Any],
        context: Dict[str, Any],
        aggregated_data: Dict[str, Any]
    ) -> PhaseResult:
        """
        执行单个 Phase

        Args:
            phase: Phase 定义
            context: 用户上下文 (如 project_path)
            aggregated_data: 前面 Phase 的聚合数据
        """
        phase_output = {}

        for step in phase['steps']:
            tool_call = step.get('tool_call')
            if not tool_call:
                # 没有工具调用，跳过
                continue

            tool_name = tool_call['tool_name']
            tool_input = tool_call['input']

            # 替换模板变量
            resolved_input = self._resolve_input(tool_input, context, aggregated_data)

            print(f"[SkillExecutor] Calling tool: {tool_name} with input: {resolved_input}")

            # 调用 MCP 工具
            try:
                result = await self.mcp_client.call_tool(tool_name, resolved_input)

                # 存储步骤结果
                phase_output[step['name']] = result

                print(f"[SkillExecutor] Tool result: {result}")
            except Exception as e:
                return PhaseResult(
                    phase_name=phase['name'],
                    success=False,
                    output=phase_output,
                    error=f"Tool '{tool_name}' failed: {e}"
                )

        return PhaseResult(
            phase_name=phase['name'],
            success=True,
            output=phase_output,
            error=None
        )

    def _resolve_input(
        self,
        tool_input: Dict[str, Any],
        context: Dict[str, Any],
        aggregated_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        解析工具输入中的模板变量

        模板变量格式:
        - <用户提供的路径> → context['project_path']
        - <Phase1.检测框架.framework> → aggregated_data['Phase1']['检测框架']['framework']
        """
        resolved = {}

        for key, value in tool_input.items():
            if key == "_raw":
                # 原始字符串，需要解析
                raw_str = value
                # 替换模板变量
                raw_str = raw_str.replace("<用户提供的路径>", context.get('project_path', ''))
                raw_str = raw_str.replace("<路径>", context.get('project_path', ''))
                try:
                    resolved = json.loads(raw_str)
                except json.JSONDecodeError:
                    resolved[key] = raw_str
            elif isinstance(value, str) and value.startswith("<") and value.endswith(">"):
                # 模板变量
                var_name = value[1:-1]  # 去掉 < >

                if var_name == "用户提供的路径" or var_name == "路径":
                    resolved[key] = context.get('project_path', '')
                else:
                    # 从聚合数据中提取
                    resolved[key] = self._extract_from_aggregated(var_name, aggregated_data)
            else:
                resolved[key] = value

        return resolved

    def _extract_from_aggregated(self, path: str, aggregated_data: Dict[str, Any]) -> Any:
        """
        从聚合数据中提取值

        路径格式: Phase1.检测框架.framework
        """
        parts = path.split('.')
        current = aggregated_data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current
