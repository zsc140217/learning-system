"""
Project Agent
Analyzes project code and extracts architectural highlights, tech stack, and interview points
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os
from .base_agent import BaseAgent
from ..utils.id_generator import generate_project_id
import hashlib


class ProjectAgent(BaseAgent):
    """
    Analyzes project codebases to extract:
    - Architectural highlights (design patterns, microservices, etc.)
    - Tech stack (frameworks, libraries, databases)
    - Interview talking points (what makes this project impressive)

    Subscribes to: project.analyze_requested
    Emits: project.analysis_started, project.analysis_progress, project.analysis_completed
    """

    async def start(self) -> None:
        """Start the agent and subscribe to project analysis events"""
        await super().start()
        await self.subscribe("project.analyze_requested")

    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        Process project analysis requests

        Args:
            event: Event containing project_path and analysis_config
        """
        event_type = event.get("type")

        if event_type != "project.analyze_requested":
            return

        project_path = event.get("project_path")
        config = event.get("config", {})

        if not project_path or not os.path.exists(project_path):
            await self.emit({
                "type": "project.analysis_failed",
                "error": "Invalid project path"
            })
            return

        # Generate project ID based on path
        project_id = self._generate_project_id(project_path)

        # Emit analysis started event
        await self.emit({
            "type": "project.analysis_started",
            "project_id": project_id,
            "project_path": project_path
        })

        # Perform analysis
        analysis_result = await self._analyze_project(project_path, config)

        # Emit analysis completed event
        await self.emit({
            "type": "project.analysis_completed",
            "project_id": project_id,
            "project_path": project_path,
            "result": analysis_result
        })

    async def _analyze_project(
        self,
        project_path: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze project codebase

        Args:
            project_path: Path to project root
            config: Analysis configuration
                {
                    "depth": "shallow" | "deep",
                    "focus": ["architecture", "tech_stack", "challenges"],
                    "language": "python" | "typescript" | "java" | "auto"
                }

        Returns:
            Analysis result dictionary
        """
        depth = config.get("depth", "shallow")
        focus_areas = config.get("focus", ["architecture", "tech_stack"])
        language = config.get("language", "auto")

        # Detect project language if auto
        if language == "auto":
            language = self._detect_language(project_path)

        result = {
            "project_path": project_path,
            "language": language,
            "analysis_depth": depth,
            "timestamp": datetime.now().isoformat()
        }

        # Perform focused analysis
        if "architecture" in focus_areas:
            result["architecture"] = await self._analyze_architecture(project_path, language, depth)

        if "tech_stack" in focus_areas:
            result["tech_stack"] = await self._analyze_tech_stack(project_path, language)

        if "challenges" in focus_areas:
            result["challenges"] = await self._identify_challenges(project_path, language)

        return result

    def _detect_language(self, project_path: str) -> str:
        """
        Detect primary programming language of the project

        Args:
            project_path: Path to project root

        Returns:
            Detected language
        """
        path = Path(project_path)

        # Check for common project files
        if (path / "package.json").exists():
            return "typescript"
        elif (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            return "python"
        elif (path / "pom.xml").exists() or (path / "build.gradle").exists():
            return "java"
        elif (path / "Cargo.toml").exists():
            return "rust"
        elif (path / "go.mod").exists():
            return "go"

        return "unknown"

    async def _analyze_architecture(
        self,
        project_path: str,
        language: str,
        depth: str
    ) -> Dict[str, Any]:
        """
        Analyze project architecture

        Returns:
            {
                "highlights": [
                    {
                        "title": "Multi-Agent Orchestration",
                        "description": "...",
                        "interview_talking_point": "..."
                    }
                ],
                "patterns": ["MVC", "Repository", "Factory"],
                "structure": "Monolith" | "Microservices" | "Layered"
            }
        """
        path = Path(project_path)
        highlights = []
        patterns = []

        # Detect architectural patterns based on directory structure
        if (path / "agents").exists() or (path / "src" / "agents").exists():
            highlights.append({
                "title": "Multi-Agent Architecture",
                "description": "Project uses agent-based architecture for modular functionality",
                "interview_talking_point": "I designed a multi-agent system where independent agents communicate via event bus, enabling loose coupling and scalability"
            })
            patterns.append("Agent-Based")

        if (path / "adapters").exists() or (path / "src" / "adapters").exists():
            highlights.append({
                "title": "Adapter Pattern",
                "description": "Uses adapter pattern for external service integration",
                "interview_talking_point": "I implemented the adapter pattern to abstract external dependencies, making the system testable and maintainable"
            })
            patterns.append("Adapter")

        if (path / "core").exists() or (path / "src" / "core").exists():
            patterns.append("Layered Architecture")

        # Check for microservices indicators
        services_dirs = ["services", "microservices", "apps"]
        is_microservices = any((path / d).exists() for d in services_dirs)

        structure = "Microservices" if is_microservices else "Layered Monolith"

        return {
            "highlights": highlights,
            "patterns": patterns,
            "structure": structure
        }

    async def _analyze_tech_stack(
        self,
        project_path: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Analyze technology stack

        Returns:
            {
                "frameworks": [{"name": "FastAPI", "version": "0.109.0"}],
                "databases": ["PostgreSQL", "Redis"],
                "infrastructure": ["Docker", "Kubernetes"],
                "mastery_levels": {"FastAPI": 0.85, "Redis": 0.60}
            }
        """
        path = Path(project_path)
        frameworks = []
        databases = []
        infrastructure = []

        # Python stack detection
        if language == "python":
            requirements_file = path / "requirements.txt"
            if requirements_file.exists():
                content = requirements_file.read_text(encoding="utf-8")

                if "fastapi" in content.lower():
                    frameworks.append({"name": "FastAPI", "version": self._extract_version(content, "fastapi")})
                if "django" in content.lower():
                    frameworks.append({"name": "Django", "version": self._extract_version(content, "django")})
                if "flask" in content.lower():
                    frameworks.append({"name": "Flask", "version": self._extract_version(content, "flask")})

                if "sqlalchemy" in content.lower():
                    databases.append("SQLAlchemy ORM")
                if "redis" in content.lower():
                    databases.append("Redis")
                if "psycopg2" in content.lower() or "asyncpg" in content.lower():
                    databases.append("PostgreSQL")

        # TypeScript stack detection
        elif language == "typescript":
            package_json = path / "package.json"
            if package_json.exists():
                import json
                data = json.loads(package_json.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                if "next" in deps:
                    frameworks.append({"name": "Next.js", "version": deps["next"]})
                if "react" in deps:
                    frameworks.append({"name": "React", "version": deps["react"]})
                if "express" in deps:
                    frameworks.append({"name": "Express", "version": deps["express"]})

        # Infrastructure detection
        if (path / "Dockerfile").exists():
            infrastructure.append("Docker")
        if (path / "docker-compose.yml").exists():
            infrastructure.append("Docker Compose")
        if (path / "kubernetes").exists() or (path / "k8s").exists():
            infrastructure.append("Kubernetes")

        return {
            "frameworks": frameworks,
            "databases": databases,
            "infrastructure": infrastructure,
            "mastery_levels": {}  # To be filled by MasteryAnalyzer
        }

    async def _identify_challenges(
        self,
        project_path: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """
        Identify technical challenges and how they were solved

        Returns:
            [
                {
                    "challenge": "Distributed transaction consistency",
                    "solution": "Implemented Saga pattern with compensating transactions",
                    "interview_point": "..."
                }
            ]
        """
        # Placeholder for challenge identification
        # In a real implementation, this would analyze code comments, commit messages, etc.
        return []

    def _generate_project_id(self, project_path: str) -> str:
        """Generate consistent project ID from path"""
        # Use hash of path for consistent ID
        path_hash = hashlib.md5(project_path.encode()).hexdigest()[:8]
        project_name = Path(project_path).name
        return f"proj-{project_name}-{path_hash}"

    def _extract_version(self, content: str, package_name: str) -> Optional[str]:
        """Extract package version from requirements.txt content"""
        for line in content.split("\n"):
            if package_name in line.lower():
                parts = line.split("==")
                if len(parts) == 2:
                    return parts[1].strip()
        return None
