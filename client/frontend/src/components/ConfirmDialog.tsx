import React, { useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { mcpClient } from '@/services/mcpClient';

export const ConfirmDialog: React.FC = () => {
  const { pendingConfirmation, setPendingConfirmation, addMessage } = useAppStore();
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);

  if (!pendingConfirmation) return null;

  const handleConfirm = async () => {
    setLoading(true);

    try {
      // Call tool again with request_state and user input
      const response = await mcpClient.callTool('confirm_action', {
        request_state: pendingConfirmation.requestState,
        ...formData,
      });

      const parsed = mcpClient.parseResponse(response);
      
      addMessage({
        role: 'assistant',
        content: `Action confirmed: ${JSON.stringify(parsed.result)}`,
      });

      setPendingConfirmation(null);
    } catch (error) {
      addMessage({
        role: 'system',
        content: `Confirmation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setPendingConfirmation(null);
    addMessage({
      role: 'system',
      content: 'Action cancelled by user',
    });
  };

  return (
    <div className="confirm-dialog fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
        <h3 className="text-lg font-semibold mb-4">Confirmation Required</h3>
        
        <p className="text-gray-700 mb-4">{pendingConfirmation.message}</p>

        {/* Form Fields */}
        <div className="space-y-3 mb-6">
          {pendingConfirmation.fields.map((field) => (
            <div key={field.name}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label || field.name}
                {field.required && <span className="text-red-500">*</span>}
              </label>
              
              {field.type === 'boolean' ? (
                <input
                  type="checkbox"
                  checked={formData[field.name] || field.default || false}
                  onChange={(e) =>
                    setFormData({ ...formData, [field.name]: e.target.checked })
                  }
                  className="w-4 h-4"
                />
              ) : field.type === 'select' ? (
                <select
                  value={formData[field.name] || field.default || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, [field.name]: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  {field.options?.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.type === 'number' ? 'number' : 'text'}
                  value={formData[field.name] || field.default || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, [field.name]: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              )}
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={handleCancel}
            disabled={loading}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={loading}
            className="px-4 py-2 text-white bg-blue-500 rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Confirming...' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
};
