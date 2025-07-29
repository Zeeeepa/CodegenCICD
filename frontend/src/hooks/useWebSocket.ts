import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';

interface WebSocketMessage {
  type: string;
  project_id?: number;
  agent_run_id?: number;
  data?: any;
  timestamp?: string;
}

interface WebSocketContextType {
  isConnected: boolean;
  sendMessage: (message: WebSocketMessage) => void;
  subscribe: (type: string, callback: (data: any) => void) => () => void;
  subscribeToProject: (projectId: number, callback: (data: any) => void) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
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
        
        // Send initial connection message
        ws.send(JSON.stringify({
          type: 'connection',
          timestamp: new Date().toISOString()
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('WebSocket message received:', message);

          // Notify subscribers based on message type
          const typeSubscribers = subscribers.get(message.type);
          if (typeSubscribers) {
            typeSubscribers.forEach(callback => callback(message.data));
          }

          // Notify project-specific subscribers
          if (message.project_id) {
            const projectSubscribers = subscribers.get(`project_${message.project_id}`);
            if (projectSubscribers) {
              projectSubscribers.forEach(callback => callback(message));
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setSocket(null);

        // Attempt to reconnect if not a manual close
        if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
          const timeout = Math.pow(2, reconnectAttempts) * 1000; // Exponential backoff
          console.log(`Attempting to reconnect in ${timeout}ms...`);
          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, timeout);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      setSocket(ws);
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [WS_URL, reconnectAttempts, subscribers]);

  useEffect(() => {
    connect();

    return () => {
      if (socket) {
        socket.close(1000, 'Component unmounting');
      }
    };
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        ...message,
        timestamp: new Date().toISOString()
      }));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }, [socket]);

  const subscribe = useCallback((type: string, callback: (data: any) => void) => {
    setSubscribers(prev => {
      const newSubscribers = new Map(prev);
      if (!newSubscribers.has(type)) {
        newSubscribers.set(type, new Set());
      }
      newSubscribers.get(type)!.add(callback);
      return newSubscribers;
    });

    // Return unsubscribe function
    return () => {
      setSubscribers(prev => {
        const newSubscribers = new Map(prev);
        const typeSubscribers = newSubscribers.get(type);
        if (typeSubscribers) {
          typeSubscribers.delete(callback);
          if (typeSubscribers.size === 0) {
            newSubscribers.delete(type);
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

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Custom hooks for specific WebSocket events
export const useAgentRunUpdates = (projectId?: number) => {
  const { subscribe, subscribeToProject } = useWebSocket();
  const [agentRuns, setAgentRuns] = useState<any[]>([]);

  useEffect(() => {
    const unsubscribeGeneral = subscribe('agent_run_update', (data) => {
      setAgentRuns(prev => {
        const index = prev.findIndex(run => run.id === data.id);
        if (index >= 0) {
          const newRuns = [...prev];
          newRuns[index] = { ...newRuns[index], ...data };
          return newRuns;
        } else {
          return [...prev, data];
        }
      });
    });

    let unsubscribeProject: (() => void) | undefined;
    if (projectId) {
      unsubscribeProject = subscribeToProject(projectId, (message) => {
        if (message.type === 'agent_run_update') {
          setAgentRuns(prev => {
            const index = prev.findIndex(run => run.id === message.data.id);
            if (index >= 0) {
              const newRuns = [...prev];
              newRuns[index] = { ...newRuns[index], ...message.data };
              return newRuns;
            } else {
              return [...prev, message.data];
            }
          });
        }
      });
    }

    return () => {
      unsubscribeGeneral();
      if (unsubscribeProject) {
        unsubscribeProject();
      }
    };
  }, [subscribe, subscribeToProject, projectId]);

  return agentRuns;
};

export const useValidationUpdates = (agentRunId?: number) => {
  const { subscribe } = useWebSocket();
  const [validationStatus, setValidationStatus] = useState<any>(null);

  useEffect(() => {
    const unsubscribe = subscribe('validation_update', (data) => {
      if (!agentRunId || data.agent_run_id === agentRunId) {
        setValidationStatus(data);
      }
    });

    return unsubscribe;
  }, [subscribe, agentRunId]);

  return validationStatus;
};

export const usePRNotifications = (projectId?: number) => {
  const { subscribe, subscribeToProject } = useWebSocket();
  const [prNotifications, setPRNotifications] = useState<any[]>([]);

  useEffect(() => {
    const unsubscribeGeneral = subscribe('pr_notification', (data) => {
      setPRNotifications(prev => [...prev, data]);
    });

    let unsubscribeProject: (() => void) | undefined;
    if (projectId) {
      unsubscribeProject = subscribeToProject(projectId, (message) => {
        if (message.type === 'pr_notification') {
          setPRNotifications(prev => [...prev, message.data]);
        }
      });
    }

    return () => {
      unsubscribeGeneral();
      if (unsubscribeProject) {
        unsubscribeProject();
      }
    };
  }, [subscribe, subscribeToProject, projectId]);

  return prNotifications;
};

