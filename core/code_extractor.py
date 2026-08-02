"""
Code Extractor - 代码知识提取器

从 knowledge_extractor.py 重构而来
职责：从代码中提取知识点，生成结构化知识节点

核心功能:
1. 从代码中提取函数、类、模式
2. 从文档中提取概念
3. 生成知识图谱节点
4. 识别知识点关联
"""

import re
import hashlib
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    id: str
    title: str
    content: str
    type: str  # concept, example, practice, theory
    category: str
    tags: List[str] = field(default_factory=list)
    related_nodes: List[str] = field(default_factory=list)
    confidence: float = 0.5
    difficulty: float = 0.5
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExtractionResult:
    """提取结果"""
    nodes: List[KnowledgeNode]
    relationships: List[Tuple[str, str, str]]  # (from_id, to_id, relation_type)
    summary: str
    total_count: int


class CodeExtractor:
    """
    代码知识提取器

    支持的语言: Python, JavaScript, Java, Go
    """

    NODE_TYPES = {
        "concept": "概念",
        "example": "示例",
        "practice": "实践",
        "theory": "理论",
    }

    # Python 模式
    PYTHON_PATTERNS = {
        "function_def": r"def\s+(\w+)\s*\([^)]*\):",
        "class_def": r"class\s+(\w+)(?:\([^)]*\))?:",
        "import": r"(?:from\s+(\S+)\s+)?import\s+(\S+)",
        "decorator": r"@(\w+)",
    }

    # JavaScript 模式
    JS_PATTERNS = {
        "function_def": r"function\s+(\w+)\s*\([^)]*\)",
        "arrow_function": r"const\s+(\w+)\s*=\s*\([^)]*\)\s*=>",
        "class_def": r"class\s+(\w+)(?:\s+extends\s+(\w+))?",
        "import": r"import\s+(?:{([^}]+)}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]",
    }

    # 文档模式
    DOC_PATTERNS = {
        "heading": r"^#{1,6}\s+(.+?)$",
        "code_block": r"```(\w+)?\n([\s\S]*?)```",
        "link": r"\[([^\]]+)\]\(([^)]+)\)",
    }

    def __init__(self):
        """初始化提取器"""
        self.language_patterns = {
            "python": self.PYTHON_PATTERNS,
            "javascript": self.JS_PATTERNS,
            "typescript": self.JS_PATTERNS,
        }

    def extract_from_code(self, code: str, language: str = "python") -> ExtractionResult:
        """
        从代码中提取知识点

        Args:
            code: 源代码
            language: 编程语言

        Returns:
            ExtractionResult: 提取结果
        """
        nodes = []
        lines = code.split('\n')

        patterns = self.language_patterns.get(language.lower(), self.PYTHON_PATTERNS)

        for idx, line in enumerate(lines):
            # 提取函数定义
            if match := re.search(patterns.get("function_def", ""), line):
                func_name = match.group(1)
                context = self._extract_context(lines, idx, 5)

                node = self._create_node(
                    title=f"函数: {func_name}",
                    content=context,
                    node_type="example",
                    category="coding",
                    tags=["function", language],
                    source=f"code:{language}",
                )
                nodes.append(node)

            # 提取类定义
            if match := re.search(patterns.get("class_def", ""), line):
                class_name = match.group(1)
                context = self._extract_context(lines, idx, 10)

                node = self._create_node(
                    title=f"类: {class_name}",
                    content=context,
                    node_type="example",
                    category="coding",
                    tags=["class", language],
                    source=f"code:{language}",
                )
                nodes.append(node)

            # 提取装饰器/注解
            if "decorator" in patterns:
                if match := re.search(patterns["decorator"], line):
                    decorator_name = match.group(1)
                    context = self._extract_context(lines, idx, 3)

                    node = self._create_node(
                        title=f"装饰器: {decorator_name}",
                        content=context,
                        node_type="practice",
                        category="coding",
                        tags=["decorator", language],
                        source=f"code:{language}",
                    )
                    nodes.append(node)

        summary = f"从 {language} 代码中提取了 {len(nodes)} 个知识点。"
        return ExtractionResult(
            nodes=nodes,
            relationships=[],
            summary=summary,
            total_count=len(nodes),
        )

    def extract_from_document(self, document: str) -> ExtractionResult:
        """
        从 Markdown 文档中提取知识点

        Args:
            document: Markdown 文档内容

        Returns:
            ExtractionResult: 提取结果
        """
        nodes = []
        relationships = []

        # 提取标题和章节内容
        for match in re.finditer(self.DOC_PATTERNS["heading"], document, re.MULTILINE):
            title = match.group(1).strip()
            start = match.end()

            # 找到下一个标题或文档结尾
            next_match = re.search(r'\n#{1,6}\s+', document[start:])
            end = start + next_match.start() if next_match else len(document)

            content = document[start:end].strip()[:500]  # 限制长度

            node = self._create_node(
                title=title,
                content=content,
                node_type="concept",
                category=self._infer_category(title, content),
                tags=self._extract_tags(content),
                source="document",
            )
            nodes.append(node)

        # 提取代码块
        for match in re.finditer(self.DOC_PATTERNS["code_block"], document):
            language = match.group(1) or "text"
            code_content = match.group(2).strip()[:300]

            if language != "text" and len(code_content) > 20:
                node = self._create_node(
                    title=f"{language} 代码示例",
                    content=code_content,
                    node_type="example",
                    category="coding",
                    tags=[language, "code-example"],
                    source="document:code-block",
                )
                nodes.append(node)

        summary = f"从文档中提取了 {len(nodes)} 个知识点。"
        return ExtractionResult(
            nodes=nodes,
            relationships=relationships,
            summary=summary,
            total_count=len(nodes),
        )

    def _create_node(
        self,
        title: str,
        content: str,
        node_type: str,
        category: str,
        tags: List[str],
        source: str
    ) -> KnowledgeNode:
        """创建知识节点"""
        node_id = self._generate_id(title, content)

        # 简单的难度估算
        difficulty = self._estimate_difficulty(content)

        return KnowledgeNode(
            id=node_id,
            title=title,
            content=content,
            type=node_type,
            category=category,
            tags=tags,
            source=source,
            difficulty=difficulty,
        )

    def _generate_id(self, title: str, content: str) -> str:
        """生成节点 ID（使用 SHA256）"""
        hash_input = f"{title}:{content[:100]}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:12]

    def _extract_context(self, lines: List[str], index: int, context_size: int) -> str:
        """提取代码上下文"""
        start = max(0, index - context_size)
        end = min(len(lines), index + context_size + 1)
        return '\n'.join(lines[start:end])

    def _infer_category(self, title: str, content: str) -> str:
        """推断类别"""
        text = (title + " " + content).lower()

        keywords_map = {
            "algorithm": ["算法", "algorithm", "复杂度", "complexity", "排序", "sort"],
            "data-structure": ["数据结构", "data structure", "链表", "树", "图", "list", "tree", "graph"],
            "system-design": ["系统", "架构", "设计", "system", "architecture", "design"],
            "database": ["数据库", "database", "SQL", "索引", "index"],
            "network": ["网络", "network", "HTTP", "TCP", "协议", "protocol"],
            "security": ["安全", "security", "加密", "认证", "auth"],
            "framework": ["框架", "framework", "库", "library"],
        }

        for category, keywords in keywords_map.items():
            if any(kw in text for kw in keywords):
                return category

        return "general"

    def _extract_tags(self, content: str) -> List[str]:
        """提取标签（从粗体文本）"""
        tags = set()

        # 提取 Markdown 粗体
        for match in re.finditer(r'\*\*(.+?)\*\*', content):
            tag = match.group(1).strip()
            if len(tag) < 30:  # 只保留短标签
                tags.add(tag)

        # 提取代码标记
        for match in re.finditer(r'`(.+?)`', content):
            tag = match.group(1).strip()
            if len(tag) < 20:
                tags.add(tag)

        return list(tags)[:10]

    def _estimate_difficulty(self, content: str) -> float:
        """简单的难度估算"""
        # 基于内容长度
        length_score = min(1.0, len(content) / 500)

        # 基于技术术语密度
        tech_terms = [
            "实现", "原理", "机制", "架构", "优化", "性能",
            "implement", "principle", "mechanism", "architecture", "optimize", "performance"
        ]
        term_count = sum(1 for term in tech_terms if term in content.lower())
        term_score = min(1.0, term_count / 3)

        # 基于代码复杂度
        code_indicators = ["{", "}", "class", "function", "def", "=>", "async", "await"]
        code_count = sum(1 for indicator in code_indicators if indicator in content)
        code_score = min(1.0, code_count / 5)

        # 综合评分
        difficulty = (length_score * 0.3 + term_score * 0.4 + code_score * 0.3)
        return round(difficulty, 2)

    def find_relationships(self, nodes: List[KnowledgeNode]) -> List[Tuple[str, str, str]]:
        """
        识别节点之间的关系

        Args:
            nodes: 知识节点列表

        Returns:
            关系列表 [(from_id, to_id, relation_type)]
        """
        relationships = []

        for i, node1 in enumerate(nodes):
            for node2 in nodes[i+1:]:
                # 检查是否有共同标签
                common_tags = set(node1.tags) & set(node2.tags)
                if len(common_tags) >= 2:
                    relationships.append((node1.id, node2.id, "related_to"))

                # 检查是否同一类别
                if node1.category == node2.category and node1.category != "general":
                    relationships.append((node1.id, node2.id, "same_category"))

                # 检查内容是否提及另一个节点的标题
                if node2.title.lower() in node1.content.lower():
                    relationships.append((node1.id, node2.id, "mentions"))
                elif node1.title.lower() in node2.content.lower():
                    relationships.append((node2.id, node1.id, "mentions"))

        return relationships
