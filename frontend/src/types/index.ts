// Type definitions for CodegenCICD Dashboard

export interface Project {
  id: string;
  name: string;
  description?: string;
  repository_url: string;
  default_branch: string;
  webhook_url?: string;
  auto_merge_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectConfiguration {
  repository_rules?: string;
  setup_commands?: string;
  planning_statement?: string;
  secrets?: string[];
}

export interface AgentRun {
  id: string;
  project_id: string;
  prompt: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  response_type?: 'regular' | 'plan' | 'pr';
  response_content?: string;
  pr_url?: string;
  created_at: string;
  updated_at: string;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface ValidationStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: string;
  error?: string;
}

export interface Validation {
  id: string;
  project_id: string;
  pr_url: string;
  branch_name: string;
  pr_number: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  steps: ValidationStep[];
  auto_merge_ready: boolean;
  created_at: string;
  updated_at: string;
}

