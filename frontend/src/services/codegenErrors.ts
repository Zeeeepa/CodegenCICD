/**
 * Codegen API Error Classes
 */

export class CodegenError extends Error {
  public statusCode?: number;
  public response?: any;

  constructor(message: string, statusCode?: number, response?: any) {
    super(message);
    this.name = 'CodegenError';
    this.statusCode = statusCode;
    this.response = response;
  }
}

export class AuthenticationError extends CodegenError {
  constructor(message: string = 'Authentication failed') {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

export class AuthorizationError extends CodegenError {
  constructor(message: string = 'Authorization failed') {
    super(message, 403);
    this.name = 'AuthorizationError';
  }
}

export class NotFoundError extends CodegenError {
  constructor(message: string = 'Resource not found') {
    super(message, 404);
    this.name = 'NotFoundError';
  }
}

export class RateLimitError extends CodegenError {
  public retryAfter?: number;

  constructor(message: string = 'Rate limit exceeded', retryAfter?: number) {
    super(message, 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class ValidationError extends CodegenError {
  public errors?: Record<string, string[]>;

  constructor(message: string = 'Validation failed', errors?: Record<string, string[]>) {
    super(message, 422);
    this.name = 'ValidationError';
    this.errors = errors;
  }
}

export class BulkOperationError extends CodegenError {
  public failedItems?: any[];

  constructor(message: string = 'Bulk operation failed', failedItems?: any[]) {
    super(message, 400);
    this.name = 'BulkOperationError';
    this.failedItems = failedItems;
  }
}

export class NetworkError extends CodegenError {
  constructor(message: string = 'Network error occurred') {
    super(message);
    this.name = 'NetworkError';
  }
}

export class ConflictError extends CodegenError {
  constructor(message: string = 'Conflict occurred') {
    super(message, 409);
    this.name = 'ConflictError';
  }
}

export class ServerError extends CodegenError {
  constructor(message: string = 'Internal server error') {
    super(message, 500);
    this.name = 'ServerError';
  }
}

export class TimeoutError extends CodegenError {
  constructor(message: string = 'Request timeout') {
    super(message);
    this.name = 'TimeoutError';
  }
}

// Alias for backward compatibility
export { CodegenError as CodegenAPIError };
