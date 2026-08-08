/**
 * Skill 加载器 - 从服务端获取 Skill 文档
 */

export interface SkillMetadata {
  name: string;
  description: string;
  trigger: string;
}

export interface SkillContent {
  metadata: SkillMetadata;
  content: string;
}

class SkillLoader {
  private skillsCache: Map<string, SkillContent> = new Map();

  /**
   * 检测消息中是否包含 Skill 触发
   * @param message 用户消息
   * @returns Skill 名称或 null
   */
  detectSkillTrigger(message: string): string | null {
    const lowerMessage = message.toLowerCase().trim();

    // 检测斜杠命令：/skill-name
    const slashMatch = message.match(/^\/([a-z-]+)/);
    if (slashMatch) {
      return slashMatch[1];
    }

    // 检测关键词触发
    const skillKeywords: Record<string, string[]> = {
      'mock-interview': ['模拟面试', '面试准备', '面试练习'],
      'learn-topic': ['学习', '学什么', '教我'],
      'summarize-knowledge': ['总结', '保存知识', '知识点'],
      'tech-deep-dive': ['深入研究', '技术深度'],
      'codebase-onboarding': ['代码分析', '项目分析']
    };

    for (const [skillName, keywords] of Object.entries(skillKeywords)) {
      if (keywords.some(kw => lowerMessage.includes(kw))) {
        return skillName;
      }
    }

    return null;
  }

  /**
   * 加载 Skill 文档
   * @param skillName Skill 名称
   * @returns Skill 文档内容
   */
  async loadSkill(skillName: string): Promise<SkillContent | null> {
    // 检查缓存
    if (this.skillsCache.has(skillName)) {
      return this.skillsCache.get(skillName)!;
    }

    try {
      // 从服务端读取 Skill 文件
      const response = await fetch(`http://localhost:8080/skills/${skillName}.md`);

      if (!response.ok) {
        console.warn(`Skill not found: ${skillName}`);
        return null;
      }

      const content = await response.text();
      const skillContent = this.parseSkill(content);

      // 缓存
      this.skillsCache.set(skillName, skillContent);

      return skillContent;
    } catch (error) {
      console.error(`Failed to load skill ${skillName}:`, error);
      return null;
    }
  }

  /**
   * 解析 Skill 文件
   */
  private parseSkill(content: string): SkillContent {
    const lines = content.split('\n');

    // 解析 frontmatter
    const metadata: any = {};
    let i = 0;

    if (lines[i]?.trim() === '---') {
      i++;
      while (i < lines.length && lines[i]?.trim() !== '---') {
        const line = lines[i];
        if (line.includes(':')) {
          const [key, ...valueParts] = line.split(':');
          metadata[key.trim()] = valueParts.join(':').trim();
        }
        i++;
      }
      i++; // 跳过结束的 ---
    }

    // 剩余内容
    const body = lines.slice(i).join('\n').trim();

    return {
      metadata: {
        name: metadata.name || 'unknown',
        description: metadata.description || '',
        trigger: metadata.trigger || ''
      },
      content: body
    };
  }

  /**
   * 列出所有可用的 Skills
   */
  async listSkills(): Promise<SkillMetadata[]> {
    // 硬编码可用的 Skills（实际应该从服务端获取列表）
    const availableSkills = [
      'summarize-knowledge',
      'interview-prep',
      'tech-deep-dive',
      'codebase-onboarding'
    ];

    const skills: SkillMetadata[] = [];

    for (const skillName of availableSkills) {
      const skill = await this.loadSkill(skillName);
      if (skill) {
        skills.push(skill.metadata);
      }
    }

    return skills;
  }
}

export const skillLoader = new SkillLoader();
