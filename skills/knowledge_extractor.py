"""
Knowledge Extractor - 知识点提取器

借鉴: ECC continuous-learning-v2 的模式识别机制
改进: 更精细的知识点提取和结构化

核心功能:
1. 从代码中提取知识点
2. 从文档中提取知识点
3. 识别知识点之间的关联
4. 生成知识图谱节点
"""

import re
import hashlib
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class KnowledgeNode:
    """知识图谱节点（对应 ECC 的 instinct）"""
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
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExtractionResult:
    """提取结果"""
    nodes: List[KnowledgeNode]
    relationships: List[Tuple[str, str, str]]
    summary: str
    total_count: int


class KnowledgeExtractor:
    """
    知识点提取器

    借鉴 ECC continuous-learning-v2:
    - parse_instinct_file 的解析逻辑
    - trigger pattern 的模式匹配
    - domain classification 的分类策略

    我们的创新:
    - 多源提取（代码、文档、会话）
    - 知识图谱构建
    - 关系识别
    """

    NODE_TYPES = {
        "concept": "概念",
        "example": "示例",
        "practice": "实践",
        "theory": "理论",
    }

    CODE_PATTERNS = {
        "function_def": r"def\s+(\w+)\s*\([^)]*\):",
        "class_def": r"class\s+(\w+)(?:\([^)]*\))?:",
        "import": r"(?:from\s+(\S+)\s+)?import\s+(\S+)",
    }

    DOC_PATTERNS = {
        "heading": r"^#{1,6}\s+(.+?)$",
        "code_block": r"```(\w+)?\n([\s\S]*?)```",
    }

    def __init__(self):
        """初始化提取器"""
        pass

    def extract_from_code(self, code: str, language: str = "python") -> ExtractionResult:
        """从代码中提取知识点"""
        nodes = []
        lines = code.split('\n')

        for idx, line in enumerate(lines):
            if match := re.search(self.CODE_PATTERNS["function_def"], line):
                func_name = match.group(1)
                node = self._create_node(
                    title=f"函数: {func_name}",
                    content=self._extract_context(lines, idx, 5),
                    node_type="example",
                    category="coding",
                    tags=["function", language],
                    source="code",
                )
                nodes.append(node)

            if match := re.search(self.CODE_PATTERNS["class_def"], line):
                class_name = match.group(1)
                node = self._create_node(
                    title=f"类: {class_name}",
                    content=self._extract_context(lines, idx, 10),
                    node_type="example",
                    category="coding",
                    tags=["class", language],
                    source="code",
                )
                nodes.append(node)

        summary = f"从代码中提取了 {len(nodes)} 个知识点。"
        return ExtractionResult(
            nodes=nodes,
            relationships=[],
            summary=summary,
            total_count=len(nodes),
        )

    def extract_from_document(self, document: str) -> ExtractionResult:
        """从文档中提取知识点"""
        nodes = []

        for match in re.finditer(self.DOC_PATTERNS["heading"], document, re.MULTILINE):
            title = match.group(1).strip()
            start = match.end()
            end = document.find('\n#', start)
            if end == -1:
                end = len(document)
            content = document[start:end].strip()[:300]

            node = self._create_node(
                title=title,
                content=content,
                node_type="concept",
                category=self._infer_category(title, content),
                tags=self._extract_tags(content),
                source="document",
            )
            nodes.append(node)

        summary = f"从文档中提取了 {len(nodes)} 个知识点。"
        return ExtractionResult(
            nodes=nodes,
            relationships=[],
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
        return KnowledgeNode(
            id=node_id,
            title=title,
            content=content,
            type=node_type,
            category=category,
            tags=tags,
            source=source,
        )

    def _generate_id(self, title: str, content: str) -> str:
        """生成节点 ID（对应 ECC 的 _project_hash）"""
        hash_input = f"{title}:{content[:100]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    def _extract_context(self, lines: List[str], index: int, context_size: int) -> str:
        """提取代码上下文"""
        start = max(0, index - context_size)
        end = min(len(lines), index + context_size + 1)
        return '\n'.join(lines[start:end])

    def _infer_category(self, title: str, content: str) -> str:
        """推断类别（对应 ECC 的 _classify_category）"""
        text = (title + " " + content).lower()
        keywords_map = {
            "algorithm": ["算法", "复杂度"],
            "data-structure": ["数据结构", "链表", "树"],
            "system-design": ["系统", "架构", "设计"],
            "database": ["数据库", "SQL"],
        }

        for category, keywords in keywords_map.items():
            if any(kw in text for kw in keywords):
                return category

        return "general"

    def _extract_tags(self, content: str) -> List[str]:
        """提取标签"""
        tags = set()
        for match in re.finditer(r'\*\*(.+?)\*\*', content):
            tags.add(match.group(1).strip())
        return list(tags)[:10]
