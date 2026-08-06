-- Learning System 知识图谱数据库初始化脚本
-- PostgreSQL + pgvector

-- 启用 pgvector 扩展（用于向量搜索）
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建 entities 表（知识节点）
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    entity_type VARCHAR(100) NOT NULL,
    observations TEXT[] NOT NULL DEFAULT '{}',  -- 存储多个观察结果
    metadata JSONB DEFAULT '{}',  -- 额外元数据
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建 relations 表（实体关系）
CREATE TABLE IF NOT EXISTS relations (
    id SERIAL PRIMARY KEY,
    from_entity VARCHAR(255) NOT NULL,
    to_entity VARCHAR(255) NOT NULL,
    relation_type VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_entity, to_entity, relation_type),
    FOREIGN KEY (from_entity) REFERENCES entities(name) ON DELETE CASCADE,
    FOREIGN KEY (to_entity) REFERENCES entities(name) ON DELETE CASCADE
);

-- 创建 entity_embeddings 表（向量索引）
CREATE TABLE IF NOT EXISTS entity_embeddings (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL,
    embedding vector(1536) NOT NULL,  -- DeepSeek embedding 维度
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_created_at ON entities(created_at);

CREATE INDEX IF NOT EXISTS idx_relation_from ON relations(from_entity);
CREATE INDEX IF NOT EXISTS idx_relation_to ON relations(to_entity);
CREATE INDEX IF NOT EXISTS idx_relation_type ON relations(relation_type);

-- 创建向量索引（使用 ivfflat 索引加速相似度搜索）
CREATE INDEX IF NOT EXISTS idx_entity_embeddings_vector
ON entity_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_entities_updated_at
BEFORE UPDATE ON entities
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 创建视图：实体及其关系统计
CREATE OR REPLACE VIEW entity_stats AS
SELECT
    e.id,
    e.name,
    e.entity_type,
    array_length(e.observations, 1) as observation_count,
    COUNT(DISTINCT r1.id) as outgoing_relations,
    COUNT(DISTINCT r2.id) as incoming_relations,
    e.created_at,
    e.updated_at
FROM entities e
LEFT JOIN relations r1 ON e.name = r1.from_entity
LEFT JOIN relations r2 ON e.name = r2.to_entity
GROUP BY e.id, e.name, e.entity_type, e.observations, e.created_at, e.updated_at;

-- 插入示例数据（可选）
-- INSERT INTO entities (name, entity_type, observations) VALUES
-- ('FastAPI', 'framework', ARRAY['Python web framework', 'High performance', 'Async support']),
-- ('MCP Protocol', 'protocol', ARRAY['Model Context Protocol', 'AI tool integration standard']);

-- INSERT INTO relations (from_entity, to_entity, relation_type) VALUES
-- ('FastAPI', 'MCP Protocol', 'implements');

COMMENT ON TABLE entities IS '知识图谱节点表，存储实体信息';
COMMENT ON TABLE relations IS '知识图谱边表，存储实体间关系';
COMMENT ON TABLE entity_embeddings IS '实体向量嵌入表，用于语义搜索';
COMMENT ON COLUMN entity_embeddings.embedding IS 'DeepSeek API 生成的 1536 维向量';
