/**
 * Zustand store for workflow management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { 
  WorkflowRun, 
  WorkflowStatus, 
  ValidationStage, 
  ValidationRun,
  WorkflowProgress,
  WorkflowError,
  AgentRunType
} from '../types/cicd';

// ============================================================================
// STORE INTERFACE
// ============================================================================

interface WorkflowStore {
  // State
  activeWorkflows: Record<string, WorkflowRun>;
  workflowHistory: WorkflowRun[];
  loading: boolean;
  error: string | null;
  
  // Actions
  createWorkflow: (
    projectId: string,
    prompt: string,
    planningStatement: string,
    triggeredBy: 'manual' | 'webhook' | 'schedule',
    triggerData?: any
  ) => WorkflowRun;
  
  updateWorkflow: (workflowId: string, updates: Partial<WorkflowRun>) => void;
  updateWorkflowProgress: (workflowId: string, progress: Partial<WorkflowProgress>) => void;
  updateWorkflowStage: (workflowId: string, stage: ValidationStage) => void;
  setWorkflowError: (workflowId: string, error: WorkflowError) => void;
  completeWorkflow: (workflowId: string, success: boolean, result?: any) => void;
  cancelWorkflow: (workflowId: string) => void;
  
  // Agent run integration
  linkAgentRun: (workflowId: string, agentRunId: number) => void;
  updateAgentRunType: (workflowId: string, type: AgentRunType) => void;
  
  // Validation integration
  linkValidationRun: (workflowId: string, validationRun: ValidationRun) => void;
  updateValidationStage: (workflowId: string, stage: ValidationStage) => void;
  
  // History management
  moveToHistory: (workflowId: string) => void;
  clearHistory: () => void;
  getWorkflowHistory: (projectId?: string, limit?: number) => WorkflowRun[];
  
  // Utility actions
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  
  // Getters
  getWorkflow: (workflowId: string) => WorkflowRun | undefined;
  getActiveWorkflows: (projectId?: string) => WorkflowRun[];
  getWorkflowsByStatus: (status: WorkflowStatus) => WorkflowRun[];
  getWorkflowsByProject: (projectId: string) => WorkflowRun[];
}

// ============================================================================
// STORE IMPLEMENTATION
// ============================================================================

export const useWorkflowStore = create<WorkflowStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        activeWorkflows: {},
        workflowHistory: [],
        loading: false,
        error: null,

        // ====================================================================
        // WORKFLOW ACTIONS
        // ====================================================================

        createWorkflow: (
          projectId: string,
          prompt: string,
          planningStatement: string,
          triggeredBy: 'manual' | 'webhook' | 'schedule',
          triggerData?: any
        ) => {
          const workflowId = `wf_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          
          const workflow: WorkflowRun = {
            id: workflowId,
            projectId,
            status: WorkflowStatus.RUNNING,
            stage: ValidationStage.PENDING,
            startedAt: new Date().toISOString(),
            triggeredBy,
            triggerData,
            prompt,
            planningStatement,
            agentRunType: AgentRunType.REGULAR,
            progress: {
              currentStage: ValidationStage.PENDING,
              completedStages: [],
              totalStages: 8, // Based on VALIDATION_STAGES_ORDER
              percentage: 0,
              logs: []
            }
          };

          set(state => ({
            activeWorkflows: {
              ...state.activeWorkflows,
              [workflowId]: workflow
            }
          }));

          console.log(`Created workflow ${workflowId} for project ${projectId}`);
          return workflow;
        },

        updateWorkflow: (workflowId: string, updates: Partial<WorkflowRun>) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            return {
              activeWorkflows: {
                ...state.activeWorkflows,
                [workflowId]: {
                  ...workflow,
                  ...updates
                }
              }
            };
          });
        },

        updateWorkflowProgress: (workflowId: string, progress: Partial<WorkflowProgress>) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            const updatedProgress = {
              ...workflow.progress,
              ...progress
            };

            // Calculate percentage based on completed stages
            if (updatedProgress.completedStages && updatedProgress.totalStages) {
              updatedProgress.percentage = Math.round(
                (updatedProgress.completedStages.length / updatedProgress.totalStages) * 100
              );
            }

            return {
              activeWorkflows: {
                ...state.activeWorkflows,
                [workflowId]: {
                  ...workflow,
                  progress: updatedProgress
                }
              }
            };
          });
        },

        updateWorkflowStage: (workflowId: string, stage: ValidationStage) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            // Add current stage to completed stages if moving forward
            const completedStages = [...workflow.progress.completedStages];
            if (workflow.stage !== stage && !completedStages.includes(workflow.stage)) {
              completedStages.push(workflow.stage);
            }

            const updatedProgress = {
              ...workflow.progress,
              currentStage: stage,
              completedStages,
              percentage: Math.round((completedStages.length / workflow.progress.totalStages) * 100)
            };

            return {
              activeWorkflows: {
                ...state.activeWorkflows,
                [workflowId]: {
                  ...workflow,
                  stage,
                  progress: updatedProgress
                }
              }
            };
          });
        },

        setWorkflowError: (workflowId: string, error: WorkflowError) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            return {
              activeWorkflows: {
                ...state.activeWorkflows,
                [workflowId]: {
                  ...workflow,
                  status: WorkflowStatus.FAILED,
                  error,
                  completedAt: new Date().toISOString(),
                  duration: Date.now() - new Date(workflow.startedAt).getTime()
                }
              }
            };
          });
        },

        completeWorkflow: (workflowId: string, success: boolean, result?: any) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            const completedWorkflow = {
              ...workflow,
              status: success ? WorkflowStatus.COMPLETED : WorkflowStatus.FAILED,
              completedAt: new Date().toISOString(),
              duration: Date.now() - new Date(workflow.startedAt).getTime(),
              result
            };

            // Move to history
            const newHistory = [completedWorkflow, ...state.workflowHistory];
            
            // Keep only last 100 workflows in history
            if (newHistory.length > 100) {
              newHistory.splice(100);
            }

            // Remove from active workflows
            const newActiveWorkflows = { ...state.activeWorkflows };
            delete newActiveWorkflows[workflowId];

            return {
              activeWorkflows: newActiveWorkflows,
              workflowHistory: newHistory
            };
          });

          console.log(`Workflow ${workflowId} completed with success: ${success}`);
        },

        cancelWorkflow: (workflowId: string) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            const cancelledWorkflow = {
              ...workflow,
              status: WorkflowStatus.CANCELLED,
              completedAt: new Date().toISOString(),
              duration: Date.now() - new Date(workflow.startedAt).getTime()
            };

            // Move to history
            const newHistory = [cancelledWorkflow, ...state.workflowHistory];
            
            // Remove from active workflows
            const newActiveWorkflows = { ...state.activeWorkflows };
            delete newActiveWorkflows[workflowId];

            return {
              activeWorkflows: newActiveWorkflows,
              workflowHistory: newHistory
            };
          });

          console.log(`Workflow ${workflowId} cancelled`);
        },

        // ====================================================================
        // AGENT RUN INTEGRATION
        // ====================================================================

        linkAgentRun: (workflowId: string, agentRunId: number) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            return {
              activeWorkflows: {
                ...state.activeWorkflows,
                [workflowId]: {
                  ...workflow,
                  agentRunId
                }
              }
            };
          });
        },

        updateAgentRunType: (workflowId: string, type: AgentRunType) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            return {
              activeWorkflows: {
                ...state.activeWorkflows,
                [workflowId]: {
                  ...workflow,
                  agentRunType: type
                }
              }
            };
          });
        },

        // ====================================================================
        // VALIDATION INTEGRATION
        // ====================================================================

        linkValidationRun: (workflowId: string, validationRun: ValidationRun) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            return {
              activeWorkflows: {
                ...state.activeWorkflows,
                [workflowId]: {
                  ...workflow,
                  validationRun,
                  status: WorkflowStatus.VALIDATING
                }
              }
            };
          });
        },

        updateValidationStage: (workflowId: string, stage: ValidationStage) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow || !workflow.validationRun) return state;

            const updatedValidationRun = {
              ...workflow.validationRun,
              status: stage
            };

            return {
              activeWorkflows: {
                ...state.activeWorkflows,
                [workflowId]: {
                  ...workflow,
                  validationRun: updatedValidationRun,
                  stage
                }
              }
            };
          });
        },

        // ====================================================================
        // HISTORY MANAGEMENT
        // ====================================================================

        moveToHistory: (workflowId: string) => {
          set(state => {
            const workflow = state.activeWorkflows[workflowId];
            if (!workflow) return state;

            const newHistory = [workflow, ...state.workflowHistory];
            
            // Keep only last 100 workflows in history
            if (newHistory.length > 100) {
              newHistory.splice(100);
            }

            // Remove from active workflows
            const newActiveWorkflows = { ...state.activeWorkflows };
            delete newActiveWorkflows[workflowId];

            return {
              activeWorkflows: newActiveWorkflows,
              workflowHistory: newHistory
            };
          });
        },

        clearHistory: () => {
          set({ workflowHistory: [] });
        },

        getWorkflowHistory: (projectId?: string, limit: number = 50) => {
          const state = get();
          let history = state.workflowHistory;
          
          if (projectId) {
            history = history.filter(workflow => workflow.projectId === projectId);
          }
          
          return history.slice(0, limit);
        },

        // ====================================================================
        // UTILITY ACTIONS
        // ====================================================================

        clearError: () => {
          set({ error: null });
        },

        setLoading: (loading: boolean) => {
          set({ loading });
        },

        // ====================================================================
        // GETTERS
        // ====================================================================

        getWorkflow: (workflowId: string) => {
          const state = get();
          return state.activeWorkflows[workflowId] || 
                 state.workflowHistory.find(w => w.id === workflowId);
        },

        getActiveWorkflows: (projectId?: string) => {
          const state = get();
          const workflows = Object.values(state.activeWorkflows);
          
          if (projectId) {
            return workflows.filter(workflow => workflow.projectId === projectId);
          }
          
          return workflows;
        },

        getWorkflowsByStatus: (status: WorkflowStatus) => {
          const state = get();
          return Object.values(state.activeWorkflows).filter(workflow => 
            workflow.status === status
          );
        },

        getWorkflowsByProject: (projectId: string) => {
          const state = get();
          const active = Object.values(state.activeWorkflows).filter(w => w.projectId === projectId);
          const history = state.workflowHistory.filter(w => w.projectId === projectId);
          
          return [...active, ...history].sort((a, b) => 
            new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()
          );
        }
      }),
      {
        name: 'workflow-store',
        partialize: (state) => ({
          workflowHistory: state.workflowHistory
        })
      }
    ),
    {
      name: 'workflow-store'
    }
  )
);

// ============================================================================
// STORE HOOKS
// ============================================================================

/**
 * Hook to get workflow by ID
 */
export const useWorkflow = (workflowId: string | null) => {
  return useWorkflowStore(state => 
    workflowId ? state.getWorkflow(workflowId) : undefined
  );
};

/**
 * Hook to get active workflows for a project
 */
export const useActiveWorkflows = (projectId?: string) => {
  return useWorkflowStore(state => state.getActiveWorkflows(projectId));
};

/**
 * Hook to get workflows by status
 */
export const useWorkflowsByStatus = (status: WorkflowStatus) => {
  return useWorkflowStore(state => state.getWorkflowsByStatus(status));
};

/**
 * Hook to get workflow history
 */
export const useWorkflowHistory = (projectId?: string, limit?: number) => {
  return useWorkflowStore(state => state.getWorkflowHistory(projectId, limit));
};

/**
 * Hook for workflow actions
 */
export const useWorkflowActions = () => {
  return useWorkflowStore(state => ({
    createWorkflow: state.createWorkflow,
    updateWorkflow: state.updateWorkflow,
    updateWorkflowProgress: state.updateWorkflowProgress,
    updateWorkflowStage: state.updateWorkflowStage,
    setWorkflowError: state.setWorkflowError,
    completeWorkflow: state.completeWorkflow,
    cancelWorkflow: state.cancelWorkflow,
    linkAgentRun: state.linkAgentRun,
    updateAgentRunType: state.updateAgentRunType,
    linkValidationRun: state.linkValidationRun,
    updateValidationStage: state.updateValidationStage,
    moveToHistory: state.moveToHistory,
    clearHistory: state.clearHistory,
    clearError: state.clearError,
    setLoading: state.setLoading
  }));
};
