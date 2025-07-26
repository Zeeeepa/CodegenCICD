/**
 * Dashboard Context for Global State Management
 */

import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import toast from 'react-hot-toast';

import {
  Project,
  AgentRun,
  DashboardState,
  UIState,
  CreateProjectRequest,
  CreateAgentRunRequest,
  ResumeAgentRunRequest,
} from '../types/api';
import apiService from '../services/apiService';
import { useWebSocket } from '../hooks/useWebSocket';

// Action Types
type DashboardAction =
  | { type: 'SET_PROJECTS'; payload: Project[] }
  | { type: 'SET_SELECTED_PROJECT'; payload: Project | undefined }
  | { type: 'SET_AGENT_RUNS'; payload: AgentRun[] }
  | { type: 'SET_ACTIVE_AGENT_RUN'; payload: AgentRun | undefined }
  | { type: 'UPDATE_AGENT_RUN'; payload: AgentRun }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | undefined }
  | { type: 'SET_WEBSOCKET_CONNECTED'; payload: boolean }
  | { type: 'UPDATE_UI_STATE'; payload: Partial<UIState> };

// Initial States
const initialDashboardState: DashboardState = {
  projects: [],
  selectedProject: undefined,
  agentRuns: [],
  activeAgentRun: undefined,
  isLoading: false,
  error: undefined,
  websocketConnected: false,
};

const initialUIState: UIState = {
  sidebarOpen: true,
  selectedTab: 'overview',
  dialogOpen: {
    agentRun: false,
    settings: false,
    createProject: false,
  },
  notifications: [],
};

// Reducers
const dashboardReducer = (state: DashboardState, action: DashboardAction): DashboardState => {
  switch (action.type) {
    case 'SET_PROJECTS':
      return { ...state, projects: action.payload };
    case 'SET_SELECTED_PROJECT':
      return { ...state, selectedProject: action.payload };
    case 'SET_AGENT_RUNS':
      return { ...state, agentRuns: action.payload };
    case 'SET_ACTIVE_AGENT_RUN':
      return { ...state, activeAgentRun: action.payload };
    case 'UPDATE_AGENT_RUN':
      return {
        ...state,
        agentRuns: state.agentRuns.map(run =>
          run.id === action.payload.id ? action.payload : run
        ),
        activeAgentRun: state.activeAgentRun?.id === action.payload.id ? action.payload : state.activeAgentRun,
      };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_WEBSOCKET_CONNECTED':
      return { ...state, websocketConnected: action.payload };
    default:
      return state;
  }
};

const uiReducer = (state: UIState, action: DashboardAction): UIState => {
  switch (action.type) {
    case 'UPDATE_UI_STATE':
      return { ...state, ...action.payload };
    default:
      return state;
  }
};

// Context Types
interface DashboardContextType {
  // State
  dashboardState: DashboardState;
  uiState: UIState;
  
  // Actions
  setSelectedProject: (project: Project | undefined) => void;
  setActiveAgentRun: (agentRun: AgentRun | undefined) => void;
  updateUIState: (updates: Partial<UIState>) => void;
  
  // API Actions
  createProject: (project: CreateProjectRequest) => Promise<Project>;
  createAgentRun: (agentRun: CreateAgentRunRequest) => Promise<AgentRun>;
  resumeAgentRun: (resumeRequest: ResumeAgentRunRequest) => Promise<AgentRun>;
  
  // Queries
  projectsQuery: any;
  agentRunsQuery: any;
  
  // WebSocket
  websocketState: any;
}

// Create Context
const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

// Provider Component
interface DashboardProviderProps {
  children: ReactNode;
}

export const DashboardProvider: React.FC<DashboardProviderProps> = ({ children }) => {
  const [dashboardState, dashboardDispatch] = useReducer(dashboardReducer, initialDashboardState);
  const [uiState, uiDispatch] = useReducer(uiReducer, initialUIState);
  const queryClient = useQueryClient();

  // WebSocket connection
  const websocketState = useWebSocket({
    onConnect: () => {
      dashboardDispatch({ type: 'SET_WEBSOCKET_CONNECTED', payload: true });
      toast.success('Connected to real-time updates');
    },
    onDisconnect: () => {
      dashboardDispatch({ type: 'SET_WEBSOCKET_CONNECTED', payload: false });
    },
    onMessage: (message) => {
      if (message.type === 'agent_run_update') {
        const agentRunUpdate = message.data;
        // Update the agent run in state
        queryClient.invalidateQueries(['agentRuns']);
        if (dashboardState.activeAgentRun?.id === agentRunUpdate.agent_run_id) {
          queryClient.invalidateQueries(['agentRun', agentRunUpdate.agent_run_id]);
        }
      }
    },
    onError: () => {
      toast.error('Connection error - some features may not work');
    },
  });

  // Queries
  const projectsQuery = useQuery(
    ['projects'],
    () => apiService.getProjects(),
    {
      onSuccess: (data) => {
        dashboardDispatch({ type: 'SET_PROJECTS', payload: data });
      },
      onError: (error: any) => {
        dashboardDispatch({ type: 'SET_ERROR', payload: error.message });
        toast.error('Failed to load projects');
      },
    }
  );

  const agentRunsQuery = useQuery(
    ['agentRuns', dashboardState.selectedProject?.id],
    () => apiService.getAgentRuns(dashboardState.selectedProject?.id),
    {
      enabled: !!dashboardState.selectedProject,
      onSuccess: (data) => {
        dashboardDispatch({ type: 'SET_AGENT_RUNS', payload: data });
      },
      onError: (error: any) => {
        toast.error('Failed to load agent runs');
      },
    }
  );

  // Mutations
  const createProjectMutation = useMutation(
    (project: CreateProjectRequest) => apiService.createProject(project),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['projects']);
        toast.success('Project created successfully');
      },
      onError: (error: any) => {
        toast.error(`Failed to create project: ${error.message}`);
      },
    }
  );

  const createAgentRunMutation = useMutation(
    (agentRun: CreateAgentRunRequest) => apiService.createAgentRun(agentRun),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['agentRuns']);
        dashboardDispatch({ type: 'SET_ACTIVE_AGENT_RUN', payload: data });
        toast.success('Agent run started successfully');
      },
      onError: (error: any) => {
        toast.error(`Failed to start agent run: ${error.message}`);
      },
    }
  );

  const resumeAgentRunMutation = useMutation(
    (resumeRequest: ResumeAgentRunRequest) => apiService.resumeAgentRun(resumeRequest),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['agentRuns']);
        dashboardDispatch({ type: 'UPDATE_AGENT_RUN', payload: data });
        toast.success('Agent run resumed successfully');
      },
      onError: (error: any) => {
        toast.error(`Failed to resume agent run: ${error.message}`);
      },
    }
  );

  // Actions
  const setSelectedProject = (project: Project | undefined) => {
    dashboardDispatch({ type: 'SET_SELECTED_PROJECT', payload: project });
  };

  const setActiveAgentRun = (agentRun: AgentRun | undefined) => {
    dashboardDispatch({ type: 'SET_ACTIVE_AGENT_RUN', payload: agentRun });
  };

  const updateUIState = (updates: Partial<UIState>) => {
    uiDispatch({ type: 'UPDATE_UI_STATE', payload: updates });
  };

  const createProject = async (project: CreateProjectRequest): Promise<Project> => {
    return createProjectMutation.mutateAsync(project);
  };

  const createAgentRun = async (agentRun: CreateAgentRunRequest): Promise<AgentRun> => {
    return createAgentRunMutation.mutateAsync(agentRun);
  };

  const resumeAgentRun = async (resumeRequest: ResumeAgentRunRequest): Promise<AgentRun> => {
    return resumeAgentRunMutation.mutateAsync(resumeRequest);
  };

  // Update loading state based on mutations
  useEffect(() => {
    const isLoading = createProjectMutation.isLoading || 
                    createAgentRunMutation.isLoading || 
                    resumeAgentRunMutation.isLoading ||
                    projectsQuery.isLoading ||
                    agentRunsQuery.isLoading;
    
    dashboardDispatch({ type: 'SET_LOADING', payload: isLoading });
  }, [
    createProjectMutation.isLoading,
    createAgentRunMutation.isLoading,
    resumeAgentRunMutation.isLoading,
    projectsQuery.isLoading,
    agentRunsQuery.isLoading,
  ]);

  const contextValue: DashboardContextType = {
    dashboardState,
    uiState,
    setSelectedProject,
    setActiveAgentRun,
    updateUIState,
    createProject,
    createAgentRun,
    resumeAgentRun,
    projectsQuery,
    agentRunsQuery,
    websocketState,
  };

  return (
    <DashboardContext.Provider value={contextValue}>
      {children}
    </DashboardContext.Provider>
  );
};

// Hook to use Dashboard Context
export const useDashboard = (): DashboardContextType => {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
};
