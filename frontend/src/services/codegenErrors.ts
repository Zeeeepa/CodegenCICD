/**
 * Custom error classes for Codegen API
 */

export class ValidationError extends Error {
  public field_errors: Record<string, string[]>;

  constructor(message: string, field_errors: Record<string, string[]> = {}) {
    super(message);
    this.name = 'ValidationError';
    this.field_errors = field_errors;
  }
}

export class CodegenAPIError extends Error {
  public status_code: number;
  public response_data?: Record<string, any>;
  public request_id?: string;

  constructor(
    message: string,
    status_code: number = 0,
    response_data?: Record<string, any>,
    request_id?: string
  ) {
    super(message);
    this.name = 'CodegenAPIError';
    this.status_code = status_code;
    this.response_data = response_data;
    this.request_id = request_id;
  }
}

export class RateLimitError extends CodegenAPIError {
  public retry_after: number;

  constructor(retry_after: number = 60, request_id?: string) {
    super(`Rate limited. Retry after ${retry_after} seconds`, 429, undefined, request_id);
    this.name = 'RateLimitError';
    this.retry_after = retry_after;
  }
}

export class AuthenticationError extends CodegenAPIError {
  constructor(message: string = 'Authentication failed', request_id?: string) {
    super(message, 401, undefined, request_id);
    this.name = 'AuthenticationError';
  }
}

export class NotFoundError extends CodegenAPIError {
  constructor(message: string = 'Resource not found', request_id?: string) {
    super(message, 404, undefined, request_id);
    this.name = 'NotFoundError';
  }
}

export class ConflictError extends CodegenAPIError {
  constructor(message: string = 'Conflict occurred', request_id?: string) {
    super(message, 409, undefined, request_id);
    this.name = 'ConflictError';
  }
}

export class ServerError extends CodegenAPIError {
  constructor(
    message: string = 'Server error occurred',
    status_code: number = 500,
    request_id?: string
  ) {
    super(message, status_code, undefined, request_id);
    this.name = 'ServerError';
  }
}

export class TimeoutError extends CodegenAPIError {
  constructor(message: string = 'Request timed out', request_id?: string) {
    super(message, 408, undefined, request_id);
    this.name = 'TimeoutError';
  }
}

export class NetworkError extends CodegenAPIError {
  constructor(message: string = 'Network error occurred', request_id?: string) {
    super(message, 0, undefined, request_id);
    this.name = 'NetworkError';
  }
}

export class WebhookError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'WebhookError';
  }
}

export class BulkOperationError extends Error {
  public failed_items: any[];

  constructor(message: string, failed_items: any[] = []) {
    super(message);
    this.name = 'BulkOperationError';
    this.failed_items = failed_items;
  }
}
