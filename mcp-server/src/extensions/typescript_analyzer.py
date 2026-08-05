"""
TypeScript Code Analyzer Extension

Analyzes TypeScript/JavaScript source code for:
- React component patterns
- React Hooks usage
- Interface and type definitions
- Framework detection (React, Next.js, Vue)
"""

import os
import re
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from .base_extension import Extension

logger = logging.getLogger(__name__)


class TypeScriptAnalyzerExtension(Extension):
    """
    Extension for analyzing TypeScript/JavaScript code structure and patterns.

    Capabilities:
    - Detect React components (functional, class-based)
    - Analyze React Hooks usage
    - Extract TypeScript interfaces and types
    - Detect frontend frameworks (React, Next.js, Vue)
    """

    @property
    def extension_id(self) -> str:
        return "io.learning-system.analyzer.typescript"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "TypeScript Code Analyzer"

    @property
    def description(self) -> str:
        return "Analyzes TypeScript/JavaScript code for React patterns, hooks, and type definitions"

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "detect_react_components": True,
            "analyze_hooks": True,
            "extract_interfaces": True,
            "detect_framework": ["React", "Next.js", "Vue", "Angular"],
            "supported_languages": ["TypeScript", "JavaScript", "TSX", "JSX"]
        }

    def register_tools(self, server: Any):
        """Register TypeScript analysis tools with the MCP server."""

        @server.tool("detect_react_components")
        async def detect_components(file_path: str) -> Dict[str, Any]:
            """
            Detect React components in a TypeScript/JavaScript file.

            Args:
                file_path: Path to .ts/.tsx/.js/.jsx file

            Returns:
                Dictionary with component detection results
            """
            try:
                components = self._detect_react_components(file_path)

                return {
                    "file": file_path,
                    "components": components,
                    "component_count": len(components)
                }
            except Exception as e:
                logger.error(f"Failed to detect components in {file_path}: {e}")
                return {"error": str(e)}

        @server.tool("analyze_react_hooks")
        async def analyze_hooks(file_path: str) -> Dict[str, Any]:
            """
            Analyze React Hooks usage in a file.

            Args:
                file_path: Path to .ts/.tsx/.js/.jsx file

            Returns:
                Dictionary with hooks usage analysis
            """
            try:
                hooks_info = self._analyze_hooks(file_path)

                return {
                    "file": file_path,
                    "hooks_used": hooks_info["hooks"],
                    "custom_hooks": hooks_info["custom_hooks"],
                    "hooks_count": len(hooks_info["hooks"])
                }
            except Exception as e:
                logger.error(f"Failed to analyze hooks in {file_path}: {e}")
                return {"error": str(e)}

        @server.tool("extract_typescript_interfaces")
        async def extract_interfaces(file_path: str) -> Dict[str, Any]:
            """
            Extract TypeScript interfaces and type definitions.

            Args:
                file_path: Path to .ts/.tsx file

            Returns:
                Dictionary with interface and type definitions
            """
            try:
                types_info = self._extract_interfaces(file_path)

                return {
                    "file": file_path,
                    "interfaces": types_info["interfaces"],
                    "types": types_info["types"],
                    "enums": types_info["enums"]
                }
            except Exception as e:
                logger.error(f"Failed to extract interfaces from {file_path}: {e}")
                return {"error": str(e)}

        @server.tool("detect_frontend_framework")
        async def detect_framework(project_path: str) -> Dict[str, Any]:
            """
            Detect frontend framework used in project.

            Args:
                project_path: Path to project directory

            Returns:
                Dictionary with framework detection results
            """
            try:
                framework_info = self._detect_project_framework(project_path)

                return {
                    "project_path": project_path,
                    "framework": framework_info["framework"],
                    "confidence": framework_info["confidence"],
                    "evidence": framework_info["evidence"]
                }
            except Exception as e:
                logger.error(f"Failed to detect framework in {project_path}: {e}")
                return {"error": str(e)}

    def _detect_react_components(self, file_path: str) -> List[Dict[str, Any]]:
        """Detect React components using regex patterns."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        components = []

        # Pattern 1: Functional components (arrow function)
        # const MyComponent = () => { ... }
        pattern1 = r'(?:export\s+)?(?:const|let|var)\s+([A-Z][a-zA-Z0-9]*)\s*=\s*\(([^)]*)\)\s*(?::\s*[^=]+)?\s*=>'
        for match in re.finditer(pattern1, content):
            components.append({
                "name": match.group(1),
                "type": "functional",
                "props": match.group(2).strip() if match.group(2) else "none",
                "pattern": "arrow_function"
            })

        # Pattern 2: Function declaration components
        # function MyComponent(props) { ... }
        pattern2 = r'(?:export\s+)?function\s+([A-Z][a-zA-Z0-9]*)\s*\(([^)]*)\)'
        for match in re.finditer(pattern2, content):
            components.append({
                "name": match.group(1),
                "type": "functional",
                "props": match.group(2).strip() if match.group(2) else "none",
                "pattern": "function_declaration"
            })

        # Pattern 3: Class components
        # class MyComponent extends React.Component { ... }
        pattern3 = r'class\s+([A-Z][a-zA-Z0-9]*)\s+extends\s+(?:React\.)?Component'
        for match in re.finditer(pattern3, content):
            components.append({
                "name": match.group(1),
                "type": "class",
                "props": "unknown",
                "pattern": "class_component"
            })

        return components

    def _analyze_hooks(self, file_path: str) -> Dict[str, Any]:
        """Analyze React Hooks usage."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        hooks = []
        custom_hooks = []

        # Built-in hooks
        builtin_hooks = [
            'useState', 'useEffect', 'useContext', 'useReducer',
            'useCallback', 'useMemo', 'useRef', 'useLayoutEffect',
            'useImperativeHandle', 'useDebugValue', 'useDeferredValue',
            'useTransition', 'useId'
        ]

        for hook in builtin_hooks:
            pattern = rf'\b{hook}\s*\('
            matches = re.finditer(pattern, content)
            for match in matches:
                hooks.append({
                    "hook": hook,
                    "type": "builtin",
                    "position": match.start()
                })

        # Custom hooks (functions starting with "use")
        custom_hook_pattern = r'(?:export\s+)?(?:const|function)\s+(use[A-Z][a-zA-Z0-9]*)\s*[=\(]'
        for match in re.finditer(custom_hook_pattern, content):
            custom_hooks.append({
                "name": match.group(1),
                "type": "custom"
            })

        return {
            "hooks": hooks,
            "custom_hooks": custom_hooks
        }

    def _extract_interfaces(self, file_path: str) -> Dict[str, Any]:
        """Extract TypeScript interfaces, types, and enums."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        interfaces = []
        types = []
        enums = []

        # Extract interfaces
        # interface MyInterface { ... }
        interface_pattern = r'(?:export\s+)?interface\s+([A-Za-z0-9_]+)\s*(?:extends\s+[^{]+)?\s*\{'
        for match in re.finditer(interface_pattern, content):
            interfaces.append({
                "name": match.group(1),
                "exported": "export" in match.group(0)
            })

        # Extract type aliases
        # type MyType = ...
        type_pattern = r'(?:export\s+)?type\s+([A-Za-z0-9_]+)\s*='
        for match in re.finditer(type_pattern, content):
            types.append({
                "name": match.group(1),
                "exported": "export" in match.group(0)
            })

        # Extract enums
        # enum MyEnum { ... }
        enum_pattern = r'(?:export\s+)?enum\s+([A-Za-z0-9_]+)\s*\{'
        for match in re.finditer(enum_pattern, content):
            enums.append({
                "name": match.group(1),
                "exported": "export" in match.group(0)
            })

        return {
            "interfaces": interfaces,
            "types": types,
            "enums": enums
        }

    def _detect_project_framework(self, project_path: str) -> Dict[str, Any]:
        """Detect frontend framework by analyzing package.json."""
        evidence = []
        framework_scores = {"React": 0, "Next.js": 0, "Vue": 0, "Angular": 0}

        # Check package.json
        pkg_json = os.path.join(project_path, "package.json")
        if os.path.exists(pkg_json):
            try:
                import json
                with open(pkg_json, 'r', encoding='utf-8') as f:
                    pkg = json.load(f)

                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                # React detection
                if "react" in deps:
                    framework_scores["React"] += 3
                    evidence.append("react in dependencies")

                # Next.js detection
                if "next" in deps:
                    framework_scores["Next.js"] += 5
                    evidence.append("next in dependencies")

                # Vue detection
                if "vue" in deps:
                    framework_scores["Vue"] += 5
                    evidence.append("vue in dependencies")

                # Angular detection
                if "@angular/core" in deps:
                    framework_scores["Angular"] += 5
                    evidence.append("@angular/core in dependencies")

            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")

        # Check for Next.js specific files
        if os.path.exists(os.path.join(project_path, "next.config.js")) or \
           os.path.exists(os.path.join(project_path, "next.config.mjs")):
            framework_scores["Next.js"] += 2
            evidence.append("next.config.js found")

        # Check for Angular specific files
        if os.path.exists(os.path.join(project_path, "angular.json")):
            framework_scores["Angular"] += 2
            evidence.append("angular.json found")

        # Determine winner
        max_score = max(framework_scores.values())
        if max_score == 0:
            return {"framework": "Unknown", "confidence": 0.0, "evidence": []}

        detected = [fw for fw, score in framework_scores.items() if score == max_score][0]
        confidence = min(max_score / 7.0, 1.0)

        return {
            "framework": detected,
            "confidence": confidence,
            "evidence": evidence
        }
