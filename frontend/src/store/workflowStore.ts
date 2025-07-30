/**
 * Workflow Store - Zustand store for workflow and agent run management
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { Workflow, AgentRun, AgentRunStatus, CreateAgentRunRequest } from '../types/cicd';
import { apiClient } from '../services/api';

interface WorkflowState {
  // State
  workflows: Record<string, Workflow>;
  activeWorkflows: Workflow[];
  agentRuns: Record<number, AgentRun>;
  recentAgentRuns: AgentRun[];
  loading: boolean;
  error: string | null;
  
  // Actions
  loadWorkflows: (projectId?: number) => Promise<void>;
  createAgentRun: (projectId: number, data: CreateAgentRunRequest) => Promise<AgentRun | null>;
  loadAgentRuns: (projectId?: number) => Promise<void>;
  refreshAgentRun: (id: number) => Promise<void>;
  cancelAgentRun: (id: number) => Promise<boolean>;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

export const useWorkflowStore = create<WorkflowState>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      // Initial state
      workflows: {},
      activeWorkflows: [],
      agentRuns: {},
      recentAgentRuns: [],
      loading: false,
      error: null,
      
      // Actions
      loadWorkflows: async (projectId?: number) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.getWorkflows(projectId);
          const workflows = response.items || [];
          const workflowsMap = workflows.reduce((acc: Record<string, Workflow>, workflow: Workflow) => {
            acc[workflow.id] = workflow;
            return acc;
          }, {});
          
          const activeWorkflows = workflows.filter((w: Workflow) => 
            w.status === 'running' || w.status === 'pending'
          );
          
          set({ 
            workflows: workflowsMap,
            activeWorkflows,
            loading: false 
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to load workflows';
          set({ 
            error: errorMessage, 
            loading: false 
          });
        }
      },
      
      createAgentRun: async (projectId: number, data: CreateAgentRunRequest) => {
        set({ loading: true, error: null });
        try {
          const agentRun = await apiClient.createAgentRun(projectId, data);
          const currentRuns = get().agentRuns;
          const newRuns = { ...currentRuns, [agentRun.id]: agentRun };
          
          // Update recent runs
          const recentRuns = Object.values(newRuns)
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .slice(0, 10);
          
          set({ 
            agentRuns: newRuns,
            recentAgentRuns: recentRuns,
            loading: false 
          });
          
          return agentRun;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to create agent run';
          set({ 
            error: errorMessage, 
            loading: false 
          });
          return null;
        }
      },
      
      loadAgentRuns: async (projectId?: number) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.getAgentRuns(projectId);
          const agentRuns = response.items || [];
          const runsMap = agentRuns.reduce((acc: Record<number, AgentRun>, run: AgentRun) => {
            acc[run.id] = run;
            return acc;
          }, {});
          
          // Get recent runs (last 10)
          const recentRuns = agentRuns
            .sort((a: AgentRun, b: AgentRun) => 
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            )
            .slice(0, 10);
          
          set({ 
            agentRuns: runsMap,
            recentAgentRuns: recentRuns,
            loading: false 
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to load agent runs';
          set({ 
            error: errorMessage, 
            loading: false 
          });
        }
      },
      
      refreshAgentRun: async (id: number) => {
        try {
          const agentRun = await apiClient.getAgentRun(id);
          const currentRuns = get().agentRuns;
          const newRuns = { ...currentRuns, [id]: agentRun };
          
          // Update recent runs
          const recentRuns = Object.values(newRuns)
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .slice(0, 10);
          
          set({ 
            agentRuns: newRuns,
            recentAgentRuns: recentRuns
          });
        } catch (error) {
          console.error('Failed to refresh agent run:', error);
        }
      },
      
      cancelAgentRun: async (id: number) => {
        try {
          await apiClient.cancelAgentRun(id);
          const currentRuns = get().agentRuns;
          const updatedRun = { 
            ...currentRuns[id], 
            status: AgentRunStatus.CANCELLED 
          };
          const newRuns = { ...currentRuns, [id]: updatedRun };
          
          // Update recent runs
          const recentRuns = Object.values(newRuns)
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .slice(0, 10);
          
          set({ 
            agentRuns: newRuns,
            recentAgentRuns: recentRuns
          });
          
          return true;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to cancel agent run';
          set({ error: errorMessage });
          return false;
        }
      },
      
      clearError: () => {
        set({ error: null });
      },
      
      setLoading: (loading: boolean) => {
        set({ loading });
      }
    })),
    {
      name: 'workflow-store',
    }
  )
);

// Selector hooks
export const useWorkflows = () => useWorkflowStore(state => state.workflows);
export const useActiveWorkflows = () => useWorkflowStore(state => state.activeWorkflows);
export const useAgentRuns = () => useWorkflowStore(state => state.agentRuns);
export const useRecentAgentRuns = () => useWorkflowStore(state => state.recentAgentRuns);
export const useWorkflowLoading = () => useWorkflowStore(state => state.loading);
export const useWorkflowError = () => useWorkflowStore(state => state.error);

// Action hooks
export const useWorkflowActions = () => useWorkflowStore(state => ({
  loadWorkflows: state.loadWorkflows,
  createAgentRun: state.createAgentRun,
  loadAgentRuns: state.loadAgentRuns,
  refreshAgentRun: state.refreshAgentRun,
  cancelAgentRun: state.cancelAgentRun,
  clearError: state.clearError,
  setLoading: state.setLoading
}));

