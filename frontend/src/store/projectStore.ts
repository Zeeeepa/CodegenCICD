/**
 * Zustand store for project management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { Project, ProjectSettings, ProjectStatus, WorkflowRun, Notification } from '../types/cicd';
import { projectService } from '../services/projectService';

// ============================================================================
// STORE INTERFACE
// ============================================================================

interface ProjectStore {
  // State
  projects: Record<string, Project>;
  selectedProjectId: string | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  loadProjects: () => Promise<void>;
  createProject: (repoFullName: string) => Promise<Project>;
  updateProject: (projectId: string, updates: Partial<Project>) => Promise<void>;
  deleteProject: (projectId: string) => Promise<void>;
  selectProject: (projectId: string | null) => void;
  
  // Settings actions
  updateSettings: (projectId: string, settings: Partial<ProjectSettings>) => Promise<void>;
  updateSecret: (projectId: string, key: string, value: string) => Promise<void>;
  removeSecret: (projectId: string, key: string) => Promise<void>;
  testSetupCommands: (projectId: string, commands: string, branch?: string) => Promise<{
    success: boolean;
    output: string;
    error?: string;
  }>;
  
  // Data refresh
  refreshProject: (projectId: string) => Promise<void>;
  refreshAllProjects: () => Promise<void>;
  
  // Utility actions
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  
  // Getters
  getProject: (projectId: string) => Project | undefined;
  getSelectedProject: () => Project | undefined;
  getActiveProjects: () => Project[];
  getProjectsByStatus: (status: ProjectStatus) => Project[];
}

// ============================================================================
// STORE IMPLEMENTATION
// ============================================================================

export const useProjectStore = create<ProjectStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        projects: {},
        selectedProjectId: null,
        loading: false,
        error: null,

        // ====================================================================
        // PROJECT ACTIONS
        // ====================================================================

        loadProjects: async () => {
          set({ loading: true, error: null });
          
          try {
            const projects = projectService.getAllProjects();
            const projectsMap = projects.reduce((acc, project) => {
              acc[project.id] = project;
              return acc;
            }, {} as Record<string, Project>);
            
            set({ projects: projectsMap, loading: false });
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to load projects';
            set({ error: errorMessage, loading: false });
            console.error('Failed to load projects:', error);
          }
        },

        createProject: async (repoFullName: string) => {
          set({ loading: true, error: null });
          
          try {
            const project = await projectService.createProject(repoFullName);
            
            set(state => ({
              projects: {
                ...state.projects,
                [project.id]: project
              },
              selectedProjectId: project.id,
              loading: false
            }));
            
            return project;
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to create project';
            set({ error: errorMessage, loading: false });
            throw error;
          }
        },

        updateProject: async (projectId: string, updates: Partial<Project>) => {
          try {
            const updatedProject = await projectService.updateProject(projectId, updates);
            
            set(state => ({
              projects: {
                ...state.projects,
                [projectId]: updatedProject
              }
            }));
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to update project';
            set({ error: errorMessage });
            throw error;
          }
        },

        deleteProject: async (projectId: string) => {
          set({ loading: true, error: null });
          
          try {
            await projectService.deleteProject(projectId);
            
            set(state => {
              const newProjects = { ...state.projects };
              delete newProjects[projectId];
              
              return {
                projects: newProjects,
                selectedProjectId: state.selectedProjectId === projectId ? null : state.selectedProjectId,
                loading: false
              };
            });
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete project';
            set({ error: errorMessage, loading: false });
            throw error;
          }
        },

        selectProject: (projectId: string | null) => {
          set({ selectedProjectId: projectId });
        },

        // ====================================================================
        // SETTINGS ACTIONS
        // ====================================================================

        updateSettings: async (projectId: string, settings: Partial<ProjectSettings>) => {
          try {
            const updatedProject = await projectService.updateSettings(projectId, settings);
            
            set(state => ({
              projects: {
                ...state.projects,
                [projectId]: updatedProject
              }
            }));
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to update settings';
            set({ error: errorMessage });
            throw error;
          }
        },

        updateSecret: async (projectId: string, key: string, value: string) => {
          try {
            await projectService.updateSecret(projectId, key, value);
            
            // Refresh project to get updated secrets
            const updatedProject = projectService.getProject(projectId);
            if (updatedProject) {
              set(state => ({
                projects: {
                  ...state.projects,
                  [projectId]: updatedProject
                }
              }));
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to update secret';
            set({ error: errorMessage });
            throw error;
          }
        },

        removeSecret: async (projectId: string, key: string) => {
          try {
            await projectService.removeSecret(projectId, key);
            
            // Refresh project to get updated secrets
            const updatedProject = projectService.getProject(projectId);
            if (updatedProject) {
              set(state => ({
                projects: {
                  ...state.projects,
                  [projectId]: updatedProject
                }
              }));
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to remove secret';
            set({ error: errorMessage });
            throw error;
          }
        },

        testSetupCommands: async (projectId: string, commands: string, branch?: string) => {
          try {
            return await projectService.testSetupCommands(projectId, commands, branch);
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to test setup commands';
            set({ error: errorMessage });
            throw error;
          }
        },

        // ====================================================================
        // DATA REFRESH
        // ====================================================================

        refreshProject: async (projectId: string) => {
          try {
            const refreshedProject = await projectService.refreshProject(projectId);
            
            set(state => ({
              projects: {
                ...state.projects,
                [projectId]: refreshedProject
              }
            }));
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to refresh project';
            set({ error: errorMessage });
            throw error;
          }
        },

        refreshAllProjects: async () => {
          set({ loading: true, error: null });
          
          try {
            const state = get();
            const projectIds = Object.keys(state.projects);
            
            // Refresh all projects in parallel
            const refreshPromises = projectIds.map(id => projectService.refreshProject(id));
            const refreshedProjects = await Promise.allSettled(refreshPromises);
            
            // Update successful refreshes
            const updatedProjects = { ...state.projects };
            refreshedProjects.forEach((result, index) => {
              if (result.status === 'fulfilled') {
                const projectId = projectIds[index];
                updatedProjects[projectId] = result.value;
              }
            });
            
            set({ projects: updatedProjects, loading: false });
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to refresh projects';
            set({ error: errorMessage, loading: false });
            throw error;
          }
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

        getProject: (projectId: string) => {
          const state = get();
          return state.projects[projectId];
        },

        getSelectedProject: () => {
          const state = get();
          return state.selectedProjectId ? state.projects[state.selectedProjectId] : undefined;
        },

        getActiveProjects: () => {
          const state = get();
          return Object.values(state.projects).filter(project => 
            project.status === ProjectStatus.ACTIVE
          );
        },

        getProjectsByStatus: (status: ProjectStatus) => {
          const state = get();
          return Object.values(state.projects).filter(project => 
            project.status === status
          );
        }
      }),
      {
        name: 'project-store',
        partialize: (state) => ({
          projects: state.projects,
          selectedProjectId: state.selectedProjectId
        })
      }
    ),
    {
      name: 'project-store'
    }
  )
);

// ============================================================================
// STORE HOOKS
// ============================================================================

/**
 * Hook to get project by ID
 */
export const useProject = (projectId: string | null) => {
  return useProjectStore(state => 
    projectId ? state.projects[projectId] : undefined
  );
};

/**
 * Hook to get selected project
 */
export const useSelectedProject = () => {
  return useProjectStore(state => 
    state.selectedProjectId ? state.projects[state.selectedProjectId] : undefined
  );
};

/**
 * Hook to get projects by status
 */
export const useProjectsByStatus = (status: ProjectStatus) => {
  return useProjectStore(state => 
    Object.values(state.projects).filter(project => project.status === status)
  );
};

/**
 * Hook to get active projects
 */
export const useActiveProjects = () => {
  return useProjectStore(state => 
    Object.values(state.projects).filter(project => 
      project.status === ProjectStatus.ACTIVE
    )
  );
};

/**
 * Hook for project actions
 */
export const useProjectActions = () => {
  return useProjectStore(state => ({
    loadProjects: state.loadProjects,
    createProject: state.createProject,
    updateProject: state.updateProject,
    deleteProject: state.deleteProject,
    selectProject: state.selectProject,
    updateSettings: state.updateSettings,
    updateSecret: state.updateSecret,
    removeSecret: state.removeSecret,
    testSetupCommands: state.testSetupCommands,
    refreshProject: state.refreshProject,
    refreshAllProjects: state.refreshAllProjects,
    clearError: state.clearError,
    setLoading: state.setLoading
  }));
};
