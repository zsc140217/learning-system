"""
ECC Instinct Adapter - 包装 instinct_cli.py 为 Pythonic API

将 subprocess 调用转换为类型安全的 Python 接口。
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class Instinct:
    """Instinct 数据类 - 代表一个学习到的模式"""
    name: str
    trigger: str
    action: str
    confidence: float
    scope: str  # 'project' or 'global'
    evidence: List[str]
    observations: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Instinct':
        """从字典创建 Instinct 对象"""
        return cls(
            name=data['name'],
            trigger=data['trigger'],
            action=data['action'],
            confidence=data.get('confidence', 0.5),
            scope=data.get('scope', 'project'),
            evidence=data.get('evidence', []),
            observations=data.get('observations', 0)
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'trigger': self.trigger,
            'action': self.action,
            'confidence': self.confidence,
            'scope': self.scope,
            'evidence': self.evidence,
            'observations': self.observations
        }


class InstinctAdapter:
    """
    Adapter for ECC instinct_cli.py

    包装 subprocess 调用，提供 Pythonic 接口
    """

    def __init__(self, cli_path: Optional[Path] = None):
        """
        初始化 Adapter

        Args:
            cli_path: instinct_cli.py 的路径，默认为 vendor/ecc/instinct_cli.py
        """
        if cli_path is None:
            # 默认路径：相对于项目根目录
            project_root = Path(__file__).parent.parent
            cli_path = project_root / 'vendor' / 'ecc' / 'instinct_cli.py'

        self.cli_path = cli_path

        if not self.cli_path.exists():
            raise FileNotFoundError(f"instinct_cli.py not found at {self.cli_path}")

    def _run_command(self, args: List[str]) -> Dict[str, Any]:
        """
        运行 instinct_cli.py 命令

        Args:
            args: 命令参数列表

        Returns:
            解析后的 JSON 输出

        Raises:
            RuntimeError: 命令执行失败
        """
        cmd = ['python', str(self.cli_path)] + args + ['--json']

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )

            # 解析 JSON 输出
            if result.stdout.strip():
                return json.loads(result.stdout)
            return {}

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}\nError: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON output: {e}")

    def get_all_instincts(self, scope: Optional[str] = None) -> List[Instinct]:
        """
        获取所有 Instincts

        Args:
            scope: 'project', 'global', 或 None (全部)

        Returns:
            Instinct 对象列表
        """
        args = ['status']
        if scope:
            args.extend(['--scope', scope])

        result = self._run_command(args)
        instincts_data = result.get('instincts', [])

        return [Instinct.from_dict(data) for data in instincts_data]

    def add_instinct(
        self,
        name: str,
        trigger: str,
        action: str,
        confidence: float = 0.5,
        scope: str = 'project',
        evidence: Optional[List[str]] = None
    ) -> Instinct:
        """
        添加新的 Instinct

        Args:
            name: Instinct 名称
            trigger: 触发条件
            action: 执行动作
            confidence: 置信度 (0.0-1.0)
            scope: 作用域 ('project' 或 'global')
            evidence: 证据列表

        Returns:
            创建的 Instinct 对象
        """
        args = [
            'add',
            '--name', name,
            '--trigger', trigger,
            '--action', action,
            '--confidence', str(confidence),
            '--scope', scope
        ]

        if evidence:
            for ev in evidence:
                args.extend(['--evidence', ev])

        result = self._run_command(args)
        return Instinct.from_dict(result.get('instinct', {}))

    def update_confidence(self, name: str, delta: float) -> Instinct:
        """
        更新 Instinct 的置信度

        Args:
            name: Instinct 名称
            delta: 置信度变化量 (正数增加，负数减少)

        Returns:
            更新后的 Instinct 对象
        """
        args = ['update', '--name', name, '--confidence-delta', str(delta)]
        result = self._run_command(args)
        return Instinct.from_dict(result.get('instinct', {}))

    def promote_to_global(self, name: str) -> Instinct:
        """
        将 project-scoped Instinct 提升到 global

        Args:
            name: Instinct 名称

        Returns:
            提升后的 Instinct 对象
        """
        args = ['promote', '--name', name]
        result = self._run_command(args)
        return Instinct.from_dict(result.get('instinct', {}))

    def delete_instinct(self, name: str) -> bool:
        """
        删除 Instinct

        Args:
            name: Instinct 名称

        Returns:
            是否成功删除
        """
        args = ['delete', '--name', name]
        try:
            self._run_command(args)
            return True
        except RuntimeError:
            return False

    def observe(self, observation: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        记录观察结果

        Args:
            observation: 观察内容
            context: 上下文信息

        Returns:
            观察结果统计
        """
        args = ['observe', '--observation', observation]

        if context:
            args.extend(['--context', json.dumps(context)])

        return self._run_command(args)

    def get_project_id(self) -> Optional[str]:
        """
        获取当前项目 ID

        Returns:
            项目 ID (Git remote URL 的 SHA256)，如果不在 Git 项目中返回 None
        """
        args = ['project-id']
        try:
            result = self._run_command(args)
            return result.get('project_id')
        except RuntimeError:
            return None
