// Global state management with Zustand

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UITemplate, TaskHandle, InputRequired } from '@/types/mcp';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  uiTemplate?: UITemplate;
}

interface AppState {
  connected: boolean;
  setConnected: (connected: boolean) => void;

  messages: Message[];
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  clearMessages: () => void;

  activeUI: UITemplate | null;
  setActiveUI: (ui: UITemplate | null) => void;

  activeTasks: Map<string, TaskHandle>;
  addTask: (task: TaskHandle) => void;
  updateTask: (taskId: string, updates: Partial<TaskHandle>) => void;
  removeTask: (taskId: string) => void;

  pendingConfirmation: InputRequired | null;
  setPendingConfirmation: (confirmation: InputRequired | null) => void;

  sessionId: string | null;
  currentProject: string | null;
  setSessionId: (id: string | null) => void;
  setCurrentProject: (path: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      connected: false,
      setConnected: (connected) => set({ connected }),

      messages: [],
      addMessage: (message) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              ...message,
              id: `msg-${Date.now()}-${Math.random()}`,
              timestamp: new Date(),
            },
          ],
        })),
      clearMessages: () => set({ messages: [] }),

      activeUI: null,
      setActiveUI: (ui) => set({ activeUI: ui }),

      activeTasks: new Map(),
      addTask: (task) =>
        set((state) => {
          const newTasks = new Map(state.activeTasks);
          newTasks.set(task.task_id, task);
          return { activeTasks: newTasks };
        }),
      updateTask: (taskId, updates) =>
        set((state) => {
          const newTasks = new Map(state.activeTasks);
          const existing = newTasks.get(taskId);
          if (existing) {
            newTasks.set(taskId, { ...existing, ...updates });
          }
          return { activeTasks: newTasks };
        }),
      removeTask: (taskId) =>
        set((state) => {
          const newTasks = new Map(state.activeTasks);
          newTasks.delete(taskId);
          return { activeTasks: newTasks };
        }),

      pendingConfirmation: null,
      setPendingConfirmation: (confirmation) => set({ pendingConfirmation: confirmation }),

      sessionId: null,
      currentProject: null,
      setSessionId: (id) => set({ sessionId: id }),
      setCurrentProject: (path) => set({ currentProject: path }),
    }),
    {
      name: 'learning-system-storage',
      partialize: (state) => ({
        sessionId: state.sessionId,
        messages: state.messages,
        currentProject: state.currentProject,
      }),
    }
  )
);
