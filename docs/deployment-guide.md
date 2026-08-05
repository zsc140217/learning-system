# 部署指南

**文档版本**: 1.0.0  
**更新时间**: 2026-08-04  
**适用项目**: Learning System

---

## 环境要求

### 系统要求
- **操作系统**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 12+
- **Python**: 3.12 或更高版本
- **内存**: 最低 2GB，推荐 4GB+
- **磁盘**: 最低 1GB 可用空间

### 依赖项

**核心依赖**:
- `fastapi` >= 0.104.0 - Web 框架
- `uvicorn` >= 0.24.0 - ASGI 服务器
- `pyjwt` >= 2.8.0 - JWT 签名验证
- `cryptography` >= 41.0.0 - 加密存储
- `httpx` >= 0.25.0 - HTTP 客户端

**可选依赖**:
- DeepSeek API - 语义分析（可选）
- Redis - Nonce 存储（生产环境推荐）

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-org/learning-system.git
cd learning-system
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

**生成 JWT 密钥**:
```bash
# Windows (PowerShell)
python -c "import secrets; print(secrets.token_hex(32))"

# Linux/macOS
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
```

**可选：DeepSeek API**:
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

### 4. 启动服务

```bash
# 开发模式（热重载）
uvicorn mcp-server.server:app --reload --port 8000

# 生产模式
uvicorn mcp-server.server:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. 验证服务

```bash
curl http://localhost:8000/health

# 预期返回
{"status": "ok", "version": "1.0.0"}
```

---

## 配置详解

### 环境变量

| 变量名 | 说明 | 必需 | 默认值 |
|-------|------|-----|--------|
| `JWT_SECRET` | JWT 签名密钥（32 字节十六进制） | ✅ | 无 |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | ❌ | 无 |
| `MCP_MEMORY_PATH` | 知识图谱存储路径 | ❌ | `./data/memory` |
| `LOG_LEVEL` | 日志级别 | ❌ | `INFO` |
| `REDIS_URL` | Redis 连接 URL | ❌ | 无（使用内存） |
| `MAX_CONCURRENT_TASKS` | 最大并发任务数 | ❌ | `50` |
| `NONCE_EXPIRY_HOURS` | Nonce 过期时间（小时） | ❌ | `1` |

### 配置文件示例

**创建 `.env` 文件**:
```bash
JWT_SECRET=your-32-byte-hex-secret-here
DEEPSEEK_API_KEY=your-api-key
MCP_MEMORY_PATH=./data/memory
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379/0
MAX_CONCURRENT_TASKS=50
NONCE_EXPIRY_HOURS=1
```

---

## 生产部署

### 使用 systemd（Linux）

**1. 创建服务文件**:
```bash
sudo nano /etc/systemd/system/learning-system.service
```

**服务配置**:
```ini
[Unit]
Description=Learning System MCP Server
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/learning-system
Environment="JWT_SECRET=your-secret"
ExecStart=/opt/learning-system/venv/bin/uvicorn \
    mcp-server.server:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. 启动服务**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable learning-system
sudo systemctl start learning-system
sudo systemctl status learning-system
```

### 使用 Nginx 反向代理

**Nginx 配置**:
```nginx
upstream learning_system {
    server 127.0.0.1:8000;
    keepalive 64;
}

server {
    listen 80;
    server_name learning-system.example.com;
    
    location / {
        proxy_pass http://learning_system;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://learning_system/health;
        access_log off;
    }
}
```

**启用配置**:
```bash
sudo ln -s /etc/nginx/sites-available/learning-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 使用 Docker

**Dockerfile**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp-server/ ./mcp-server/
COPY data/ ./data/

EXPOSE 8000

CMD ["uvicorn", "mcp-server.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  learning-system:
    build: .
    ports:
      - "8000:8000"
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

**启动容器**:
```bash
docker-compose up -d
docker-compose logs -f learning-system
```

---

## 监控和日志

### 日志配置

**日志格式**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

### 性能监控指标

- 请求 QPS
- 响应时间 P50/P95/P99
- 任务执行状态
- 缓存命中率
- 错误率

---

## 安全加固

### 1. JWT 密钥管理

```bash
# 生成强密钥
python -c "import secrets; print(secrets.token_hex(32))" > jwt.secret
chmod 600 jwt.secret

# 从文件读取
export JWT_SECRET=$(cat jwt.secret)
```

### 2. 防火墙配置

```bash
# UFW（Ubuntu）
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 3. 限流配置

**Nginx 限流**:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location / {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://learning_system;
}
```

---

## 故障排查

### 常见问题

**1. JWT 验证失败**
```
错误: Invalid signature
解决: 确认 JWT_SECRET 环境变量正确设置
```

**2. 任务无法启动**
```
错误: Semaphore limit reached
解决: 增加 MAX_CONCURRENT_TASKS 或等待任务完成
```

**3. 数据库连接失败**
```
错误: Unable to connect to database
解决: 检查 MCP_MEMORY_PATH 路径权限
```

### 日志查看

```bash
# systemd 日志
sudo journalctl -u learning-system -n 100

# 应用日志
tail -f logs/app.log
```

---

## 升级指南

### 版本升级步骤

**1. 备份数据**:
```bash
cp data/learning_system.db data/learning_system.db.backup
tar -czf memory-backup.tar.gz data/memory/
```

**2. 更新代码**:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

**3. 重启服务**:
```bash
sudo systemctl restart learning-system
```

**4. 验证升级**:
```bash
curl http://localhost:8000/health
```

---

## 性能调优

### 并发优化

```bash
# 增加并发任务数
MAX_CONCURRENT_TASKS=100

# 增加 uvicorn workers
uvicorn mcp-server.server:app --workers 8
```

### 缓存优化

```bash
# 延长缓存时间
CACHE_TTL_HOURS=24
```

---

## 总结

本指南涵盖了 Learning System 的完整部署流程：

✅ 环境配置  
✅ 快速开始  
✅ 生产部署（systemd + Nginx + Docker）  
✅ 监控和日志  
✅ 安全加固  
✅ 故障排查  

**下一步**: 查看 [面试准备要点](interview-highlights.md)。
