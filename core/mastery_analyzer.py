"""
Mastery Analyzer - 掌握度分析器

从 session_reviewer.py 重构而来
职责：专注于掌握度分析，不包含解析/提取功能（由 ECC Instinct 处理）

核心功能:
1. 分析知识点掌握度
2. 计算整体掌握水平
3. 生成复习优先级
4. 更新置信度

与 ECC 的关系:
- ECC Instinct 负责: 模式提取、观察记录
- 我们负责: 掌握度评估、复习优先级（ECC 没有的功能）
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class KnowledgePoint:
    """知识点数据结构"""
    id: str
    title: str
    content: str
    category: str
    confidence: float  # 0.0-1.0，掌握度
    difficulty: float  # 0.0-1.0，难度
    evidence: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_reviewed: Optional[str] = None
    review_count: int = 0


@dataclass
class MasteryReport:
    """掌握度报告"""
    mastery_level: float  # 整体掌握度 0.0-1.0
    total_concepts: int
    review_priority: List[str]  # 需要优先复习的知识点 ID
    weak_areas: Dict[str, int]  # 薄弱领域: {category: count}
    strong_areas: Dict[str, int]  # 强项领域: {category: count}
    summary: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class MasteryAnalyzer:
    """
    掌握度分析器

    我们的创新功能（ECC 没有）：
    - 掌握度评分
    - 复习优先级排序
    - 薄弱领域识别
    - 学习建议生成
    """

    def __init__(self):
        """初始化分析器"""
        self.low_confidence_threshold = 0.5
        self.high_confidence_threshold = 0.8
        self.high_difficulty_threshold = 0.7

    def analyze_mastery(self, knowledge_points: List[KnowledgePoint]) -> MasteryReport:
        """
        分析整体掌握度

        Args:
            knowledge_points: 知识点列表

        Returns:
            MasteryReport: 掌握度报告
        """
        if not knowledge_points:
            return MasteryReport(
                mastery_level=0.0,
                total_concepts=0,
                review_priority=[],
                weak_areas={},
                strong_areas={},
                summary="暂无知识点数据。"
            )

        # 1. 计算整体掌握度
        mastery_level = self._calculate_mastery_level(knowledge_points)

        # 2. 生成复习优先级
        review_priority = self._generate_review_priority(knowledge_points)

        # 3. 识别薄弱和强项领域
        weak_areas, strong_areas = self._identify_areas(knowledge_points)

        # 4. 生成摘要
        summary = self._generate_summary(
            knowledge_points,
            mastery_level,
            weak_areas,
            strong_areas
        )

        return MasteryReport(
            mastery_level=mastery_level,
            total_concepts=len(knowledge_points),
            review_priority=review_priority,
            weak_areas=weak_areas,
            strong_areas=strong_areas,
            summary=summary
        )

    def _calculate_mastery_level(self, knowledge_points: List[KnowledgePoint]) -> float:
        """
        计算整体掌握度

        算法: 加权平均，难度越高权重越大
        """
        total_weighted_confidence = 0.0
        total_weight = 0.0

        for kp in knowledge_points:
            # 难度作为权重因子 (难度高的知识点更重要)
            weight = 1.0 + kp.difficulty
            total_weighted_confidence += kp.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(total_weighted_confidence / total_weight, 2)

    def _generate_review_priority(self, knowledge_points: List[KnowledgePoint]) -> List[str]:
        """
        生成复习优先级

        优先级算法:
        priority_score = (1 - confidence) * (1 + difficulty)
        - 低掌握度 + 高难度 = 最优先
        - 已掌握的低难度 = 最不优先
        """
        scored_points = []
        for kp in knowledge_points:
            # 优先级分数：掌握度越低、难度越高，分数越高
            priority_score = (1 - kp.confidence) * (1 + kp.difficulty)
            scored_points.append((kp.id, priority_score))

        # 按优先级分数降序排序
        scored_points.sort(key=lambda x: x[1], reverse=True)

        # 返回前 10 个最需要复习的知识点 ID
        return [kp_id for kp_id, _ in scored_points[:10]]

    def _identify_areas(
        self,
        knowledge_points: List[KnowledgePoint]
    ) -> tuple[Dict[str, int], Dict[str, int]]:
        """
        识别薄弱和强项领域

        Returns:
            (weak_areas, strong_areas)
        """
        weak_areas = {}
        strong_areas = {}

        for kp in knowledge_points:
            category = kp.category

            if kp.confidence < self.low_confidence_threshold:
                # 薄弱领域
                weak_areas[category] = weak_areas.get(category, 0) + 1
            elif kp.confidence >= self.high_confidence_threshold:
                # 强项领域
                strong_areas[category] = strong_areas.get(category, 0) + 1

        return weak_areas, strong_areas

    def _generate_summary(
        self,
        knowledge_points: List[KnowledgePoint],
        mastery_level: float,
        weak_areas: Dict[str, int],
        strong_areas: Dict[str, int]
    ) -> str:
        """生成掌握度摘要"""
        summary_parts = []

        # 整体评价
        if mastery_level >= 0.8:
            overall = "整体掌握良好"
        elif mastery_level >= 0.6:
            overall = "整体掌握中等"
        else:
            overall = "需要加强学习"

        summary_parts.append(
            f"{overall}（掌握度: {mastery_level:.0%}），"
            f"共 {len(knowledge_points)} 个知识点。"
        )

        # 薄弱领域
        if weak_areas:
            weak_list = [f"{cat}({cnt}个)" for cat, cnt in weak_areas.items()]
            summary_parts.append(f"薄弱领域: {', '.join(weak_list)}。")

        # 强项领域
        if strong_areas:
            strong_list = [f"{cat}({cnt}个)" for cat, cnt in strong_areas.items()]
            summary_parts.append(f"强项领域: {', '.join(strong_list)}。")

        # 高难度知识点
        high_difficulty = [
            kp for kp in knowledge_points
            if kp.difficulty >= self.high_difficulty_threshold
        ]
        if high_difficulty:
            summary_parts.append(f"包含 {len(high_difficulty)} 个高难度知识点。")

        # 建议
        low_confidence_count = len([
            kp for kp in knowledge_points
            if kp.confidence < self.low_confidence_threshold
        ])
        if low_confidence_count > 0:
            summary_parts.append(f"建议重点复习 {low_confidence_count} 个低掌握度知识点。")

        return " ".join(summary_parts)

    def update_confidence(
        self,
        knowledge_point: KnowledgePoint,
        review_result: bool,
        delta: float = 0.1
    ) -> KnowledgePoint:
        """
        更新知识点置信度

        对应 ECC 的 confidence 演化机制

        Args:
            knowledge_point: 知识点
            review_result: 复习结果（True=掌握，False=未掌握）
            delta: 变化幅度

        Returns:
            更新后的知识点
        """
        if review_result:
            # 掌握良好 -> 提升 confidence
            knowledge_point.confidence = min(1.0, knowledge_point.confidence + delta)
        else:
            # 未掌握 -> 降低 confidence
            # 降低幅度更大，对应 ECC 的负反馈机制
            knowledge_point.confidence = max(0.0, knowledge_point.confidence - delta * 1.5)

        # 更新复习记录
        knowledge_point.last_reviewed = datetime.now().isoformat()
        knowledge_point.review_count += 1

        return knowledge_point

    def batch_update_confidence(
        self,
        knowledge_points: List[KnowledgePoint],
        results: Dict[str, bool]
    ) -> List[KnowledgePoint]:
        """
        批量更新置信度

        Args:
            knowledge_points: 知识点列表
            results: {knowledge_point_id: review_result}

        Returns:
            更新后的知识点列表
        """
        updated_points = []
        for kp in knowledge_points:
            if kp.id in results:
                updated_kp = self.update_confidence(kp, results[kp.id])
                updated_points.append(updated_kp)
            else:
                updated_points.append(kp)

        return updated_points

    def get_study_suggestions(
        self,
        knowledge_points: List[KnowledgePoint],
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        生成学习建议

        Args:
            knowledge_points: 知识点列表
            limit: 返回建议数量

        Returns:
            学习建议列表
        """
        suggestions = []

        # 获取优先级排序的知识点
        priority_ids = self._generate_review_priority(knowledge_points)
        priority_kps = [
            kp for kp in knowledge_points
            if kp.id in priority_ids[:limit]
        ]

        for kp in priority_kps:
            suggestion = {
                'id': kp.id,
                'title': kp.title,
                'category': kp.category,
                'reason': self._get_suggestion_reason(kp),
                'difficulty_label': self._get_difficulty_label(kp.difficulty),
                'confidence_label': self._get_confidence_label(kp.confidence)
            }
            suggestions.append(suggestion)

        return suggestions

    def _get_suggestion_reason(self, kp: KnowledgePoint) -> str:
        """生成建议原因"""
        if kp.confidence < 0.3:
            return "掌握度很低，需要重新学习"
        elif kp.confidence < 0.5:
            return "掌握度较低，需要加强练习"
        elif kp.difficulty > 0.7 and kp.confidence < 0.7:
            return "高难度知识点，需要深入理解"
        else:
            return "需要巩固记忆"

    def _get_difficulty_label(self, difficulty: float) -> str:
        """获取难度标签"""
        if difficulty >= 0.7:
            return "困难"
        elif difficulty >= 0.4:
            return "中等"
        else:
            return "简单"

    def _get_confidence_label(self, confidence: float) -> str:
        """获取掌握度标签"""
        if confidence >= 0.8:
            return "熟练"
        elif confidence >= 0.6:
            return "一般"
        elif confidence >= 0.4:
            return "较弱"
        else:
            return "未掌握"
