"""
Review CLI - 复习命令行工具
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.review_scheduler import ReviewScheduler
from core.mastery_analyzer import MasteryAnalyzer, KnowledgePoint
from adapters.storage_adapter import StorageAdapter


class ReviewCLI:
    """复习命令行工具"""

    def __init__(self):
        self.scheduler = ReviewScheduler()
        self.analyzer = MasteryAnalyzer()
        self.storage = StorageAdapter()

    def show_due_reviews(self):
        print("
到期复习列表:")
        print("=" * 60)
        
        due_reviews = self.storage.list_due_reviews()
        
        if not due_reviews:
            print("没有到期的复习内容。")
            return

        for idx, review in enumerate(due_reviews, 1):
            concept = review.get('concept', 'Unknown')
            next_date = review.get('next_review_date', '')
            interval = review.get('interval_days', 0)
            
            print(f"{idx}. {concept}")
            print(f"   计划复习: {next_date}")
            print(f"   间隔: {interval} 天")
            print()

    def review_concept(self, concept: str, success: bool):
        schedule = self.storage.get_review_schedule(concept)
        
        if not schedule:
            print(f"错误: 未找到 {concept} 的复习计划")
            return

        # 更新复习计划
        current_interval = schedule.get('interval_days', 1)
        new_plan = self.scheduler.calculate_next_review(
            last_review_date=datetime.now(),
            current_interval=current_interval,
            review_success=success
        )
        
        self.storage.save_review_schedule(concept, new_plan)
        print(f"
{concept} 复习{'成功' if success else '失败'}")
        print(f"下次复习: {new_plan['next_review_date']}")

    def interactive_mode(self):
        print("
复习系统 - 交互模式")
        while True:
            try:
                cmd = input("复习> ").strip()
                if cmd == 'exit': break
                if cmd == 'list': self.show_due_reviews()
            except KeyboardInterrupt:
                break


def main():
    cli = ReviewCLI()
    if len(sys.argv) > 1:
        if sys.argv[1] == 'list':
            cli.show_due_reviews()
        elif sys.argv[1] == '--interactive':
            cli.interactive_mode()
    else:
        print("用法: python -m cli.review_cli list|--interactive")


if __name__ == '__main__':
    main()
