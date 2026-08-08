"""
Skill 管理器
加载和管理 Skill 文档（方法论）
"""
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Skill:
    """Skill 定义"""
    name: str
    description: str
    content: str
    file_path: Path
    metadata: Dict[str, str]


class SkillManager:
    """
    Skill 管理器

    职责：
    1. 从 skills/ 目录加载 .md 文件
    2. 解析 frontmatter（name, description）
    3. 提供给 LLM 的系统提示

    Skill 格式：
    ---
    name: interview-prep
    description: 准备技术面试
    ---

    ## 触发条件
    ...

    ## 工作流程
    ...
    """

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}

    def load_skills(self):
        """加载所有 Skills"""
        if not self.skills_dir.exists():
            print(f"[SkillManager] Skills directory not found: {self.skills_dir}")
            return

        for skill_file in self.skills_dir.glob("*.md"):
            try:
                skill = self._parse_skill_file(skill_file)
                self.skills[skill.name] = skill
                print(f"[SkillManager] Loaded skill: {skill.name}")
            except Exception as e:
                print(f"[SkillManager] Failed to load {skill_file.name}: {e}")

    def _parse_skill_file(self, file_path: Path) -> Skill:
        """解析 Skill 文件"""
        content = file_path.read_text(encoding="utf-8")

        # 解析 frontmatter
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            raise ValueError("Invalid skill format: missing frontmatter")

        frontmatter_text = frontmatter_match.group(1)
        body = frontmatter_match.group(2)

        # 解析 frontmatter 字段
        metadata = {}
        for line in frontmatter_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        if "name" not in metadata or "description" not in metadata:
            raise ValueError("Skill must have 'name' and 'description' in frontmatter")

        return Skill(
            name=metadata["name"],
            description=metadata["description"],
            content=body.strip(),
            file_path=file_path,
            metadata=metadata
        )

    def get_skill(self, name: str) -> Optional[Skill]:
        """获取 Skill"""
        return self.skills.get(name)

    def list_skills(self) -> List[Skill]:
        """列出所有 Skills"""
        return list(self.skills.values())

    def get_system_prompt(self) -> str:
        """
        生成系统提示（给 LLM）

        告诉 LLM 有哪些 Skills 可用，以及如何触发
        """
        if not self.skills:
            return ""

        prompt = "# 可用的 Skills（方法论）\n\n"
        prompt += "当用户的请求匹配以下 Skills 时，你应该按照 Skill 中定义的工作流程执行：\n\n"

        for skill in self.skills.values():
            prompt += f"## {skill.name}\n"
            prompt += f"**描述**：{skill.description}\n"
            prompt += f"**内容**：\n```markdown\n{skill.content}\n```\n\n"

        return prompt

    def match_skill(self, user_message: str) -> Optional[Skill]:
        """
        根据用户消息匹配 Skill

        简单实现：检查是否包含关键词
        更好的实现：使用 LLM 理解意图
        """
        user_lower = user_message.lower()

        for skill in self.skills.values():
            # 从 Skill 内容中提取触发条件
            trigger_match = re.search(
                r"##\s*触发条件\s*\n(.*?)(?=\n##|\Z)",
                skill.content,
                re.DOTALL | re.IGNORECASE
            )

            if trigger_match:
                triggers = trigger_match.group(1)
                # 提取引号中的关键词
                keywords = re.findall(r'["""](.*?)["""]', triggers)

                for keyword in keywords:
                    if keyword.lower() in user_lower:
                        return skill

        return None
