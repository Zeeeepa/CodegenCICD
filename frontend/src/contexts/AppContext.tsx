import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import {
  Project,
  AgentRun,
  ValidationRun,
  Notification,
  WebSocketMessage,
  WebSocketMessageType,
  NotificationType
} from '../types';
import { webSocketService } from '../services/websocket';
import { apiService } from '../services/api';

// State interface
interface AppState {
  projects: Project[];
  agentRuns: AgentRun[];
  validationRuns: ValidationRun[];
  notifications: Notification[];
  loading: boolean;
  error: string | null;
  wsConnected: boolean;
}

// Action types
type AppAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_PROJECTS'; payload: Project[] }
  | { type: 'ADD_PROJECT'; payload: Project }
  | { type: 'UPDATE_PROJECT'; payload: Project }
  | { type: 'DELETE_PROJECT'; payload: string }
  | { type: 'SET_AGENT_RUNS'; payload: AgentRun[] }
  | { type: 'ADD_AGENT_RUN'; payload: AgentRun }
  | { type: 'UPDATE_AGENT_RUN'; payload: AgentRun }
  | { type: 'SET_VALIDATION_RUNS'; payload: ValidationRun[] }
  | { type: 'ADD_VALIDATION_RUN'; payload: ValidationRun }
  | { type: 'UPDATE_VALIDATION_RUN'; payload: ValidationRun }
  | { type: 'ADD_NOTIFICATION'; payload: Notification }
  | { type: 'REMOVE_NOTIFICATION'; payload: string }
  | { type: 'MARK_NOTIFICATION_READ'; payload: string }
  | { type: 'SET_WS_CONNECTED'; payload: boolean };

// Initial state
const initialState: AppState = {
  projects: [],
  agentRuns: [],
  validationRuns: [],
  notifications: [],
  loading: false,
  error: null,
  wsConnected: false
};

// Reducer
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    
    case 'SET_PROJECTS':
      return { ...state, projects: action.payload };
    
    case 'ADD_PROJECT':
      return { ...state, projects: [...state.projects, action.payload] };
    
    case 'UPDATE_PROJECT':
      return {
        ...state,
        projects: state.projects.map(p => 
          p.id === action.payload.id ? action.payload : p
        )
      };
    
    case 'DELETE_PROJECT':
      return {
        ...state,
        projects: state.projects.filter(p => p.id !== action.payload)
      };
    
    case 'SET_AGENT_RUNS':
      return { ...state, agentRuns: action.payload };
    
    case 'ADD_AGENT_RUN':
      return { ...state, agentRuns: [...state.agentRuns, action.payload] };
    
    case 'UPDATE_AGENT_RUN':
      return {
        ...state,
        agentRuns: state.agentRuns.map(run => 
          run.id === action.payload.id ? action.payload : run
        )
      };
    
    case 'SET_VALIDATION_RUNS':
      return { ...state, validationRuns: action.payload };
    
    case 'ADD_VALIDATION_RUN':
      return { ...state, validationRuns: [...state.validationRuns, action.payload] };
    
    case 'UPDATE_VALIDATION_RUN':
      return {
        ...state,
        validationRuns: state.validationRuns.map(run => 
          run.id === action.payload.id ? action.payload : run
        )
      };
    
    case 'ADD_NOTIFICATION':
      return { ...state, notifications: [action.payload, ...state.notifications] };
    
    case 'REMOVE_NOTIFICATION':
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload)
      };
    
    case 'MARK_NOTIFICATION_READ':
      return {
        ...state,
        notifications: state.notifications.map(n => 
          n.id === action.payload ? { ...n, read: true } : n
        )
      };
    
    case 'SET_WS_CONNECTED':
      return { ...state, wsConnected: action.payload };
    
    default:
      return state;
  }
}

// Context interface
interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  // Action creators
  loadProjects: () => Promise<void>;
  createProject: (project: any) => Promise<void>;
  updateProject: (id: string, updates: any) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  loadAgentRuns: (projectId?: string) => Promise<void>;
  createAgentRun: (projectId: string, data: any) => Promise<void>;
  resumeAgentRun: (id: string, prompt: string) => Promise<void>;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  removeNotification: (id: string) => void;
  markNotificationRead: (id: string) => void;
}

// Create context
const AppContext = createContext<AppContextType | undefined>(undefined);

// Provider component
interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // WebSocket event handlers
  useEffect(() => {
    const handleAgentRunUpdate = (message: WebSocketMessage) => {
      if (message.data) {
        dispatch({ type: 'UPDATE_AGENT_RUN', payload: message.data });
      }
    };

    const handleValidationUpdate = (message: WebSocketMessage) => {
      if (message.data) {
        dispatch({ type: 'UPDATE_VALIDATION_RUN', payload: message.data });
      }
    };

    const handlePRNotification = (message: WebSocketMessage) => {
      if (message.data) {
        addNotification({
          type: NotificationType.INFO,
          title: 'Pull Request Created',
          message: `PR #${message.data.pr_number} created for project ${message.data.project_name}`,
          project_id: message.data.project_id,
          agent_run_id: message.data.agent_run_id
        });
      }
    };

    const handleProjectUpdate = (message: WebSocketMessage) => {
      if (message.data) {
        dispatch({ type: 'UPDATE_PROJECT', payload: message.data });
      }
    };

    const handleNotification = (message: WebSocketMessage) => {
      if (message.data) {
        addNotification(message.data);
      }
    };

    const handleError = (message: WebSocketMessage) => {
      console.error('WebSocket error:', message.data);
      dispatch({ type: 'SET_ERROR', payload: message.data?.message || 'WebSocket error' });
    };

    // Subscribe to WebSocket events
    webSocketService.on(WebSocketMessageType.AGENT_RUN_UPDATE, handleAgentRunUpdate);
    webSocketService.on(WebSocketMessageType.VALIDATION_UPDATE, handleValidationUpdate);
    webSocketService.on(WebSocketMessageType.PR_NOTIFICATION, handlePRNotification);
    webSocketService.on(WebSocketMessageType.PROJECT_UPDATE, handleProjectUpdate);
    webSocketService.on(WebSocketMessageType.NOTIFICATION, handleNotification);
    webSocketService.on(WebSocketMessageType.ERROR, handleError);

    // Connect to WebSocket
    webSocketService.connect()
      .then(() => {
        dispatch({ type: 'SET_WS_CONNECTED', payload: true });
      })
      .catch((error) => {
        console.error('Failed to connect to WebSocket:', error);
        dispatch({ type: 'SET_WS_CONNECTED', payload: false });
      });

    // Cleanup
    return () => {
      webSocketService.off(WebSocketMessageType.AGENT_RUN_UPDATE, handleAgentRunUpdate);
      webSocketService.off(WebSocketMessageType.VALIDATION_UPDATE, handleValidationUpdate);
      webSocketService.off(WebSocketMessageType.PR_NOTIFICATION, handlePRNotification);
      webSocketService.off(WebSocketMessageType.PROJECT_UPDATE, handleProjectUpdate);
      webSocketService.off(WebSocketMessageType.NOTIFICATION, handleNotification);
      webSocketService.off(WebSocketMessageType.ERROR, handleError);
      webSocketService.disconnect();
    };
  }, []);

  // Action creators
  const loadProjects = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const projects = await apiService.getProjects();
      dispatch({ type: 'SET_PROJECTS', payload: projects });
      dispatch({ type: 'SET_ERROR', payload: null });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to load projects' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const createProject = async (projectData: any) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const project = await apiService.createProject(projectData);
      dispatch({ type: 'ADD_PROJECT', payload: project });
      
      // Subscribe to project updates
      webSocketService.subscribeToProject(project.id);
      
      addNotification({
        type: NotificationType.SUCCESS,
        title: 'Project Created',
        message: `Project "${project.name}" has been created successfully`
      });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to create project' });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const updateProject = async (id: string, updates: any) => {
    try {
      const project = await apiService.updateProject(id, updates);
      dispatch({ type: 'UPDATE_PROJECT', payload: project });
      
      addNotification({
        type: NotificationType.SUCCESS,
        title: 'Project Updated',
        message: `Project "${project.name}" has been updated successfully`
      });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to update project' });
      throw error;
    }
  };

  const deleteProject = async (id: string) => {
    try {
      await apiService.deleteProject(id);
      dispatch({ type: 'DELETE_PROJECT', payload: id });
      
      // Unsubscribe from project updates
      webSocketService.unsubscribeFromProject(id);
      
      addNotification({
        type: NotificationType.SUCCESS,
        title: 'Project Deleted',
        message: 'Project has been deleted successfully'
      });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to delete project' });
      throw error;
    }
  };

  const loadAgentRuns = async (projectId?: string) => {
    try {
      const agentRuns = await apiService.getAgentRuns(projectId);
      dispatch({ type: 'SET_AGENT_RUNS', payload: agentRuns });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to load agent runs' });
    }
  };

  const createAgentRun = async (projectId: string, data: any) => {
    try {
      const agentRun = await apiService.createAgentRun(projectId, data);
      dispatch({ type: 'ADD_AGENT_RUN', payload: agentRun });
      
      addNotification({
        type: NotificationType.INFO,
        title: 'Agent Run Started',
        message: 'Agent run has been started successfully',
        project_id: projectId,
        agent_run_id: agentRun.id
      });
      
      return agentRun;
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to create agent run' });
      throw error;
    }
  };

  const resumeAgentRun = async (id: string, prompt: string) => {
    try {
      const agentRun = await apiService.resumeAgentRun(id, prompt);
      dispatch({ type: 'UPDATE_AGENT_RUN', payload: agentRun });
      
      addNotification({
        type: NotificationType.INFO,
        title: 'Agent Run Resumed',
        message: 'Agent run has been resumed with new input',
        agent_run_id: id
      });
      
      return agentRun;
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to resume agent run' });
      throw error;
    }
  };

  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const fullNotification: Notification = {
      ...notification,
      id: `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      read: false
    };
    dispatch({ type: 'ADD_NOTIFICATION', payload: fullNotification });
  };

  const removeNotification = (id: string) => {
    dispatch({ type: 'REMOVE_NOTIFICATION', payload: id });
  };

  const markNotificationRead = (id: string) => {
    dispatch({ type: 'MARK_NOTIFICATION_READ', payload: id });
  };

  const contextValue: AppContextType = {
    state,
    dispatch,
    loadProjects,
    createProject,
    updateProject,
    deleteProject,
    loadAgentRuns,
    createAgentRun,
    resumeAgentRun,
    addNotification,
    removeNotification,
    markNotificationRead
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}

// Hook to use the context
export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

export default AppContext;
