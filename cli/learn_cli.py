"""
Learn CLI - 学习命令行工具

用法:
    python -m cli.learn_cli <file_path>
    python -m cli.learn_cli --interactive
"""

import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.code_extractor import CodeExtractor
from core.mastery_analyzer import MasteryAnalyzer, KnowledgePoint
from adapters.storage_adapter import StorageAdapter


class LearnCLI:
    """学习命令行工具"""

    def __init__(self):
        self.code_extractor = CodeExtractor()
        self.mastery_analyzer = MasteryAnalyzer()
        self.storage = StorageAdapter()

    def learn_from_file(self, file_path: str, language: Optional[str] = None):
        path = Path(file_path)
        if not path.exists():
            print(f"错误: 文件不存在 - {file_path}")
            return

        print(f"
正在分析文件: {path.name}")
        print("=" * 60)

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if path.suffix in ['.py', '.js', '.ts', '.java', '.go']:
            language = language or path.suffix[1:]
            result = self.code_extractor.extract_from_code(content, language)
        elif path.suffix in ['.md', '.txt']:
            result = self.code_extractor.extract_from_document(content)
        else:
            print(f"不支持的文件类型: {path.suffix}")
            return

        print(f"
{result.summary}")
        
        for idx, node in enumerate(result.nodes[:5], 1):
            print(f"{idx}. {node.title} (难度: {node.difficulty:.2f})")

        if len(result.nodes) > 5:
            print(f"... 还有 {len(result.nodes) - 5} 个知识点")

    def interactive_mode(self):
        print("
学习系统 - 交互模式 (输入 exit 退出)")
        while True:
            try:
                cmd = input("学习> ").strip()
                if cmd == 'exit': break
                if cmd.startswith('learn '): self.learn_from_file(cmd[6:])
            except KeyboardInterrupt:
                break


def main():
    cli = LearnCLI()
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--interactive', '-i']:
            cli.interactive_mode()
        else:
            cli.learn_from_file(sys.argv[1])
    else:
        print("用法: python -m cli.learn_cli <file> 或 --interactive")


if __name__ == '__main__':
    main()
