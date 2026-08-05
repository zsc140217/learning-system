"""
UI Template Manager
Manages UI templates, validation, and rendering
"""

from typing import Any, Callable, Dict, Optional
from pathlib import Path

from ..protocol.result_types import UITemplateResult
from .components import UIComponent
from .validators import validate_template_data, ValidationError


class TemplateManager:
    """
    Manages UI templates and rendering

    Usage:
        template_mgr = TemplateManager()
        template_mgr.register_template(
            "com.learning-system.session-summary",
            validator=custom_validator
        )

        ui_result = template_mgr.render_template(
            "com.learning-system.session-summary",
            data={"sections": [...]}
        )
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize template manager

        Args:
            templates_dir: Directory containing HTML templates (optional)
        """
        self.templates_dir = templates_dir or Path(__file__).parent.parent.parent / "templates"
        self.validators: Dict[str, Callable] = {}
        self._template_paths: Dict[str, str] = {}

    def register_template(
        self,
        template_id: str,
        validator: Optional[Callable[[Dict[str, Any]], bool]] = None,
        template_path: Optional[str] = None
    ) -> None:
        """
        Register a UI template

        Args:
            template_id: Unique template identifier
            validator: Optional validation function
            template_path: Optional path to HTML template file
        """
        if validator:
            self.validators[template_id] = validator

        if template_path:
            self._template_paths[template_id] = template_path

    def validate_data(
        self,
        template_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Validate data for a template

        Args:
            template_id: Template identifier
            data: Data to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        # Use custom validator if registered
        if template_id in self.validators:
            return self.validators[template_id](data)

        # Fall back to default validation
        return validate_template_data(template_id, data)

    def render_template(
        self,
        template_id: str,
        data: Dict[str, Any],
        template_path: Optional[str] = None
    ) -> UITemplateResult:
        """
        Render a UI template

        Args:
            template_id: Template identifier
            data: Template data
            template_path: Optional override for template path

        Returns:
            UITemplateResult ready to return from MCP tool

        Raises:
            ValidationError: If data validation fails
        """
        # Validate data
        self.validate_data(template_id, data)

        # Get template path (use override or registered path)
        final_template_path = template_path or self._template_paths.get(template_id, "")

        # Create UITemplateResult
        return UITemplateResult(
            template_id=template_id,
            template_path=final_template_path,
            template_data=data
        )

    def render_components(
        self,
        template_id: str,
        components: list[UIComponent]
    ) -> UITemplateResult:
        """
        Render UI components (convenience method)

        Args:
            template_id: Template identifier
            components: List of UIComponent objects

        Returns:
            UITemplateResult with components serialized as JSON
        """
        data = {
            "sections": [comp.to_dict() for comp in components]
        }

        return self.render_template(template_id, data)

    def load_html_template(self, template_name: str) -> str:
        """
        Load HTML template content from file

        Args:
            template_name: Template filename (e.g., "knowledge_graph.html")

        Returns:
            HTML template content

        Raises:
            FileNotFoundError: If template file not found
        """
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        return template_path.read_text(encoding="utf-8")


# Global template manager instance
_global_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """
    Get the global template manager instance

    Returns:
        Global TemplateManager instance
    """
    global _global_template_manager

    if _global_template_manager is None:
        _global_template_manager = TemplateManager()

    return _global_template_manager
