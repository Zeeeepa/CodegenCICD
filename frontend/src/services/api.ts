/**
 * API Client for CICD Dashboard
 */

import {
  Project,
  AgentRun,
  Workflow,
  GitHubRepository,
  CreateProjectRequest,
  UpdateProjectRequest,
  CreateAgentRunRequest,
  PaginatedResponse,
  SystemHealth,
  ProjectSettings,
  ProjectSecret
} from '../types/cicd';

class APIClient {
  private baseURL: string;
  private timeout: number;

  constructor(baseURL: string = '/api', timeout: number = 30000) {
    this.baseURL = baseURL;
    this.timeout = timeout;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error('Request timeout');
        }
        throw error;
      }
      throw new Error('Unknown error occurred');
    }
  }

  // Health and System
  async getHealth(): Promise<SystemHealth> {
    return this.request<SystemHealth>('/health');
  }

  // Projects
  async getProjects(): Promise<PaginatedResponse<Project>> {
    return this.request<PaginatedResponse<Project>>('/projects');
  }

  async getProject(id: number): Promise<Project> {
    return this.request<Project>(`/projects/${id}`);
  }

  async createProject(data: CreateProjectRequest): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateProject(id: number, data: UpdateProjectRequest): Promise<Project> {
    return this.request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteProject(id: number): Promise<void> {
    return this.request<void>(`/projects/${id}`, {
      method: 'DELETE',
    });
  }

  // Project Configuration
  async getProjectConfiguration(id: number): Promise<{
    project: Project;
    settings: ProjectSettings;
    secrets: ProjectSecret[];
  }> {
    return this.request(`/projects/${id}/configuration`);
  }

  async updateProjectSettings(id: number, settings: Partial<ProjectSettings>): Promise<ProjectSettings> {
    return this.request<ProjectSettings>(`/projects/${id}/settings`, {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }

  async updateProjectSecrets(id: number, secrets: Array<{key_name: string; value: string}>): Promise<ProjectSecret[]> {
    return this.request<ProjectSecret[]>(`/projects/${id}/secrets`, {
      method: 'PUT',
      body: JSON.stringify({ secrets }),
    });
  }

  // Agent Runs
  async getAgentRuns(projectId?: number): Promise<PaginatedResponse<AgentRun>> {
    const endpoint = projectId ? `/projects/${projectId}/agent-runs` : '/agent-runs';
    return this.request<PaginatedResponse<AgentRun>>(endpoint);
  }

  async getAgentRun(id: number): Promise<AgentRun> {
    return this.request<AgentRun>(`/agent-runs/${id}`);
  }

  async createAgentRun(projectId: number, data: CreateAgentRunRequest): Promise<AgentRun> {
    return this.request<AgentRun>(`/projects/${projectId}/agent-runs`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async cancelAgentRun(id: number): Promise<void> {
    return this.request<void>(`/agent-runs/${id}/cancel`, {
      method: 'POST',
    });
  }

  // Workflows
  async getWorkflows(projectId?: number): Promise<PaginatedResponse<Workflow>> {
    const endpoint = projectId ? `/projects/${projectId}/workflows` : '/workflows';
    return this.request<PaginatedResponse<Workflow>>(endpoint);
  }

  async getWorkflow(id: string): Promise<Workflow> {
    return this.request<Workflow>(`/workflows/${id}`);
  }

  // GitHub Integration
  async getGitHubRepositories(): Promise<GitHubRepository[]> {
    return this.request<GitHubRepository[]>('/github/repositories');
  }

  async searchGitHubRepositories(query: string): Promise<GitHubRepository[]> {
    return this.request<GitHubRepository[]>(`/github/repositories/search?q=${encodeURIComponent(query)}`);
  }

  // Webhooks
  async setupWebhook(projectId: number): Promise<{ webhook_url: string }> {
    return this.request<{ webhook_url: string }>(`/projects/${projectId}/webhook`, {
      method: 'POST',
    });
  }

  async removeWebhook(projectId: number): Promise<void> {
    return this.request<void>(`/projects/${projectId}/webhook`, {
      method: 'DELETE',
    });
  }

  // Statistics and Monitoring
  async getProjectStats(id: number): Promise<{
    totalRuns: number;
    successRate: number;
    averageRunTime: number;
    recentActivity: Array<{
      date: string;
      runs: number;
      success: number;
    }>;
  }> {
    return this.request(`/projects/${id}/stats`);
  }

  async getSystemStats(): Promise<{
    totalProjects: number;
    activeProjects: number;
    totalRuns: number;
    runningRuns: number;
    systemLoad: number;
  }> {
    return this.request('/stats');
  }
}

// Create singleton instance
export const apiClient = new APIClient();

// Export for testing
export { APIClient };

