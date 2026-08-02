"""
Test script for Learning System Phase 2
Tests ProjectAgent and analyze_project tool
"""
import sys
import os

# Add mcp-server to path
project_root = os.path.dirname(os.path.abspath(__file__))
mcp_server_path = os.path.join(project_root, 'mcp-server')
sys.path.insert(0, mcp_server_path)

from src.tools.learning_tools import analyze_project
import json


def test_analyze_project():
    """Test project analysis functionality"""
    print("=" * 60)
    print("Testing Learning System - Phase 2")
    print("=" * 60)

    # Test 1: Request configuration (MCP App)
    print("\n[Test 1] Request project analysis configuration...")
    project_path = os.path.abspath(os.path.dirname(__file__))

    result = analyze_project(project_path, request_config=True)

    print(f"Success: {result.get('success')}")
    if result.get('success'):
        meta = result.get('result', {}).get('_meta', {})
        input_required = meta.get('io.modelcontextprotocol/inputRequired', {})
        print(f"Message: {input_required.get('message')}")
        print(f"Template ID: {input_required.get('uiTemplate', {}).get('templateId')}")
        print(f"Template Path: {input_required.get('uiTemplate', {}).get('templatePath')}")

    # Test 2: Direct analysis (no config UI)
    print("\n" + "=" * 60)
    print("[Test 2] Direct project analysis (default config)...")

    result = analyze_project(project_path, request_config=False)

    print(f"Success: {result.get('success')}")
    if result.get('success'):
        analysis = result.get('result', {})
        print(f"\nProject Path: {analysis.get('project_path')}")
        print(f"Language: {analysis.get('language')}")
        print(f"Analysis Depth: {analysis.get('analysis_depth')}")

        # Architecture
        arch = analysis.get('architecture', {})
        print(f"\nArchitecture Highlights: {len(arch.get('highlights', []))}")
        for highlight in arch.get('highlights', []):
            print(f"  - {highlight['title']}")
        print(f"Patterns: {', '.join(arch.get('patterns', []))}")
        print(f"Structure: {arch.get('structure')}")

        # Tech Stack
        tech = analysis.get('tech_stack', {})
        print(f"\nTech Stack:")
        print(f"  Frameworks: {tech.get('frameworks', [])}")
        print(f"  Databases: {tech.get('databases', [])}")
        print(f"  Infrastructure: {tech.get('infrastructure', [])}")
    else:
        print(f"Error: {result.get('error')}")

    # Test 3: Invalid project path
    print("\n" + "=" * 60)
    print("[Test 3] Invalid project path handling...")

    result = analyze_project("/invalid/path", request_config=False)
    print(f"Success: {result.get('success')}")
    print(f"Error (expected): {result.get('error')}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_analyze_project()
