"""
Learning Coach Agent
响应空闲事件，主动触发学习巩固和复习计划
"""
from typing import Dict, Any
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from loguru import logger


class LearningCoach(BaseAgent):
    """
    学习教练 Agent

    职责：
    1. 监听 client.idle 事件
    2. 分析最近的学习内容
    3. 触发知识巩固和复习计划
    4. 生成学习建议

    Subscribes to: client.idle
    Emits: learning.consolidation_triggered, learning.review_plan_generated
    """

    def __init__(self, agent_id: str, bus):
        super().__init__(agent_id, bus)
        self.last_consolidation_time: datetime = None
        self.consolidation_cooldown = timedelta(hours=1)  # 至少间隔1小时

    async def start(self) -> None:
        """启动 Agent 并订阅空闲事件"""
        await super().start()
        await self.subscribe("client.idle")
        logger.info("LearningCoach 已启动，等待空闲事件...")

    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        处理空闲事件

        Args:
            event: 包含空闲状态信息的事件
        """
        event_type = event.get("type")

        if event_type != "client.idle":
            return

        logger.info("收到空闲事件，开始分析学习状态...")

        # 检查冷却时间（避免频繁触发）
        if self._is_in_cooldown():
            logger.info("在冷却期内，跳过本次巩固")
            return

        # 分析会话数据
        session_data = event.get("session_data", {})
        tool_calls = session_data.get("tool_calls", [])

        if not tool_calls:
            logger.info("无会话数据，跳过巩固")
            return

        # 触发知识巩固
        await self._trigger_consolidation(session_data)

        # 更新最后巩固时间
        self.last_consolidation_time = datetime.now()

    def _is_in_cooldown(self) -> bool:
        """
        检查是否在冷却期内

        Returns:
            True 如果在冷却期内
        """
        if self.last_consolidation_time is None:
            return False

        time_since_last = datetime.now() - self.last_consolidation_time
        return time_since_last < self.consolidation_cooldown

    async def _trigger_consolidation(self, session_data: Dict[str, Any]):
        """
        触发知识巩固流程

        Args:
            session_data: 会话数据
        """
        tool_calls = session_data.get("tool_calls", [])

        # 分析工具使用模式
        analysis = self._analyze_session_pattern(tool_calls)

        # 生成巩固建议
        suggestions = self._generate_suggestions(analysis)

        # 发布巩固事件
        await self.emit({
            "type": "learning.consolidation_triggered",
            "timestamp": datetime.now().isoformat(),
            "session_analysis": analysis,
            "suggestions": suggestions
        })

        logger.info(f"已触发知识巩固 - 建议: {len(suggestions)} 条")

    def _analyze_session_pattern(self, tool_calls: list) -> Dict[str, Any]:
        """
        分析会话模式

        Args:
            tool_calls: 工具调用列表

        Returns:
            分析结果
        """
        if not tool_calls:
            return {
                "total_calls": 0,
                "unique_tools": 0,
                "dominant_activity": "none"
            }

        # 统计工具使用频率
        tool_frequency = {}
        for call in tool_calls:
            tool_name = call.get("tool", "unknown")
            tool_frequency[tool_name] = tool_frequency.get(tool_name, 0) + 1

        # 找出主要活动
        dominant_tool = max(tool_frequency, key=tool_frequency.get)

        return {
            "total_calls": len(tool_calls),
            "unique_tools": len(tool_frequency),
            "tool_frequency": tool_frequency,
            "dominant_activity": dominant_tool,
            "duration_minutes": self._estimate_duration(tool_calls)
        }

    def _estimate_duration(self, tool_calls: list) -> float:
        """
        估算会话持续时间

        Args:
            tool_calls: 工具调用列表

        Returns:
            持续时间（分钟）
        """
        if len(tool_calls) < 2:
            return 0.0

        try:
            first_time = datetime.fromisoformat(tool_calls[0]["timestamp"])
            last_time = datetime.fromisoformat(tool_calls[-1]["timestamp"])
            duration = (last_time - first_time).total_seconds() / 60
            return round(duration, 1)
        except (KeyError, ValueError):
            return 0.0

    def _generate_suggestions(self, analysis: Dict[str, Any]) -> list:
        """
        根据分析结果生成学习建议

        Args:
            analysis: 会话分析结果

        Returns:
            建议列表
        """
        suggestions = []

        # 建议 1: 复习刚学的内容
        if analysis["total_calls"] > 0:
            suggestions.append({
                "type": "review",
                "priority": "high",
                "message": "建议复习刚才学习的内容，巩固记忆",
                "action": "review_recent_knowledge"
            })

        # 建议 2: 如果会话较短，推荐相关主题
        if analysis["duration_minutes"] < 10:
            suggestions.append({
                "type": "explore",
                "priority": "medium",
                "message": "会话较短，推荐探索相关主题",
                "action": "explore_related_topics"
            })

        # 建议 3: 如果主要使用了分析工具，建议做练习
        dominant = analysis.get("dominant_activity", "")
        if "analyze" in dominant or "search" in dominant:
            suggestions.append({
                "type": "practice",
                "priority": "medium",
                "message": "理论学习较多，建议做一些实践练习",
                "action": "practice_coding"
            })

        return suggestions
