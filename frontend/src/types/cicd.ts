/**
 * TypeScript type definitions for CICD Dashboard
 */

export interface Project {
  id: number;
  name: string;
  github_owner: string;
  github_repo: string;
  status: 'active' | 'inactive' | 'error';
  webhook_url?: string;
  auto_merge_enabled: boolean;
  auto_confirm_plans: boolean;
  created_at: string;
  updated_at: string;
  stats: ProjectStats;
  settings?: ProjectSettings;
  secrets?: ProjectSecret[];
}

export interface ProjectStats {
  totalRuns: number;
  successRate: number;
  lastRunAt?: string;
  averageRunTime?: number;
  failureCount: number;
}

export interface ProjectSettings {
  id?: number;
  project_id: number;
  planning_statement?: string;
  repository_rules?: string;
  setup_commands?: string;
  branch_name: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectSecret {
  id?: number;
  project_id: number;
  key_name: string;
  encrypted_value: string;
  created_at?: string;
}

export interface AgentRun {
  id: number;
  project_id: number;
  prompt: string;
  status: AgentRunStatus;
  result?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  metadata?: Record<string, any>;
}

export enum AgentRunStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface Workflow {
  id: string;
  project_id: number;
  name: string;
  status: WorkflowStatus;
  steps: WorkflowStep[];
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export enum WorkflowStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface WorkflowStep {
  id: string;
  name: string;
  status: WorkflowStatus;
  type: 'agent_run' | 'webhook' | 'validation' | 'merge';
  config: Record<string, any>;
  result?: Record<string, any>;
  error?: string;
}

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  autoDismiss?: boolean;
  dismissAfter?: number;
  actions?: NotificationAction[];
}

export enum NotificationType {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info'
}

export interface NotificationAction {
  label: string;
  action: () => void;
  variant?: 'text' | 'outlined' | 'contained';
}

export interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  owner: {
    login: string;
    avatar_url: string;
  };
  description?: string;
  private: boolean;
  default_branch: string;
  updated_at: string;
}

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
}

export interface APIError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface CreateProjectRequest {
  name: string;
  github_owner: string;
  github_repo: string;
  auto_merge_enabled?: boolean;
  auto_confirm_plans?: boolean;
  settings?: Partial<ProjectSettings>;
  secrets?: Array<{key_name: string; value: string}>;
}

export interface UpdateProjectRequest {
  name?: string;
  status?: string;
  auto_merge_enabled?: boolean;
  auto_confirm_plans?: boolean;
  webhook_url?: string;
}

export interface CreateAgentRunRequest {
  prompt: string;
  metadata?: Record<string, any>;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    database: boolean;
    github: boolean;
    codegen: boolean;
    grainchain: boolean;
    web_eval_agent: boolean;
  };
  uptime: number;
  version: string;
}

