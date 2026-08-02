"""
Learning Tools - MCP Server Tools

MCP Tools for Learning System
Exposes core algorithms as MCP protocol tools

Tools:
1. analyze_session - Extract knowledge from session text
2. get_review_plan - Generate review schedule
3. estimate_difficulty - Assess knowledge difficulty
4. calculate_mastery - Calculate mastery level
5. search_knowledge - Search knowledge graph
6. analyze_project - Analyze project codebase (NEW)
"""

import sys
import os
from typing import Dict, List, Any

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, project_root)

from core.code_extractor import CodeExtractor, KnowledgeNode
from core.review_scheduler import ReviewScheduler
from core.difficulty_estimator import DifficultyEstimator
from core.mastery_analyzer import MasteryAnalyzer, KnowledgePoint
import asyncio
import json


class LearningTools:
    """Learning Tools for MCP Server"""

    def __init__(self):
        """Initialize tools"""
        self.code_extractor = CodeExtractor()
        self.review_scheduler = ReviewScheduler()
        self.difficulty_estimator = DifficultyEstimator()
        self.mastery_analyzer = MasteryAnalyzer()
        self._project_agent = None  # Lazy initialization

    def analyze_session(self, session_text: str, content_type: str = "document") -> Dict[str, Any]:
        """
        Tool: analyze_session
        Extract knowledge points from session text

        Args:
            session_text: Session content (code or markdown)
            content_type: "document" or "code"

        Returns:
            Extraction result with nodes and summary
        """
        try:
            if content_type == "code":
                # Extract from code
                language = self._detect_language(session_text)
                result = self.code_extractor.extract_from_code(session_text, language)
            else:
                # Extract from document
                result = self.code_extractor.extract_from_document(session_text)

            # Convert to dict format
            nodes_dict = [
                {
                    "id": node.id,
                    "title": node.title,
                    "content": node.content,
                    "type": node.type,
                    "category": node.category,
                    "tags": node.tags,
                    "difficulty": node.difficulty,
                    "confidence": node.confidence,
                    "source": node.source,
                    "created_at": node.created_at,
                }
                for node in result.nodes
            ]

            return {
                "success": True,
                "nodes": nodes_dict,
                "relationships": result.relationships,
                "summary": result.summary,
                "total_count": result.total_count,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "nodes": [],
                "total_count": 0,
            }

    def get_review_plan(self, knowledge_points: List[Dict], target_date: str = None) -> Dict[str, Any]:
        """
        Tool: get_review_plan
        Generate review schedule based on Ebbinghaus curve

        Args:
            knowledge_points: List of knowledge point dicts
            target_date: Target date (ISO format), defaults to today

        Returns:
            Review plan with prioritized items
        """
        try:
            plan = self.review_scheduler.generate_plan(knowledge_points, target_date)

            # Convert ReviewItems to dicts
            high_priority = [self._review_item_to_dict(item) for item in plan.high_priority]
            medium_priority = [self._review_item_to_dict(item) for item in plan.medium_priority]
            low_priority = [self._review_item_to_dict(item) for item in plan.low_priority]

            return {
                "success": True,
                "plan_date": plan.plan_date,
                "total_items": plan.total_items,
                "high_priority": high_priority,
                "medium_priority": medium_priority,
                "low_priority": low_priority,
                "estimated_time_minutes": plan.estimated_time_minutes,
                "summary": plan.summary,
                "_meta": {
                    "ttlMs": 0  # Don't cache - always recalculate
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_items": 0,
            }

    def estimate_difficulty(self, content: str, category: str = "general", metadata: Dict = None) -> Dict[str, Any]:
        """
        Tool: estimate_difficulty
        Assess knowledge difficulty (5 dimensions)

        Args:
            content: Knowledge content
            category: Knowledge category
            metadata: Additional metadata (e.g., code_depth)

        Returns:
            Difficulty score with dimensions breakdown
        """
        try:
            score = self.difficulty_estimator.estimate(content, category, metadata)

            return {
                "success": True,
                "overall": score.overall,
                "dimensions": score.dimensions,
                "explanation": score.explanation,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "overall": 0.5,
            }

    def calculate_mastery(self, knowledge_points: List[Dict]) -> Dict[str, Any]:
        """
        Tool: calculate_mastery
        Calculate mastery level for knowledge points

        Args:
            knowledge_points: List of knowledge point dicts with confidence/difficulty

        Returns:
            Mastery report with weak/strong areas
        """
        try:
            # Convert dicts to KnowledgePoint objects
            kp_objects = [
                KnowledgePoint(
                    id=kp.get("id", ""),
                    title=kp.get("title", ""),
                    content=kp.get("content", ""),
                    category=kp.get("category", "general"),
                    confidence=kp.get("confidence", 0.5),
                    difficulty=kp.get("difficulty", 0.5),
                    evidence=kp.get("evidence", []),
                    created_at=kp.get("created_at", ""),
                    last_reviewed=kp.get("last_reviewed"),
                    review_count=kp.get("review_count", 0),
                )
                for kp in knowledge_points
            ]

            report = self.mastery_analyzer.analyze_mastery(kp_objects)

            return {
                "success": True,
                "mastery_level": report.mastery_level,
                "total_concepts": report.total_concepts,
                "review_priority": report.review_priority,
                "weak_areas": report.weak_areas,
                "strong_areas": report.strong_areas,
                "summary": report.summary,
                "generated_at": report.generated_at,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "mastery_level": 0.0,
                "total_concepts": 0,
            }

    def search_knowledge(self, query: str) -> Dict[str, Any]:
        """
        Tool: search_knowledge
        Search knowledge graph (delegates to Memory MCP)

        Note: This is a placeholder - actual implementation should
        call the Memory MCP server via MCP protocol

        Args:
            query: Search query

        Returns:
            Search results from knowledge graph
        """
        # TODO: Implement actual MCP call to Memory server
        # For now, return placeholder
        return {
            "success": True,
            "query": query,
            "nodes": [],
            "message": "Memory MCP integration pending",
            "_meta": {
                "ttlMs": 3600000,  # Cache 1 hour
                "cacheScope": "user"
            }
        }

    def analyze_project(self, project_path: str, request_config: bool = True) -> Dict[str, Any]:
        """
        Tool: analyze_project
        Analyze project codebase with optional interactive configuration

        Args:
            project_path: Path to project root directory
            request_config: If True, return MCP App for user configuration

        Returns:
            Either InputRequiredResult (with MCP App) or analysis result
        """
        import os

        # Validate project path
        if not os.path.exists(project_path):
            return {
                "success": False,
                "error": f"Project path does not exist: {project_path}"
            }

        # If requesting configuration, return MCP App
        if request_config:
            app_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'apps',
                'project_analysis_config.html'
            )

            return {
                "success": True,
                "result": {
                    "_meta": {
                        "io.modelcontextprotocol/inputRequired": {
                            "message": f"Configure analysis for: {os.path.basename(project_path)}",
                            "uiTemplate": {
                                "templateId": "io.learning-system.project-analysis-config",
                                "templatePath": app_path,
                                "data": {
                                    "project_path": project_path,
                                    "project_name": os.path.basename(project_path)
                                }
                            }
                        }
                    }
                }
            }

        # Otherwise, perform analysis with default config
        default_config = {
            "depth": "shallow",
            "focus": ["architecture", "tech_stack"],
            "language": "auto"
        }

        return self._perform_project_analysis(project_path, default_config)

    def _perform_project_analysis(self, project_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform actual project analysis

        Args:
            project_path: Project directory path
            config: Analysis configuration from user

        Returns:
            Analysis result
        """
        try:
            # Initialize ProjectAgent if needed
            if self._project_agent is None:
                from ..agents.project_agent import ProjectAgent
                from ..bus.agent_bus import bus
                self._project_agent = ProjectAgent("project_agent", bus)

            # Run analysis synchronously (simulate async)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                self._project_agent._analyze_project(project_path, config)
            )

            loop.close()

            return {
                "success": True,
                "result": result,
                "_meta": {
                    "ttlMs": 86400000,  # Cache for 1 day
                    "cacheScope": "user"
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }

    def _detect_language(self, code: str) -> str:
        """Detect programming language from code"""
        if "def " in code or "import " in code or "class " in code:
            return "python"
        elif "function " in code or "const " in code or "=>" in code:
            return "javascript"
        elif "public class" in code or "public static" in code:
            return "java"
        elif "func " in code or "package " in code:
            return "go"
        else:
            return "python"  # default

    def _review_item_to_dict(self, item) -> Dict[str, Any]:
        """Convert ReviewItem to dict"""
        return {
            "knowledge_id": item.knowledge_id,
            "title": item.title,
            "category": item.category,
            "difficulty": item.difficulty,
            "confidence": item.confidence,
            "last_reviewed": item.last_reviewed,
            "review_count": item.review_count,
            "next_review_date": item.next_review_date,
            "priority_score": item.priority_score,
        }


# Singleton instance
learning_tools = LearningTools()


# Tool functions for MCP Server registration
def analyze_session(session_text: str, content_type: str = "document") -> Dict[str, Any]:
    """Extract knowledge from session"""
    return learning_tools.analyze_session(session_text, content_type)


def get_review_plan(knowledge_points: List[Dict], target_date: str = None) -> Dict[str, Any]:
    """Generate review schedule"""
    return learning_tools.get_review_plan(knowledge_points, target_date)


def estimate_difficulty(content: str, category: str = "general", metadata: Dict = None) -> Dict[str, Any]:
    """Assess knowledge difficulty"""
    return learning_tools.estimate_difficulty(content, category, metadata)


def calculate_mastery(knowledge_points: List[Dict]) -> Dict[str, Any]:
    """Calculate mastery level"""
    return learning_tools.calculate_mastery(knowledge_points)


def search_knowledge(query: str) -> Dict[str, Any]:
    """Search knowledge graph"""
    return learning_tools.search_knowledge(query)


def analyze_project(project_path: str, request_config: bool = True) -> Dict[str, Any]:
    """
    Analyze project codebase with interactive configuration

    Args:
        project_path: Path to project root directory
        request_config: Whether to request user configuration via MCP App

    Returns:
        MCP result with either InputRequired (if request_config=True) or analysis result
    """
    return learning_tools.analyze_project(project_path, request_config)
