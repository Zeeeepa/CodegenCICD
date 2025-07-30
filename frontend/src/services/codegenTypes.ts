/**
 * Codegen API Types
 */

export interface CodegenUser {
  id: number;
  github_username: string;
  full_name?: string;
  email?: string;
  avatar_url?: string;
}

export interface CodegenOrganization {
  id: number;
  name: string;
  slug: string;
  description?: string;
}

export interface CodegenAgentRun {
  id: number;
  org_id: number;
  prompt: string;
  status: AgentRunStatus;
  result?: string;
  error?: string;
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

export interface CodegenHealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy';
  user_id?: number;
  response_time_seconds?: number;
  timestamp: string;
}

export interface CodegenClientStats {
  config?: {
    base_url: string;
    timeout: number;
  };
  metrics?: {
    total_requests: number;
    error_rate: number;
    average_response_time?: number;
  };
  cache?: {
    hit_rate_percentage?: number;
    size: number;
  };
}

export interface CodegenBulkProgress {
  total: number;
  completed: number;
  failed: number;
  in_progress: number;
}

export interface CodegenWebhookEvent {
  eventType: string;
  payload: any;
  timestamp: Date;
}

export interface CodegenPaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface CreateCodegenAgentRunRequest {
  prompt: string;
  metadata?: Record<string, any>;
}

export class CodegenAPIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: any
  ) {
    super(message);
    this.name = 'CodegenAPIError';
  }
}

export class AuthenticationError extends CodegenAPIError {
  constructor(message: string = 'Authentication failed') {
    super(message, 401, 'AUTHENTICATION_ERROR');
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends CodegenAPIError {
  constructor(
    message: string = 'Rate limit exceeded',
    public retry_after: number = 60
  ) {
    super(message, 429, 'RATE_LIMIT_ERROR');
    this.name = 'RateLimitError';
  }
}

export class ValidationError extends CodegenAPIError {
  constructor(
    message: string = 'Validation failed',
    public details?: Record<string, string[]>
  ) {
    super(message, 400, 'VALIDATION_ERROR', details);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends CodegenAPIError {
  constructor(message: string = 'Resource not found') {
    super(message, 404, 'NOT_FOUND_ERROR');
    this.name = 'NotFoundError';
  }
}

export class ServerError extends CodegenAPIError {
  constructor(message: string = 'Internal server error') {
    super(message, 500, 'SERVER_ERROR');
    this.name = 'ServerError';
  }
}

