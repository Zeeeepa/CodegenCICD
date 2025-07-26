import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  Project,
  AgentRun,
  ProjectConfiguration,
  ValidationRun,
  ApiResponse,
  PaginatedResponse,
  CreateProjectForm,
  UpdateProjectConfigurationForm,
  CreateSecretForm,
  AgentRunForm,
  GitHubRepository,
  PullRequest
} from '../types';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Projects API
  async getProjects(): Promise<Project[]> {
    const response: AxiosResponse<ApiResponse<Project[]>> = await this.api.get('/projects');
    return response.data.data;
  }

  async getProject(id: string): Promise<Project> {
    const response: AxiosResponse<ApiResponse<Project>> = await this.api.get(`/projects/${id}`);
    return response.data.data;
  }

  async createProject(data: CreateProjectForm): Promise<Project> {
    const response: AxiosResponse<ApiResponse<Project>> = await this.api.post('/projects', data);
    return response.data.data;
  }

  async updateProject(id: string, data: Partial<CreateProjectForm>): Promise<Project> {
    const response: AxiosResponse<ApiResponse<Project>> = await this.api.put(`/projects/${id}`, data);
    return response.data.data;
  }

  async deleteProject(id: string): Promise<void> {
    await this.api.delete(`/projects/${id}`);
  }

  // Agent Runs API
  async getAgentRuns(projectId?: string): Promise<AgentRun[]> {
    const params = projectId ? { project_id: projectId } : {};
    const response: AxiosResponse<ApiResponse<AgentRun[]>> = await this.api.get('/agent-runs', { params });
    return response.data.data;
  }

  async getAgentRun(id: string): Promise<AgentRun> {
    const response: AxiosResponse<ApiResponse<AgentRun>> = await this.api.get(`/agent-runs/${id}`);
    return response.data.data;
  }

  async createAgentRun(projectId: string, data: AgentRunForm): Promise<AgentRun> {
    const response: AxiosResponse<ApiResponse<AgentRun>> = await this.api.post('/agent-runs', {
      project_id: projectId,
      ...data
    });
    return response.data.data;
  }

  async resumeAgentRun(id: string, prompt: string): Promise<AgentRun> {
    const response: AxiosResponse<ApiResponse<AgentRun>> = await this.api.post(`/agent-runs/${id}/resume`, {
      prompt
    });
    return response.data.data;
  }

  async cancelAgentRun(id: string): Promise<void> {
    await this.api.post(`/agent-runs/${id}/cancel`);
  }

  // Configurations API
  async getProjectConfiguration(projectId: string): Promise<ProjectConfiguration> {
    const response: AxiosResponse<ApiResponse<ProjectConfiguration>> = await this.api.get(`/configurations/${projectId}`);
    return response.data.data;
  }

  async updateProjectConfiguration(projectId: string, data: UpdateProjectConfigurationForm): Promise<ProjectConfiguration> {
    const response: AxiosResponse<ApiResponse<ProjectConfiguration>> = await this.api.put(`/configurations/${projectId}`, data);
    return response.data.data;
  }

  // Secrets API
  async createSecret(projectId: string, data: CreateSecretForm): Promise<void> {
    await this.api.post(`/configurations/${projectId}/secrets`, data);
  }

  async updateSecret(projectId: string, secretId: string, data: CreateSecretForm): Promise<void> {
    await this.api.put(`/configurations/${projectId}/secrets/${secretId}`, data);
  }

  async deleteSecret(projectId: string, secretId: string): Promise<void> {
    await this.api.delete(`/configurations/${projectId}/secrets/${secretId}`);
  }

  // Validation Runs API
  async getValidationRuns(agentRunId: string): Promise<ValidationRun[]> {
    const response: AxiosResponse<ApiResponse<ValidationRun[]>> = await this.api.get(`/agent-runs/${agentRunId}/validations`);
    return response.data.data;
  }

  async getValidationRun(id: string): Promise<ValidationRun> {
    const response: AxiosResponse<ApiResponse<ValidationRun>> = await this.api.get(`/validations/${id}`);
    return response.data.data;
  }

  // GitHub Integration API
  async getGitHubRepositories(): Promise<GitHubRepository[]> {
    const response: AxiosResponse<ApiResponse<GitHubRepository[]>> = await this.api.get('/github/repositories');
    return response.data.data;
  }

  async getPullRequests(projectId: string): Promise<PullRequest[]> {
    const response: AxiosResponse<ApiResponse<PullRequest[]>> = await this.api.get(`/projects/${projectId}/pull-requests`);
    return response.data.data;
  }

  async mergePullRequest(projectId: string, prNumber: number): Promise<void> {
    await this.api.post(`/projects/${projectId}/pull-requests/${prNumber}/merge`);
  }

  // Setup Commands API
  async runSetupCommands(projectId: string, branch?: string): Promise<{ success: boolean; logs: string[] }> {
    const response: AxiosResponse<ApiResponse<{ success: boolean; logs: string[] }>> = await this.api.post(
      `/projects/${projectId}/setup-commands/run`,
      { branch }
    );
    return response.data.data;
  }

  async testSetupCommands(projectId: string, commands: string, branch?: string): Promise<{ success: boolean; logs: string[] }> {
    const response: AxiosResponse<ApiResponse<{ success: boolean; logs: string[] }>> = await this.api.post(
      `/projects/${projectId}/setup-commands/test`,
      { commands, branch }
    );
    return response.data.data;
  }

  // Health Check API
  async healthCheck(): Promise<{ status: string; checks: Record<string, string> }> {
    const response: AxiosResponse<{ status: string; checks: Record<string, string> }> = await this.api.get('/health');
    return response.data;
  }

  // Authentication API
  async login(email: string, password: string): Promise<{ token: string; user: any }> {
    const response: AxiosResponse<ApiResponse<{ token: string; user: any }>> = await this.api.post('/auth/login', {
      email,
      password
    });
    return response.data.data;
  }

  async register(email: string, password: string, name: string): Promise<{ token: string; user: any }> {
    const response: AxiosResponse<ApiResponse<{ token: string; user: any }>> = await this.api.post('/auth/register', {
      email,
      password,
      name
    });
    return response.data.data;
  }

  async getCurrentUser(): Promise<any> {
    const response: AxiosResponse<ApiResponse<any>> = await this.api.get('/auth/me');
    return response.data.data;
  }

  async logout(): Promise<void> {
    await this.api.post('/auth/logout');
    localStorage.removeItem('auth_token');
  }
}

export const apiService = new ApiService();
export default apiService;
