"""
Local Knowledge Graph Storage
使用 SQLite + sqlite-vec 实现本地知识图谱存储
参考 hot-memory-mcp 的实现方案
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    import sqlite_vec
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False
    logger.warning("Vector search dependencies not available. Install sqlite-vec and sentence-transformers.")


class LocalKnowledgeGraph:
    """
    本地知识图谱存储

    Schema:
    - entities: 知识节点 (id, name, entity_type, observations, created_at, updated_at)
    - relations: 关系 (id, from_entity, to_entity, relation_type, created_at)
    - entity_embeddings: 向量索引 (entity_id, embedding)
    """

    def __init__(self, db_path: str | Path):
        """
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

        # 初始化嵌入模型（如果可用）
        self.model = None
        if VECTOR_SEARCH_AVAILABLE:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence transformer model loaded: all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")

    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(str(self.db_path))

        # 加载 sqlite-vec 扩展
        if VECTOR_SEARCH_AVAILABLE:
            try:
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
            except Exception as e:
                logger.warning(f"Failed to load sqlite-vec: {e}")

        cursor = conn.cursor()

        # 创建 entities 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                entity_type TEXT NOT NULL,
                observations TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 创建 relations 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity TEXT NOT NULL,
                to_entity TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(from_entity, to_entity, relation_type)
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relation_from ON relations(from_entity)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relation_to ON relations(to_entity)
        """)

        # 创建向量表（如果支持）
        if VECTOR_SEARCH_AVAILABLE:
            try:
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS entity_embeddings
                    USING vec0(
                        entity_id INTEGER PRIMARY KEY,
                        embedding FLOAT[384]
                    )
                """)
            except Exception as e:
                logger.warning(f"Failed to create vector table: {e}")

        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")

    def create_entities(self, entities: List[Dict[str, Any]]) -> int:
        """创建知识节点"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        created_count = 0
        now = datetime.utcnow().isoformat()

        for entity in entities:
            name = entity.get("name")
            entity_type = entity.get("entityType", "Knowledge")
            observations = entity.get("observations", [])

            if not name:
                continue

            try:
                cursor.execute("""
                    INSERT INTO entities (name, entity_type, observations, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        observations = json_insert(excluded.observations, '$[#]', ?),
                        updated_at = ?
                """, (name, entity_type, json.dumps(observations), now, now, json.dumps(observations), now))

                entity_id = cursor.lastrowid

                # 生成嵌入向量
                if self.model and VECTOR_SEARCH_AVAILABLE and entity_id:
                    text_to_embed = f"{name}: {' '.join(observations)}"
                    embedding = self.model.encode(text_to_embed).tolist()

                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO entity_embeddings (entity_id, embedding)
                            VALUES (?, ?)
                        """, (entity_id, json.dumps(embedding)))
                    except Exception as e:
                        logger.warning(f"Failed to store embedding for {name}: {e}")

                created_count += 1

            except Exception as e:
                logger.error(f"Failed to create entity {name}: {e}")

        conn.commit()
        conn.close()

        logger.info(f"Created {created_count} entities")
        return created_count

    def create_relations(self, relations: List[Dict[str, Any]]) -> int:
        """创建关系"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        created_count = 0
        now = datetime.utcnow().isoformat()

        for relation in relations:
            from_entity = relation.get("from")
            to_entity = relation.get("to")
            relation_type = relation.get("relationType", "related_to")

            if not from_entity or not to_entity:
                continue

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO relations (from_entity, to_entity, relation_type, created_at)
                    VALUES (?, ?, ?, ?)
                """, (from_entity, to_entity, relation_type, now))

                if cursor.rowcount > 0:
                    created_count += 1

            except Exception as e:
                logger.error(f"Failed to create relation: {e}")

        conn.commit()
        conn.close()

        logger.info(f"Created {created_count} relations")
        return created_count

    def search_nodes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索节点（支持语义搜索和关键词搜索）"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        results = []

        # 尝试向量搜索
        if self.model and VECTOR_SEARCH_AVAILABLE:
            try:
                query_embedding = self.model.encode(query).tolist()

                cursor.execute("""
                    SELECT e.id, e.name, e.entity_type, e.observations, e.created_at, e.updated_at
                    FROM entity_embeddings v
                    JOIN entities e ON e.id = v.entity_id
                    WHERE v.embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """, (json.dumps(query_embedding), limit))

                for row in cursor.fetchall():
                    results.append({
                        "id": row[0],
                        "name": row[1],
                        "entityType": row[2],
                        "observations": json.loads(row[3]),
                        "created_at": row[4],
                        "updated_at": row[5]
                    })

                if results:
                    conn.close()
                    return results

            except Exception as e:
                logger.warning(f"Vector search failed: {e}")

        # 关键词搜索 fallback
        cursor.execute("""
            SELECT id, name, entity_type, observations, created_at, updated_at
            FROM entities
            WHERE name LIKE ? OR observations LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))

        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "name": row[1],
                "entityType": row[2],
                "observations": json.loads(row[3]),
                "created_at": row[4],
                "updated_at": row[5]
            })

        conn.close()
        return results

    def open_nodes(self, names: List[str]) -> List[Dict[str, Any]]:
        """获取指定节点的详细信息"""
        if not names:
            return []

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(names))
        cursor.execute(f"""
            SELECT id, name, entity_type, observations, created_at, updated_at
            FROM entities
            WHERE name IN ({placeholders})
        """, names)

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "name": row[1],
                "entityType": row[2],
                "observations": json.loads(row[3]),
                "created_at": row[4],
                "updated_at": row[5]
            })

        conn.close()
        return results

    def read_graph(self) -> Dict[str, Any]:
        """读取完整知识图谱"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 读取所有 entities
        cursor.execute("SELECT id, name, entity_type, observations, created_at, updated_at FROM entities")

        entities = []
        for row in cursor.fetchall():
            entities.append({
                "id": row[0],
                "name": row[1],
                "entityType": row[2],
                "observations": json.loads(row[3]),
                "created_at": row[4],
                "updated_at": row[5]
            })

        # 读取所有 relations
        cursor.execute("SELECT id, from_entity, to_entity, relation_type, created_at FROM relations")

        relations = []
        for row in cursor.fetchall():
            relations.append({
                "id": row[0],
                "from": row[1],
                "to": row[2],
                "relationType": row[3],
                "created_at": row[4]
            })

        conn.close()

        return {
            "entities": entities,
            "relations": relations
        }

    def delete_entities(self, entity_names: List[str]) -> int:
        """删除节点及其相关关系"""
        if not entity_names:
            return 0

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(entity_names))

        # 删除相关关系
        cursor.execute(f"DELETE FROM relations WHERE from_entity IN ({placeholders}) OR to_entity IN ({placeholders})", entity_names + entity_names)

        # 删除 entities
        cursor.execute(f"DELETE FROM entities WHERE name IN ({placeholders})", entity_names)

        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()

        return deleted_count
