/**
 * Utility classes for Codegen client
 */

import { CacheStats, RateLimitUsage, RequestMetrics, ClientStats, WebhookHandler, WebhookMiddleware } from './codegenTypes';

// ============================================================================
// RATE LIMITER
// ============================================================================

export class RateLimiter {
  private requests: number[] = [];
  private readonly requestsPerPeriod: number;
  private readonly periodSeconds: number;

  constructor(requestsPerPeriod: number, periodSeconds: number) {
    this.requestsPerPeriod = requestsPerPeriod;
    this.periodSeconds = periodSeconds;
  }

  async waitIfNeeded(): Promise<void> {
    const now = Date.now() / 1000;
    
    // Remove old requests
    this.requests = this.requests.filter(
      requestTime => now - requestTime < this.periodSeconds
    );

    if (this.requests.length >= this.requestsPerPeriod) {
      const sleepTime = this.periodSeconds - (now - this.requests[0]);
      if (sleepTime > 0) {
        console.info(`Rate limit reached, sleeping for ${sleepTime.toFixed(2)}s`);
        await new Promise(resolve => setTimeout(resolve, sleepTime * 1000));
      }
    }

    this.requests.push(now);
  }

  getCurrentUsage(): RateLimitUsage {
    const now = Date.now() / 1000;
    const recentRequests = this.requests.filter(
      requestTime => now - requestTime < this.periodSeconds
    );

    return {
      current_requests: recentRequests.length,
      max_requests: this.requestsPerPeriod,
      period_seconds: this.periodSeconds,
      usage_percentage: (recentRequests.length / this.requestsPerPeriod) * 100
    };
  }
}

// ============================================================================
// CACHE MANAGER
// ============================================================================

interface CacheItem<T> {
  value: T;
  timestamp: number;
  accessCount: number;
}

export class CacheManager<T = any> {
  private cache = new Map<string, CacheItem<T>>();
  private readonly maxSize: number;
  private readonly ttlSeconds: number;
  private hits = 0;
  private misses = 0;

  constructor(maxSize: number = 128, ttlSeconds: number = 300) {
    this.maxSize = maxSize;
    this.ttlSeconds = ttlSeconds;
  }

  get(key: string): T | null {
    const item = this.cache.get(key);
    
    if (!item) {
      this.misses++;
      return null;
    }

    // Check if expired
    const now = Date.now() / 1000;
    if (now - item.timestamp > this.ttlSeconds) {
      this.cache.delete(key);
      this.misses++;
      return null;
    }

    this.hits++;
    item.accessCount++;
    return item.value;
  }

  set(key: string, value: T): void {
    // Evict oldest if at capacity
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      if (this.cache.size > 0) {
        const oldestKey = Array.from(this.cache.entries())
          .sort(([, a], [, b]) => a.timestamp - b.timestamp)[0][0];
        this.cache.delete(oldestKey);
      }
    }

    const now = Date.now() / 1000;
    this.cache.set(key, {
      value,
      timestamp: now,
      accessCount: 0
    });
  }

  clear(): void {
    this.cache.clear();
    this.hits = 0;
    this.misses = 0;
  }

  getStats(): CacheStats {
    const totalRequests = this.hits + this.misses;
    const hitRate = totalRequests > 0 ? (this.hits / totalRequests) * 100 : 0;

    return {
      size: this.cache.size,
      max_size: this.maxSize,
      hits: this.hits,
      misses: this.misses,
      hit_rate_percentage: hitRate,
      ttl_seconds: this.ttlSeconds
    };
  }
}

// ============================================================================
// WEBHOOK HANDLER
// ============================================================================



export class WebhookManager {
  private handlers = new Map<string, WebhookHandler[]>();
  private middleware: WebhookMiddleware[] = [];
  private secretKey?: string;

  constructor(secretKey?: string) {
    this.secretKey = secretKey;
  }

  registerHandler(eventType: string, handler: WebhookHandler): void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler);
    console.info(`Registered webhook handler for event type: ${eventType}`);
  }

  registerMiddleware(middleware: WebhookMiddleware): void {
    this.middleware.push(middleware);
  }

  async verifySignature(payload: string, signature: string): Promise<boolean> {
    if (!this.secretKey) {
      console.warn('No secret key configured for webhook signature verification');
      return true;
    }

    try {
      // Use Web Crypto API for HMAC verification
      const encoder = new TextEncoder();
      const key = await crypto.subtle.importKey(
        'raw',
        encoder.encode(this.secretKey),
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
      );

      const signatureBuffer = await crypto.subtle.sign('HMAC', key, encoder.encode(payload));
      const expectedSignature = 'sha256=' + Array.from(new Uint8Array(signatureBuffer))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');

      return expectedSignature === signature;
    } catch (error) {
      console.error('Error verifying webhook signature:', error);
      return false;
    }
  }

  async handleWebhook(payload: Record<string, any>, signature?: string): Promise<void> {
    try {
      // Verify signature if provided
      if (signature && !(await this.verifySignature(JSON.stringify(payload), signature))) {
        throw new Error('Invalid webhook signature');
      }

      // Apply middleware
      let processedPayload = payload;
      for (const middleware of this.middleware) {
        processedPayload = middleware(processedPayload);
      }

      const eventType = processedPayload.event_type;
      if (!eventType) {
        throw new Error('Missing event_type in webhook payload');
      }

      // Execute handlers
      const handlers = this.handlers.get(eventType);
      if (handlers) {
        for (const handler of handlers) {
          try {
            handler(processedPayload);
          } catch (error) {
            console.error(`Handler error for ${eventType}:`, error);
          }
        }
        console.info(`Successfully processed webhook event: ${eventType}`);
      } else {
        console.warn(`No handler registered for event type: ${eventType}`);
      }
    } catch (error) {
      console.error('Error processing webhook:', error);
      throw new Error(`Webhook processing failed: ${error}`);
    }
  }
}

// ============================================================================
// METRICS COLLECTOR
// ============================================================================

export class MetricsCollector {
  private requests: RequestMetrics[] = [];
  private readonly startTime = new Date();

  recordRequest(
    method: string,
    endpoint: string,
    duration: number,
    statusCode: number,
    requestId: string,
    cached: boolean = false
  ): void {
    const metric: RequestMetrics = {
      method,
      endpoint,
      status_code: statusCode,
      duration_seconds: duration,
      timestamp: new Date().toISOString(),
      request_id: requestId,
      cached
    };

    this.requests.push(metric);

    // Keep only recent requests (last 1000)
    if (this.requests.length > 1000) {
      this.requests = this.requests.slice(-1000);
    }
  }

  getStats(): ClientStats {
    if (this.requests.length === 0) {
      return {
        uptime_seconds: 0,
        total_requests: 0,
        total_errors: 0,
        error_rate: 0,
        requests_per_minute: 0,
        average_response_time: 0,
        cache_hit_rate: 0,
        status_code_distribution: {},
        recent_requests: []
      };
    }

    const uptime = (Date.now() - this.startTime.getTime()) / 1000;
    const totalRequests = this.requests.length;
    const errorRequests = this.requests.filter(r => r.status_code >= 400);
    const cachedRequests = this.requests.filter(r => r.cached);

    const avgResponseTime = this.requests.reduce((sum, r) => sum + r.duration_seconds, 0) / totalRequests;
    const errorRate = errorRequests.length / totalRequests;
    const cacheHitRate = cachedRequests.length / totalRequests;
    const requestsPerMinute = totalRequests / (uptime / 60);

    // Status code distribution
    const statusCodes: Record<number, number> = {};
    for (const request of this.requests) {
      statusCodes[request.status_code] = (statusCodes[request.status_code] || 0) + 1;
    }

    return {
      uptime_seconds: uptime,
      total_requests: totalRequests,
      total_errors: errorRequests.length,
      error_rate: errorRate,
      requests_per_minute: requestsPerMinute,
      average_response_time: avgResponseTime,
      cache_hit_rate: cacheHitRate,
      status_code_distribution: statusCodes,
      recent_requests: this.requests.slice(-10)
    };
  }

  reset(): void {
    this.requests = [];
  }
}

// ============================================================================
// RETRY UTILITY
// ============================================================================

export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  backoffFactor: number = 2.0,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt === maxRetries) {
        throw error;
      }

      // Special handling for rate limit errors
      if (error instanceof Error && error.name === 'RateLimitError') {
        const rateLimitError = error as any;
        const waitTime = rateLimitError.retry_after * 1000;
        console.warn(`Rate limited, waiting ${rateLimitError.retry_after} seconds`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }

      // Exponential backoff for other errors
      const sleepTime = baseDelay * Math.pow(backoffFactor, attempt);
      console.warn(`Request failed (attempt ${attempt + 1}), retrying in ${sleepTime}ms:`, error instanceof Error ? error.message : String(error));
      await new Promise(resolve => setTimeout(resolve, sleepTime));
    }
  }

  throw lastError!;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

export function generateRequestId(): string {
  return crypto.randomUUID();
}

export function validatePagination(skip: number, limit: number): void {
  if (skip < 0) {
    throw new Error('skip must be >= 0');
  }
  if (limit < 1 || limit > 100) {
    throw new Error('limit must be between 1 and 100');
  }
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
