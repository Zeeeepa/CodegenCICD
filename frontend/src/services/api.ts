import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth tokens if needed
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// Types
export interface Project {
  id: number;
  name: string;
  description?: string;
  github_repo: string;
  github_owner: string;
  github_branch: string;
  github_url: string;
  webhook_url: string;
  webhook_active: boolean;
  auto_merge_enabled: boolean;
  auto_confirm_plans: boolean;
  auto_merge_threshold: number;
  auto_merge_validated_pr?: boolean;
  planning_statement?: string;
  repository_rules?: string;
  setup_commands?: string;
  setup_branch?: string;
  is_active: boolean;
  status: 'active' | 'inactive';
  validation_enabled: boolean;
  
  // Configuration indicators
  has_repository_rules: boolean;
  has_setup_commands: boolean;
  has_secrets: boolean;
  has_planning_statement: boolean;
  
  // Current agent run status
  current_agent_run?: {
    id: string;
    status: 'pending' | 'running' | 'waiting_for_input' | 'completed' | 'failed' | 'cancelled';
    progress_percentage: number;
    current_step?: string;
    run_type: 'regular' | 'plan' | 'pr_creation' | 'error_fix';
    pr_number?: number;
    pr_url?: string;
  };
  
  // Recent activity
  last_run_at?: string;
  total_runs: number;
  success_rate: number;
  created_at: string;
  updated_at: string;
}

export interface AgentRun {
  id: number;
  project_id: number;
  codegen_run_id?: number;
  target_text: string;
  planning_statement?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  run_type: 'regular' | 'plan' | 'pr';
  result?: string;
  error_message?: string;
  pr_number?: number;
  pr_url?: string;
  validation_status: string;
  auto_merge_enabled: boolean;
  merge_completed: boolean;
  started_at: string;
  completed_at?: string;
}

export interface ProjectConfiguration {
  id: number;
  project_id: number;
  repository_rules?: string;
  setup_commands?: string;
  planning_statement?: string;
  branch_name: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectSecret {
  id: number;
  project_id: number;
  key: string;
  value: string; // This will be encrypted on the backend
  created_at: string;
}

// API Functions
export const projectsApi = {
  // Get all projects
  getAll: () => api.get<Project[]>('/projects'),
  
  // Get project by ID
  getById: (id: number) => api.get<Project>(`/projects/${id}`),
  
  // Create new project
  create: (data: Partial<Project>) => api.post<Project>('/projects', data),
  
  // Update project
  update: (id: number, data: Partial<Project>) => api.put<Project>(`/projects/${id}`, data),
  
  // Delete project
  delete: (id: number) => api.delete(`/projects/${id}`),
  
  // Get GitHub repositories for dropdown
  getGitHubRepos: () => api.get<any[]>('/projects/github-repos'),
};

export const agentRunsApi = {
  // Get all agent runs for a project
  getByProject: (projectId: number) => api.get<AgentRun[]>(`/agent-runs?project_id=${projectId}`),
  
  // Get agent run by ID
  getById: (id: number) => api.get<AgentRun>(`/agent-runs/${id}`),
  
  // Create new agent run
  create: (data: {
    project_id: number;
    target_text: string;
    planning_statement?: string;
  }) => api.post<AgentRun>('/agent-runs', data),
  
  // Continue agent run
  continue: (id: number, data: { message: string }) => 
    api.post<AgentRun>(`/agent-runs/${id}/continue`, data),
  
  // Cancel agent run
  cancel: (id: number) => api.post(`/agent-runs/${id}/cancel`),
};

export const configurationsApi = {
  // Get project configuration
  getByProject: (projectId: number) => 
    api.get<ProjectConfiguration>(`/configurations/${projectId}`),
  
  // Update project configuration
  update: (projectId: number, data: Partial<ProjectConfiguration>) => 
    api.put<ProjectConfiguration>(`/configurations/${projectId}`, data),
  
  // Get project secrets
  getSecrets: (projectId: number) => 
    api.get<ProjectSecret[]>(`/configurations/${projectId}/secrets`),
  
  // Create secret
  createSecret: (projectId: number, data: { key: string; value: string }) => 
    api.post<ProjectSecret>(`/configurations/${projectId}/secrets`, data),
  
  // Update secret
  updateSecret: (projectId: number, secretId: number, data: { key: string; value: string }) => 
    api.put<ProjectSecret>(`/configurations/${projectId}/secrets/${secretId}`, data),
  
  // Delete secret
  deleteSecret: (projectId: number, secretId: number) => 
    api.delete(`/configurations/${projectId}/secrets/${secretId}`),
  
  // Test setup commands
  testSetupCommands: (projectId: number, data: { commands: string; branch?: string }) => 
    api.post(`/configurations/${projectId}/test-setup`, data),
};

export const validationApi = {
  // Get validation status
  getStatus: (agentRunId: number) => 
    api.get(`/validation/${agentRunId}/status`),
  
  // Get validation logs
  getLogs: (agentRunId: number) => 
    api.get(`/validation/${agentRunId}/logs`),
  
  // Retry validation
  retry: (agentRunId: number) => 
    api.post(`/validation/${agentRunId}/retry`),
};

export default api;
