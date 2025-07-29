/**
 * React hook for managing pinned projects state
 * Provides optimistic updates and error handling
 */

import { useState, useEffect, useCallback } from 'react';
import { PinnedProject, PinProjectRequest } from '../types/pinnedProjects';
import { pinnedProjectsApi, PinnedProjectsApiError } from '../services/pinnedProjectsApi';

export interface UsePinnedProjectsReturn {
  projects: PinnedProject[];
  loading: boolean;
  error: string | null;
  pinProject: (project: PinProjectRequest) => Promise<void>;
  unpinProject: (projectId: number) => Promise<void>;
  refreshProjects: () => Promise<void>;
  clearError: () => void;
}

export const usePinnedProjects = (): UsePinnedProjectsReturn => {
  const [projects, setProjects] = useState<PinnedProject[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const handleApiError = useCallback((error: unknown): string => {
    if (error instanceof PinnedProjectsApiError) {
      return error.message;
    }
    if (error instanceof Error) {
      return error.message;
    }
    return 'An unexpected error occurred';
  }, []);

  const refreshProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const pinnedProjects = await pinnedProjectsApi.getPinnedProjects();
      setProjects(pinnedProjects);
    } catch (error) {
      const errorMessage = handleApiError(error);
      setError(errorMessage);
      console.error('Failed to fetch pinned projects:', error);
    } finally {
      setLoading(false);
    }
  }, [handleApiError]);

  const pinProject = useCallback(async (project: PinProjectRequest) => {
    try {
      setError(null);
      
      // Optimistic update - add temporary project
      const tempProject: PinnedProject = {
        id: Date.now(), // Temporary ID
        userId: 'temp',
        githubRepoName: project.github_repo_name,
        githubRepoUrl: project.github_repo_url,
        githubOwner: project.github_owner,
        displayName: project.display_name,
        description: project.description,
        pinnedAt: new Date().toISOString(),
        lastUpdated: new Date().toISOString(),
        isActive: true,
      };
      
      setProjects(prev => [...prev, tempProject]);

      // Make API call
      const pinnedProject = await pinnedProjectsApi.pinProject(project);
      
      // Replace temporary project with real one
      setProjects(prev => 
        prev.map(p => p.id === tempProject.id ? pinnedProject : p)
      );
    } catch (error) {
      // Revert optimistic update on error
      setProjects(prev => 
        prev.filter(p => p.githubRepoName !== project.github_repo_name)
      );
      
      const errorMessage = handleApiError(error);
      setError(errorMessage);
      console.error('Failed to pin project:', error);
      throw error; // Re-throw so caller can handle if needed
    }
  }, [handleApiError]);

  const unpinProject = useCallback(async (projectId: number) => {
    try {
      setError(null);
      
      // Store the project for potential rollback
      const projectToRemove = projects.find(p => p.id === projectId);
      if (!projectToRemove) {
        throw new Error('Project not found');
      }

      // Optimistic update - remove project
      setProjects(prev => prev.filter(p => p.id !== projectId));

      // Make API call
      await pinnedProjectsApi.unpinProject(projectId);
    } catch (error) {
      // Revert optimistic update on error
      const projectToRestore = projects.find(p => p.id === projectId);
      if (projectToRestore) {
        setProjects(prev => [...prev, projectToRestore]);
      }
      
      const errorMessage = handleApiError(error);
      setError(errorMessage);
      console.error('Failed to unpin project:', error);
      throw error; // Re-throw so caller can handle if needed
    }
  }, [projects, handleApiError]);

  // Load projects on mount
  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  return {
    projects,
    loading,
    error,
    pinProject,
    unpinProject,
    refreshProjects,
    clearError,
  };
};

// Hook for checking if a repository is pinned
export const useIsPinned = (repoName: string, owner: string): boolean => {
  const { projects } = usePinnedProjects();
  
  return projects.some(
    project => 
      project.githubRepoName === repoName && 
      project.githubOwner === owner
  );
};

// Hook for getting a specific pinned project
export const usePinnedProject = (repoName: string, owner: string): PinnedProject | undefined => {
  const { projects } = usePinnedProjects();
  
  return projects.find(
    project => 
      project.githubRepoName === repoName && 
      project.githubOwner === owner
  );
};
