"""
Quiz CLI - 测验命令行工具
"""

import sys
from pathlib import Path
from datetime import datetime
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.difficulty_estimator import DifficultyEstimator
from core.mastery_analyzer import MasteryAnalyzer, KnowledgePoint
from adapters.storage_adapter import StorageAdapter


class QuizCLI:
    """测验命令行工具"""

    def __init__(self):
        self.difficulty_estimator = DifficultyEstimator()
        self.analyzer = MasteryAnalyzer()
        self.storage = StorageAdapter()

    def generate_quiz(self, count: int = 5):
        print("
生成测验题:")
        print("=" * 60)
        
        # 获取所有学习记录
        records = self.storage.list_all_learning_records()
        
        if not records:
            print("没有学习记录。请先使用 learn 命令学习知识点。")
            return

        # 随机选择题目
        selected = random.sample(records, min(count, len(records)))
        
        correct = 0
        total = len(selected)
        
        for idx, record in enumerate(selected, 1):
            concept = record.get('concept', 'Unknown')
            print(f"
题目 {idx}/{total}: {concept}")
            print("-" * 40)
            
            answer = input("你掌握这个知识点了吗? (y/n): ").strip().lower()
            
            if answer == 'y':
                correct += 1
                # 保存测验结果
                self.storage.save_quiz_result(concept, {
                    'result': 'correct',
                    'score': 1.0
                })
            else:
                self.storage.save_quiz_result(concept, {
                    'result': 'incorrect',
                    'score': 0.0
                })

        print("
" + "=" * 60)
        print(f"测验完成！正确率: {correct}/{total} ({correct/total*100:.0f}%)")

    def show_quiz_stats(self):
        print("
测验统计:")
        print("=" * 60)
        
        stats = self.storage.get_statistics()
        print(f"总测验次数: {stats['quiz_results']}")

    def interactive_mode(self):
        print("
测验系统 - 交互模式")
        while True:
            try:
                cmd = input("测验> ").strip()
                if cmd == 'exit': break
                if cmd == 'start': self.generate_quiz()
                if cmd == 'stats': self.show_quiz_stats()
            except KeyboardInterrupt:
                break


def main():
    cli = QuizCLI()
    if len(sys.argv) > 1:
        if sys.argv[1] == 'start':
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            cli.generate_quiz(count)
        elif sys.argv[1] == 'stats':
            cli.show_quiz_stats()
        elif sys.argv[1] == '--interactive':
            cli.interactive_mode()
    else:
        print("用法: python -m cli.quiz_cli start [count]|stats|--interactive")


if __name__ == '__main__':
    main()
