import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import React from 'react';

// WebSocket context types
interface WebSocketContextType {
  isConnected: boolean;
  sendMessage: (message: any) => void;
  subscribe: (event: string, callback: (data: any) => void) => () => void;
  subscribeToProject: (projectId: number, callback: (data: any) => void) => () => void;
}

interface WebSocketProviderProps {
  children: ReactNode;
}

// Create WebSocket context
const WebSocketContext = createContext<WebSocketContextType | null>(null);

// WebSocket provider component
export const WebSocketProvider = ({ children }: WebSocketProviderProps) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [subscribers, setSubscribers] = useState<Map<string, Set<(data: any) => void>>>(new Map());
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const maxReconnectAttempts = 5;

  const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

  const connect = useCallback(() => {
    try {
      const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const ws = new WebSocket(`${WS_URL}/ws/${clientId}`);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setReconnectAttempts(0);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const eventType = data.type || 'message';
          
          // Notify subscribers
          const eventSubscribers = subscribers.get(eventType);
          if (eventSubscribers) {
            eventSubscribers.forEach(callback => callback(data));
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        
        // Attempt to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, Math.pow(2, reconnectAttempts) * 1000);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      setSocket(ws);
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
    }
  }, [WS_URL, reconnectAttempts, subscribers, maxReconnectAttempts]);

  useEffect(() => {
    connect();
    
    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, [socket]);

  const subscribe = useCallback((event: string, callback: (data: any) => void) => {
    setSubscribers(prev => {
      const newSubscribers = new Map(prev);
      if (!newSubscribers.has(event)) {
        newSubscribers.set(event, new Set());
      }
      newSubscribers.get(event)!.add(callback);
      return newSubscribers;
    });

    // Return unsubscribe function
    return () => {
      setSubscribers(prev => {
        const newSubscribers = new Map(prev);
        const eventSubscribers = newSubscribers.get(event);
        if (eventSubscribers) {
          eventSubscribers.delete(callback);
          if (eventSubscribers.size === 0) {
            newSubscribers.delete(event);
          }
        }
        return newSubscribers;
      });
    };
  }, []);

  const subscribeToProject = useCallback((projectId: number, callback: (data: any) => void) => {
    return subscribe(`project_${projectId}`, callback);
  }, [subscribe]);

  const contextValue: WebSocketContextType = {
    isConnected,
    sendMessage,
    subscribe,
    subscribeToProject,
  };

  return React.createElement(
    WebSocketContext.Provider,
    { value: contextValue },
    children
  );
};

// Custom hooks for specific WebSocket events
export const useAgentRunUpdates = (projectId?: number) => {
  const { subscribe, subscribeToProject } = useWebSocket();
  const [agentRuns, setAgentRuns] = useState<any[]>([]);

  useEffect(() => {
    if (projectId) {
      const unsubscribe = subscribeToProject(projectId, (data) => {
        if (data.type === 'agent_run_update') {
          setAgentRuns(prev => {
            const updated = [...prev];
            const index = updated.findIndex(run => run.id === data.agent_run.id);
            if (index >= 0) {
              updated[index] = data.agent_run;
            } else {
              updated.push(data.agent_run);
            }
            return updated;
          });
        }
      });

      return unsubscribe;
    }
  }, [projectId, subscribe, subscribeToProject]);

  return agentRuns;
};

export const useValidationUpdates = (projectId?: number) => {
  const { subscribeToProject } = useWebSocket();
  const [validationStatus, setValidationStatus] = useState<any>(null);

  useEffect(() => {
    if (projectId) {
      const unsubscribe = subscribeToProject(projectId, (data) => {
        if (data.type === 'validation_update') {
          setValidationStatus(data.validation);
        }
      });

      return unsubscribe;
    }
  }, [projectId, subscribeToProject]);

  return validationStatus;
};

// Hook to use WebSocket context
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

