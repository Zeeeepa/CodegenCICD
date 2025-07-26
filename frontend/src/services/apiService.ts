/**
 * API Service Layer for CodegenCICD Dashboard
 * Handles all communication with the FastAPI backend
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  Project,
  CreateProjectRequest,
  AgentRun,
  CreateAgentRunRequest,
  ResumeAgentRunRequest,
  AgentRunLogsResponse,
  ProjectConfiguration,
  ProjectSecret,
  CreateSecretRequest,
  ApiResponse,
  PaginatedResponse,
  ApiError,
} from '../types/api';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || '/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for adding auth headers if needed
    this.api.interceptors.request.use(
      (config) => {
        // Add any authentication headers here if needed
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response: AxiosResponse) => {
        return response;
      },
      (error) => {
        const apiError: ApiError = {
          message: error.response?.data?.message || error.message || 'An error occurred',
          code: error.response?.status?.toString(),
          details: error.response?.data,
        };
        return Promise.reject(apiError);
      }
    );
  }

  // Project Management
  async getProjects(): Promise<Project[]> {
    const response = await this.api.get<ApiResponse<Project[]>>('/projects');
    return response.data.data;
  }

  async getProject(id: string): Promise<Project> {
    const response = await this.api.get<ApiResponse<Project>>(`/projects/${id}`);
    return response.data.data;
  }

  async createProject(project: CreateProjectRequest): Promise<Project> {
    const response = await this.api.post<ApiResponse<Project>>('/projects', project);
    return response.data.data;
  }

  async updateProject(id: string, project: Partial<Project>): Promise<Project> {
    const response = await this.api.put<ApiResponse<Project>>(`/projects/${id}`, project);
    return response.data.data;
  }

  async deleteProject(id: string): Promise<void> {
    await this.api.delete(`/projects/${id}`);
  }

  // Agent Run Management
  async getAgentRuns(projectId?: string): Promise<AgentRun[]> {
    const params = projectId ? { project_id: projectId } : {};
    const response = await this.api.get<ApiResponse<AgentRun[]>>('/agent-runs', { params });
    return response.data.data;
  }

  async getAgentRun(id: string): Promise<AgentRun> {
    const response = await this.api.get<ApiResponse<AgentRun>>(`/agent-runs/${id}`);
    return response.data.data;
  }

  async createAgentRun(agentRun: CreateAgentRunRequest): Promise<AgentRun> {
    const response = await this.api.post<ApiResponse<AgentRun>>('/agent-runs', agentRun);
    return response.data.data;
  }

  async resumeAgentRun(resumeRequest: ResumeAgentRunRequest): Promise<AgentRun> {
    const response = await this.api.post<ApiResponse<AgentRun>>('/agent-runs/resume', resumeRequest);
    return response.data.data;
  }

  async cancelAgentRun(id: string): Promise<void> {
    await this.api.post(`/agent-runs/${id}/cancel`);
  }

  async getAgentRunLogs(id: string, page: number = 1, limit: number = 100): Promise<AgentRunLogsResponse> {
    const response = await this.api.get<AgentRunLogsResponse>(`/agent-runs/${id}/logs`, {
      params: { skip: (page - 1) * limit, limit }
    });
    return response.data;
  }

  // Project Configuration
  async getProjectConfiguration(projectId: string): Promise<ProjectConfiguration | null> {
    try {
      const response = await this.api.get<ApiResponse<ProjectConfiguration>>(`/configurations/${projectId}`);
      return response.data.data;
    } catch (error: any) {
      if (error.code === '404') {
        return null;
      }
      throw error;
    }
  }

  async updateProjectConfiguration(projectId: string, config: Partial<ProjectConfiguration>): Promise<ProjectConfiguration> {
    const response = await this.api.put<ApiResponse<ProjectConfiguration>>(`/configurations/${projectId}`, config);
    return response.data.data;
  }

  // Secrets Management
  async getProjectSecrets(projectId: string): Promise<ProjectSecret[]> {
    const response = await this.api.get<ApiResponse<ProjectSecret[]>>(`/configurations/secrets/${projectId}`);
    return response.data.data;
  }

  async createProjectSecret(secret: CreateSecretRequest): Promise<ProjectSecret> {
    const response = await this.api.post<ApiResponse<ProjectSecret>>('/configurations/secrets', secret);
    return response.data.data;
  }

  async updateProjectSecret(id: string, value: string): Promise<ProjectSecret> {
    const response = await this.api.put<ApiResponse<ProjectSecret>>(`/configurations/secrets/${id}`, { value });
    return response.data.data;
  }

  async deleteProjectSecret(id: string): Promise<void> {
    await this.api.delete(`/configurations/secrets/${id}`);
  }

  // GitHub Integration
  async getGitHubRepositories(): Promise<any[]> {
    const response = await this.api.get<ApiResponse<any[]>>('/github/repositories');
    return response.data.data;
  }

  async getGitHubBranches(owner: string, repo: string): Promise<string[]> {
    const response = await this.api.get<ApiResponse<string[]>>(`/github/repositories/${owner}/${repo}/branches`);
    return response.data.data;
  }

  // Validation Pipeline
  async getValidationPipeline(agentRunId: string): Promise<any> {
    const response = await this.api.get<ApiResponse<any>>(`/validation/${agentRunId}`);
    return response.data.data;
  }

  async triggerValidation(agentRunId: string, prNumber: number): Promise<any> {
    const response = await this.api.post<ApiResponse<any>>('/validation/trigger', {
      agent_run_id: agentRunId,
      pr_number: prNumber
    });
    return response.data.data;
  }

  // Health Check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await this.api.get<{ status: string; timestamp: string }>('/health');
    return response.data;
  }
}

// Create and export a singleton instance
export const apiService = new ApiService();
export default apiService;
