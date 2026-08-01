"""
Skills 综合测试

测试我们基于 ECC continuous-learning-v2 构建的 4 个核心 skill
"""

import sys
sys.path.insert(0, 'E:/Desktop/learning-system')

from skills import (
    SessionReviewer,
    KnowledgeExtractor,
    DifficultyEstimator,
    ReviewScheduler,
)


def test_session_reviewer():
    """测试会话复习器"""
    print("\n" + "="*60)
    print("测试 1: SessionReviewer (会话复习器)")
    print("="*60)

    sample_session = """
    # 算法复习

    ## 什么是二分查找？
    二分查找是一种高效的查找算法，时间复杂度为 O(log n)。

    实现代码：
    ```python
    def binary_search(arr, target):
        left, right = 0, len(arr) - 1
        while left <= right:
            mid = (left + right) // 2
            if arr[mid] == target:
                return mid
            elif arr[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return -1
    ```

    ## 如何优化数据库查询？
    使用索引可以大大提高查询性能。
    """

    reviewer = SessionReviewer()
    result = reviewer.analyze_session(sample_session, "test-session-001")

    print(f"\n[OK] 会话分析结果:")
    print(f"   - 知识点数量: {result.total_concepts}")
    print(f"   - 整体掌握度: {result.mastery_level}")
    print(f"   - 摘要: {result.summary}")
    print(f"\n   需要优先复习的知识点 (前3个):")
    for kp_id in result.review_priority[:3]:
        kp = next((k for k in result.knowledge_points if k.id == kp_id), None)
        if kp:
            print(f"     - {kp.title} (难度: {kp.difficulty}, 置信度: {kp.confidence}, 类别: {kp.category})")


def test_knowledge_extractor():
    """测试知识点提取器"""
    print("\n" + "="*60)
    print("测试 2: KnowledgeExtractor (知识点提取器)")
    print("="*60)

    sample_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class BinaryTree:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None
"""

    extractor = KnowledgeExtractor()
    result = extractor.extract_from_code(sample_code, "python")

    print(f"\n[OK] 代码提取结果:")
    print(f"   - 知识点数量: {result.total_count}")
    print(f"   - 摘要: {result.summary}")
    print(f"\n   提取的知识点:")
    for node in result.nodes:
        print(f"     - {node.title} (类型: {node.type}, 类别: {node.category})")


def test_difficulty_estimator():
    """测试难度评估器"""
    print("\n" + "="*60)
    print("测试 3: DifficultyEstimator (难度评估器)")
    print("="*60)

    sample_content = """
    动态规划是一种算法设计技术，通过将复杂问题分解为子问题来优化求解过程。
    时间复杂度通常为 O(n²) 或 O(n)，具体取决于问题的特性。

    ```python
    def longest_common_subsequence(str1, str2):
        m, n = len(str1), len(str2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i-1] == str2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[m][n]
    ```
    """

    estimator = DifficultyEstimator()
    result = estimator.estimate(sample_content, category="algorithm")

    print(f"\n[OK] 难度评估结果:")
    print(f"   - 总体难度: {result.overall} (0.0-1.0)")
    print(f"   - 解释: {result.explanation}")
    print(f"\n   各维度得分:")
    for dim, score in result.dimensions.items():
        print(f"     - {dim}: {score}")


def test_review_scheduler():
    """测试复习计划生成器"""
    print("\n" + "="*60)
    print("测试 4: ReviewScheduler (复习计划生成器)")
    print("="*60)

    from datetime import datetime, timedelta, timezone

    knowledge_points = [
        {
            "id": "kp-001",
            "title": "二分查找算法",
            "category": "algorithm",
            "difficulty": 0.65,
            "confidence": 0.4,
            "last_reviewed": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "review_count": 1,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        },
        {
            "id": "kp-002",
            "title": "数据库索引优化",
            "category": "database",
            "difficulty": 0.75,
            "confidence": 0.3,
            "last_reviewed": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "review_count": 2,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=15)).isoformat(),
        },
        {
            "id": "kp-003",
            "title": "HTTP 协议基础",
            "category": "network",
            "difficulty": 0.5,
            "confidence": 0.7,
            "last_reviewed": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "review_count": 3,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(),
        },
    ]

    scheduler = ReviewScheduler()
    plan = scheduler.generate_plan(knowledge_points)

    print(f"\n[OK] 复习计划结果:")
    print(f"   - 计划日期: {plan.plan_date[:10]}")
    print(f"   - 总项目数: {plan.total_items}")
    print(f"   - 预计时间: {plan.estimated_time_minutes} 分钟")
    print(f"   - 摘要: {plan.summary}")

    print(f"\n   高优先级 ({len(plan.high_priority)} 个):")
    for item in plan.high_priority:
        print(f"     - {item.title} (优先级: {item.priority_score})")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print(" Learning System Skills 综合测试")
    print("="*60)
    print("\n基于 ECC continuous-learning-v2 构建的 4 个核心 skill:")
    print("  1. SessionReviewer - 会话复习器")
    print("  2. KnowledgeExtractor - 知识点提取器")
    print("  3. DifficultyEstimator - 难度评估器")
    print("  4. ReviewScheduler - 复习计划生成器")

    try:
        test_session_reviewer()
        test_knowledge_extractor()
        test_difficulty_estimator()
        test_review_scheduler()

        print("\n" + "="*60)
        print("[SUCCESS] 所有测试通过！Skills 构建成功！")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
