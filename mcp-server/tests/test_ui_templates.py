"""
Tests for UI Template System
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.ui import (
    TemplateManager,
    UIComponent,
    ComponentType,
    create_header,
    create_stats_grid,
    create_chart,
    create_action_bar,
    ValidationError,
)
from src.protocol.result_types import UITemplateResult


def test_template_manager_init():
    """Test template manager initialization"""
    tm = TemplateManager()
    assert tm is not None
    assert isinstance(tm.templates_dir, Path)


def test_create_header_full():
    """Test creating header with all params"""
    h = create_header("Title", subtitle="Sub", icon="chart")
    assert h.type == ComponentType.HEADER
    assert h.props["title"] == "Title"
    assert h.props["subtitle"] == "Sub"
    assert h.props["icon"] == "chart"


def test_create_stats_grid():
    """Test creating stats grid"""
    items = [
        {"label": "Total", "value": "100"},
        {"label": "Active", "value": "50"},
    ]
    sg = create_stats_grid(items, columns=2)
    assert sg.type == ComponentType.STATS_GRID
    assert len(sg.props["items"]) == 2
    assert sg.props["columns"] == 2


def test_component_to_dict():
    """Test component serialization"""
    c = create_header("Test", subtitle="Sub")
    d = c.to_dict()
    assert d["type"] == "header"
    assert d["props"]["title"] == "Test"
    assert d["props"]["subtitle"] == "Sub"


def test_template_manager_render():
    """Test rendering template"""
    tm = TemplateManager()
    components = [
        create_header("Test"),
        create_stats_grid([{"label": "A", "value": "1"}])
    ]
    result = tm.render_components("test-id", components)
    
    assert isinstance(result, UITemplateResult)
    assert result.template_id == "test-id"
    assert "sections" in result.template_data
    assert len(result.template_data["sections"]) == 2


def test_ui_template_result_to_jsonrpc():
    """Test UITemplateResult to JSON-RPC conversion"""
    tm = TemplateManager()
    components = [create_header("Test")]
    result = tm.render_components("test", components)
    
    jsonrpc = result.to_jsonrpc(request_id=42)
    
    assert jsonrpc["jsonrpc"] == "2.0"
    assert jsonrpc["id"] == 42
    assert "result" in jsonrpc
    assert "_meta" in jsonrpc
    assert "io.modelcontextprotocol/uiTemplate" in jsonrpc["_meta"]
    
    meta = jsonrpc["_meta"]["io.modelcontextprotocol/uiTemplate"]
    assert meta["templateId"] == "test"
    assert "data" in meta


def test_create_chart():
    """Test creating chart component"""
    data = {"labels": ["A", "B"], "values": [10, 20]}
    chart = create_chart("bar", "Test Chart", data)
    
    assert chart.type == ComponentType.CHART
    assert chart.props["chartType"] == "bar"
    assert chart.props["title"] == "Test Chart"
    assert chart.props["data"] == data


def test_create_action_bar():
    """Test creating action bar"""
    actions = [
        {"label": "Save", "style": "primary", "toolName": "save_data"},
        {"label": "Cancel", "style": "secondary", "toolName": "cancel"},
    ]
    ab = create_action_bar(actions)
    
    assert ab.type == ComponentType.ACTION_BAR
    assert len(ab.props["actions"]) == 2


if __name__ == "__main__":
    # Run all tests
    test_template_manager_init()
    test_create_header_full()
    test_create_stats_grid()
    test_component_to_dict()
    test_template_manager_render()
    test_ui_template_result_to_jsonrpc()
    test_create_chart()
    test_create_action_bar()
    print("\nAll tests passed!")
