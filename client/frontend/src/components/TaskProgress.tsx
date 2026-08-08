import React, { useEffect } from 'react';
import type { TaskHandle } from '@/types/mcp';
import { useAppStore } from '@/store/appStore';
import { mcpClient } from '@/services/mcpClient';

interface TaskProgressProps {
  task: TaskHandle;
}

export const TaskProgress: React.FC<TaskProgressProps> = ({ task }) => {
  const { updateTask, removeTask } = useAppStore();

  useEffect(() => {
    if (task.status === 'completed' || task.status === 'failed') {
      return;
    }

    // Poll task status every 2 seconds
    const interval = setInterval(async () => {
      try {
        const response = await mcpClient.callTool('tasks/get', {
          task_id: task.task_id,
        });

        const parsed = mcpClient.parseResponse(response);
        if (parsed.taskHandle) {
          updateTask(task.task_id, parsed.taskHandle);

          // Remove if completed/failed
          if (
            parsed.taskHandle.status === 'completed' ||
            parsed.taskHandle.status === 'failed'
          ) {
            setTimeout(() => removeTask(task.task_id), 3000);
          }
        }
      } catch (error) {
        console.error('[TaskProgress] Failed to poll task:', error);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [task.task_id, task.status, updateTask, removeTask]);

  const progressPercent = Math.round(task.progress * 100);
  const statusColor = {
    pending: 'bg-gray-400',
    running: 'bg-blue-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  }[task.status];

  return (
    <div className="task-progress mb-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${statusColor}`} />
          <span className="text-sm font-medium">
            {task.message || `Task ${task.task_id}`}
          </span>
        </div>
        <span className="text-sm text-gray-600">{progressPercent}%</span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full ${statusColor} transition-all duration-300`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* ETA */}
      {task.eta && task.status === 'running' && (
        <div className="text-xs text-gray-500 mt-1">
          ETA: {Math.round(task.eta / 60)} minutes
        </div>
      )}
    </div>
  );
};
