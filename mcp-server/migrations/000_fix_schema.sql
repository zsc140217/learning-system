-- Migration: 修复数据库架构
-- Date: 2026-08-08
-- Description: 重命名表并添加缺失字段

-- 1. 重命名表
ALTER TABLE IF EXISTS knowledge_entities RENAME TO entities;
ALTER TABLE IF EXISTS knowledge_relations RENAME TO relations;

-- 2. 为 entities 表添加缺失字段
ALTER TABLE entities
ADD COLUMN IF NOT EXISTS observations TEXT[] NOT NULL DEFAULT '{}';

ALTER TABLE entities
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

ALTER TABLE entities
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- 3. 为 relations 表添加缺失字段
ALTER TABLE relations
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- 4. 添加索引
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_updated ON entities(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity);
CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);

-- 5. 添加唯一约束（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'relations_unique_triplet'
    ) THEN
        ALTER TABLE relations
        ADD CONSTRAINT relations_unique_triplet
        UNIQUE(from_entity, to_entity, relation_type);
    END IF;
END $$;

-- 6. 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 7. 为 entities 表添加更新时间触发器
DROP TRIGGER IF EXISTS update_entities_updated_at ON entities;
CREATE TRIGGER update_entities_updated_at
BEFORE UPDATE ON entities
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 8. 添加表注释
COMMENT ON TABLE entities IS '知识图谱实体表，存储知识点、技术、概念等';
COMMENT ON TABLE relations IS '知识图谱关系表，存储实体之间的关系';
COMMENT ON COLUMN entities.observations IS '观察列表，存储关于该实体的多个事实描述';
