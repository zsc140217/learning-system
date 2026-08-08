// MCP Protocol Type Definitions

export interface JSONRPCRequest {
  jsonrpc: '2.0';
  id: number | string;
  method: string;
  params?: Record<string, any>;
}

export interface JSONRPCResponse {
  jsonrpc: '2.0';
  id: number | string;
  result?: any;
  error?: JSONRPCError;
  _meta?: MCPMeta;
}

export interface JSONRPCError {
  code: number;
  message: string;
  data?: any;
}

export interface MCPMeta {
  'io.modelcontextprotocol/uiTemplate'?: UITemplate;
  'io.modelcontextprotocol/inputRequired'?: InputRequired;
  'io.modelcontextprotocol.tasks/taskHandle'?: TaskHandle;
  ttlMs?: number;
  cacheScope?: 'user' | 'public';
}

export interface UITemplate {
  templateId: string;
  version?: string;
  layout?: 'card' | 'fullscreen' | 'wizard' | 'dashboard';
  theme?: 'auto' | 'light' | 'dark';
  templatePath?: string;
  data: Record<string, any>;
  actions?: Record<string, UIAction>;
}

export interface UIAction {
  label?: string;
  toolName: string;
  params: Record<string, any>;
  style?: 'primary' | 'secondary' | 'danger';
}

export interface InputRequired {
  message: string;
  fields: InputField[];
  requestState: string;
  uiTemplate?: UITemplate;
}

export interface InputField {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'select';
  label?: string;
  required?: boolean;
  default?: any;
  options?: Array<{ value: any; label: string }>;
}

export interface TaskHandle {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message?: string;
  eta?: number;
}

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
}

export type ComponentType =
  | 'header'
  | 'stats-grid'
  | 'knowledge-list'
  | 'chart'
  | 'action-bar'
  | 'card'
  | 'task-list';

export interface UIComponent {
  type: ComponentType;
  props?: Record<string, any>;
  children?: UIComponent[];
}

export interface UISection {
  type: ComponentType;
  [key: string]: any;
}
