"""
Session Reviewer - 会话复习器

借鉴: ECC continuous-learning-v2 的 instinct 提取机制
改进: 针对面试复习场景优化

核心功能:
1. 解析会话内容
2. 识别知识点模式
3. 评估掌握程度
4. 生成复习建议
"""

import re
from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class KnowledgePoint:
    """知识点数据结构"""
    id: str
    title: str
    content: str
    category: str  # 对应 ECC 的 domain
    confidence: float  # 0.0-1.0，对应 ECC 的 confidence
    difficulty: float  # 0.0-1.0，我们的创新
    evidence: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_reviewed: Optional[str] = None
    review_count: int = 0


@dataclass
class SessionAnalysis:
    """会话分析结果"""
    session_id: str
    knowledge_points: List[KnowledgePoint]
    summary: str
    total_concepts: int
    mastery_level: float  # 整体掌握度
    review_priority: List[str]  # 需要优先复习的知识点 ID
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionReviewer:
    """
    会话复习器

    借鉴 ECC continuous-learning-v2 的核心思想:
    - Hook-based 观察 -> 我们的会话捕获
    - Instinct 提取 -> 我们的知识点提取
    - Confidence 评分 -> 我们的掌握度评分
    - Domain 分类 -> 我们的 Category 分类

    我们的创新:
    - 增加难度评估（difficulty）
    - 增加复习优先级排序
    - 针对面试场景优化分类
    """

    # 知识点类别（对应 ECC 的 domains）
    CATEGORIES = [
        "algorithm",      # 算法
        "data-structure", # 数据结构
        "system-design",  # 系统设计
        "coding",         # 编码实践
        "framework",      # 框架使用
        "database",       # 数据库
        "network",        # 网络
        "security",       # 安全
        "devops",         # DevOps
        "general",        # 通用
    ]

    # 触发模式（借鉴 ECC 的 trigger 机制）
    TRIGGER_PATTERNS = {
        "definition": r"(?:什么是|定义|概念|介绍)(.+?)(?:\?|？|。|\n)",
        "how_to": r"(?:如何|怎么|怎样)(.+?)(?:\?|？|。|\n)",
        "why": r"(?:为什么|原因|原理)(.+?)(?:\?|？|。|\n)",
        "comparison": r"(?:对比|比较|区别|vs)(.+?)(?:\?|？|。|\n)",
        "best_practice": r"(?:最佳实践|推荐|建议)(.+?)(?:\?|？|。|\n)",
    }

    def __init__(self):
        """初始化会话复习器"""
        self.min_confidence = 0.3  # 对应 ECC 的 min_confidence
        self.high_confidence_threshold = 0.8  # 对应 ECC 的 auto_promote_confidence

    def analyze_session(self, session_content: str, session_id: str) -> SessionAnalysis:
        """
        分析会话内容，提取知识点

        对应 ECC 的: Observer Agent 分析 observations.jsonl

        Args:
            session_content: 会话内容（markdown 格式）
            session_id: 会话唯一标识

        Returns:
            SessionAnalysis: 分析结果
        """
        # 1. 分段（借鉴 ECC 的分段策略）
        sections = self._split_sections(session_content)

        # 2. 提取知识点（对应 ECC 的 instinct 提取）
        knowledge_points = []
        for idx, section in enumerate(sections):
            points = self._extract_knowledge_points(section, f"{session_id}-{idx}")
            knowledge_points.extend(points)

        # 3. 计算整体掌握度（我们的创新）
        mastery_level = self._calculate_mastery_level(knowledge_points)

        # 4. 生成复习优先级（我们的创新）
        review_priority = self._generate_review_priority(knowledge_points)

        # 5. 生成摘要
        summary = self._generate_summary(knowledge_points)

        return SessionAnalysis(
            session_id=session_id,
            knowledge_points=knowledge_points,
            summary=summary,
            total_concepts=len(knowledge_points),
            mastery_level=mastery_level,
            review_priority=review_priority,
        )

    def _split_sections(self, content: str) -> List[str]:
        """
        分段策略

        借鉴 ECC 的 parse_instinct_file 逻辑:
        - 按标记分隔（ECC 用 ---，我们用 markdown headers）
        - 保持内容完整性
        """
        # 按 markdown 标题分段
        sections = re.split(r'\n#{1,3}\s+', content)
        return [s.strip() for s in sections if s.strip()]

    def _extract_knowledge_points(self, section: str, base_id: str) -> List[KnowledgePoint]:
        """
        从段落中提取知识点

        对应 ECC 的 instinct 提取逻辑:
        - 模式匹配（TRIGGER_PATTERNS）
        - 置信度评分
        - 分类标记
        """
        points = []

        # 检测每种触发模式
        for pattern_type, pattern in self.TRIGGER_PATTERNS.items():
            matches = re.finditer(pattern, section, re.IGNORECASE)
            for idx, match in enumerate(matches):
                title = match.group(1).strip()

                # 提取上下文作为 content
                context_start = max(0, match.start() - 100)
                context_end = min(len(section), match.end() + 200)
                content = section[context_start:context_end].strip()

                # 分类（简化版，实际应该用 NLP）
                category = self._classify_category(title, content)

                # 初始置信度（对应 ECC 的 confidence）
                confidence = 0.5  # 默认中等置信度

                # 难度评估（我们的创新）
                difficulty = self._estimate_difficulty_simple(content)

                point = KnowledgePoint(
                    id=f"{base_id}-{pattern_type}-{idx}",
                    title=title,
                    content=content,
                    category=category,
                    confidence=confidence,
                    difficulty=difficulty,
                    evidence=[f"Found via {pattern_type} pattern"],
                )
                points.append(point)

        return points

    def _classify_category(self, title: str, content: str) -> str:
        """
        知识点分类

        对应 ECC 的 domain 分类逻辑
        """
        text = (title + " " + content).lower()

        # 简单的关键词匹配（实际应该用更复杂的 NLP）
        keywords_map = {
            "algorithm": ["算法", "复杂度", "排序", "搜索", "递归", "动态规划"],
            "data-structure": ["数据结构", "链表", "树", "图", "栈", "队列", "哈希"],
            "system-design": ["系统设计", "架构", "扩展性", "高可用", "分布式"],
            "database": ["数据库", "SQL", "索引", "事务", "查询"],
            "network": ["网络", "HTTP", "TCP", "IP", "协议"],
            "security": ["安全", "加密", "认证", "授权", "漏洞"],
        }

        for category, keywords in keywords_map.items():
            if any(kw in text for kw in keywords):
                return category

        return "general"

    def _estimate_difficulty_simple(self, content: str) -> float:
        """
        简单难度评估

        我们的创新: ECC 没有难度评估

        评估维度:
        1. 内容长度
        2. 技术术语密度
        3. 代码复杂度（如果有代码块）
        """
        # 1. 长度因子
        length_score = min(1.0, len(content) / 500)

        # 2. 技术术语密度
        tech_terms = ["实现", "原理", "机制", "架构", "优化", "性能"]
        term_count = sum(1 for term in tech_terms if term in content)
        term_score = min(1.0, term_count / 3)

        # 3. 代码块因子
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        code_score = min(1.0, len(code_blocks) * 0.3)

        # 综合评分
        difficulty = (length_score * 0.3 + term_score * 0.4 + code_score * 0.3)
        return round(difficulty, 2)

    def _calculate_mastery_level(self, knowledge_points: List[KnowledgePoint]) -> float:
        """
        计算整体掌握度

        我们的创新: 基于所有知识点的平均 confidence
        """
        if not knowledge_points:
            return 0.0

        total_confidence = sum(kp.confidence for kp in knowledge_points)
        return round(total_confidence / len(knowledge_points), 2)

    def _generate_review_priority(self, knowledge_points: List[KnowledgePoint]) -> List[str]:
        """
        生成复习优先级

        我们的创新: 结合 confidence 和 difficulty 排序
        对应 ECC 的 evolve 聚类思想

        优先级规则:
        - 低 confidence + 高 difficulty = 最优先
        - 高 difficulty + 中 confidence = 次优先
        - 其他按 confidence 升序
        """
        # 计算优先级分数 (分数越低越优先)
        scored_points = []
        for kp in knowledge_points:
            # 优先级 = confidence - difficulty (越低越需要复习)
            priority_score = kp.confidence - (kp.difficulty * 0.5)
            scored_points.append((kp.id, priority_score))

        # 按分数排序
        scored_points.sort(key=lambda x: x[1])

        # 返回前 10 个最需要复习的知识点 ID
        return [kp_id for kp_id, _ in scored_points[:10]]

    def _generate_summary(self, knowledge_points: List[KnowledgePoint]) -> str:
        """
        生成会话摘要

        对应 ECC 的 evolve 分析报告
        """
        if not knowledge_points:
            return "本次会话未提取到知识点。"

        # 按类别统计
        category_counts = {}
        for kp in knowledge_points:
            category_counts[kp.category] = category_counts.get(kp.category, 0) + 1

        # 生成摘要
        summary_parts = [
            f"本次会话共提取 {len(knowledge_points)} 个知识点。",
            f"涉及类别: {', '.join(category_counts.keys())}。",
        ]

        # 高难度知识点
        high_difficulty = [kp for kp in knowledge_points if kp.difficulty >= 0.7]
        if high_difficulty:
            summary_parts.append(f"其中 {len(high_difficulty)} 个为高难度知识点。")

        # 低掌握度知识点
        low_confidence = [kp for kp in knowledge_points if kp.confidence < 0.5]
        if low_confidence:
            summary_parts.append(f"建议重点复习 {len(low_confidence)} 个低掌握度知识点。")

        return " ".join(summary_parts)

    def update_confidence(
        self,
        knowledge_point: KnowledgePoint,
        review_result: bool,
        delta: float = 0.1
    ) -> KnowledgePoint:
        """
        更新知识点置信度

        对应 ECC 的 confidence 演化机制:
        - 正确回答 -> 提升 confidence
        - 错误回答 -> 降低 confidence

        Args:
            knowledge_point: 知识点
            review_result: 复习结果（True=掌握，False=未掌握）
            delta: 变化幅度

        Returns:
            更新后的知识点
        """
        if review_result:
            # 掌握良好 -> 提升 confidence
            knowledge_point.confidence = min(0.9, knowledge_point.confidence + delta)
        else:
            # 未掌握 -> 降低 confidence
            knowledge_point.confidence = max(0.3, knowledge_point.confidence - delta * 1.5)

        # 更新复习记录
        knowledge_point.last_reviewed = datetime.now(timezone.utc).isoformat()
        knowledge_point.review_count += 1

        return knowledge_point
