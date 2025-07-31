/**
 * Codegen Configuration and Presets
 */

export interface CodegenConfig {
  base_url: string;
  api_token: string;
  org_id: number;
  timeout: number;
  max_retries: number;
  rate_limit_requests: number;
  rate_limit_window: number;
  enable_caching: boolean;
  cache_ttl: number;
  log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
}

export class ConfigPresets {
  static development(): CodegenConfig {
    return {
      base_url: process.env.REACT_APP_CODEGEN_BASE_URL || 'https://api.codegen.com',
      api_token: process.env.REACT_APP_CODEGEN_API_TOKEN || '',
      org_id: parseInt(process.env.REACT_APP_CODEGEN_ORG_ID || '323'),
      timeout: 30000,
      max_retries: 3,
      rate_limit_requests: 50,
      rate_limit_window: 60,
      enable_caching: false,
      cache_ttl: 300,
      log_level: 'DEBUG'
    };
  }

  static production(): CodegenConfig {
    return {
      base_url: process.env.REACT_APP_CODEGEN_BASE_URL || 'https://api.codegen.com',
      api_token: process.env.REACT_APP_CODEGEN_API_TOKEN || '',
      org_id: parseInt(process.env.REACT_APP_CODEGEN_ORG_ID || '323'),
      timeout: 60000,
      max_retries: 5,
      rate_limit_requests: 100,
      rate_limit_window: 60,
      enable_caching: true,
      cache_ttl: 600,
      log_level: 'ERROR'
    };
  }

  static testing(): CodegenConfig {
    return {
      base_url: 'http://localhost:8000',
      api_token: 'test-token',
      org_id: 323,
      timeout: 5000,
      max_retries: 1,
      rate_limit_requests: 1000,
      rate_limit_window: 60,
      enable_caching: false,
      cache_ttl: 0,
      log_level: 'DEBUG'
    };
  }
}

