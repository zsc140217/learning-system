// MCP Client Service - handles JSON-RPC protocol and MCP features

import { wsService } from './websocket';
import type {
  JSONRPCRequest,
  JSONRPCResponse,
  MCPTool,
  UITemplate,
  InputRequired,
  TaskHandle,
} from '@/types/mcp';

export class MCPClient {
  private requestId = 0;
  private pendingRequests = new Map<number, {
    resolve: (value: any) => void;
    reject: (error: any) => void;
  }>();
  private cleanupHandler: (() => void) | null = null;

  constructor() {
    this.registerMessageHandler();
  }

  private registerMessageHandler() {
    // Clean up previous handler if exists
    if (this.cleanupHandler) {
      this.cleanupHandler();
    }

    // Register new handler
    this.cleanupHandler = wsService.onMessage(this.handleMessage.bind(this));
    console.log('[MCPClient] Message handler registered');
  }

  // Public method to re-register handler after reconnection
  reregisterHandler() {
    this.registerMessageHandler();
  }

  private handleMessage(response: JSONRPCResponse): void {
    console.log('[MCPClient] Received message:', response);
    console.log('[MCPClient] Response ID:', response.id);
    console.log('[MCPClient] Pending requests:', Array.from(this.pendingRequests.keys()));

    const pending = this.pendingRequests.get(response.id as number);
    if (!pending) {
      console.warn('[MCPClient] No pending request for ID:', response.id);
      return;
    }

    this.pendingRequests.delete(response.id as number);

    if (response.error) {
      console.error('[MCPClient] Error response:', response.error);
      pending.reject(response.error);
    } else {
      console.log('[MCPClient] Success response, resolving request', response.id);
      pending.resolve(response);
    }
  }

  async callTool(toolName: string, args: Record<string, any>): Promise<JSONRPCResponse> {
    const id = ++this.requestId;

    const request: JSONRPCRequest = {
      jsonrpc: '2.0',
      id,
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: args,
      },
    };

    return new Promise((resolve, reject) => {
      // Check connection before sending
      if (!wsService.isConnected()) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      this.pendingRequests.set(id, { resolve, reject });
      console.log(`[MCPClient] Sending request ${id}:`, request);
      wsService.send(request);

      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          console.error(`[MCPClient] Request ${id} timeout - no response received`);
          reject(new Error('Request timeout'));
        }
      }, 30000);
    });
  }

  async listTools(): Promise<MCPTool[]> {
    const id = ++this.requestId;

    const request: JSONRPCRequest = {
      jsonrpc: '2.0',
      id,
      method: 'tools/list',
    };

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });
      wsService.send(request);

      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error('Request timeout'));
        }
      }, 10000);
    });
  }

  parseResponse(response: JSONRPCResponse | string | any): {
    result: any;
    uiTemplate?: UITemplate;
    inputRequired?: InputRequired;
    taskHandle?: TaskHandle;
  } {
    console.log('[MCPClient] parseResponse called with type:', typeof response);
    console.log('[MCPClient] parseResponse raw data:', response);

    // Handle string response (shouldn't happen but defensive)
    if (typeof response === 'string') {
      console.warn('[MCPClient] Received string response, attempting to parse');
      try {
        // Try to parse as JSON first
        const parsed = JSON.parse(response);
        if (parsed && typeof parsed === 'object') {
          console.log('[MCPClient] Successfully parsed string to object');
          response = parsed;
        } else {
          console.warn('[MCPClient] Parsed result is not an object, returning as-is');
          return {
            result: response,
            uiTemplate: undefined,
            inputRequired: undefined,
            taskHandle: undefined,
          };
        }
      } catch (e) {
        // Not JSON, return as-is
        console.error('[MCPClient] Failed to parse string as JSON:', e);
        return {
          result: response,
          uiTemplate: undefined,
          inputRequired: undefined,
          taskHandle: undefined,
        };
      }
    }

    // Handle non-object responses
    if (!response || typeof response !== 'object') {
      console.warn('[MCPClient] Response is not an object:', typeof response);
      return {
        result: response,
        uiTemplate: undefined,
        inputRequired: undefined,
        taskHandle: undefined,
      };
    }

    const meta = response._meta || {};
    console.log('[MCPClient] Extracted meta:', meta);
    console.log('[MCPClient] Extracted result:', response.result);

    return {
      result: response.result,
      uiTemplate: meta['io.modelcontextprotocol/uiTemplate'],
      inputRequired: meta['io.modelcontextprotocol/inputRequired'],
      taskHandle: meta['io.modelcontextprotocol.tasks/taskHandle'],
    };
  }

  isUITemplate(response: JSONRPCResponse): boolean {
    return !!response._meta?.['io.modelcontextprotocol/uiTemplate'];
  }

  isInputRequired(response: JSONRPCResponse): boolean {
    return !!response._meta?.['io.modelcontextprotocol/inputRequired'];
  }

  isTaskHandle(response: JSONRPCResponse): boolean {
    return !!response._meta?.['io.modelcontextprotocol.tasks/taskHandle'];
  }
}

export const mcpClient = new MCPClient();
