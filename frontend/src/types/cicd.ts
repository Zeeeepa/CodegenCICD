/**
 * Core CICD system types and interfaces
 */

// ============================================================================
// ENUMS
// ============================================================================

export enum ProjectStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error',
  CONFIGURING = 'configuring'
}

export enum WorkflowStatus {
  IDLE = 'idle',
  RUNNING = 'running',
  VALIDATING = 'validating',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export enum ValidationStage {
  PENDING = 'pending',
  SNAPSHOT_CREATING = 'snapshot_creating',
  CLONING = 'cloning',
  SETUP_RUNNING = 'setup_running',
  GRAPH_SITTER_ANALYSIS = 'graph_sitter_analysis',
  WEB_EVAL_TESTING = 'web_eval_testing',
  VALIDATION_COMPLETE = 'validation_complete',
  AUTO_MERGE_DECISION = 'auto_merge_decision',
  MERGED = 'merged',
  FAILED = 'failed'
}

export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error'
}

export enum AgentRunType {
  REGULAR = 'regular',
  PLAN = 'plan',
  PR = 'pr'
}

// ============================================================================
// CORE INTERFACES
// ============================================================================

export interface Project {
  id: string;
  name: string;
  fullName: string; // owner/repo
  owner: string;
  repo: string;
  description?: string;
  defaultBranch: string;
  url: string;
  cloneUrl: string;
  status: ProjectStatus;
  webhookUrl?: string;
  webhookSecret?: string;
  createdAt: string;
  updatedAt: string;
  
  // Configuration
  settings: ProjectSettings;
  
  // Current state
  currentWorkflow?: WorkflowRun;
  lastValidation?: ValidationRun;
  activePRs: PullRequest[];
  
  // Statistics
  stats: ProjectStats;
}

export interface ProjectSettings {
  // Agent configuration
  autoConfirmPlan: boolean;
  planningStatement: string;
  repositoryRules: string;
  
  // Deployment configuration
  setupCommands: string;
  selectedBranch: string;
  availableBranches: string[];
  
  // Secrets and environment
  secrets: Record<string, string>;
  environmentVariables: Record<string, string>;
  
  // Validation settings
  autoMergeValidatedPR: boolean;
  validationTimeout: number; // in minutes
  retryAttempts: number;
  
  // Webhook settings
  webhookEnabled: boolean;
  webhookEvents: string[];
}

export interface ProjectStats {
  totalRuns: number;
  successfulRuns: number;
  failedRuns: number;
  averageValidationTime: number; // in minutes
  lastRunDate?: string;
  successRate: number; // percentage
}

// ============================================================================
// WORKFLOW INTERFACES
// ============================================================================

export interface WorkflowRun {
  id: string;
  projectId: string;
  agentRunId?: number;
  status: WorkflowStatus;
  stage: ValidationStage;
  startedAt: string;
  completedAt?: string;
  duration?: number; // in seconds
  
  // Trigger information
  triggeredBy: 'manual' | 'webhook' | 'schedule';
  triggerData?: any;
  
  // Agent run details
  prompt: string;
  planningStatement: string;
  agentRunType: AgentRunType;
  
  // Validation details
  validationRun?: ValidationRun;
  
  // Results
  result?: WorkflowResult;
  error?: WorkflowError;
  
  // Progress tracking
  progress: WorkflowProgress;
}

export interface WorkflowResult {
  success: boolean;
  pullRequest?: PullRequest;
  validationResults: ValidationResult[];
  autoMerged: boolean;
  message: string;
}

export interface WorkflowError {
  stage: ValidationStage;
  message: string;
  details?: any;
  retryable: boolean;
  retryCount: number;
}

export interface WorkflowProgress {
  currentStage: ValidationStage;
  completedStages: ValidationStage[];
  totalStages: number;
  percentage: number;
  estimatedTimeRemaining?: number; // in seconds
  logs: WorkflowLog[];
}

export interface WorkflowLog {
  timestamp: string;
  stage: ValidationStage;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  details?: any;
}

// ============================================================================
// VALIDATION INTERFACES
// ============================================================================

export interface ValidationRun {
  id: string;
  workflowRunId: string;
  projectId: string;
  pullRequestId: string;
  status: ValidationStage;
  startedAt: string;
  completedAt?: string;
  
  // Snapshot details
  snapshotId?: string;
  snapshotUrl?: string;
  
  // Validation steps
  steps: ValidationStep[];
  
  // Results
  results: ValidationResult[];
  
  // Error handling
  errors: ValidationError[];
  retryCount: number;
}

export interface ValidationStep {
  id: string;
  name: string;
  stage: ValidationStage;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  logs: string[];
  result?: any;
  error?: string;
}

export interface ValidationResult {
  step: string;
  stage: ValidationStage;
  success: boolean;
  score?: number; // 0-100
  message: string;
  details?: any;
  artifacts?: string[]; // URLs to artifacts
}

export interface ValidationError {
  step: string;
  stage: ValidationStage;
  message: string;
  details?: any;
  retryable: boolean;
  timestamp: string;
}

// ============================================================================
// PULL REQUEST INTERFACES
// ============================================================================

export interface PullRequest {
  id: string;
  number: number;
  title: string;
  description: string;
  url: string;
  branch: string;
  baseBranch: string;
  author: string;
  status: 'open' | 'closed' | 'merged';
  createdAt: string;
  updatedAt: string;
  
  // Validation status
  validationStatus?: ValidationStage;
  validationRunId?: string;
  
  // Auto-merge eligibility
  autoMergeEligible: boolean;
  autoMergeBlocked?: string; // reason if blocked
  
  // Files changed
  filesChanged: number;
  additions: number;
  deletions: number;
  
  // Checks and reviews
  checksStatus: 'pending' | 'success' | 'failure';
  reviewsStatus: 'pending' | 'approved' | 'changes_requested';
}

// ============================================================================
// WEBHOOK INTERFACES
// ============================================================================

export interface WebhookEvent {
  id: string;
  projectId: string;
  eventType: string;
  payload: any;
  signature?: string;
  receivedAt: string;
  processed: boolean;
  processedAt?: string;
  
  // Processing results
  triggeredWorkflow?: string;
  error?: string;
}

export interface WebhookConfig {
  url: string;
  secret: string;
  events: string[];
  active: boolean;
  lastDelivery?: string;
  deliveryCount: number;
  errorCount: number;
}

// ============================================================================
// NOTIFICATION INTERFACES
// ============================================================================

export interface Notification {
  id: string;
  projectId?: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  
  // Action buttons
  actions?: NotificationAction[];
  
  // Auto-dismiss
  autoDismiss?: boolean;
  dismissAfter?: number; // seconds
}

export interface NotificationAction {
  id: string;
  label: string;
  action: string;
  variant: 'primary' | 'secondary' | 'danger';
  data?: any;
}

// ============================================================================
// DASHBOARD STATE INTERFACES
// ============================================================================

export interface DashboardState {
  // Projects
  projects: Record<string, Project>;
  selectedProjectId?: string;
  
  // Workflows
  activeWorkflows: Record<string, WorkflowRun>;
  workflowHistory: WorkflowRun[];
  
  // Notifications
  notifications: Notification[];
  unreadCount: number;
  
  // UI State
  loading: boolean;
  error?: string;
  
  // Settings
  globalSettings: GlobalSettings;
}

export interface GlobalSettings {
  // Default values
  defaultPlanningStatement: string;
  defaultValidationTimeout: number;
  defaultRetryAttempts: number;
  
  // UI preferences
  theme: 'light' | 'dark' | 'auto';
  autoRefreshInterval: number; // seconds
  showNotifications: boolean;
  
  // Integration settings
  githubToken?: string;
  codegenOrgId?: string;
  codegenApiToken?: string;
  cloudflareWorkerUrl?: string;
  
  // Advanced settings
  debugMode: boolean;
  logLevel: 'error' | 'warn' | 'info' | 'debug';
}

// ============================================================================
// API RESPONSE INTERFACES
// ============================================================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

export interface PaginatedResponse<T = any> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

// ============================================================================
// SERVICE INTERFACES
// ============================================================================

export interface ServiceConfig {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
  retries?: number;
}

export interface GrainchainConfig extends ServiceConfig {
  snapshotTemplate?: string;
  environmentVariables?: Record<string, string>;
}

export interface WebEvalConfig extends ServiceConfig {
  geminiApiKey: string;
  testSuites?: string[];
  validationCriteria?: string[];
}

export interface CloudflareConfig extends ServiceConfig {
  accountId: string;
  workerName: string;
  workerUrl: string;
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export type ProjectId = string;
export type WorkflowRunId = string;
export type ValidationRunId = string;
export type PullRequestId = string;
export type WebhookEventId = string;

export type EventHandler<T = any> = (event: T) => void | Promise<void>;
export type ProgressCallback = (progress: WorkflowProgress) => void;
export type ErrorCallback = (error: WorkflowError) => void;

// ============================================================================
// CONSTANTS
// ============================================================================

export const DEFAULT_PLANNING_STATEMENT = `You are an expert software engineer working on the project: <Project='{projectName}'>. 

Please analyze the following requirements and create a comprehensive implementation plan:

{userInput}

Consider the project's existing codebase, architecture, and best practices. Provide a detailed plan that includes:
1. Technical approach and implementation strategy
2. File changes and new components needed
3. Testing requirements and validation criteria
4. Potential risks and mitigation strategies
5. Timeline and dependencies

Ensure the solution is production-ready, well-tested, and follows the project's coding standards.`;

export const DEFAULT_VALIDATION_TIMEOUT = 30; // minutes
export const DEFAULT_RETRY_ATTEMPTS = 3;
export const DEFAULT_AUTO_REFRESH_INTERVAL = 30; // seconds

export const WEBHOOK_EVENTS = [
  'pull_request',
  'push',
  'issues',
  'issue_comment',
  'pull_request_review',
  'pull_request_review_comment',
  'check_run',
  'check_suite'
] as const;

export const VALIDATION_STAGES_ORDER: ValidationStage[] = [
  ValidationStage.PENDING,
  ValidationStage.SNAPSHOT_CREATING,
  ValidationStage.CLONING,
  ValidationStage.SETUP_RUNNING,
  ValidationStage.GRAPH_SITTER_ANALYSIS,
  ValidationStage.WEB_EVAL_TESTING,
  ValidationStage.VALIDATION_COMPLETE,
  ValidationStage.AUTO_MERGE_DECISION
];
