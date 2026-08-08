# Learning System - React Frontend

React 前端客户端，基于 MCP 协议与后端通信。

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Zustand** - 状态管理
- **Tailwind CSS** - 样式框架
- **WebSocket** - 实时通信
- **Recharts** - 图表库
- **D3.js** - 数据可视化

## 项目结构

```
frontend/
├── src/
│   ├── components/         # React 组件
│   │   ├── ChatInterface.tsx        # 对话界面
│   │   ├── TaskProgress.tsx         # 任务进度条
│   │   ├── ConfirmDialog.tsx        # MRTR 确认对话框
│   │   └── ui/                      # UI 组件库
│   │       ├── UIRenderer.tsx       # MCP App 渲染器
│   │       ├── Header.tsx
│   │       ├── StatsGrid.tsx
│   │       ├── KnowledgeList.tsx
│   │       └── Chart.tsx
│   ├── services/          # 服务层
│   │   ├── websocket.ts   # WebSocket 服务
│   │   └── mcpClient.ts   # MCP 客户端
│   ├── store/             # 状态管理
│   │   └── appStore.ts    # Zustand store
│   ├── types/             # TypeScript 类型
│   │   └── mcp.ts         # MCP 协议类型
│   ├── styles/            # 样式
│   │   └── index.css
│   ├── App.tsx            # 主应用
│   └── main.tsx           # 入口文件
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## 核心功能

### 1. WebSocket 实时通信

通过 WebSocket 与后端保持持久连接，实现实时双向通信。

```typescript
// 自动重连机制
wsService.connect('ws://localhost:8000/ws');
```

### 2. MCP 协议支持

完整实现 MCP 2026 协议的四大特性：

- **UITemplate** - 渲染 MCP App 界面
- **MRTR** - 二次确认对话框
- **Tasks** - 长任务进度追踪
- **Cache** - 响应缓存（未来）

### 3. UI 渲染引擎

支持两种渲染方式：

- **JSON 组件渲染** - 标准组件（Header, StatsGrid, Chart 等）
- **HTML 沙箱渲染** - 复杂界面（知识图谱）

### 4. 状态管理

使用 Zustand 管理全局状态：

- 连接状态
- 消息历史
- 活动任务
- UI 模板
- 待确认操作

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

## 配置

创建 `.env` 文件：

```env
VITE_WS_URL=ws://localhost:8000/ws
```

## MCP App 示例

### 1. 会话总结（纯 JSON）

```typescript
{
  templateId: "com.learning-system.session-summary",
  data: {
    sections: [
      { type: "header", title: "学习总结" },
      { type: "stats-grid", items: [...] },
      { type: "knowledge-list", items: [...] }
    ]
  }
}
```

### 2. 知识图谱（HTML 模板）

```typescript
{
  templateId: "com.learning-system.knowledge-graph",
  templatePath: "/templates/knowledge_graph.html",
  data: {
    nodes: [...],
    edges: [...]
  }
}
```

## 开发指南

### 添加新的 UI 组件

1. 在 `src/components/ui/` 创建组件
2. 在 `UIRenderer.tsx` 中注册
3. 更新 `mcp.ts` 类型定义

### 调用 MCP Tool

```typescript
const response = await mcpClient.callTool('tool_name', {
  param1: 'value1',
});

const { result, uiTemplate, taskHandle } = mcpClient.parseResponse(response);
```

### 处理长任务

```typescript
if (taskHandle) {
  useAppStore.getState().addTask(taskHandle);
  // TaskProgress 组件会自动轮询状态
}
```

## 架构亮点

### 1. AI-First 设计

- 服务端返回 UI 描述，客户端负责渲染
- 支持动态 UI（服务端推送新界面）
- LLM 可以决定展示什么界面

### 2. 类型安全

- 完整的 TypeScript 类型定义
- MCP 协议类型覆盖
- 编译时错误检查

### 3. 模块化设计

- 服务层独立（WebSocket, MCP Client）
- UI 组件可复用
- 状态管理集中

### 4. 用户体验

- 实时连接状态显示
- 自动重连机制
- 任务进度可视化
- 二次确认保护

## 待实现功能

- [ ] 知识图谱 D3.js 可视化
- [ ] 更多图表类型（折线图、饼图）
- [ ] 响应缓存机制
- [ ] 离线支持
- [ ] 主题切换（明暗模式）
- [ ] 消息搜索和过滤
- [ ] 导出对话记录

## 调试

### 查看 WebSocket 消息

打开浏览器控制台：

```javascript
// 查看所有消息
wsService.onMessage((data) => console.log('WS Message:', data));
```

### 查看状态

```javascript
// 查看全局状态
useAppStore.getState();
```

## 常见问题

### Q: WebSocket 连接失败？

A: 确保后端服务已启动（`python backend/main.py`）

### Q: UI 渲染不正确？

A: 检查 templateId 是否在 UIRenderer 中注册

### Q: 任务进度不更新？

A: 确保后端返回了正确的 taskHandle

## 贡献

欢迎提交 Issue 和 PR！

## License

MIT
