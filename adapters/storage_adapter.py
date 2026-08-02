"""
Storage Adapter - 统一存储接口

提供统一的本地文件系统存储接口，用于：
- 学习记录
- 复习计划
- 测验结果
- 难度评估数据
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class StorageAdapter:
    """
    统一存储适配器

    管理所有本地数据的读写操作，确保数据一致性。
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化 Storage Adapter

        Args:
            data_dir: 数据目录路径，默认为 data/
        """
        if data_dir is None:
            project_root = Path(__file__).parent.parent
            data_dir = project_root / 'data'

        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 子目录
        self.learning_dir = self.data_dir / 'learning'
        self.reviews_dir = self.data_dir / 'reviews'
        self.quizzes_dir = self.data_dir / 'quizzes'
        self.difficulty_dir = self.data_dir / 'difficulty'

        # 创建子目录
        for dir_path in [self.learning_dir, self.reviews_dir, self.quizzes_dir, self.difficulty_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _read_json(self, file_path: Path) -> Dict[str, Any]:
        """
        读取 JSON 文件

        Args:
            file_path: 文件路径

        Returns:
            解析后的字典
        """
        if not file_path.exists():
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _write_json(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """
        写入 JSON 文件

        Args:
            file_path: 文件路径
            data: 要写入的数据

        Returns:
            是否成功写入
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"写入文件失败: {e}")
            return False

    # === 学习记录 ===

    def save_learning_record(self, concept: str, record: Dict[str, Any]) -> bool:
        """
        保存学习记录

        Args:
            concept: 概念名称
            record: 学习记录数据

        Returns:
            是否成功保存
        """
        file_path = self.learning_dir / f"{concept}.json"
        existing = self._read_json(file_path)

        # 添加时间戳
        record['timestamp'] = datetime.now().isoformat()

        # 追加到历史记录
        if 'history' not in existing:
            existing['history'] = []
        existing['history'].append(record)

        # 更新最新记录
        existing['latest'] = record
        existing['concept'] = concept

        return self._write_json(file_path, existing)

    def get_learning_record(self, concept: str) -> Optional[Dict[str, Any]]:
        """
        获取学习记录

        Args:
            concept: 概念名称

        Returns:
            学习记录数据，如果不存在返回 None
        """
        file_path = self.learning_dir / f"{concept}.json"
        data = self._read_json(file_path)
        return data if data else None

    def list_all_learning_records(self) -> List[Dict[str, Any]]:
        """
        列出所有学习记录

        Returns:
            所有学习记录的列表
        """
        records = []
        for file_path in self.learning_dir.glob('*.json'):
            data = self._read_json(file_path)
            if data:
                records.append(data)
        return records

    # === 复习计划 ===

    def save_review_schedule(self, concept: str, schedule: Dict[str, Any]) -> bool:
        """
        保存复习计划

        Args:
            concept: 概念名称
            schedule: 复习计划数据

        Returns:
            是否成功保存
        """
        file_path = self.reviews_dir / f"{concept}.json"
        schedule['concept'] = concept
        schedule['updated_at'] = datetime.now().isoformat()
        return self._write_json(file_path, schedule)

    def get_review_schedule(self, concept: str) -> Optional[Dict[str, Any]]:
        """
        获取复习计划

        Args:
            concept: 概念名称

        Returns:
            复习计划数据
        """
        file_path = self.reviews_dir / f"{concept}.json"
        return self._read_json(file_path)

    def list_due_reviews(self) -> List[Dict[str, Any]]:
        """
        列出所有到期的复习

        Returns:
            到期复习列表
        """
        now = datetime.now()
        due_reviews = []

        for file_path in self.reviews_dir.glob('*.json'):
            schedule = self._read_json(file_path)
            if not schedule:
                continue

            next_review = schedule.get('next_review_date')
            if next_review:
                next_review_dt = datetime.fromisoformat(next_review)
                if next_review_dt <= now:
                    due_reviews.append(schedule)

        return due_reviews

    # === 测验结果 ===

    def save_quiz_result(self, concept: str, result: Dict[str, Any]) -> bool:
        """
        保存测验结果

        Args:
            concept: 概念名称
            result: 测验结果数据

        Returns:
            是否成功保存
        """
        file_path = self.quizzes_dir / f"{concept}.json"
        existing = self._read_json(file_path)

        # 添加时间戳
        result['timestamp'] = datetime.now().isoformat()

        # 追加到结果列表
        if 'results' not in existing:
            existing['results'] = []
        existing['results'].append(result)

        # 更新最新结果
        existing['latest'] = result
        existing['concept'] = concept

        return self._write_json(file_path, existing)

    def get_quiz_results(self, concept: str) -> Optional[Dict[str, Any]]:
        """
        获取测验结果

        Args:
            concept: 概念名称

        Returns:
            测验结果数据
        """
        file_path = self.quizzes_dir / f"{concept}.json"
        return self._read_json(file_path)

    # === 难度评估 ===

    def save_difficulty_assessment(self, concept: str, assessment: Dict[str, Any]) -> bool:
        """
        保存难度评估

        Args:
            concept: 概念名称
            assessment: 难度评估数据

        Returns:
            是否成功保存
        """
        file_path = self.difficulty_dir / f"{concept}.json"
        assessment['concept'] = concept
        assessment['assessed_at'] = datetime.now().isoformat()
        return self._write_json(file_path, assessment)

    def get_difficulty_assessment(self, concept: str) -> Optional[Dict[str, Any]]:
        """
        获取难度评估

        Args:
            concept: 概念名称

        Returns:
            难度评估数据
        """
        file_path = self.difficulty_dir / f"{concept}.json"
        return self._read_json(file_path)

    # === 统计信息 ===

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取存储统计信息

        Returns:
            统计数据
        """
        return {
            'learning_records': len(list(self.learning_dir.glob('*.json'))),
            'review_schedules': len(list(self.reviews_dir.glob('*.json'))),
            'quiz_results': len(list(self.quizzes_dir.glob('*.json'))),
            'difficulty_assessments': len(list(self.difficulty_dir.glob('*.json'))),
            'data_dir': str(self.data_dir)
        }

    # === 清理操作 ===

    def delete_concept_data(self, concept: str) -> bool:
        """
        删除概念的所有数据

        Args:
            concept: 概念名称

        Returns:
            是否成功删除
        """
        success = True
        for directory in [self.learning_dir, self.reviews_dir, self.quizzes_dir, self.difficulty_dir]:
            file_path = directory / f"{concept}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    success = False
        return success
