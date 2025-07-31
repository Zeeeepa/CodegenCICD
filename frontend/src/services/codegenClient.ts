/**
 * Enhanced TypeScript Codegen API Client
 * 
 * This is a comprehensive TypeScript implementation of the Codegen API client
 * with full feature parity to the Python version, including:
 * - Rate limiting with sliding window
 * - Advanced caching with TTL support
 * - Retry logic with exponential backoff
 * - Request metrics and performance monitoring
 * - Webhook handling with signature verification
 * - Bulk operations with progress tracking
 * - Streaming with automatic pagination
 * - Configuration presets for different environments
 */

import {
  ClientConfig,
  UserResponse,
  AgentRunResponse,
  AgentRunsResponse,
  UsersResponse,
  OrganizationsResponse,
  AgentRunWithLogsResponse,
  BulkOperationResult,
  HealthCheckResponse,
  SourceType,
  AgentRunStatus,
  ProgressCallback
} from './codegenTypes';

import {
  CodegenAPIError,
  RateLimitError,
  AuthenticationError,
  NotFoundError,
  ConflictError,
  ServerError,
  TimeoutError,
  NetworkError,
  ValidationError,
  BulkOperationError
} from './codegenErrors';

import {
  RateLimiter,
  CacheManager,
  WebhookManager,
  MetricsCollector,
  retryWithBackoff,
  generateRequestId,
  validatePagination
} from './codegenUtils';

import { DEFAULT_CONFIG, validateConfig } from './codegenConfig';

// ============================================================================
// MAIN CLIENT CLASS
// ============================================================================

export class CodegenClient {
  private config: ClientConfig;
  private rateLimiter: RateLimiter;
  private cache?: CacheManager;
  private webhookManager?: WebhookManager;
  private metrics?: MetricsCollector;

  constructor(config?: Partial<ClientConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    validateConfig(this.config);

    // Initialize components
    this.rateLimiter = new RateLimiter(
      this.config.rate_limit_requests_per_period,
      this.config.rate_limit_period_seconds
    );

    if (this.config.enable_caching) {
      this.cache = new CacheManager(
        this.config.cache_max_size,
        this.config.cache_ttl_seconds
      );
    }

    if (this.config.enable_webhooks) {
      this.webhookManager = new WebhookManager(this.config.webhook_secret);
    }

    if (this.config.enable_metrics) {
      this.metrics = new MetricsCollector();
    }

    console.info(`Initialized CodegenClient with base URL: ${this.config.base_url}`);
  }

  // ========================================================================
  // PRIVATE METHODS
  // ========================================================================

  private async handleResponse(response: Response, requestId: string): Promise<any> {
    const statusCode = response.status;

    if (statusCode === 429) {
      const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
      throw new RateLimitError(retryAfter, requestId);
    }

    if (statusCode === 401) {
      throw new AuthenticationError('Invalid API token or insufficient permissions', requestId);
    } else if (statusCode === 404) {
      throw new NotFoundError('Requested resource not found', requestId);
    } else if (statusCode === 409) {
      throw new ConflictError('Resource conflict occurred', requestId);
    } else if (statusCode >= 500) {
      throw new ServerError(`Server error: ${statusCode}`, statusCode, requestId);
    } else if (!response.ok) {
      let message = `API request failed: ${statusCode}`;
      let errorData: any = null;
      
      try {
        errorData = await response.json();
        message = errorData.message || message;
      } catch {
        // Ignore JSON parsing errors
      }
      
      throw new CodegenAPIError(message, statusCode, errorData, requestId);
    }

    return response.json();
  }

  private async makeRequest(
    method: string,
    endpoint: string,
    options: {
      useCache?: boolean;
      body?: any;
      params?: Record<string, string | number>;
    } = {}
  ): Promise<any> {
    const requestId = generateRequestId();

    // Rate limiting
    await this.rateLimiter.waitIfNeeded();

    // Check cache
    let cacheKey: string | null = null;
    if (options.useCache && this.cache && method.toUpperCase() === 'GET') {
      cacheKey = `${method}:${endpoint}:${JSON.stringify(options.params || {})}`;
      const cachedResult = this.cache.get(cacheKey);
      if (cachedResult !== null) {
        if (this.config.log_requests) {
          console.debug(`Cache hit for ${endpoint} (request_id: ${requestId})`);
        }
        if (this.metrics) {
          this.metrics.recordRequest(method, endpoint, 0, 200, requestId, true);
        }
        return cachedResult;
      }
    }

    // Build URL with query parameters
    let url = `${this.config.base_url}${endpoint}`;
    if (options.params) {
      const searchParams = new URLSearchParams();
      Object.entries(options.params).forEach(([key, value]) => {
        searchParams.append(key, value.toString());
      });
      url += `?${searchParams.toString()}`;
    }

    // Prepare request options
    const fetchOptions: RequestInit = {
      method,
      headers: {
        'Authorization': `Bearer ${this.config.api_token}`,
        'User-Agent': this.config.user_agent,
        'Content-Type': 'application/json'
      },
      signal: AbortSignal.timeout(this.config.timeout)
    };

    if (options.body) {
      fetchOptions.body = JSON.stringify(options.body);
    }

    // Make request with retry logic
    const executeRequest = async (): Promise<any> => {
      const startTime = Date.now();

      if (this.config.log_requests) {
        console.info(`Making ${method} request to ${endpoint} (request_id: ${requestId})`);
        if (this.config.log_request_bodies && options.body) {
          console.debug('Request body:', JSON.stringify(options.body, null, 2));
        }
      }

      try {
        const response = await fetch(url, fetchOptions);
        const duration = (Date.now() - startTime) / 1000;

        if (this.config.log_requests) {
          console.info(
            `Request completed in ${duration.toFixed(2)}s - Status: ${response.status} (request_id: ${requestId})`
          );
        }

        if (this.config.log_responses && response.ok) {
          const responseText = await response.clone().text();
          console.debug('Response:', responseText);
        }

        // Record metrics
        if (this.metrics) {
          this.metrics.recordRequest(method, endpoint, duration, response.status, requestId);
        }

        const result = await this.handleResponse(response, requestId);

        // Cache successful GET requests
        if (cacheKey && response.ok && this.cache) {
          this.cache.set(cacheKey, result);
        }

        return result;

      } catch (error) {
        const duration = (Date.now() - startTime) / 1000;

        if (error instanceof DOMException && error.name === 'TimeoutError') {
          if (this.metrics) {
            this.metrics.recordRequest(method, endpoint, duration, 408, requestId);
          }
          throw new TimeoutError(`Request timed out after ${this.config.timeout}ms`, requestId);
        }

        if (error instanceof TypeError && error.message.includes('fetch')) {
          if (this.metrics) {
            this.metrics.recordRequest(method, endpoint, duration, 0, requestId);
          }
          throw new NetworkError(`Network error: ${error.message}`, requestId);
        }

        // Re-throw known errors
        if (error instanceof CodegenAPIError) {
          throw error;
        }

        console.error(`Request failed after ${duration.toFixed(2)}s:`, error, `(request_id: ${requestId})`);
        if (this.metrics) {
          this.metrics.recordRequest(method, endpoint, duration, 0, requestId);
        }
        throw error;
      }
    };

    return retryWithBackoff(
      executeRequest,
      this.config.max_retries,
      this.config.retry_backoff_factor,
      this.config.retry_delay
    );
  }

  // ========================================================================
  // USER ENDPOINTS
  // ========================================================================

  async getUsers(orgId: string, skip: number = 0, limit: number = 100): Promise<UsersResponse> {
    validatePagination(skip, limit);

    const response = await this.makeRequest('GET', `/organizations/${orgId}/users`, {
      useCache: true,
      params: { skip, limit }
    });

    return {
      items: response.items.map((user: any) => ({
        id: user.id || 0,
        email: user.email,
        github_user_id: user.github_user_id || '',
        github_username: user.github_username || '',
        avatar_url: user.avatar_url,
        full_name: user.full_name
      })).filter((user: UserResponse) => user.id && user.github_user_id && user.github_username),
      total: response.total,
      page: response.page,
      size: response.size,
      pages: response.pages
    };
  }

  async getUser(orgId: string, userId: string): Promise<UserResponse> {
    const response = await this.makeRequest('GET', `/organizations/${orgId}/users/${userId}`, {
      useCache: true
    });

    return {
      id: response.id || 0,
      email: response.email,
      github_user_id: response.github_user_id || '',
      github_username: response.github_username || '',
      avatar_url: response.avatar_url,
      full_name: response.full_name
    };
  }

  async getCurrentUser(): Promise<UserResponse> {
    const response = await this.makeRequest('GET', '/users/me', { useCache: true });
    
    return {
      id: response.id || 0,
      email: response.email,
      github_user_id: response.github_user_id || '',
      github_username: response.github_username || '',
      avatar_url: response.avatar_url,
      full_name: response.full_name
    };
  }

  // ========================================================================
  // ORGANIZATION ENDPOINTS
  // ========================================================================

  async getOrganizations(skip: number = 0, limit: number = 100): Promise<OrganizationsResponse> {
    validatePagination(skip, limit);

    const response = await this.makeRequest('GET', '/organizations', {
      useCache: true,
      params: { skip, limit }
    });

    return {
      items: response.items.map((org: any) => ({
        id: org.id,
        name: org.name,
        settings: {}
      })),
      total: response.total,
      page: response.page,
      size: response.size,
      pages: response.pages
    };
  }

  // ========================================================================
  // AGENT ENDPOINTS
  // ========================================================================

  async createAgentRun(
    orgId: number,
    prompt: string,
    images?: string[],
    metadata?: Record<string, any>
  ): Promise<AgentRunResponse> {
    // Validate inputs
    if (!prompt || prompt.trim().length === 0) {
      throw new ValidationError('Prompt cannot be empty');
    }
    if (prompt.length > 50000) {
      throw new ValidationError('Prompt cannot exceed 50,000 characters');
    }
    if (images && images.length > 10) {
      throw new ValidationError('Cannot include more than 10 images');
    }

    const data = { prompt, images, metadata };

    const response = await this.makeRequest('POST', `/organizations/${orgId}/agent/run`, {
      body: data
    });

    return this.parseAgentRunResponse(response);
  }

  async getAgentRun(orgId: number, agentRunId: number): Promise<AgentRunResponse> {
    const response = await this.makeRequest('GET', `/organizations/${orgId}/agent/run/${agentRunId}`, {
      useCache: true
    });

    return this.parseAgentRunResponse(response);
  }

  async listAgentRuns(
    orgId: number,
    options: {
      userId?: number;
      sourceType?: SourceType;
      skip?: number;
      limit?: number;
    } = {}
  ): Promise<AgentRunsResponse> {
    const { userId, sourceType, skip = 0, limit = 100 } = options;
    validatePagination(skip, limit);

    const params: Record<string, string | number> = { skip, limit };
    if (userId) params.user_id = userId;
    if (sourceType) params.source_type = sourceType;

    const response = await this.makeRequest('GET', `/organizations/${orgId}/agent/runs`, {
      useCache: true,
      params
    });

    return {
      items: response.items.map((run: any) => this.parseAgentRunResponse(run)),
      total: response.total,
      page: response.page,
      size: response.size,
      pages: response.pages
    };
  }

  async resumeAgentRun(
    orgId: number,
    agentRunId: number,
    prompt: string,
    images?: string[]
  ): Promise<AgentRunResponse> {
    if (!prompt || prompt.trim().length === 0) {
      throw new ValidationError('Prompt cannot be empty');
    }

    const data = { agent_run_id: agentRunId, prompt, images };

    const response = await this.makeRequest('POST', `/organizations/${orgId}/agent/run/resume`, {
      body: data
    });

    return this.parseAgentRunResponse(response);
  }

  private parseAgentRunResponse(data: any): AgentRunResponse {
    return {
      id: data.id,
      organization_id: data.organization_id,
      status: data.status,
      created_at: data.created_at,
      web_url: data.web_url,
      result: data.result,
      source_type: data.source_type ? data.source_type as SourceType : undefined,
      github_pull_requests: (data.github_pull_requests || [])
        .filter((pr: any) => pr.id && pr.title && pr.url && pr.created_at)
        .map((pr: any) => ({
          id: pr.id,
          title: pr.title,
          url: pr.url,
          created_at: pr.created_at
        })),
      metadata: data.metadata
    };
  }

  // ========================================================================
  // ALPHA ENDPOINTS
  // ========================================================================

  async getAgentRunLogs(
    orgId: number,
    agentRunId: number,
    skip: number = 0,
    limit: number = 100
  ): Promise<AgentRunWithLogsResponse> {
    validatePagination(skip, limit);

    const response = await this.makeRequest(
      'GET',
      `/organizations/${orgId}/agent/run/${agentRunId}/logs`,
      {
        useCache: true,
        params: { skip, limit }
      }
    );

    return {
      id: response.id,
      organization_id: response.organization_id,
      logs: response.logs.map((log: any) => ({
        agent_run_id: log.agent_run_id || 0,
        created_at: log.created_at || '',
        message_type: log.message_type || '',
        thought: log.thought,
        tool_name: log.tool_name,
        tool_input: log.tool_input,
        tool_output: log.tool_output,
        observation: log.observation
      })),
      status: response.status,
      created_at: response.created_at,
      web_url: response.web_url,
      result: response.result,
      metadata: response.metadata,
      total_logs: response.total_logs,
      page: response.page,
      size: response.size,
      pages: response.pages
    };
  }

  // ========================================================================
  // UTILITY METHODS
  // ========================================================================

  async waitForCompletion(
    orgId: number,
    agentRunId: number,
    pollInterval: number = 5000,
    timeout?: number
  ): Promise<AgentRunResponse> {
    const startTime = Date.now();

    while (true) {
      const run = await this.getAgentRun(orgId, agentRunId);

      if ([
        AgentRunStatus.COMPLETED,
        AgentRunStatus.FAILED,
        AgentRunStatus.CANCELLED
      ].includes(run.status as AgentRunStatus)) {
        return run;
      }

      if (timeout && (Date.now() - startTime) > timeout) {
        throw new TimeoutError(
          `Agent run ${agentRunId} did not complete within ${timeout}ms`
        );
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }

  async healthCheck(): Promise<HealthCheckResponse> {
    try {
      const startTime = Date.now();
      const user = await this.getCurrentUser();
      const duration = (Date.now() - startTime) / 1000;

      return {
        status: 'healthy',
        response_time_seconds: duration,
        user_id: user.id,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : String(error),
        timestamp: new Date().toISOString()
      };
    }
  }

  getStats(): Record<string, any> {
    const stats: Record<string, any> = {
      config: {
        base_url: this.config.base_url,
        timeout: this.config.timeout,
        max_retries: this.config.max_retries,
        rate_limit_requests_per_period: this.config.rate_limit_requests_per_period,
        caching_enabled: this.config.enable_caching,
        webhooks_enabled: this.config.enable_webhooks,
        bulk_operations_enabled: this.config.enable_bulk_operations,
        streaming_enabled: this.config.enable_streaming,
        metrics_enabled: this.config.enable_metrics
      }
    };

    if (this.metrics) {
      const clientStats = this.metrics.getStats();
      stats.metrics = {
        uptime_seconds: clientStats.uptime_seconds,
        total_requests: clientStats.total_requests,
        total_errors: clientStats.total_errors,
        error_rate: clientStats.error_rate,
        requests_per_minute: clientStats.requests_per_minute,
        average_response_time: clientStats.average_response_time,
        cache_hit_rate: clientStats.cache_hit_rate,
        status_code_distribution: clientStats.status_code_distribution
      };
    }

    if (this.cache) {
      stats.cache = this.cache.getStats();
    }

    stats.rate_limiter = this.rateLimiter.getCurrentUsage();

    return stats;
  }

  clearCache(): void {
    if (this.cache) {
      this.cache.clear();
      console.info('Cache cleared');
    }
  }

  resetMetrics(): void {
    if (this.metrics) {
      this.metrics.reset();
      console.info('Metrics reset');
    }
  }

  // ========================================================================
  // WEBHOOK METHODS
  // ========================================================================

  registerWebhookHandler(eventType: string, handler: (payload: Record<string, any>) => void): void {
    if (!this.webhookManager) {
      throw new Error('Webhooks are disabled. Enable them in configuration.');
    }
    this.webhookManager.registerHandler(eventType, handler);
  }

  registerWebhookMiddleware(middleware: (payload: Record<string, any>) => Record<string, any>): void {
    if (!this.webhookManager) {
      throw new Error('Webhooks are disabled. Enable them in configuration.');
    }
    this.webhookManager.registerMiddleware(middleware);
  }

  async handleWebhook(payload: Record<string, any>, signature?: string): Promise<void> {
    if (!this.webhookManager) {
      throw new Error('Webhooks are disabled. Enable them in configuration.');
    }
    return this.webhookManager.handleWebhook(payload, signature);
  }

  // ========================================================================
  // STREAMING METHODS
  // ========================================================================

  async* streamAllUsers(orgId: string): AsyncGenerator<UserResponse, void, unknown> {
    if (!this.config.enable_streaming) {
      throw new ValidationError('Streaming is disabled');
    }

    let skip = 0;
    while (true) {
      const response = await this.getUsers(orgId, skip, 100);
      
      for (const user of response.items) {
        yield user;
      }

      if (response.items.length < 100) {
        break;
      }
      skip += 100;
    }
  }

  async* streamAllAgentRuns(
    orgId: number,
    options: { userId?: number; sourceType?: SourceType } = {}
  ): AsyncGenerator<AgentRunResponse, void, unknown> {
    if (!this.config.enable_streaming) {
      throw new ValidationError('Streaming is disabled');
    }

    let skip = 0;
    while (true) {
      const response = await this.listAgentRuns(orgId, { ...options, skip, limit: 100 });
      
      for (const run of response.items) {
        yield run;
      }

      if (response.items.length < 100) {
        break;
      }
      skip += 100;
    }
  }

  // ========================================================================
  // BULK OPERATIONS
  // ========================================================================

  async bulkGetUsers(
    orgId: string,
    userIds: string[],
    progressCallback?: ProgressCallback
  ): Promise<BulkOperationResult<UserResponse>> {
    if (!this.config.enable_bulk_operations) {
      throw new BulkOperationError('Bulk operations are disabled');
    }

    return this.executeBulkOperation(
      userIds,
      async (userId) => this.getUser(orgId, userId),
      progressCallback
    );
  }

  async bulkCreateAgentRuns(
    orgId: number,
    runConfigs: Array<{
      prompt: string;
      images?: string[];
      metadata?: Record<string, any>;
    }>,
    progressCallback?: ProgressCallback
  ): Promise<BulkOperationResult<AgentRunResponse>> {
    if (!this.config.enable_bulk_operations) {
      throw new BulkOperationError('Bulk operations are disabled');
    }

    return this.executeBulkOperation(
      runConfigs,
      async (config) => this.createAgentRun(orgId, config.prompt, config.images, config.metadata),
      progressCallback
    );
  }

  private async executeBulkOperation<T, R>(
    items: T[],
    operation: (item: T) => Promise<R>,
    progressCallback?: ProgressCallback
  ): Promise<BulkOperationResult<R>> {
    const startTime = Date.now();
    const results: R[] = [];
    const errors: Array<{
      index: number;
      item: string;
      error: string;
      error_type: string;
    }> = [];

    let completed = 0;
    const maxConcurrent = this.config.bulk_max_workers;
    
    // Process items in batches
    for (let i = 0; i < items.length; i += maxConcurrent) {
      const batch = items.slice(i, i + maxConcurrent);
      const promises = batch.map(async (item, batchIndex) => {
        const itemIndex = i + batchIndex;
        try {
          const result = await operation(item);
          results[itemIndex] = result;
          return { success: true, index: itemIndex };
        } catch (error) {
          const errorInfo = {
            index: itemIndex,
            item: String(item),
            error: error instanceof Error ? error.message : String(error),
            error_type: error instanceof Error ? error.constructor.name : 'Unknown'
          };
          errors.push(errorInfo);
          return { success: false, index: itemIndex };
        }
      });

      await Promise.all(promises);
      completed += batch.length;

      if (progressCallback) {
        progressCallback(completed, items.length);
      }
    }

    const duration = (Date.now() - startTime) / 1000;
    const successfulItems = results.filter(r => r !== undefined).length;
    const successRate = items.length > 0 ? successfulItems / items.length : 0;

    return {
      total_items: items.length,
      successful_items: successfulItems,
      failed_items: errors.length,
      success_rate: successRate,
      duration_seconds: duration,
      errors,
      results: results.filter(r => r !== undefined)
    };
  }
}

// ============================================================================
// EXPORTS
// ============================================================================

export default CodegenClient;

// Re-export everything for convenience
export * from './codegenTypes';
export { 
  CodegenAPIError as CodegenAPIErrorClass,
  RateLimitError,
  AuthenticationError,
  NotFoundError,
  ConflictError,
  ServerError,
  TimeoutError,
  NetworkError
} from './codegenErrors';
export * from './codegenUtils';
export * from './codegenConfig';
