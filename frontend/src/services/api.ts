// API client for CodegenCICD Dashboard
import axios from 'axios';
import { Project, ProjectConfiguration, AgentRun } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests (for now using a mock token)
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token') || 'sk-demo-token';
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Projects API
export const projectsApi = {
  list: async (skip = 0, limit = 10): Promise<Project[]> => {
    const response = await apiClient.get(`/projects?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  get: async (projectId: string): Promise<Project> => {
    const response = await apiClient.get(`/projects/${projectId}`);
    return response.data;
  },

  create: async (projectData: Omit<Project, 'id' | 'created_at' | 'updated_at'>): Promise<Project> => {
    const response = await apiClient.post('/projects', projectData);
    return response.data;
  },

  update: async (projectId: string, projectData: Partial<Project>): Promise<Project> => {
    const response = await apiClient.put(`/projects/${projectId}`, projectData);
    return response.data;
  },

  delete: async (projectId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}`);
  },

  getConfiguration: async (projectId: string): Promise<ProjectConfiguration> => {
    const response = await apiClient.get(`/projects/${projectId}/configuration`);
    return response.data;
  },

  updateConfiguration: async (projectId: string, config: ProjectConfiguration): Promise<void> => {
    await apiClient.put(`/projects/${projectId}/configuration`, config);
  },
};

// Agent Runs API
export const agentRunsApi = {
  list: async (projectId?: string, skip = 0, limit = 10): Promise<AgentRun[]> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    if (projectId) {
      params.append('project_id', projectId);
    }
    const response = await apiClient.get(`/agent-runs?${params}`);
    return response.data;
  },

  get: async (agentRunId: string): Promise<AgentRun> => {
    const response = await apiClient.get(`/agent-runs/${agentRunId}`);
    return response.data;
  },

  create: async (data: {
    project_id: string;
    prompt: string;
    use_planning_statement?: boolean;
  }): Promise<AgentRun> => {
    const response = await apiClient.post('/agent-runs', data);
    return response.data;
  },

  continue: async (agentRunId: string, continuationPrompt: string): Promise<AgentRun> => {
    const response = await apiClient.post(`/agent-runs/${agentRunId}/continue`, {
      continuation_prompt: continuationPrompt,
    });
    return response.data;
  },
};

// Webhooks API
export const webhooksApi = {
  listEvents: async (eventType?: string, skip = 0, limit = 20) => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    if (eventType) {
      params.append('event_type', eventType);
    }
    const response = await apiClient.get(`/webhooks/events?${params}`);
    return response.data;
  },

  getEvent: async (eventId: string) => {
    const response = await apiClient.get(`/webhooks/events/${eventId}`);
    return response.data;
  },
};

// Health check
export const healthApi = {
  check: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

export default apiClient;

