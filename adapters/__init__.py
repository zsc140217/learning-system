"""
Adapter Layer - 包装外部依赖为统一的 Python API

这一层将不兼容的接口转换为我们期望的接口：
- ECC CLI (subprocess) → Pythonic API
- MCP Tools (tool calls) → Pythonic API
- 统一异常处理和数据模型
"""

from .ecc_instinct_adapter import InstinctAdapter, Instinct
from .ecc_memory_adapter import MemoryAdapter, Entity, Relation, Observation
from .storage_adapter import StorageAdapter

__all__ = [
    'InstinctAdapter',
    'Instinct',
    'MemoryAdapter',
    'Entity',
    'Relation',
    'Observation',
    'StorageAdapter',
]
