/**
 * Configuration management for Codegen client
 */

import { ClientConfig } from './codegenTypes';

// ============================================================================
// DEFAULT CONFIGURATION
// ============================================================================

export const DEFAULT_CONFIG: ClientConfig = {
  // Core settings
  api_token: process.env.REACT_APP_CODEGEN_API_TOKEN || '',
  org_id: process.env.REACT_APP_CODEGEN_ORG_ID || '',
  base_url: process.env.REACT_APP_CODEGEN_BASE_URL || 'https://api.codegen.com/v1',

  // Performance settings
  timeout: parseInt(process.env.REACT_APP_CODEGEN_TIMEOUT || '30000'),
  max_retries: parseInt(process.env.REACT_APP_CODEGEN_MAX_RETRIES || '3'),
  retry_delay: parseFloat(process.env.REACT_APP_CODEGEN_RETRY_DELAY || '1000'),
  retry_backoff_factor: parseFloat(process.env.REACT_APP_CODEGEN_RETRY_BACKOFF || '2.0'),

  // Rate limiting
  rate_limit_requests_per_period: parseInt(process.env.REACT_APP_CODEGEN_RATE_LIMIT_REQUESTS || '60'),
  rate_limit_period_seconds: parseInt(process.env.REACT_APP_CODEGEN_RATE_LIMIT_PERIOD || '60'),
  rate_limit_buffer: 0.1,

  // Caching
  enable_caching: (process.env.REACT_APP_CODEGEN_ENABLE_CACHING || 'true').toLowerCase() === 'true',
  cache_ttl_seconds: parseInt(process.env.REACT_APP_CODEGEN_CACHE_TTL || '300'),
  cache_max_size: parseInt(process.env.REACT_APP_CODEGEN_CACHE_MAX_SIZE || '128'),

  // Features
  enable_webhooks: (process.env.REACT_APP_CODEGEN_ENABLE_WEBHOOKS || 'true').toLowerCase() === 'true',
  enable_bulk_operations: (process.env.REACT_APP_CODEGEN_ENABLE_BULK_OPERATIONS || 'true').toLowerCase() === 'true',
  enable_streaming: (process.env.REACT_APP_CODEGEN_ENABLE_STREAMING || 'true').toLowerCase() === 'true',
  enable_metrics: (process.env.REACT_APP_CODEGEN_ENABLE_METRICS || 'true').toLowerCase() === 'true',

  // Bulk operations
  bulk_max_workers: parseInt(process.env.REACT_APP_CODEGEN_BULK_MAX_WORKERS || '5'),
  bulk_batch_size: parseInt(process.env.REACT_APP_CODEGEN_BULK_BATCH_SIZE || '100'),

  // Logging
  log_level: process.env.REACT_APP_CODEGEN_LOG_LEVEL || 'INFO',
  log_requests: (process.env.REACT_APP_CODEGEN_LOG_REQUESTS || 'true').toLowerCase() === 'true',
  log_responses: (process.env.REACT_APP_CODEGEN_LOG_RESPONSES || 'false').toLowerCase() === 'true',
  log_request_bodies: (process.env.REACT_APP_CODEGEN_LOG_REQUEST_BODIES || 'false').toLowerCase() === 'true',

  // Webhook settings
  webhook_secret: process.env.REACT_APP_CODEGEN_WEBHOOK_SECRET,

  // User agent
  user_agent: 'codegen-typescript-client/1.0.0'
};

// ============================================================================
// CONFIGURATION PRESETS
// ============================================================================

export class ConfigPresets {
  /**
   * Development configuration with verbose logging and lower limits
   */
  static development(): ClientConfig {
    return {
      ...DEFAULT_CONFIG,
      timeout: 60000,
      max_retries: 1,
      rate_limit_requests_per_period: 30,
      cache_ttl_seconds: 60,
      log_level: 'DEBUG',
      log_requests: true,
      log_responses: true,
      log_request_bodies: true
    };
  }

  /**
   * Production configuration with optimized settings
   */
  static production(): ClientConfig {
    return {
      ...DEFAULT_CONFIG,
      timeout: 30000,
      max_retries: 3,
      rate_limit_requests_per_period: 100,
      cache_ttl_seconds: 300,
      log_level: 'INFO',
      log_requests: true,
      log_responses: false,
      log_request_bodies: false
    };
  }

  /**
   * High performance configuration for heavy workloads
   */
  static highPerformance(): ClientConfig {
    return {
      ...DEFAULT_CONFIG,
      timeout: 45000,
      max_retries: 5,
      rate_limit_requests_per_period: 200,
      cache_ttl_seconds: 600,
      cache_max_size: 256,
      bulk_max_workers: 10,
      bulk_batch_size: 200,
      log_level: 'WARNING'
    };
  }

  /**
   * Testing configuration with minimal caching and retries
   */
  static testing(): ClientConfig {
    return {
      ...DEFAULT_CONFIG,
      timeout: 10000,
      max_retries: 1,
      enable_caching: false,
      rate_limit_requests_per_period: 10,
      log_level: 'DEBUG'
    };
  }
}

// ============================================================================
// CONFIGURATION VALIDATION
// ============================================================================

export function validateConfig(config: ClientConfig): void {
  if (!config.api_token) {
    throw new Error(
      'API token is required. Set REACT_APP_CODEGEN_API_TOKEN environment variable or provide it directly.'
    );
  }

  if (!config.org_id) {
    throw new Error(
      'Organization ID is required. Set REACT_APP_CODEGEN_ORG_ID environment variable or provide it directly.'
    );
  }

  if (config.timeout <= 0) {
    throw new Error('Timeout must be greater than 0');
  }

  if (config.max_retries < 0) {
    throw new Error('Max retries must be >= 0');
  }

  if (config.rate_limit_requests_per_period <= 0) {
    throw new Error('Rate limit requests per period must be greater than 0');
  }

  if (config.rate_limit_period_seconds <= 0) {
    throw new Error('Rate limit period must be greater than 0');
  }

  if (config.cache_max_size <= 0) {
    throw new Error('Cache max size must be greater than 0');
  }

  if (config.cache_ttl_seconds <= 0) {
    throw new Error('Cache TTL must be greater than 0');
  }
}

// ============================================================================
// CONFIGURATION BUILDER
// ============================================================================

export class ConfigBuilder {
  private config: Partial<ClientConfig> = {};

  constructor(baseConfig?: Partial<ClientConfig>) {
    if (baseConfig) {
      this.config = { ...baseConfig };
    }
  }

  /**
   * Set API credentials
   */
  credentials(apiToken: string, orgId: string): ConfigBuilder {
    this.config.api_token = apiToken;
    this.config.org_id = orgId;
    return this;
  }

  /**
   * Set base URL
   */
  baseUrl(url: string): ConfigBuilder {
    this.config.base_url = url;
    return this;
  }

  /**
   * Set timeout in milliseconds
   */
  timeout(ms: number): ConfigBuilder {
    this.config.timeout = ms;
    return this;
  }

  /**
   * Set retry configuration
   */
  retries(maxRetries: number, delay: number = 1000, backoffFactor: number = 2.0): ConfigBuilder {
    this.config.max_retries = maxRetries;
    this.config.retry_delay = delay;
    this.config.retry_backoff_factor = backoffFactor;
    return this;
  }

  /**
   * Set rate limiting configuration
   */
  rateLimit(requestsPerPeriod: number, periodSeconds: number = 60): ConfigBuilder {
    this.config.rate_limit_requests_per_period = requestsPerPeriod;
    this.config.rate_limit_period_seconds = periodSeconds;
    return this;
  }

  /**
   * Set caching configuration
   */
  caching(enabled: boolean, ttlSeconds: number = 300, maxSize: number = 128): ConfigBuilder {
    this.config.enable_caching = enabled;
    this.config.cache_ttl_seconds = ttlSeconds;
    this.config.cache_max_size = maxSize;
    return this;
  }

  /**
   * Enable/disable features
   */
  features(options: {
    webhooks?: boolean;
    bulkOperations?: boolean;
    streaming?: boolean;
    metrics?: boolean;
  }): ConfigBuilder {
    if (options.webhooks !== undefined) {
      this.config.enable_webhooks = options.webhooks;
    }
    if (options.bulkOperations !== undefined) {
      this.config.enable_bulk_operations = options.bulkOperations;
    }
    if (options.streaming !== undefined) {
      this.config.enable_streaming = options.streaming;
    }
    if (options.metrics !== undefined) {
      this.config.enable_metrics = options.metrics;
    }
    return this;
  }

  /**
   * Set logging configuration
   */
  logging(options: {
    level?: string;
    requests?: boolean;
    responses?: boolean;
    requestBodies?: boolean;
  }): ConfigBuilder {
    if (options.level !== undefined) {
      this.config.log_level = options.level;
    }
    if (options.requests !== undefined) {
      this.config.log_requests = options.requests;
    }
    if (options.responses !== undefined) {
      this.config.log_responses = options.responses;
    }
    if (options.requestBodies !== undefined) {
      this.config.log_request_bodies = options.requestBodies;
    }
    return this;
  }

  /**
   * Set webhook secret
   */
  webhookSecret(secret: string): ConfigBuilder {
    this.config.webhook_secret = secret;
    return this;
  }

  /**
   * Set user agent
   */
  userAgent(userAgent: string): ConfigBuilder {
    this.config.user_agent = userAgent;
    return this;
  }

  /**
   * Build the final configuration
   */
  build(): ClientConfig {
    const finalConfig = { ...DEFAULT_CONFIG, ...this.config };
    validateConfig(finalConfig);
    return finalConfig;
  }
}

// ============================================================================
// ENVIRONMENT DETECTION
// ============================================================================

export function detectEnvironment(): 'development' | 'production' | 'test' {
  if (process.env.NODE_ENV === 'test') {
    return 'test';
  }
  if (process.env.NODE_ENV === 'production') {
    return 'production';
  }
  return 'development';
}

/**
 * Get configuration based on current environment
 */
export function getEnvironmentConfig(): ClientConfig {
  const env = detectEnvironment();
  
  switch (env) {
    case 'development':
      return ConfigPresets.development();
    case 'production':
      return ConfigPresets.production();
    case 'test':
      return ConfigPresets.testing();
    default:
      return DEFAULT_CONFIG;
  }
}
