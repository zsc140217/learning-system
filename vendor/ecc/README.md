# Vendor - ECC Continuous Learning v2

**来源**: ECC continuous-learning-v2  
**版本**: 2.1.0  
**日期**: 2026-08-02  

## 文件清单

| 文件 | 大小 | 用途 |
|-----|------|------|
| instinct_cli.py | 81KB | Instinct 管理 CLI |
| detect_project.sh | 11KB | 项目检测脚本 |
| observe.sh | 23KB | Hook 观察脚本 |

## 复用的核心函数

- `detect_project()` - Git 项目检测
- `_project_hash()` - SHA256 哈希生成
- `parse_instinct_file()` - YAML 解析

## 使用方式

通过 Adapter 层调用（不直接导入）：

```python
from adapters.ecc_instinct_adapter import InstinctAdapter
adapter = InstinctAdapter()
```
