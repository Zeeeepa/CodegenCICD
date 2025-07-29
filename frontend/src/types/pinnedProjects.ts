/**
 * TypeScript interfaces for Pinned Projects API
 * Matches backend models from simple_projects.py
 */

export interface PinnedProject {
  id: number;
  userId: string;
  githubRepoName: string;
  githubRepoUrl: string;
  githubOwner: string;
  displayName?: string;
  description?: string;
  pinnedAt: string;
  lastUpdated: string;
  isActive: boolean;
}

export interface PinProjectRequest {
  github_repo_name: string;
  github_repo_url: string;
  github_owner: string;
  display_name?: string;
  description?: string;
}

export interface UpdateProjectRequest {
  display_name?: string;
  description?: string;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
}

// Conversion utilities between frontend and backend models
export const convertToProjectData = (pinnedProject: PinnedProject) => ({
  id: pinnedProject.id,
  name: pinnedProject.displayName || pinnedProject.githubRepoName,
  description: pinnedProject.description,
  url: pinnedProject.githubRepoUrl,
  owner: pinnedProject.githubOwner,
  lastUpdated: pinnedProject.lastUpdated,
  status: pinnedProject.isActive ? 'active' as const : 'inactive' as const,
  isPinned: true,
});

export const convertToPinRequest = (repo: {
  name: string;
  full_name: string;
  description?: string;
  html_url: string;
  owner: { login: string };
}): PinProjectRequest => ({
  github_repo_name: repo.name,
  github_repo_url: repo.html_url,
  github_owner: repo.owner.login,
  display_name: repo.name,
  description: repo.description,
});
