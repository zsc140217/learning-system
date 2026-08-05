"""
UI Component System
Defines standard UI components for MCP Apps
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ComponentType(Enum):
    """Standard UI component types"""
    HEADER = "header"
    STATS_GRID = "stats-grid"
    KNOWLEDGE_LIST = "knowledge-list"
    CHART = "chart"
    ACTION_BAR = "action-bar"
    CARD = "card"
    TASK_LIST = "task-list"
    WIZARD = "wizard"
    DASHBOARD = "dashboard"


@dataclass
class UIComponent:
    """
    Base UI component with type, props, and children

    Example:
        component = UIComponent(
            type=ComponentType.HEADER,
            props={"title": "Session Summary", "icon": "chart"},
            children=[]
        )
    """
    type: ComponentType
    props: Dict[str, Any] = field(default_factory=dict)
    children: List['UIComponent'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert component to JSON-serializable dict"""
        result = {
            "type": self.type.value,
            "props": self.props
        }

        if self.children:
            result["children"] = [child.to_dict() for child in self.children]

        return result


# Component Factory Functions

def create_header(
    title: str,
    subtitle: Optional[str] = None,
    icon: Optional[str] = None
) -> UIComponent:
    """
    Create a header component

    Args:
        title: Main title text
        subtitle: Optional subtitle text
        icon: Optional icon name (e.g., "chart", "lightbulb")

    Returns:
        UIComponent with type HEADER
    """
    props = {"title": title}

    if subtitle:
        props["subtitle"] = subtitle
    if icon:
        props["icon"] = icon

    return UIComponent(
        type=ComponentType.HEADER,
        props=props
    )


def create_stats_grid(
    items: List[Dict[str, Any]],
    columns: int = 4
) -> UIComponent:
    """
    Create a stats grid component

    Args:
        items: List of stat items, each with:
            - label: str
            - value: str or number
            - icon: Optional[str]
            - trend: Optional[str] ("up" | "down" | "neutral")
        columns: Number of columns (1-4)

    Returns:
        UIComponent with type STATS_GRID
    """
    return UIComponent(
        type=ComponentType.STATS_GRID,
        props={
            "items": items,
            "columns": columns
        }
    )


def create_knowledge_list(
    items: List[Dict[str, Any]],
    show_mastery: bool = True
) -> UIComponent:
    """
    Create a knowledge list component

    Args:
        items: List of knowledge items, each with:
            - id: str
            - title: str
            - mastery: float (0-1)
            - last_review: Optional[str] (ISO 8601)
            - tags: Optional[List[str]]
        show_mastery: Whether to show mastery level

    Returns:
        UIComponent with type KNOWLEDGE_LIST
    """
    return UIComponent(
        type=ComponentType.KNOWLEDGE_LIST,
        props={
            "items": items,
            "showMastery": show_mastery
        }
    )


def create_chart(
    chart_type: str,
    title: str,
    data: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> UIComponent:
    """
    Create a chart component

    Args:
        chart_type: Chart type ("bar" | "line" | "pie" | "donut")
        title: Chart title
        data: Chart data with labels and values
        config: Optional chart configuration (colors, legend, etc.)

    Returns:
        UIComponent with type CHART
    """
    props = {
        "chartType": chart_type,
        "title": title,
        "data": data
    }

    if config:
        props["config"] = config

    return UIComponent(
        type=ComponentType.CHART,
        props=props
    )


def create_action_bar(
    actions: List[Dict[str, Any]]
) -> UIComponent:
    """
    Create an action bar component

    Args:
        actions: List of action items, each with:
            - label: str
            - style: str ("primary" | "secondary" | "danger")
            - toolName: str (MCP tool to call)
            - params: Optional[Dict[str, Any]]

    Returns:
        UIComponent with type ACTION_BAR
    """
    return UIComponent(
        type=ComponentType.ACTION_BAR,
        props={"actions": actions}
    )


def create_card(
    title: str,
    content: Any,
    footer: Optional[Dict[str, Any]] = None
) -> UIComponent:
    """
    Create a card component

    Args:
        title: Card title
        content: Card content (can be another component)
        footer: Optional footer with actions

    Returns:
        UIComponent with type CARD
    """
    props = {
        "title": title,
        "content": content
    }

    if footer:
        props["footer"] = footer

    return UIComponent(
        type=ComponentType.CARD,
        props=props
    )


def create_task_list(
    items: List[Dict[str, Any]],
    show_priority: bool = True
) -> UIComponent:
    """
    Create a task list component

    Args:
        items: List of task items, each with:
            - knowledge: str (knowledge point name)
            - due: str (due date)
            - priority: str ("high" | "medium" | "low")
            - status: Optional[str] ("pending" | "completed")
        show_priority: Whether to show priority indicator

    Returns:
        UIComponent with type TASK_LIST
    """
    return UIComponent(
        type=ComponentType.TASK_LIST,
        props={
            "items": items,
            "showPriority": show_priority
        }
    )
