/**
 * Project Store - Zustand store for project management
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { Project, CreateProjectRequest, UpdateProjectRequest, APIError } from '../types/cicd';
import { apiClient } from '../services/api';

interface ProjectState {
  // State
  projects: Project[];
  activeProjects: Project[];
  loading: boolean;
  error: string | null;
  
  // Computed
  totalProjects: number;
  activeProjectCount: number;
  
  // Actions
  loadProjects: () => Promise<void>;
  createProject: (data: CreateProjectRequest) => Promise<Project | null>;
  updateProject: (id: number, data: UpdateProjectRequest) => Promise<Project | null>;
  deleteProject: (id: number) => Promise<boolean>;
  refreshProject: (id: number) => Promise<void>;
  refreshAllProjects: () => Promise<void>;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

export const useProjectStore = create<ProjectState>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      // Initial state
      projects: [],
      activeProjects: [],
      loading: false,
      error: null,
      
      // Computed properties
      get totalProjects() {
        return get().projects.length;
      },
      
      get activeProjectCount() {
        return get().activeProjects.length;
      },
      
      // Actions
      loadProjects: async () => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.getProjects();
          const projects = response.items || response.projects || [];
          const activeProjects = projects.filter((p: Project) => p.status === 'active');
          
          set({ 
            projects, 
            activeProjects,
            loading: false 
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to load projects';
          set({ 
            error: errorMessage, 
            loading: false 
          });
        }
      },
      
      createProject: async (data: CreateProjectRequest) => {
        set({ loading: true, error: null });
        try {
          const project = await apiClient.createProject(data);
          const currentProjects = get().projects;
          const newProjects = [...currentProjects, project];
          const activeProjects = newProjects.filter(p => p.status === 'active');
          
          set({ 
            projects: newProjects,
            activeProjects,
            loading: false 
          });
          
          return project;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to create project';
          set({ 
            error: errorMessage, 
            loading: false 
          });
          return null;
        }
      },
      
      updateProject: async (id: number, data: UpdateProjectRequest) => {
        set({ loading: true, error: null });
        try {
          const updatedProject = await apiClient.updateProject(id, data);
          const currentProjects = get().projects;
          const newProjects = currentProjects.map(p => 
            p.id === id ? updatedProject : p
          );
          const activeProjects = newProjects.filter(p => p.status === 'active');
          
          set({ 
            projects: newProjects,
            activeProjects,
            loading: false 
          });
          
          return updatedProject;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to update project';
          set({ 
            error: errorMessage, 
            loading: false 
          });
          return null;
        }
      },
      
      deleteProject: async (id: number) => {
        set({ loading: true, error: null });
        try {
          await apiClient.deleteProject(id);
          const currentProjects = get().projects;
          const newProjects = currentProjects.filter(p => p.id !== id);
          const activeProjects = newProjects.filter(p => p.status === 'active');
          
          set({ 
            projects: newProjects,
            activeProjects,
            loading: false 
          });
          
          return true;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to delete project';
          set({ 
            error: errorMessage, 
            loading: false 
          });
          return false;
        }
      },
      
      refreshProject: async (id: number) => {
        try {
          const project = await apiClient.getProject(id);
          const currentProjects = get().projects;
          const newProjects = currentProjects.map(p => 
            p.id === id ? project : p
          );
          const activeProjects = newProjects.filter(p => p.status === 'active');
          
          set({ 
            projects: newProjects,
            activeProjects
          });
        } catch (error) {
          console.error('Failed to refresh project:', error);
        }
      },
      
      refreshAllProjects: async () => {
        await get().loadProjects();
      },
      
      clearError: () => {
        set({ error: null });
      },
      
      setLoading: (loading: boolean) => {
        set({ loading });
      }
    })),
    {
      name: 'project-store',
    }
  )
);

// Selector hooks for better performance
export const useProjects = () => useProjectStore(state => state.projects);
export const useActiveProjects = () => useProjectStore(state => state.activeProjects);
export const useProjectLoading = () => useProjectStore(state => state.loading);
export const useProjectError = () => useProjectStore(state => state.error);

// Action hooks
export const useProjectActions = () => useProjectStore(state => ({
  loadProjects: state.loadProjects,
  createProject: state.createProject,
  updateProject: state.updateProject,
  deleteProject: state.deleteProject,
  refreshProject: state.refreshProject,
  refreshAllProjects: state.refreshAllProjects,
  clearError: state.clearError,
  setLoading: state.setLoading
}));

// Computed selectors
export const useProjectStats = () => useProjectStore(state => ({
  totalProjects: state.totalProjects,
  activeProjectCount: state.activeProjectCount
}));

