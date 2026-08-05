"""
MCP Apps UI Module
Provides UI template management and component system
"""

from .template_manager import TemplateManager
from .components import (
    UIComponent,
    ComponentType,
    create_header,
    create_stats_grid,
    create_knowledge_list,
    create_chart,
    create_action_bar,
    create_card,
    create_task_list,
)
from .validators import (
    validate_template_data,
    validate_component,
    ValidationError,
)

__all__ = [
    "TemplateManager",
    "UIComponent",
    "ComponentType",
    "create_header",
    "create_stats_grid",
    "create_knowledge_list",
    "create_chart",
    "create_action_bar",
    "create_card",
    "create_task_list",
    "validate_template_data",
    "validate_component",
    "ValidationError",
]
