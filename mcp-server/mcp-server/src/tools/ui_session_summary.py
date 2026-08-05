"""
Session Summary UI Tool
Generates interactive session summary UI using MCP Apps
"""
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from ..ui import (
    TemplateManager,
    create_header,
    create_stats_grid,
    create_knowledge_list,
    create_chart,
    create_action_bar,
)
from ..protocol.result_types import UITemplateResult


async def generate_session_summary_ui(
    session_id: str,
    session_data: Optional[Dict[str, Any]] = None
) -> UITemplateResult:
    """
    Generate session summary UI
    
    Args:
        session_id: Session identifier
        session_data: Optional session data (for testing/demo)
    
    Returns:
        UITemplateResult with session summary UI
    """
    logger.info(f"Generating session summary UI for session: {session_id}")
    
    # Use provided data or fetch from SessionAnalyzer
    if session_data is None:
        session_data = await _fetch_session_data(session_id)
    
    # Build UI components
    components = []
    
    # 1. Header
    start_time = session_data.get("start_time", datetime.now().isoformat())
    end_time = session_data.get("end_time", datetime.now().isoformat())
    
    components.append(
        create_header(
            title="学习会话总结",
            subtitle=f"{start_time} - {end_time}",
            icon="chart"
        )
    )
    
    # 2. Stats Grid
    stats = session_data.get("stats", {})
    stats_items = [
        {
            "label": "学习时长",
            "value": stats.get("duration", "0h"),
            "icon": "clock"
        },
        {
            "label": "知识点数",
            "value": str(stats.get("knowledge_count", 0)),
            "icon": "lightbulb"
        },
        {
            "label": "消息数",
            "value": str(stats.get("message_count", 0)),
            "icon": "message"
        },
        {
            "label": "平均掌握度",
            "value": f"{stats.get('avg_mastery', 0):.1f}%",
            "icon": "star"
        }
    ]
    
    components.append(create_stats_grid(stats_items, columns=4))
    
    # 3. Knowledge Points List
    knowledge_points = session_data.get("knowledge_points", [])
    knowledge_items = []
    
    for kp in knowledge_points:
        knowledge_items.append({
            "id": kp.get("id", ""),
            "title": kp.get("title", "Unknown"),
            "mastery": kp.get("mastery", 0.0),
            "last_review": kp.get("last_review"),
            "tags": kp.get("tags", [])
        })
    
    if knowledge_items:
        components.append(
            create_knowledge_list(knowledge_items, show_mastery=True)
        )
    
    # 4. Mastery Distribution Chart
    mastery_dist = session_data.get("mastery_distribution", {})
    if mastery_dist:
        chart_data = {
            "labels": list(mastery_dist.keys()),
            "values": list(mastery_dist.values())
        }
        
        components.append(
            create_chart(
                chart_type="bar",
                title="掌握度分布",
                data=chart_data,
                config={"colors": ["#4CAF50", "#8BC34A", "#FFC107", "#FF5722"]}
            )
        )
    
    # 5. Action Bar
    actions = [
        {
            "label": "生成复习计划",
            "style": "primary",
            "toolName": "generate_review_plan",
            "params": {"session_id": session_id}
        },
        {
            "label": "导出PDF",
            "style": "secondary",
            "toolName": "export_session_pdf",
            "params": {"session_id": session_id}
        },
        {
            "label": "查看知识图谱",
            "style": "secondary",
            "toolName": "ui/knowledge_graph",
            "params": {
                "knowledge_ids": [kp["id"] for kp in knowledge_points[:5]]
            }
        }
    ]
    
    components.append(create_action_bar(actions))
    
    # Render template
    template_mgr = TemplateManager()
    return template_mgr.render_components(
        template_id="com.learning-system.session-summary",
        components=components
    )


async def _fetch_session_data(session_id: str) -> Dict[str, Any]:
    """
    Fetch session data from SessionAnalyzer
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session data dict
    """
    # TODO: Integrate with actual SessionAnalyzer
    # For now, return demo data
    
    logger.warning(f"Using demo data for session: {session_id}")
    
    return {
        "session_id": session_id,
        "start_time": "2026-08-03T10:00:00Z",
        "end_time": "2026-08-03T12:30:00Z",
        "stats": {
            "duration": "2.5h",
            "knowledge_count": 8,
            "message_count": 45,
            "avg_mastery": 72.5
        },
        "knowledge_points": [
            {
                "id": "kp-001",
                "title": "FastAPI 依赖注入",
                "mastery": 0.85,
                "last_review": "2026-08-03T12:00:00Z",
                "tags": ["FastAPI", "Python", "后端"]
            },
            {
                "id": "kp-002",
                "title": "MCP 协议设计",
                "mastery": 0.70,
                "last_review": "2026-08-03T11:30:00Z",
                "tags": ["MCP", "协议", "架构"]
            },
            {
                "id": "kp-003",
                "title": "知识图谱构建",
                "mastery": 0.60,
                "last_review": "2026-08-03T11:00:00Z",
                "tags": ["知识图谱", "Neo4j", "数据"]
            }
        ],
        "mastery_distribution": {
            "已掌握 (>80%)": 3,
            "熟悉 (60-80%)": 3,
            "学习中 (40-60%)": 2,
            "待复习 (<40%)": 0
        }
    }
