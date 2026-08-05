"""
Project Configuration UI Tool

Generates wizard-style multi-step form for project analysis configuration.
"""

import logging
from typing import Dict, Any

from ..ui.components import UIComponent, ComponentType, create_header
from ..ui.template_manager import TemplateManager, UITemplateResult

logger = logging.getLogger(__name__)


async def generate_project_config_ui() -> UITemplateResult:
    """
    Generate project configuration wizard UI.

    Returns:
        UITemplateResult with wizard layout

    Example:
        >>> result = await generate_project_config_ui()
        >>> jsonrpc = result.to_jsonrpc(request_id=1)
    """
    data = {
        "layout": "wizard",
        "steps": [
            {
                "id": "step1",
                "title": "Select Analysis Strategy",
                "description": "Choose how deeply to analyze your project",
                "type": "radio-group",
                "field": "strategy",
                "options": [
                    {
                        "value": "quick",
                        "label": "Quick Analysis",
                        "description": "Based on file structure and naming conventions",
                        "eta_seconds": 10,
                        "pros": ["Fast", "No LLM cost"],
                        "cons": ["Surface-level insights"]
                    },
                    {
                        "value": "standard",
                        "label": "Standard Analysis",
                        "description": "LLM analysis of core code files",
                        "recommended": True,
                        "eta_seconds": 90,
                        "pros": ["Balanced depth", "Identifies key patterns"],
                        "cons": ["Moderate LLM cost"]
                    },
                    {
                        "value": "deep",
                        "label": "Deep Analysis",
                        "description": "Full semantic analysis of entire codebase",
                        "eta_seconds": 600,
                        "pros": ["Comprehensive insights", "Discovers hidden patterns"],
                        "cons": ["Slow", "Higher LLM cost"]
                    }
                ]
            },
            {
                "id": "step2",
                "title": "Select Analysis Dimensions",
                "description": "Choose what aspects to analyze",
                "type": "checkbox-group",
                "field": "dimensions",
                "options": [
                    {
                        "value": "architecture",
                        "label": "Architecture Patterns",
                        "description": "MVC, Clean Architecture, Hexagonal, etc.",
                        "checked": True
                    },
                    {
                        "value": "tech_stack",
                        "label": "Technology Stack",
                        "description": "Frameworks, libraries, tools used",
                        "checked": True
                    },
                    {
                        "value": "highlights",
                        "label": "Project Highlights",
                        "description": "Notable features and implementations",
                        "checked": True
                    },
                    {
                        "value": "interview_qa",
                        "label": "Interview Q&A Generation",
                        "description": "Generate interview questions based on project",
                        "checked": False
                    },
                    {
                        "value": "dependencies",
                        "label": "Dependency Analysis",
                        "description": "Module coupling and dependency graph",
                        "checked": False
                    },
                    {
                        "value": "code_quality",
                        "label": "Code Quality Metrics",
                        "description": "Complexity, duplication, test coverage",
                        "checked": False
                    }
                ]
            },
            {
                "id": "step3",
                "title": "Configure Output",
                "description": "Choose how to save analysis results",
                "type": "checkbox-group",
                "field": "output_formats",
                "options": [
                    {
                        "value": "knowledge_graph",
                        "label": "Knowledge Graph",
                        "description": "Save to MCP knowledge graph for future reference",
                        "checked": True
                    },
                    {
                        "value": "markdown_report",
                        "label": "Markdown Report",
                        "description": "Generate detailed markdown documentation",
                        "checked": True
                    },
                    {
                        "value": "json_export",
                        "label": "JSON Export",
                        "description": "Export structured data as JSON file",
                        "checked": False
                    }
                ]
            },
            {
                "id": "step4",
                "title": "Review Configuration",
                "type": "summary",
                "content": "Please review your configuration before starting analysis"
            }
        ],
        "actions": {
            "submit": {
                "label": "Start Analysis",
                "style": "primary",
                "toolName": "start_project_analysis",
                "icon": "play"
            },
            "cancel": {
                "label": "Cancel",
                "style": "secondary",
                "action": "close"
            },
            "save_preset": {
                "label": "Save as Preset",
                "style": "outline",
                "toolName": "save_analysis_preset",
                "icon": "bookmark"
            }
        },
        "defaults": {
            "strategy": "standard",
            "dimensions": ["architecture", "tech_stack", "highlights"],
            "output_formats": ["knowledge_graph", "markdown_report"]
        }
    }

    template_id = "com.learning-system.project-config"
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
        print("=== Project Config Wizard UI Demo ===")
        result = await generate_project_config_ui()

        print(f"[OK] Template ID: {result.template_id}")
        print(f"[OK] Steps: {len(result.data['steps'])}")
        print(f"[OK] Actions: {len(result.data['actions'])}")

        # Convert to JSON-RPC
        jsonrpc = result.to_jsonrpc(request_id=1)
        print(json.dumps(jsonrpc, indent=2))

        # Validate structure
        assert "steps" in result.data, "Missing steps"
        assert len(result.data["steps"]) == 4, "Expected 4 steps"
        assert "actions" in result.data, "Missing actions"
        assert "defaults" in result.data, "Missing defaults"

        print("\n[OK] All validations passed")

    asyncio.run(main())
