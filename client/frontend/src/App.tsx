import { useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { useAppStore } from './store/appStore';
import { wsService } from './services/websocket';
import { mcpClient } from './services/mcpClient';

function App() {
  const { setConnected } = useAppStore();

  useEffect(() => {
    // Connect to WebSocket
    const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000/ws';

    wsService
      .connect(WS_URL)
      .then(() => {
        console.log('[App] WebSocket connected');
        setConnected(true);
        // Re-register message handler after connection
        mcpClient.reregisterHandler();
      })
      .catch((error) => {
        console.error('[App] WebSocket connection failed:', error);
        setConnected(false);
      });

    // Cleanup
    return () => {
      wsService.disconnect();
    };
  }, [setConnected]);

  return (
    <div className="App">
      <ChatInterface />
    </div>
  );
}

export default App;
