"""
Review Dashboard UI Tool

Generates dashboard-style multi-widget interface for review management.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..ui.components import (
    UIComponent, ComponentType,
    create_header, create_stats_grid, create_card
)
from ..ui.template_manager import TemplateManager, UITemplateResult

logger = logging.getLogger(__name__)


def _get_demo_review_data() -> Dict[str, Any]:
    """Get demo review dashboard data."""
    today = datetime.now()

    return {
        "today_tasks": [
            {
                "knowledge_id": "kp-002",
                "title": "FastAPI Dependency Injection",
                "due": "today",
                "priority": "high",
                "last_reviewed": (today - timedelta(days=3)).isoformat()
            },
            {
                "knowledge_id": "kp-005",
                "title": "MCP Server Implementation",
                "due": "today",
                "priority": "high",
                "last_reviewed": (today - timedelta(days=2)).isoformat()
            },
            {
                "knowledge_id": "kp-008",
                "title": "JWT Authentication",
                "due": "today",
                "priority": "medium",
                "last_reviewed": (today - timedelta(days=1)).isoformat()
            }
        ],
        "mastery_distribution": {
            "labels": ["Mastered", "Familiar", "Learning", "Needs Review"],
            "values": [12, 18, 15, 5],
            "colors": ["#4CAF50", "#2196F3", "#FF9800", "#F44336"]
        },
        "learning_curve": {
            "labels": ["08-27", "08-28", "08-29", "08-30", "08-31", "09-01", "09-02"],
            "datasets": [
                {
                    "label": "New Knowledge Points",
                    "values": [3, 5, 2, 4, 6, 3, 5],
                    "color": "#4CAF50"
                },
                {
                    "label": "Review Sessions",
                    "values": [8, 12, 6, 10, 15, 9, 14],
                    "color": "#2196F3"
                }
            ]
        },
        "stats": {
            "total_knowledge": 50,
            "needs_review": 5,
            "average_mastery": 72.5,
            "streak_days": 7
        }
    }


async def generate_review_dashboard_ui() -> UITemplateResult:
    """
    Generate review dashboard UI with multiple widgets.

    Returns:
        UITemplateResult with dashboard layout

    Example:
        >>> result = await generate_review_dashboard_ui()
        >>> jsonrpc = result.to_jsonrpc(request_id=1)
    """
    # TODO: Replace with actual MemoryManager integration
    # review_data = await memory_manager.get_review_dashboard_data()
    review_data = _get_demo_review_data()

    data = {
        "layout": "dashboard",
        "widgets": [
            {
                "id": "today-tasks",
                "type": "card",
                "title": "Today's Review Tasks",
                "subtitle": f"{len(review_data['today_tasks'])} items",
                "icon": "calendar",
                "content": {
                    "type": "task-list",
                    "items": [
                        {
                            "id": task["knowledge_id"],
                            "title": task["title"],
                            "due": task["due"],
                            "priority": task["priority"],
                            "action": {
                                "label": "Start Review",
                                "toolName": "start_review_session",
                                "params": {"knowledge_id": task["knowledge_id"]}
                            }
                        }
                        for task in review_data["today_tasks"]
                    ]
                },
                "footer": {
                    "action": {
                        "label": "View All Tasks",
                        "toolName": "view_all_review_tasks"
                    }
                }
            },
            {
                "id": "mastery-distribution",
                "type": "card",
                "title": "Mastery Distribution",
                "icon": "pie-chart",
                "content": {
                    "type": "donut-chart",
                    "data": review_data["mastery_distribution"]
                }
            },
            {
                "id": "learning-curve",
                "type": "card",
                "title": "Learning Curve (Last 7 Days)",
                "icon": "trending-up",
                "content": {
                    "type": "line-chart",
                    "data": review_data["learning_curve"],
                    "config": {
                        "showGrid": True,
                        "showLegend": True,
                        "smooth": True
                    }
                }
            },
            {
                "id": "stats-summary",
                "type": "stats-grid",
                "columns": 2,
                "items": [
                    {
                        "label": "Total Knowledge Points",
                        "value": str(review_data["stats"]["total_knowledge"]),
                        "icon": "book",
                        "trend": None
                    },
                    {
                        "label": "Needs Review",
                        "value": str(review_data["stats"]["needs_review"]),
                        "icon": "alert-circle",
                        "trend": None,
                        "color": "warning" if review_data["stats"]["needs_review"] > 0 else "success"
                    },
                    {
                        "label": "Average Mastery",
                        "value": f"{review_data['stats']['average_mastery']}%",
                        "icon": "target",
                        "trend": None
                    },
                    {
                        "label": "Current Streak",
                        "value": f"{review_data['stats']['streak_days']} days",
                        "icon": "flame",
                        "trend": None,
                        "color": "success"
                    }
                ]
            }
        ],
        "quick_actions": [
            {
                "label": "Start Review Session",
                "style": "primary",
                "toolName": "start_review_session",
                "icon": "play"
            },
            {
                "label": "Add Knowledge Point",
                "style": "secondary",
                "toolName": "add_knowledge_point",
                "icon": "plus"
            },
            {
                "label": "Generate Study Plan",
                "style": "outline",
                "toolName": "generate_study_plan",
                "icon": "calendar"
            }
        ]
    }

    template_id = "com.learning-system.review-dashboard"
    template_mgr = TemplateManager()

    return template_mgr.render_template(
        template_id=template_id,
        data=data
    )


# Example usage for testing
if __name__ == "__main__":
    import asyncio
    import json

    async def main():
        print("=== Review Dashboard UI Demo ===")
        result = await generate_review_dashboard_ui()

        print(f"[OK] Template ID: {result.template_id}")
        print(f"[OK] Widgets: {len(result.data['widgets'])}")
        print(f"[OK] Quick Actions: {len(result.data['quick_actions'])}")

        # Convert to JSON-RPC
        jsonrpc = result.to_jsonrpc(request_id=1)
        print(json.dumps(jsonrpc, indent=2, ensure_ascii=False))

        # Validate structure
        assert "widgets" in result.data, "Missing widgets"
        assert len(result.data["widgets"]) == 4, "Expected 4 widgets"
        assert "quick_actions" in result.data, "Missing quick_actions"

        print("\n[OK] All validations passed")

    asyncio.run(main())
