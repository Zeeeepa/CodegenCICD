/**
 * TypeScript types and interfaces for Codegen API
 */

// ============================================================================
// ENUMS
// ============================================================================

export enum SourceType {
  LOCAL = "LOCAL",
  SLACK = "SLACK",
  GITHUB = "GITHUB",
  GITHUB_CHECK_SUITE = "GITHUB_CHECK_SUITE",
  LINEAR = "LINEAR",
  API = "API",
  CHAT = "CHAT",
  JIRA = "JIRA"
}

export enum MessageType {
  ACTION = "ACTION",
  PLAN_EVALUATION = "PLAN_EVALUATION",
  FINAL_ANSWER = "FINAL_ANSWER",
  ERROR = "ERROR",
  USER_MESSAGE = "USER_MESSAGE",
  USER_GITHUB_ISSUE_COMMENT = "USER_GITHUB_ISSUE_COMMENT",
  INITIAL_PR_GENERATION = "INITIAL_PR_GENERATION",
  DETECT_PR_ERRORS = "DETECT_PR_ERRORS",
  FIX_PR_ERRORS = "FIX_PR_ERRORS",
  PR_CREATION_FAILED = "PR_CREATION_FAILED",
  PR_EVALUATION = "PR_EVALUATION",
  COMMIT_EVALUATION = "COMMIT_EVALUATION",
  AGENT_RUN_LINK = "AGENT_RUN_LINK"
}

export enum AgentRunStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
  PAUSED = "paused"
}

export enum LogLevel {
  DEBUG = "DEBUG",
  INFO = "INFO",
  WARNING = "WARNING",
  ERROR = "ERROR",
  CRITICAL = "CRITICAL"
}

// ============================================================================
// INTERFACES AND TYPES
// ============================================================================

export interface UserResponse {
  id: number;
  email?: string;
  github_user_id: string;
  github_username: string;
  avatar_url?: string;
  full_name?: string;
}

export interface GithubPullRequestResponse {
  id: number;
  title: string;
  url: string;
  created_at: string;
}

export interface AgentRunResponse {
  id: number;
  organization_id: number;
  status?: string;
  created_at?: string;
  web_url?: string;
  result?: string;
  source_type?: SourceType;
  github_pull_requests?: GithubPullRequestResponse[];
  metadata?: Record<string, any>;
}

export interface AgentRunLogResponse {
  agent_run_id: number;
  created_at: string;
  message_type: string;
  thought?: string;
  tool_name?: string;
  tool_input?: Record<string, any>;
  tool_output?: Record<string, any>;
  observation?: Record<string, any> | string;
}

export interface OrganizationSettings {
  // Add specific settings fields as they become available
}

export interface OrganizationResponse {
  id: number;
  name: string;
  settings: OrganizationSettings;
}

export interface PaginatedResponse {
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface UsersResponse extends PaginatedResponse {
  items: UserResponse[];
}

export interface AgentRunsResponse extends PaginatedResponse {
  items: AgentRunResponse[];
}

export interface OrganizationsResponse extends PaginatedResponse {
  items: OrganizationResponse[];
}

export interface AgentRunWithLogsResponse {
  id: number;
  organization_id: number;
  logs: AgentRunLogResponse[];
  status?: string;
  created_at?: string;
  web_url?: string;
  result?: string;
  metadata?: Record<string, any>;
  total_logs?: number;
  page?: number;
  size?: number;
  pages?: number;
}

export interface WebhookEvent {
  event_type: string;
  data: Record<string, any>;
  timestamp: string;
  signature?: string;
}

export interface BulkOperationResult<T = any> {
  total_items: number;
  successful_items: number;
  failed_items: number;
  success_rate: number;
  duration_seconds: number;
  errors: Array<{
    index: number;
    item: string;
    error: string;
    error_type: string;
  }>;
  results: T[];
}

export interface RequestMetrics {
  method: string;
  endpoint: string;
  status_code: number;
  duration_seconds: number;
  timestamp: string;
  request_id: string;
  cached?: boolean;
}

export interface ClientStats {
  uptime_seconds: number;
  total_requests: number;
  total_errors: number;
  error_rate: number;
  requests_per_minute: number;
  average_response_time: number;
  cache_hit_rate: number;
  status_code_distribution: Record<number, number>;
  recent_requests: RequestMetrics[];
}

// ============================================================================
// CONFIGURATION INTERFACES
// ============================================================================

export interface ClientConfig {
  // Core settings
  api_token: string;
  org_id: string;
  base_url: string;

  // Performance settings
  timeout: number;
  max_retries: number;
  retry_delay: number;
  retry_backoff_factor: number;

  // Rate limiting
  rate_limit_requests_per_period: number;
  rate_limit_period_seconds: number;
  rate_limit_buffer: number;

  // Caching
  enable_caching: boolean;
  cache_ttl_seconds: number;
  cache_max_size: number;

  // Features
  enable_webhooks: boolean;
  enable_bulk_operations: boolean;
  enable_streaming: boolean;
  enable_metrics: boolean;

  // Bulk operations
  bulk_max_workers: number;
  bulk_batch_size: number;

  // Logging
  log_level: string;
  log_requests: boolean;
  log_responses: boolean;
  log_request_bodies: boolean;

  // Webhook settings
  webhook_secret?: string;

  // User agent
  user_agent: string;
}

// ============================================================================
// ERROR INTERFACES
// ============================================================================

export interface ValidationError extends Error {
  field_errors?: Record<string, string[]>;
}

export interface CodegenAPIError extends Error {
  status_code: number;
  response_data?: Record<string, any>;
  request_id?: string;
}

export interface RateLimitError extends CodegenAPIError {
  retry_after: number;
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export type ProgressCallback = (completed: number, total: number) => void;

export type WebhookHandler = (payload: Record<string, any>) => void;

export type WebhookMiddleware = (payload: Record<string, any>) => Record<string, any>;

export interface CacheStats {
  size: number;
  max_size: number;
  hits: number;
  misses: number;
  hit_rate_percentage: number;
  ttl_seconds: number;
}

export interface RateLimitUsage {
  current_requests: number;
  max_requests: number;
  period_seconds: number;
  usage_percentage: number;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  response_time_seconds?: number;
  user_id?: number;
  timestamp: string;
  error?: string;
}
