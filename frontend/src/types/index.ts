// Core Types for CodegenCICD Dashboard

export interface Project {
  id: string;
  name: string;
  description?: string;
  github_repository: string;
  default_branch: string;
  webhook_url?: string;
  created_at: string;
  updated_at: string;
  configuration?: ProjectConfiguration;
  auto_confirm_plan: boolean;
  auto_merge_validated_pr: boolean;
}

export interface ProjectConfiguration {
  id: string;
  project_id: string;
  repository_rules?: string;
  setup_commands?: string;
  planning_statement?: string;
  secrets: ProjectSecret[];
  created_at: string;
  updated_at: string;
}

export interface ProjectSecret {
  id: string;
  project_id: string;
  key: string;
  value: string; // This will be encrypted on backend
  created_at: string;
}

export interface AgentRun {
  id: string;
  project_id: string;
  prompt: string;
  status: AgentRunStatus;
  response_type: AgentResponseType;
  response_data?: any;
  logs: AgentRunLog[];
  created_at: string;
  updated_at: string;
  completed_at?: string;
  error_message?: string;
}

export enum AgentRunStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export enum AgentResponseType {
  REGULAR = 'regular',
  PLAN = 'plan',
  PR = 'pr'
}

export interface AgentRunLog {
  id: string;
  agent_run_id: string;
  message: string;
  level: LogLevel;
  timestamp: string;
  metadata?: any;
}

export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error'
}

export interface ValidationRun {
  id: string;
  agent_run_id: string;
  pr_number?: number;
  status: ValidationStatus;
  deployment_status: ValidationStepStatus;
  ui_test_status: ValidationStepStatus;
  logs: ValidationLog[];
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export enum ValidationStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export enum ValidationStepStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  SUCCESS = 'success',
  FAILED = 'failed'
}

export interface ValidationLog {
  id: string;
  validation_run_id: string;
  step: ValidationStep;
  message: string;
  level: LogLevel;
  timestamp: string;
}

export enum ValidationStep {
  SNAPSHOT_CREATION = 'snapshot_creation',
  CODE_CLONE = 'code_clone',
  DEPLOYMENT = 'deployment',
  DEPLOYMENT_VALIDATION = 'deployment_validation',
  UI_TESTING = 'ui_testing',
  AUTO_MERGE = 'auto_merge'
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: WebSocketMessageType;
  data?: any;
  timestamp?: string;
}

export enum WebSocketMessageType {
  // Client to Server
  SUBSCRIBE_PROJECT = 'subscribe_project',
  UNSUBSCRIBE_PROJECT = 'unsubscribe_project',
  PING = 'ping',
  GET_STATUS = 'get_status',
  
  // Server to Client
  AGENT_RUN_UPDATE = 'agent_run_update',
  VALIDATION_UPDATE = 'validation_update',
  PR_NOTIFICATION = 'pr_notification',
  PROJECT_UPDATE = 'project_update',
  NOTIFICATION = 'notification',
  PONG = 'pong',
  STATUS = 'status',
  ERROR = 'error',
  SUBSCRIPTION_CONFIRMED = 'subscription_confirmed',
  UNSUBSCRIPTION_CONFIRMED = 'unsubscription_confirmed'
}

// UI State Types
export interface DashboardState {
  projects: Project[];
  selectedProject?: Project;
  loading: boolean;
  error?: string;
}

export interface AgentRunDialogState {
  open: boolean;
  project?: Project;
  targetText: string;
  currentRun?: AgentRun;
  loading: boolean;
  error?: string;
}

export interface SettingsDialogState {
  open: boolean;
  project?: Project;
  activeTab: SettingsTab;
  loading: boolean;
  error?: string;
}

export enum SettingsTab {
  REPOSITORY_RULES = 'repository_rules',
  SETUP_COMMANDS = 'setup_commands',
  SECRETS = 'secrets',
  PLANNING_STATEMENT = 'planning_statement'
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// GitHub Integration Types
export interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  description?: string;
  html_url: string;
  default_branch: string;
  private: boolean;
}

export interface PullRequest {
  id: number;
  number: number;
  title: string;
  body?: string;
  state: 'open' | 'closed' | 'merged';
  html_url: string;
  created_at: string;
  updated_at: string;
  merged_at?: string;
}

// Notification Types
export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  project_id?: string;
  agent_run_id?: string;
}

export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error'
}

// Form Types
export interface CreateProjectForm {
  name: string;
  description?: string;
  github_repository: string;
  default_branch: string;
  auto_confirm_plan: boolean;
  auto_merge_validated_pr: boolean;
}

export interface UpdateProjectConfigurationForm {
  repository_rules?: string;
  setup_commands?: string;
  planning_statement?: string;
}

export interface CreateSecretForm {
  key: string;
  value: string;
}

export interface AgentRunForm {
  target_text: string;
}

// Theme and UI Types
export interface ThemeConfig {
  mode: 'light' | 'dark';
  primaryColor: string;
  secondaryColor: string;
}

export interface UIPreferences {
  theme: ThemeConfig;
  autoRefresh: boolean;
  refreshInterval: number;
  showNotifications: boolean;
}
