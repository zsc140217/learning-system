#!/usr/bin/env python
"""
启动 Learning System MCP Server
"""
import sys
from pathlib import Path

# 添加 mcp-server 到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))

if __name__ == "__main__":
    from server import main
    main()
