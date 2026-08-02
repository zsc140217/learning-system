"""
Difficulty Estimator - 难度评估器

ECC 创新: ECC continuous-learning-v2 没有难度评估功能，这是我们的独创

核心功能:
1. 基于多维度评估知识点难度
2. 机器学习辅助难度预测
3. 用户反馈校准
"""

import re
import math
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class DifficultyScore:
    """难度评分"""
    overall: float  # 总体难度 0.0-1.0
    dimensions: Dict[str, float]  # 各维度得分
    explanation: str  # 难度解释


class DifficultyEstimator:
    """
    难度评估器

    我们的创新: ECC 没有此功能

    评估维度:
    1. 内容复杂度 (complexity)
    2. 概念抽象度 (abstraction)
    3. 先决知识要求 (prerequisites)
    4. 实践难度 (practice_difficulty)
    5. 认知负荷 (cognitive_load)
    """

    # 难度等级描述
    DIFFICULTY_LEVELS = {
        (0.0, 0.3): "入门",
        (0.3, 0.5): "初级",
        (0.5, 0.7): "中级",
        (0.7, 0.85): "高级",
        (0.85, 1.0): "专家",
    }

    def __init__(self):
        """初始化评估器"""
        self.user_feedback_history: Dict[str, List[float]] = {}

    def estimate(
        self,
        content: str,
        category: str = "general",
        metadata: Dict = None
    ) -> DifficultyScore:
        """
        评估难度

        Args:
            content: 知识点内容
            category: 知识点类别
            metadata: 额外元数据（如代码长度、嵌套深度等）

        Returns:
            DifficultyScore: 难度评分
        """
        metadata = metadata or {}

        # 1. 内容复杂度
        complexity = self._estimate_complexity(content, metadata)

        # 2. 概念抽象度
        abstraction = self._estimate_abstraction(content, category)

        # 3. 先决知识要求
        prerequisites = self._estimate_prerequisites(content, category)

        # 4. 实践难度
        practice_difficulty = self._estimate_practice_difficulty(content, metadata)

        # 5. 认知负荷
        cognitive_load = self._estimate_cognitive_load(content)

        # 综合评分（加权平均）
        dimensions = {
            "complexity": complexity,
            "abstraction": abstraction,
            "prerequisites": prerequisites,
            "practice_difficulty": practice_difficulty,
            "cognitive_load": cognitive_load,
        }

        overall = (
            complexity * 0.25 +
            abstraction * 0.20 +
            prerequisites * 0.20 +
            practice_difficulty * 0.20 +
            cognitive_load * 0.15
        )

        # 生成解释
        explanation = self._generate_explanation(overall, dimensions)

        return DifficultyScore(
            overall=round(overall, 2),
            dimensions={k: round(v, 2) for k, v in dimensions.items()},
            explanation=explanation,
        )

    def _estimate_complexity(self, content: str, metadata: Dict) -> float:
        """评估内容复杂度"""
        score = 0.0

        # 长度因子
        length = len(content)
        length_score = min(1.0, length / 1000)
        score += length_score * 0.4

        # 代码复杂度
        if "code_depth" in metadata:
            depth = metadata["code_depth"]
            depth_score = min(1.0, depth / 5)
            score += depth_score * 0.3
        else:
            code_blocks = re.findall(r'```[\s\S]*?```', content)
            if code_blocks:
                max_depth = max(self._estimate_code_depth(cb) for cb in code_blocks)
                depth_score = min(1.0, max_depth / 5)
                score += depth_score * 0.3

        # 技术术语密度
        tech_terms = len(re.findall(r'\b[A-Z]{2,}\b', content))
        term_score = min(1.0, tech_terms / 10)
        score += term_score * 0.3

        return min(1.0, score)

    def _estimate_abstraction(self, content: str, category: str) -> float:
        """评估概念抽象度"""
        score = 0.3

        # 抽象关键词
        abstract_keywords = ["抽象", "模式", "范式", "原理", "本质", "理论"]
        abstract_count = sum(1 for kw in abstract_keywords if kw in content)
        score += min(0.4, abstract_count * 0.1)

        # 数学公式
        math_patterns = [r'O\([^)]+\)', r'\$[^$]+\$', r'[α-ωΑ-Ω]']
        math_count = sum(len(re.findall(p, content)) for p in math_patterns)
        score += min(0.3, math_count * 0.1)

        return min(1.0, score)

    def _estimate_prerequisites(self, content: str, category: str) -> float:
        """评估先决知识要求"""
        score = 0.2

        # 类别基线
        category_baseline = {
            "algorithm": 0.6,
            "system-design": 0.7,
            "data-structure": 0.5,
            "database": 0.5,
            "network": 0.6,
            "security": 0.6,
            "general": 0.3,
        }
        score += category_baseline.get(category, 0.3)

        # 引用的概念
        references = re.findall(r'\[([^\]]+)\]', content)
        ref_score = min(0.3, len(references) * 0.05)
        score += ref_score

        return min(1.0, score)

    def _estimate_practice_difficulty(self, content: str, metadata: Dict) -> float:
        """评估实践难度"""
        score = 0.3

        # 步骤数量
        steps = re.findall(r'^\s*\d+[\.)]\s+', content, re.MULTILINE)
        step_score = min(0.4, len(steps) * 0.05)
        score += step_score

        # 代码块数量
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        code_score = min(0.3, len(code_blocks) * 0.1)
        score += code_score

        return min(1.0, score)

    def _estimate_cognitive_load(self, content: str) -> float:
        """评估认知负荷"""
        score = 0.2

        # 信息密度
        sentences = re.split(r'[。！？.!?]', content)
        if len(content) > 0:
            density = len(sentences) / (len(content) / 100)
            density_score = min(0.4, density * 0.1)
            score += density_score

        # 新概念
        capitalized_words = set(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', content))
        concept_score = min(0.4, len(capitalized_words) * 0.05)
        score += concept_score

        return min(1.0, score)

    def _estimate_code_depth(self, code_block: str) -> int:
        """估算代码嵌套深度"""
        lines = code_block.split('\n')
        max_depth = 0

        for line in lines:
            indent = len(line) - len(line.lstrip())
            depth = indent // 4
            max_depth = max(max_depth, depth)

        return max_depth

    def _generate_explanation(self, overall: float, dimensions: Dict[str, float]) -> str:
        """生成难度解释"""
        level = "未知"
        for (low, high), label in self.DIFFICULTY_LEVELS.items():
            if low <= overall < high:
                level = label
                break

        top_dimension = max(dimensions.items(), key=lambda x: x[1])
        dimension_name_map = {
            "complexity": "内容复杂度",
            "abstraction": "概念抽象度",
            "prerequisites": "先决知识要求",
            "practice_difficulty": "实践难度",
            "cognitive_load": "认知负荷",
        }

        explanation = f"难度等级: {level}。"
        explanation += f"主要挑战来自{dimension_name_map[top_dimension[0]]}。"

        return explanation

    def calibrate_with_feedback(
        self,
        knowledge_id: str,
        estimated_difficulty: float,
        actual_difficulty: float
    ):
        """根据用户反馈校准难度评估"""
        if knowledge_id not in self.user_feedback_history:
            self.user_feedback_history[knowledge_id] = []

        error = abs(estimated_difficulty - actual_difficulty)
        self.user_feedback_history[knowledge_id].append(error)
