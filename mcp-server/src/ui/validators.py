"""
UI Data Validators
Validates template data and component structures
"""

from typing import Any, Dict, List
from .components import ComponentType


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


def validate_component(component_dict: Dict[str, Any]) -> bool:
    """
    Validate a component dictionary structure

    Args:
        component_dict: Component as dict

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(component_dict, dict):
        raise ValidationError("Component must be a dictionary")

    if "type" not in component_dict:
        raise ValidationError("Component missing 'type' field")

    component_type = component_dict["type"]

    # Validate type is valid
    valid_types = [ct.value for ct in ComponentType]
    if component_type not in valid_types:
        raise ValidationError(
            f"Invalid component type '{component_type}'. "
            f"Must be one of: {', '.join(valid_types)}"
        )

    # Validate props
    if "props" in component_dict:
        if not isinstance(component_dict["props"], dict):
            raise ValidationError("Component 'props' must be a dictionary")

    # Validate children recursively
    if "children" in component_dict:
        if not isinstance(component_dict["children"], list):
            raise ValidationError("Component 'children' must be a list")

        for child in component_dict["children"]:
            validate_component(child)

    return True


def validate_template_data(
    template_id: str,
    data: Dict[str, Any]
) -> bool:
    """
    Validate template data for a given template ID

    Args:
        template_id: Template identifier
        data: Template data to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValidationError("Template data must be a dictionary")

    # Template-specific validation
    if "session-summary" in template_id:
        _validate_session_summary(data)
    elif "knowledge-graph" in template_id:
        _validate_knowledge_graph(data)
    elif "project-config" in template_id:
        _validate_project_config(data)
    elif "review-dashboard" in template_id:
        _validate_review_dashboard(data)

    return True


def _validate_session_summary(data: Dict[str, Any]) -> None:
    """Validate session summary data"""
    if "sections" in data:
        if not isinstance(data["sections"], list):
            raise ValidationError("'sections' must be a list")

        for section in data["sections"]:
            validate_component(section)


def _validate_knowledge_graph(data: Dict[str, Any]) -> None:
    """Validate knowledge graph data"""
    required_fields = ["nodes", "edges"]

    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Knowledge graph missing required field: {field}")

    if not isinstance(data["nodes"], list):
        raise ValidationError("'nodes' must be a list")

    if not isinstance(data["edges"], list):
        raise ValidationError("'edges' must be a list")

    # Validate nodes
    for node in data["nodes"]:
        if not isinstance(node, dict):
            raise ValidationError("Each node must be a dictionary")
        if "id" not in node:
            raise ValidationError("Node missing 'id' field")

    # Validate edges
    for edge in data["edges"]:
        if not isinstance(edge, dict):
            raise ValidationError("Each edge must be a dictionary")
        if "source" not in edge or "target" not in edge:
            raise ValidationError("Edge missing 'source' or 'target' field")


def _validate_project_config(data: Dict[str, Any]) -> None:
    """Validate project config data"""
    if "steps" in data:
        if not isinstance(data["steps"], list):
            raise ValidationError("'steps' must be a list")

        for step in data["steps"]:
            if not isinstance(step, dict):
                raise ValidationError("Each step must be a dictionary")
            if "id" not in step or "title" not in step:
                raise ValidationError("Step missing 'id' or 'title' field")


def _validate_review_dashboard(data: Dict[str, Any]) -> None:
    """Validate review dashboard data"""
    if "widgets" in data:
        if not isinstance(data["widgets"], list):
            raise ValidationError("'widgets' must be a list")

        for widget in data["widgets"]:
            if not isinstance(widget, dict):
                raise ValidationError("Each widget must be a dictionary")
            if "id" not in widget or "type" not in widget:
                raise ValidationError("Widget missing 'id' or 'type' field")
