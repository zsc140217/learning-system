"""
客户端状态管理器
核心职责：管理无状态 MCP 协议的会话状态
"""
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """对话消息"""
    role: str  # user | assistant | system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """运行中的任务"""
    task_id: str
    tool_name: str
    status: str  # running | completed | failed | cancelled
    progress: float = 0.0  # 0-100
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Confirmation:
    """待确认的操作（MRTR）"""
    request_id: str
    tool_name: str
    args: Dict[str, Any]
    prompt: str
    fields: List[Dict[str, Any]]
    request_state: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MCPApp:
    """运行中的 MCP App"""
    app_id: str
    tool_name: str
    template: str
    data: Any
    created_at: datetime = field(default_factory=datetime.now)


class ClientStateManager:
    """
    客户端状态管理器

    MCP 协议是无状态的，服务端不保存会话信息。
    客户端必须管理所有状态：
    - session_id: 会话标识
    - user_id: 用户标识
    - conversation_history: 对话历史
    - current_project: 当前分析的项目
    - running_tasks: 运行中的长任务
    - pending_confirmations: 待确认的操作
    - active_apps: 运行中的 MCP Apps
    """

    def __init__(self, user_id: Optional[str] = None):
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id or str(uuid.uuid4())
        self.conversation_history: List[Message] = []
        self.current_project: Optional[str] = None
        self.running_tasks: Dict[str, Task] = {}
        self.pending_confirmations: Dict[str, Confirmation] = {}
        self.active_apps: Dict[str, MCPApp] = {}

    # ===== 对话历史管理 =====

    def add_message(self, role: str, content: str, **metadata) -> Message:
        """添加消息到对话历史"""
        msg = Message(role=role, content=content, metadata=metadata)
        self.conversation_history.append(msg)
        return msg

    def get_history(self, last_n: Optional[int] = None) -> List[Message]:
        """获取对话历史"""
        if last_n:
            return self.conversation_history[-last_n:]
        return self.conversation_history

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()

    # ===== 项目管理 =====

    def set_current_project(self, project_path: str):
        """设置当前项目"""
        self.current_project = project_path

    def get_current_project(self) -> Optional[str]:
        """获取当前项目"""
        return self.current_project

    # ===== 任务管理 =====

    def add_task(self, task_id: str, tool_name: str) -> Task:
        """添加任务"""
        task = Task(task_id=task_id, tool_name=tool_name, status="running")
        self.running_tasks[task_id] = task
        return task

    def update_task(self, task_id: str, **updates):
        """更新任务状态"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            for key, value in updates.items():
                setattr(task, key, value)
            task.updated_at = datetime.now()

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.running_tasks.get(task_id)

    def remove_task(self, task_id: str):
        """移除任务"""
        self.running_tasks.pop(task_id, None)

    def get_running_tasks(self) -> List[Task]:
        """获取所有运行中的任务"""
        return [t for t in self.running_tasks.values() if t.status == "running"]

    # ===== MRTR 确认管理 =====

    def add_confirmation(
        self,
        request_id: str,
        tool_name: str,
        args: Dict[str, Any],
        prompt: str,
        fields: List[Dict[str, Any]],
        request_state: str
    ) -> Confirmation:
        """添加待确认操作"""
        conf = Confirmation(
            request_id=request_id,
            tool_name=tool_name,
            args=args,
            prompt=prompt,
            fields=fields,
            request_state=request_state
        )
        self.pending_confirmations[request_id] = conf
        return conf

    def get_confirmation(self, request_id: str) -> Optional[Confirmation]:
        """获取待确认操作"""
        return self.pending_confirmations.get(request_id)

    def remove_confirmation(self, request_id: str):
        """移除确认"""
        self.pending_confirmations.pop(request_id, None)

    # ===== MCP App 管理 =====

    def add_app(
        self,
        app_id: str,
        tool_name: str,
        template: str,
        data: Any
    ) -> MCPApp:
        """添加 MCP App"""
        app = MCPApp(
            app_id=app_id,
            tool_name=tool_name,
            template=template,
            data=data
        )
        self.active_apps[app_id] = app
        return app

    def get_app(self, app_id: str) -> Optional[MCPApp]:
        """获取 MCP App"""
        return self.active_apps.get(app_id)

    def remove_app(self, app_id: str):
        """移除 MCP App"""
        self.active_apps.pop(app_id, None)

    # ===== 上下文构建 =====

    def build_tool_context(self) -> Dict[str, Any]:
        """
        构建工具调用的上下文参数
        每次调用 MCP 工具时都要显式传递这些参数
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "project_id": self.current_project,
        }

    def get_state_summary(self) -> Dict[str, Any]:
        """获取状态摘要（用于调试）"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "current_project": self.current_project,
            "conversation_count": len(self.conversation_history),
            "running_tasks": len(self.get_running_tasks()),
            "pending_confirmations": len(self.pending_confirmations),
            "active_apps": len(self.active_apps),
        }
