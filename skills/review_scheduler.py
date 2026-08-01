"""
Review Scheduler - 复习计划生成器

借鉴: ECC continuous-learning-v2 的 instinct 演化机制
改进: 基于记忆曲线和优先级的智能复习计划

核心功能:
1. 基于艾宾浩斯遗忘曲线生成复习计划
2. 根据难度和掌握度动态调整
3. 优先级排序
4. 生成每日复习清单
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass


@dataclass
class ReviewItem:
    """复习项"""
    knowledge_id: str
    title: str
    category: str
    difficulty: float
    confidence: float
    last_reviewed: Optional[str]
    review_count: int
    next_review_date: str
    priority_score: float


@dataclass
class ReviewPlan:
    """复习计划"""
    plan_date: str
    total_items: int
    high_priority: List[ReviewItem]
    medium_priority: List[ReviewItem]
    low_priority: List[ReviewItem]
    estimated_time_minutes: int
    summary: str


class ReviewScheduler:
    """
    复习计划生成器

    借鉴 ECC continuous-learning-v2:
    - confidence 演化机制 -> 我们的掌握度追踪
    - promote 提升逻辑 -> 我们的优先级计算

    我们的创新:
    - 艾宾浩斯遗忘曲线
    - 动态间隔调整
    - 每日复习清单
    """

    EBBINGHAUS_INTERVALS = [1, 2, 4, 7, 15, 30, 60]

    PRIORITY_THRESHOLDS = {
        "high": 0.3,
        "medium": 0.6,
        "low": 1.0,
    }

    def __init__(self):
        """初始化调度器"""
        pass

    def generate_plan(
        self,
        knowledge_points: List[Dict],
        target_date: Optional[str] = None
    ) -> ReviewPlan:
        """生成复习计划（对应 ECC evolve 命令）"""
        if target_date is None:
            target_date = datetime.now(timezone.utc).isoformat()

        review_items = []
        for kp in knowledge_points:
            item = self._create_review_item(kp, target_date)
            if item:
                review_items.append(item)

        today_items = self._filter_today_items(review_items, target_date)

        high_priority = [item for item in today_items if item.priority_score >= 0.7]
        medium_priority = [item for item in today_items if 0.4 <= item.priority_score < 0.7]
        low_priority = [item for item in today_items if item.priority_score < 0.4]

        high_priority.sort(key=lambda x: x.priority_score, reverse=True)
        medium_priority.sort(key=lambda x: x.priority_score, reverse=True)
        low_priority.sort(key=lambda x: x.priority_score, reverse=True)

        estimated_time = self._estimate_time(today_items)
        summary = self._generate_summary(high_priority, medium_priority, low_priority)

        return ReviewPlan(
            plan_date=target_date,
            total_items=len(today_items),
            high_priority=high_priority,
            medium_priority=medium_priority,
            low_priority=low_priority,
            estimated_time_minutes=estimated_time,
            summary=summary,
        )

    def _create_review_item(self, knowledge_point: Dict, current_date: str) -> Optional[ReviewItem]:
        """创建复习项（对应 ECC instinct 追踪）"""
        kp_id = knowledge_point.get("id")
        title = knowledge_point.get("title", "未命名")
        category = knowledge_point.get("category", "general")
        difficulty = knowledge_point.get("difficulty", 0.5)
        confidence = knowledge_point.get("confidence", 0.5)
        last_reviewed = knowledge_point.get("last_reviewed")
        review_count = knowledge_point.get("review_count", 0)

        next_review_date = self._calculate_next_review(
            last_reviewed or knowledge_point.get("created_at"),
            review_count,
            confidence,
        )

        priority_score = self._calculate_priority(
            confidence,
            difficulty,
            next_review_date,
            current_date,
        )

        return ReviewItem(
            knowledge_id=kp_id,
            title=title,
            category=category,
            difficulty=difficulty,
            confidence=confidence,
            last_reviewed=last_reviewed,
            review_count=review_count,
            next_review_date=next_review_date,
            priority_score=priority_score,
        )

    def _calculate_next_review(
        self,
        last_review_date: str,
        review_count: int,
        confidence: float
    ) -> str:
        """计算下次复习时间（艾宾浩斯曲线 + confidence 调整）"""
        try:
            last_date = datetime.fromisoformat(last_review_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            last_date = datetime.now(timezone.utc)

        if review_count < len(self.EBBINGHAUS_INTERVALS):
            base_interval = self.EBBINGHAUS_INTERVALS[review_count]
        else:
            base_interval = self.EBBINGHAUS_INTERVALS[-1] * (2 ** (review_count - len(self.EBBINGHAUS_INTERVALS)))

        confidence_factor = 0.5 + confidence
        adjusted_interval = int(base_interval * confidence_factor)

        next_date = last_date + timedelta(days=adjusted_interval)
        return next_date.isoformat()

    def _calculate_priority(
        self,
        confidence: float,
        difficulty: float,
        next_review_date: str,
        current_date: str
    ) -> float:
        """计算优先级分数（对应 ECC _generate_review_priority）"""
        try:
            next_date = datetime.fromisoformat(next_review_date.replace('Z', '+00:00'))
            current = datetime.fromisoformat(current_date.replace('Z', '+00:00'))
            days_overdue = max(0, (current - next_date).days)
        except (ValueError, AttributeError):
            days_overdue = 0

        confidence_score = 1.0 - confidence
        difficulty_score = difficulty
        overdue_score = min(1.0, days_overdue / 7)

        priority = (
            confidence_score * 0.4 +
            difficulty_score * 0.3 +
            overdue_score * 0.3
        )

        return round(priority, 2)

    def _filter_today_items(self, items: List[ReviewItem], target_date: str) -> List[ReviewItem]:
        """筛选需要今天复习的项"""
        try:
            target = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            target = datetime.now(timezone.utc)

        today_items = []
        for item in items:
            try:
                next_date = datetime.fromisoformat(item.next_review_date.replace('Z', '+00:00'))
                if next_date <= target:
                    today_items.append(item)
            except (ValueError, AttributeError):
                continue

        return today_items

    def _estimate_time(self, items: List[ReviewItem]) -> int:
        """估算复习时间（分钟）"""
        if not items:
            return 0

        total_time = 0
        for item in items:
            base_time = 5
            difficulty_factor = 1.0 + item.difficulty
            time = base_time * difficulty_factor
            total_time += time

        return int(total_time)

    def _generate_summary(
        self,
        high_priority: List[ReviewItem],
        medium_priority: List[ReviewItem],
        low_priority: List[ReviewItem]
    ) -> str:
        """生成计划摘要（对应 ECC _generate_summary）"""
        total = len(high_priority) + len(medium_priority) + len(low_priority)

        if total == 0:
            return "今日无需复习。"

        parts = [f"今日共需复习 {total} 个知识点。"]

        if high_priority:
            parts.append(f"高优先级 {len(high_priority)} 个（建议优先完成）。")

        if medium_priority:
            parts.append(f"中优先级 {len(medium_priority)} 个。")

        if low_priority:
            parts.append(f"低优先级 {len(low_priority)} 个。")

        all_items = high_priority + medium_priority + low_priority
        category_counts = {}
        for item in all_items:
            category_counts[item.category] = category_counts.get(item.category, 0) + 1

        if category_counts:
            top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            parts.append(f"主要涉及: {', '.join(cat for cat, _ in top_categories)}。")

        return " ".join(parts)

    def update_after_review(
        self,
        knowledge_point: Dict,
        review_success: bool
    ) -> Dict:
        """复习后更新知识点（对应 ECC update_confidence）"""
        delta = 0.1
        if review_success:
            knowledge_point["confidence"] = min(0.9, knowledge_point.get("confidence", 0.5) + delta)
        else:
            knowledge_point["confidence"] = max(0.3, knowledge_point.get("confidence", 0.5) - delta * 1.5)

        knowledge_point["last_reviewed"] = datetime.now(timezone.utc).isoformat()
        knowledge_point["review_count"] = knowledge_point.get("review_count", 0) + 1

        return knowledge_point
