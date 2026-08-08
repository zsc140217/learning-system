"""Skill 加载和解析器"""
from pathlib import Path
from typing import Dict, List, Optional


class SkillLoader:
    """Skills 加载器"""

    def __init__(self, skills_dir: str = "../../mcp-server/skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_cache: Dict[str, Dict] = {}

    def load_skill(self, skill_name: str) -> Optional[Dict]:
        """加载单个 Skill"""
        if skill_name in self.skills_cache:
            return self.skills_cache[skill_name]

        skill_path = self.skills_dir / f"{skill_name}.md"
        if not skill_path.exists():
            return None

        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        skill_data = self._parse_skill(content)
        self.skills_cache[skill_name] = skill_data
        return skill_data

    def _parse_skill(self, content: str) -> Dict:
        """解析 Skill frontmatter 和内容"""
        lines = content.split('\n')
        
        if not lines or lines[0].strip() != '---':
            return {"metadata": {}, "content": content}

        frontmatter = {}
        i = 1
        while i < len(lines) and lines[i].strip() != '---':
            if ':' in lines[i]:
                key, value = lines[i].split(':', 1)
                frontmatter[key.strip()] = value.strip()
            i += 1

        body = '\n'.join(lines[i+1:]) if i < len(lines) else ""

        return {"metadata": frontmatter, "content": body.strip()}

    def list_skills(self) -> List[str]:
        """列出所有可用的 Skills"""
        if not self.skills_dir.exists():
            return []
        return sorted([p.stem for p in self.skills_dir.glob("*.md")])
