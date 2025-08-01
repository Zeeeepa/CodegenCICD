/**
 * Codegen Configuration Presets
 */

import { ClientConfig } from './codegenTypes';

export const DEFAULT_CONFIG: ClientConfig = {
  baseUrl: 'https://api.codegen.com',
  timeout: 30000,
  retries: 3,
  rateLimit: {
    maxRequests: 100,
    windowMs: 60000
  },
  cache: {
    enabled: true,
    ttl: 300000 // 5 minutes
  }
};

export interface CodegenConfig {
  apiToken?: string;
  orgId?: number;
  baseUrl?: string;
  timeout?: number;
  retries?: number;
}

export const ConfigPresets = {
  development: {
    baseUrl: 'http://localhost:3001',
    timeout: 30000,
    retries: 3
  } as CodegenConfig,
  
  staging: {
    baseUrl: 'https://staging-api.codegen.com',
    timeout: 30000,
    retries: 3
  } as CodegenConfig,
  
  production: {
    baseUrl: 'https://api.codegen.com',
    timeout: 30000,
    retries: 5
  } as CodegenConfig
};

export const validateConfig = (config: Partial<ClientConfig>): ClientConfig => {
  const validatedConfig = { ...DEFAULT_CONFIG, ...config };

  if (validatedConfig.timeout && validatedConfig.timeout < 1000) {
    throw new Error('Timeout must be at least 1000ms');
  }

  if (validatedConfig.retries && validatedConfig.retries < 0) {
    throw new Error('Retries must be non-negative');
  }

  return validatedConfig;
};

export const getConfig = (preset: keyof typeof ConfigPresets = 'development'): CodegenConfig => {
  return ConfigPresets[preset];
};
