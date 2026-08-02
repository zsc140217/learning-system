"""
Interview Agent
Generates interview questions and answers based on project analysis
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_agent import BaseAgent


class InterviewAgent(BaseAgent):
    """
    Generates interview questions and standard answers based on project analysis.

    Subscribes to: project.analysis_completed
    Emits: interview.questions_generated

    Features:
    - Extracts technical highlights from project analysis
    - Generates behavioral and technical interview questions
    - Provides standard answer templates (with optional LLM enhancement)
    - Identifies weak knowledge points requiring review
    """

    def __init__(self, agent_id: str, bus, llm_provider=None):
        super().__init__(agent_id, bus)
        # Question templates for different categories
        self._question_templates = self._init_question_templates()
        # Optional LLM provider for generating high-quality answers
        self._llm_provider = llm_provider
        self._llm_available = llm_provider is not None

    async def start(self) -> None:
        """Start the agent and subscribe to events"""
        await super().start()
        await self.subscribe("project.analysis_completed")

    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        Process project.analysis_completed event and generate interview questions

        Args:
            event: Event containing project_id and analysis results
        """
        event_type = event.get("type")

        if event_type != "project.analysis_completed":
            return

        project_id = event.get("project_id")
        analysis = event.get("analysis", {})

        # Generate interview questions
        questions = await self._generate_questions(project_id, analysis)

        # Emit questions generated event
        await self.emit({
            "type": "interview.questions_generated",
            "project_id": project_id,
            "questions": questions,
            "generated_at": datetime.now().isoformat()
        })

    async def _generate_questions(
        self,
        project_id: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate interview questions based on project analysis

        Args:
            project_id: Project identifier
            analysis: Project analysis results

        Returns:
            List of question dictionaries with answers
        """
        questions = []

        # Extract key information
        project_path = analysis.get("project_path", "unknown")
        project_name = project_path.split("\\")[-1] if "\\" in project_path else project_path.split("/")[-1]
        language = analysis.get("language", "unknown")
        tech_stack = analysis.get("tech_stack", {})
        architecture = analysis.get("architecture", {})

        # 1. Architecture questions
        architecture_highlights = architecture.get("highlights", [])
        patterns = architecture.get("patterns", [])

        if patterns:
            for pattern in patterns:
                q = self._generate_architecture_question(project_name, pattern, architecture_highlights)
                if q:
                    questions.append(q)

        # 2. Tech stack questions
        frameworks = tech_stack.get("frameworks", [])
        databases = tech_stack.get("databases", [])

        if frameworks:
            for framework in frameworks[:3]:  # Limit to top 3
                q = self._generate_tech_stack_question(project_name, framework, "framework")
                if q:
                    questions.append(q)

        if databases:
            for database in databases[:2]:  # Limit to top 2
                q = self._generate_tech_stack_question(project_name, database, "database")
                if q:
                    questions.append(q)

        # 3. Technical challenge questions
        if frameworks or patterns:
            q = self._generate_challenge_question(project_name, language)
            if q:
                questions.append(q)

        # 4. Project overview question (always include)
        q = self._generate_overview_question(project_name, analysis)
        questions.insert(0, q)  # Put at the beginning

        # 5. Enhance answers with LLM if available
        if self._llm_available:
            questions = await self._enhance_answers_with_llm(questions, analysis)

        return questions

    async def _enhance_answers_with_llm(
        self,
        questions: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Enhance standard answers using LLM

        Args:
            questions: List of questions with template answers
            analysis: Project analysis for context

        Returns:
            Questions with LLM-enhanced answers
        """
        enhanced_questions = []

        for q in questions:
            try:
                # Generate enhanced answer using LLM
                enhanced_answer = await self._generate_llm_answer(q, analysis)

                # Keep template as fallback
                q["template_answer"] = q["standard_answer"]
                q["standard_answer"] = enhanced_answer
                q["answer_source"] = "llm"

            except Exception as e:
                # Fallback to template on error
                self._logger.warning(f"LLM enhancement failed for {q['id']}: {e}")
                q["answer_source"] = "template"

            enhanced_questions.append(q)

        return enhanced_questions

    async def _generate_llm_answer(
        self,
        question: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> str:
        """
        Generate answer using LLM based on question and project context

        Args:
            question: Question dict with template answer
            analysis: Project analysis results

        Returns:
            LLM-generated answer text
        """
        # Prepare context for LLM
        project_path = analysis.get("project_path", "unknown")
        project_name = project_path.split("\\")[-1] if "\\" in project_path else project_path.split("/")[-1]
        language = analysis.get("language", "unknown")
        tech_stack = analysis.get("tech_stack", {})
        architecture = analysis.get("architecture", {})

        # Build prompt for LLM
        prompt = f"""You are helping a candidate prepare for a technical interview.

**Project Context:**
- Project Name: {project_name}
- Language: {language}
- Architecture: {architecture.get("structure", "unknown")}
- Tech Stack: {self._format_tech_stack(tech_stack)}

**Interview Question:**
{question["question"]}

**Template Answer (for reference):**
{question["standard_answer"]}

**Task:**
Generate a natural, professional interview answer (150-250 words) that:
1. Directly answers the question
2. Uses the project context provided
3. Sounds conversational, not like a template
4. Includes specific technical details
5. Demonstrates deep understanding

**Answer:**"""

        messages = [{"role": "user", "content": prompt}]

        # Call LLM
        response = await self._llm_provider.chat(
            messages,
            temperature=0.7,
            max_tokens=500
        )

        return response.strip()

    def _generate_overview_question(
        self,
        project_name: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate project overview question"""
        language = analysis.get("language", "unknown")
        architecture = analysis.get("architecture", {})
        structure = architecture.get("structure", "unknown")

        return {
            "id": f"q-overview-{project_name}",
            "category": "project_overview",
            "difficulty": "easy",
            "question": f"Please introduce your {project_name} project",
            "standard_answer": f"""
This is a {language.upper()}-based project using {structure} architecture.

**Project Positioning:**
[Describe project goals based on functionality]

**Tech Stack:**
- Language: {language.upper()}
- Architecture: {structure}
{self._format_tech_stack(analysis.get("tech_stack", {}))}

**Core Features:**
[List 2-3 core functional modules]

**My Role:**
[Describe role and contributions in the project]
            """.strip(),
            "key_points": [
                f"Project uses {structure} architecture",
                f"Developed with {language.upper()}",
                "Clear description of positioning and core features"
            ],
            "follow_up_questions": [
                f"Why choose {structure} architecture?",
                "What technical challenges did you encounter?"
            ]
        }

    def _generate_architecture_question(
        self,
        project_name: str,
        pattern: str,
        highlights: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Generate architecture-related question"""
        return {
            "id": f"q-arch-{pattern.lower().replace(' ', '-')}",
            "category": "architecture",
            "difficulty": "medium",
            "question": f"How is the architecture of {project_name} designed?",
            "standard_answer": f"""
The project adopts the {pattern} architectural pattern.

**Design Philosophy:**
{self._format_highlights(highlights)}

**Advantages:**
- Decoupling: Clear responsibilities, independent modules
- Testability: Can test each module separately
- Extensibility: Add features without modifying existing code

**Practical Application:**
[Describe how this pattern is applied in the project]
            """.strip(),
            "key_points": [
                f"Uses {pattern} pattern",
                "Explain design advantages",
                "Provide specific implementation examples"
            ],
            "follow_up_questions": [
                f"Why choose {pattern} over other architectures?",
                "What are the drawbacks of this architecture?"
            ]
        }

    def _generate_tech_stack_question(
        self,
        project_name: str,
        tech: Dict[str, Any],
        tech_type: str
    ) -> Optional[Dict[str, Any]]:
        """Generate tech stack question"""
        tech_name = tech.get("name", "unknown")

        if tech_type == "framework":
            return {
                "id": f"q-tech-{tech_name.lower()}",
                "category": "tech_stack",
                "difficulty": "medium",
                "question": f"How is {tech_name} used in the {project_name} project?",
                "standard_answer": f"""
The project uses the {tech_name} framework.

**Selection Rationale:**
- [List 2-3 reasons for choosing this framework]

**Core Functions:**
- [Function 1]
- [Function 2]
- [Function 3]

**Practical Experience:**
- [Share a specific implementation case or problem encountered]
                """.strip(),
                "key_points": [
                    f"Explain why {tech_name} was chosen",
                    "List core use cases",
                    "Share practical experience"
                ],
                "follow_up_questions": [
                    f"What are alternatives to {tech_name}?",
                    f"Any pitfalls encountered with {tech_name}?"
                ]
            }
        elif tech_type == "database":
            return {
                "id": f"q-tech-{tech_name.lower()}",
                "category": "tech_stack",
                "difficulty": "medium",
                "question": f"What is the database design of {project_name}?",
                "standard_answer": f"""
The project uses {tech_name} database.

**Database Design:**
- [Core table structure]
- [Key index design]

**Performance Optimization:**
- [Optimization 1]
- [Optimization 2]

**Practical Experience:**
- [Share a specific database optimization case]
                """.strip(),
                "key_points": [
                    f"Uses {tech_name}",
                    "Clear database structure description",
                    "Explain performance optimization measures"
                ],
                "follow_up_questions": [
                    "How to ensure data consistency?",
                    "Encountered performance bottlenecks? How solved?"
                ]
            }

        return None

    def _generate_challenge_question(
        self,
        project_name: str,
        language: str
    ) -> Dict[str, Any]:
        """Generate technical challenge question"""
        return {
            "id": f"q-challenge-{project_name}",
            "category": "technical_challenges",
            "difficulty": "hard",
            "question": f"What technical difficulties did you encounter in {project_name}? How were they resolved?",
            "standard_answer": """
**Difficulties Encountered:**
[Describe a specific technical challenge, e.g., performance bottleneck, concurrency issue, architectural design problem]

**Analysis Process:**
1. [Problem symptoms]
2. [Investigation steps]
3. [Root cause identification]

**Solution:**
- [Solution description]
- [Implementation details]
- [Effect evaluation]

**Lessons Learned:**
[What was learned from this problem]
            """.strip(),
            "key_points": [
                "Choose representative technical challenges",
                "Clear description of problem and solution process",
                "Emphasize thinking approach and learnings"
            ],
            "follow_up_questions": [
                "Did you consider other solutions?",
                "If redesigning, what would you do differently?"
            ]
        }

    def _format_tech_stack(self, tech_stack: Dict[str, Any]) -> str:
        """Format tech stack for display"""
        lines = []

        frameworks = tech_stack.get("frameworks", [])
        if frameworks:
            framework_names = [f["name"] for f in frameworks]
            lines.append(f"- Frameworks: {', '.join(framework_names)}")

        databases = tech_stack.get("databases", [])
        if databases:
            db_names = [d["name"] for d in databases]
            lines.append(f"- Databases: {', '.join(db_names)}")

        infrastructure = tech_stack.get("infrastructure", [])
        if infrastructure:
            infra_names = [i["name"] for i in infrastructure]
            lines.append(f"- Infrastructure: {', '.join(infra_names)}")

        return "\n".join(lines) if lines else "- [To be added]"

    def _format_highlights(self, highlights: List[Dict[str, Any]]) -> str:
        """Format architecture highlights"""
        if not highlights:
            return "[Describe design philosophy based on actual architecture]"

        lines = []
        for h in highlights[:3]:  # Limit to 3
            title = h.get("title", "")
            description = h.get("description", "")
            if title:
                lines.append(f"- {title}: {description}")

        return "\n".join(lines) if lines else "[Describe design philosophy based on actual architecture]"

    def _init_question_templates(self) -> Dict[str, Any]:
        """Initialize question templates for different patterns"""
        return {
            "architecture": {
                "Agent-Based": {
                    "question": "How is the Agent architecture designed?",
                    "answer_template": "Multi-Agent architecture with event bus communication..."
                },
                "Layered Architecture": {
                    "question": "How is the layered architecture divided?",
                    "answer_template": "Divided into presentation, business, and data layers..."
                },
                "Microservices": {
                    "question": "How is the microservices architecture split?",
                    "answer_template": "Split into independent services by business domain..."
                }
            }
        }
