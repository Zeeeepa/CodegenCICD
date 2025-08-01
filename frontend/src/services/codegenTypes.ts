/**
 * Codegen API Types
 */

export interface ClientConfig {
  apiKey?: string;
  orgId?: number;
  baseUrl?: string;
  timeout?: number;
  retries?: number;
  max_retries?: number;
  rateLimit?: {
    maxRequests: number;
    windowMs: number;
  };
  cache?: {
    enabled: boolean;
    ttl: number;
  };
  rate_limit_requests_per_period?: number;
  rate_limit_period_seconds?: number;
  enable_caching?: boolean;
  cache_max_size?: number;
  cache_ttl_seconds?: number;
  enable_metrics?: boolean;
  enable_webhooks?: boolean;
  webhook_secret?: string;
  max_concurrent_requests?: number;
  request_timeout_seconds?: number;
  retry_backoff_factor?: number;
  retry_delay?: number;
  max_retry_delay_seconds?: number;
  log_requests?: boolean;
  log_request_bodies?: boolean;
  log_responses?: boolean;
  user_agent?: string;
  enable_bulk_operations?: boolean;
  enable_streaming?: boolean;
  bulk_max_workers?: number;
}

export enum AgentRunStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface AgentRun {
  id: number;
  status: AgentRunStatus;
  prompt: string;
  orgId: number;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  error?: string;
}

export interface Organization {
  id: number;
  name: string;
  slug: string;
  createdAt: string;
}

export interface UserResponse {
  id: number;
  email: string;
  name?: string;
  created_at: string;
  updated_at: string;
  github_user_id?: string;
  github_username?: string;
  avatar_url?: string;
  full_name?: string;
}

export interface AgentRunResponse {
  id: number;
  organization_id?: number;
  status: string;
  created_at: string;
  updated_at?: string;
  logs?: string[] | LogEntry[];
  web_url?: string;
  result?: any;
  source_type?: SourceType;
  github_pull_requests?: any[];
  metadata?: any;
}

export interface AgentRunsResponse {
  items: AgentRunResponse[];
  total: number;
  page?: number;
  per_page?: number;
  size?: number;
  pages?: number;
}

export interface UsersResponse {
  items: UserResponse[];
  total: number;
  page?: number;
  per_page?: number;
  size?: number;
  pages?: number;
}

export interface OrganizationsResponse {
  items: Organization[];
  total: number;
  page?: number;
  per_page?: number;
  size?: number;
  pages?: number;
}

export interface AgentRunWithLogsResponse extends AgentRunResponse {
  logs: LogEntry[];
  total_logs?: number;
  page?: number;
  size?: number;
  pages?: number;
}

export interface LogEntry {
  id: number;
  message: string;
  level: string;
  created_at: string;
  metadata?: any;
}

export interface BulkOperationResult<T = any> {
  success: number;
  failed: number;
  total: number;
  errors?: string[];
  results?: T[];
}

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  version?: string;
  uptime?: number;
  response_time_seconds?: number;
  user_id?: number;
  error?: string;
}

export enum SourceType {
  GITHUB = 'github',
  GITLAB = 'gitlab',
  BITBUCKET = 'bitbucket',
  LOCAL = 'local'
}

export type ProgressCallback = (progress: {
  completed: number;
  total: number;
  percentage: number;
}) => void;

export interface User {
  id: number;
  name: string;
  email: string;
  createdAt: string;
}

export interface AgentRunLog {
  id: number;
  agentRunId: number;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  timestamp: string;
}

export interface BulkOperation {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  total: number;
  results: any[];
}

export interface Webhook {
  id: number;
  url: string;
  events: string[];
  active: boolean;
  secret?: string;
  createdAt: string;
}

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

export interface RequestMetrics {
  method: string;
  endpoint: string;
  status_code: number;
  duration_seconds: number;
  timestamp: string;
  request_id: string;
  cached: boolean;
}

export interface ClientStats {
  uptime_seconds: number;
  total_requests: number;
  total_errors: number;
  error_rate: number;
  requests_per_minute: number;
  average_response_time: number;
  cache_hit_rate: number;
  status_code_distribution: Record<string, number>;
  recent_requests: RequestMetrics[];
  cache?: CacheStats;
  rateLimit?: RateLimitUsage;
  metrics?: RequestMetrics;
}

export type WebhookHandler = (payload: Record<string, any>) => void;

export interface WebhookMiddleware {
  before?: (event: string, data: any) => Promise<any>;
  after?: (event: string, data: any, result: any) => Promise<void>;
  error?: (event: string, data: any, error: Error) => Promise<void>;
}

export interface HealthCheck {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  services: Record<string, 'up' | 'down'>;
}
