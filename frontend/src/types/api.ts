/**
 * TypeScript interfaces for CodegenCICD Dashboard API
 */

// Project Types
export interface Project {
  id: string;
  name: string;
  description?: string;
  github_repo: string;
  github_owner: string;
  webhook_url?: string;
  auto_merge_enabled: boolean;
  auto_confirm_plans: boolean;
  created_at: string;
  updated_at: string;
  status: 'active' | 'inactive' | 'error';
  last_activity?: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  github_repo: string;
  github_owner: string;
  auto_merge_enabled?: boolean;
  auto_confirm_plans?: boolean;
}

// Agent Run Types
export interface AgentRun {
  id: string;
  project_id: string;
  prompt: string;
  status: 'ACTIVE' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  result?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  web_url?: string;
  response_type?: 'regular' | 'plan' | 'pr';
  pr_number?: number;
  pr_url?: string;
}

export interface CreateAgentRunRequest {
  project_id: string;
  prompt: string;
  metadata?: Record<string, any>;
}

export interface ResumeAgentRunRequest {
  agent_run_id: string;
  prompt: string;
}

// Agent Run Log Types
export interface AgentRunLog {
  agent_run_id: string;
  created_at: string;
  message_type: string;
  thought?: string;
  tool_name?: string;
  tool_input?: Record<string, any>;
  tool_output?: Record<string, any>;
  observation?: any;
}

export interface AgentRunLogsResponse {
  id: string;
  organization_id: number;
  status: string;
  created_at: string;
  web_url?: string;
  result?: string;
  logs: AgentRunLog[];
  total_logs: number;
  page: number;
  size: number;
  pages: number;
}

// Configuration Types
export interface ProjectConfiguration {
  id: string;
  project_id: string;
  repository_rules?: string;
  planning_statement?: string;
  setup_commands?: string;
  target_branch?: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectSecret {
  id: string;
  project_id: string;
  key: string;
  value: string; // This will be encrypted on the backend
  created_at: string;
  updated_at: string;
}

export interface CreateSecretRequest {
  project_id: string;
  key: string;
  value: string;
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: 'agent_run_update' | 'project_update' | 'validation_update' | 'connection_status';
  data: any;
  timestamp: string;
}

export interface AgentRunUpdateMessage {
  agent_run_id: string;
  status: string;
  progress?: number;
  current_step?: string;
  logs?: AgentRunLog[];
  result?: string;
  pr_created?: {
    pr_number: number;
    pr_url: string;
  };
}

// Validation Pipeline Types
export interface ValidationStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  logs?: string[];
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface ValidationPipeline {
  id: string;
  agent_run_id: string;
  pr_number: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  steps: ValidationStep[];
  created_at: string;
  updated_at: string;
}

// GitHub Integration Types
export interface GitHubPR {
  number: number;
  title: string;
  url: string;
  status: 'open' | 'closed' | 'merged';
  created_at: string;
  updated_at: string;
  validation_status?: 'pending' | 'running' | 'passed' | 'failed';
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Error Types
export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

// Dashboard State Types
export interface DashboardState {
  projects: Project[];
  selectedProject?: Project;
  agentRuns: AgentRun[];
  activeAgentRun?: AgentRun;
  isLoading: boolean;
  error?: string;
  websocketConnected: boolean;
}

// Form Types
export interface RequirementsForm {
  requirements: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  context?: string;
  acceptance_criteria?: string;
}

export interface ProjectSettingsForm {
  repository_rules?: string;
  planning_statement?: string;
  setup_commands?: string;
  target_branch?: string;
  auto_merge_enabled: boolean;
  auto_confirm_plans: boolean;
}

// UI State Types
export interface UIState {
  sidebarOpen: boolean;
  selectedTab: string;
  dialogOpen: {
    agentRun: boolean;
    settings: boolean;
    createProject: boolean;
  };
  notifications: Notification[];
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}
