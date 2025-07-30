/**
 * Codegen Client React Hooks
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  CodegenConfig,
  CodegenUser,
  CodegenOrganization,
  CodegenAgentRun,
  CodegenHealthCheck,
  CodegenClientStats,
  CodegenBulkProgress,
  CodegenWebhookEvent,
  CodegenPaginatedResponse,
  CreateCodegenAgentRunRequest,
  AgentRunStatus,
  CodegenAPIError,
  AuthenticationError,
  RateLimitError
} from '../services/codegenTypes';

// Mock Codegen Client for demonstration
class MockCodegenClient {
  private config: CodegenConfig;
  private connected: boolean = false;
  private stats: CodegenClientStats = {
    config: { base_url: '', timeout: 30000 },
    metrics: { total_requests: 0, error_rate: 0, average_response_time: 0.5 },
    cache: { hit_rate_percentage: 85, size: 0 }
  };

  constructor(config: CodegenConfig) {
    this.config = config;
  }

  async connect(): Promise<void> {
    // Simulate connection
    await new Promise(resolve => setTimeout(resolve, 1000));
    this.connected = true;
  }

  async healthCheck(): Promise<CodegenHealthCheck> {
    return {
      status: 'healthy',
      user_id: 123,
      response_time_seconds: 0.1,
      timestamp: new Date().toISOString()
    };
  }

  async getCurrentUser(): Promise<CodegenUser> {
    return {
      id: 123,
      github_username: 'demo-user',
      full_name: 'Demo User',
      email: 'demo@example.com'
    };
  }

  async getOrganizations(): Promise<CodegenPaginatedResponse<CodegenOrganization>> {
    return {
      items: [
        { id: 323, name: 'Demo Organization', slug: 'demo-org' }
      ],
      total: 1,
      page: 1,
      per_page: 10,
      has_next: false,
      has_prev: false
    };
  }

  async createAgentRun(orgId: number, prompt: string, metadata?: any): Promise<CodegenAgentRun> {
    const run: CodegenAgentRun = {
      id: Math.floor(Math.random() * 10000),
      org_id: orgId,
      prompt,
      status: AgentRunStatus.PENDING,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata
    };

    // Simulate status progression
    setTimeout(() => {
      run.status = AgentRunStatus.RUNNING;
      run.updated_at = new Date().toISOString();
    }, 1000);

    setTimeout(() => {
      run.status = AgentRunStatus.COMPLETED;
      run.result = `Generated code for: ${prompt}`;
      run.completed_at = new Date().toISOString();
      run.updated_at = new Date().toISOString();
    }, 5000);

    return run;
  }

  async getAgentRuns(orgId: number): Promise<CodegenPaginatedResponse<CodegenAgentRun>> {
    return {
      items: [],
      total: 0,
      page: 1,
      per_page: 10,
      has_next: false,
      has_prev: false
    };
  }

  async getAgentRun(orgId: number, runId: number): Promise<CodegenAgentRun> {
    return {
      id: runId,
      org_id: orgId,
      prompt: 'Demo prompt',
      status: AgentRunStatus.COMPLETED,
      result: 'Demo result',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      completed_at: new Date().toISOString()
    };
  }

  getStats(): CodegenClientStats {
    return this.stats;
  }

  refreshStats(): void {
    this.stats.metrics!.total_requests += 1;
  }

  isConnected(): boolean {
    return this.connected;
  }

  disconnect(): void {
    this.connected = false;
  }
}

// Hook for Codegen Client
export function useCodegenClient(options: {
  config: CodegenConfig;
  autoConnect?: boolean;
}) {
  const [client] = useState(() => new MockCodegenClient(options.config));
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [stats, setStats] = useState<CodegenClientStats | null>(null);

  const connect = useCallback(async () => {
    if (isConnecting || isConnected) return;

    setIsConnecting(true);
    setError(null);

    try {
      await client.connect();
      setIsConnected(true);
      setStats(client.getStats());
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Connection failed'));
    } finally {
      setIsConnecting(false);
    }
  }, [client, isConnecting, isConnected]);

  const refreshStats = useCallback(() => {
    client.refreshStats();
    setStats(client.getStats());
  }, [client]);

  useEffect(() => {
    if (options.autoConnect) {
      connect();
    }

    return () => {
      client.disconnect();
      setIsConnected(false);
    };
  }, [options.autoConnect, connect, client]);

  return {
    client,
    isConnected,
    isConnecting,
    error,
    stats,
    connect,
    refreshStats
  };
}

// Hook for current user
export function useCurrentUser() {
  const [user, setUser] = useState<CodegenUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { client, isConnected } = useCodegenClient({
    config: { base_url: '', api_token: '', org_id: 323 } as CodegenConfig,
    autoConnect: true
  });

  useEffect(() => {
    if (isConnected) {
      setLoading(true);
      client.getCurrentUser()
        .then(setUser)
        .catch(setError)
        .finally(() => setLoading(false));
    }
  }, [client, isConnected]);

  return { user, loading, error };
}

// Hook for organizations
export function useOrganizations() {
  const [organizations, setOrganizations] = useState<CodegenPaginatedResponse<CodegenOrganization> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { client, isConnected } = useCodegenClient({
    config: { base_url: '', api_token: '', org_id: 323 } as CodegenConfig,
    autoConnect: true
  });

  useEffect(() => {
    if (isConnected) {
      setLoading(true);
      client.getOrganizations()
        .then(setOrganizations)
        .catch(setError)
        .finally(() => setLoading(false));
    }
  }, [client, isConnected]);

  return { organizations, loading, error };
}

// Hook for creating agent runs
export function useCreateAgentRun() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { client } = useCodegenClient({
    config: { base_url: '', api_token: '', org_id: 323 } as CodegenConfig,
    autoConnect: true
  });

  const createAgentRun = useCallback(async (
    orgId: number,
    prompt: string,
    metadata?: any
  ): Promise<CodegenAgentRun | null> => {
    setLoading(true);
    setError(null);

    try {
      const run = await client.createAgentRun(orgId, prompt, metadata);
      return run;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create agent run');
      setError(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [client]);

  const resumeAgentRun = useCallback(async (
    orgId: number,
    runId: number
  ): Promise<CodegenAgentRun | null> => {
    // Mock implementation
    return client.getAgentRun(orgId, runId);
  }, [client]);

  return { createAgentRun, resumeAgentRun, loading, error };
}

// Hook for agent run details
export function useAgentRun(options: {
  orgId: number;
  agentRunId: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}) {
  const [agentRun, setAgentRun] = useState<CodegenAgentRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { client } = useCodegenClient({
    config: { base_url: '', api_token: '', org_id: 323 } as CodegenConfig,
    autoConnect: true
  });

  const waitForCompletion = useCallback(async (timeout: number = 300): Promise<CodegenAgentRun | null> => {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout * 1000) {
      try {
        const run = await client.getAgentRun(options.orgId, options.agentRunId);
        if (run.status === AgentRunStatus.COMPLETED || run.status === AgentRunStatus.FAILED) {
          return run;
        }
        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (err) {
        console.error('Error waiting for completion:', err);
        break;
      }
    }
    
    return null;
  }, [client, options.orgId, options.agentRunId]);

  useEffect(() => {
    setLoading(true);
    client.getAgentRun(options.orgId, options.agentRunId)
      .then(setAgentRun)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [client, options.orgId, options.agentRunId]);

  return { agentRun, loading, error, waitForCompletion };
}

// Hook for agent runs list
export function useAgentRuns(options: {
  orgId: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}) {
  const [agentRuns, setAgentRuns] = useState<CodegenPaginatedResponse<CodegenAgentRun> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { client } = useCodegenClient({
    config: { base_url: '', api_token: '', org_id: 323 } as CodegenConfig,
    autoConnect: true
  });

  const refetch = useCallback(() => {
    setLoading(true);
    client.getAgentRuns(options.orgId)
      .then(setAgentRuns)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [client, options.orgId]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  useEffect(() => {
    if (options.autoRefresh) {
      const interval = setInterval(refetch, options.refreshInterval || 10000);
      return () => clearInterval(interval);
    }
  }, [options.autoRefresh, options.refreshInterval, refetch]);

  return { agentRuns, loading, error, refetch };
}

// Hook for bulk operations
export function useBulkOperations() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [progress, setProgress] = useState<CodegenBulkProgress | null>(null);

  const { client } = useCodegenClient({
    config: { base_url: '', api_token: '', org_id: 323 } as CodegenConfig,
    autoConnect: true
  });

  const bulkCreateAgentRuns = useCallback(async (
    orgId: number,
    configs: Array<{ prompt: string; metadata?: any }>
  ): Promise<CodegenAgentRun[]> => {
    setLoading(true);
    setError(null);
    setProgress({ total: configs.length, completed: 0, failed: 0, in_progress: configs.length });

    try {
      const results: CodegenAgentRun[] = [];
      
      for (let i = 0; i < configs.length; i++) {
        const config = configs[i];
        try {
          const run = await client.createAgentRun(orgId, config.prompt, config.metadata);
          results.push(run);
          setProgress(prev => prev ? {
            ...prev,
            completed: prev.completed + 1,
            in_progress: prev.in_progress - 1
          } : null);
        } catch (err) {
          setProgress(prev => prev ? {
            ...prev,
            failed: prev.failed + 1,
            in_progress: prev.in_progress - 1
          } : null);
        }
      }

      return results;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Bulk operation failed');
      setError(error);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  return { bulkCreateAgentRuns, loading, error, progress };
}

// Hook for streaming agent runs
export function useStreamingAgentRuns() {
  // Mock implementation
  return {
    streamAgentRuns: async function* (orgId: number) {
      // Mock streaming
      yield* [];
    }
  };
}

// Hook for webhooks
export function useWebhooks() {
  const [events, setEvents] = useState<CodegenWebhookEvent[]>([]);

  const registerHandler = useCallback((eventType: string, handler: (payload: any) => void) => {
    // Mock implementation
    console.log(`Registered handler for ${eventType}`);
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return { events, registerHandler, clearEvents };
}

// Hook for health check
export function useHealthCheck(interval?: number) {
  const [health, setHealth] = useState<CodegenHealthCheck | null>(null);
  const [loading, setLoading] = useState(false);

  const { client } = useCodegenClient({
    config: { base_url: '', api_token: '', org_id: 323 } as CodegenConfig,
    autoConnect: true
  });

  const checkHealth = useCallback(async () => {
    setLoading(true);
    try {
      const healthData = await client.healthCheck();
      setHealth(healthData);
    } catch (err) {
      console.error('Health check failed:', err);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    checkHealth();
    
    if (interval) {
      const intervalId = setInterval(checkHealth, interval);
      return () => clearInterval(intervalId);
    }
  }, [checkHealth, interval]);

  return { health, loading, checkHealth };
}

