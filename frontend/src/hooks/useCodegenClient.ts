/**
 * React hooks for Codegen API client
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import CodegenClient, {
  AgentRunResponse,
  AgentRunsResponse,
  UserResponse,
  OrganizationsResponse,
  AgentRunWithLogsResponse,
  HealthCheckResponse,
  ClientConfig,
  SourceType,
  AgentRunStatus,
  BulkOperationResult,
  ProgressCallback
} from '../services/codegenClient';
import { ConfigPresets } from '../services/codegenConfig';

// ============================================================================
// TYPES
// ============================================================================

interface UseCodegenClientOptions {
  config?: Partial<ClientConfig>;
  autoConnect?: boolean;
}

interface UseAgentRunOptions {
  orgId: number;
  agentRunId: number;
  pollInterval?: number;
  autoRefresh?: boolean;
}

interface UseAgentRunsOptions {
  orgId: number;
  userId?: number;
  sourceType?: SourceType;
  skip?: number;
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseAgentRunLogsOptions {
  orgId: number;
  agentRunId: number;
  skip?: number;
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

// ============================================================================
// MAIN CLIENT HOOK
// ============================================================================

export function useCodegenClient(options: UseCodegenClientOptions = {}) {
  const { config, autoConnect = true } = options;
  
  const clientRef = useRef<CodegenClient | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [stats, setStats] = useState<Record<string, any> | null>(null);

  // Create client instance
  const client = useMemo(() => {
    if (!clientRef.current) {
      try {
        const clientConfig = config || ConfigPresets.development();
        clientRef.current = new CodegenClient(clientConfig);
      } catch (err) {
        setError(err as Error);
        return null;
      }
    }
    return clientRef.current;
  }, [config]);

  // Health check and connection
  const connect = useCallback(async () => {
    if (!client || isConnecting) return;

    setIsConnecting(true);
    setError(null);

    try {
      const health = await client.healthCheck();
      if (health.status === 'healthy') {
        setIsConnected(true);
        setStats(client.getStats());
      } else {
        throw new Error(health.error || 'Health check failed');
      }
    } catch (err) {
      setError(err as Error);
      setIsConnected(false);
    } finally {
      setIsConnecting(false);
    }
  }, [client, isConnecting]);

  const disconnect = useCallback(() => {
    setIsConnected(false);
    setStats(null);
  }, []);

  const refreshStats = useCallback(() => {
    if (client && isConnected) {
      setStats(client.getStats());
    }
  }, [client, isConnected]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && client && !isConnected && !isConnecting) {
      connect();
    }
  }, [autoConnect, client, isConnected, isConnecting, connect]);

  return {
    client,
    isConnected,
    isConnecting,
    error,
    stats,
    connect,
    disconnect,
    refreshStats
  };
}

// ============================================================================
// AGENT RUN HOOKS
// ============================================================================

export function useAgentRun(options: UseAgentRunOptions) {
  const { orgId, agentRunId, pollInterval = 5000, autoRefresh = false } = options;
  const { client } = useCodegenClient();
  
  const [agentRun, setAgentRun] = useState<AgentRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchAgentRun = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);

    try {
      const run = await client.getAgentRun(orgId, agentRunId);
      setAgentRun(run);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client, orgId, agentRunId]);

  const waitForCompletion = useCallback(async (timeout?: number) => {
    if (!client) return null;

    try {
      const completedRun = await client.waitForCompletion(orgId, agentRunId, pollInterval, timeout);
      setAgentRun(completedRun);
      return completedRun;
    } catch (err) {
      setError(err as Error);
      return null;
    }
  }, [client, orgId, agentRunId, pollInterval]);

  // Auto-refresh logic
  useEffect(() => {
    if (autoRefresh && agentRun && ![
      AgentRunStatus.COMPLETED,
      AgentRunStatus.FAILED,
      AgentRunStatus.CANCELLED
    ].includes(agentRun.status as AgentRunStatus)) {
      intervalRef.current = setInterval(fetchAgentRun, pollInterval);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, agentRun, fetchAgentRun, pollInterval]);

  // Initial fetch
  useEffect(() => {
    fetchAgentRun();
  }, [fetchAgentRun]);

  return {
    agentRun,
    loading,
    error,
    refetch: fetchAgentRun,
    waitForCompletion
  };
}

export function useAgentRuns(options: UseAgentRunsOptions) {
  const { orgId, userId, sourceType, skip = 0, limit = 100, autoRefresh = false, refreshInterval = 30000 } = options;
  const { client } = useCodegenClient();
  
  const [agentRuns, setAgentRuns] = useState<AgentRunsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchAgentRuns = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);

    try {
      const runs = await client.listAgentRuns(orgId, { userId, sourceType, skip, limit });
      setAgentRuns(runs);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client, orgId, userId, sourceType, skip, limit]);

  // Auto-refresh logic
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchAgentRuns, refreshInterval);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, fetchAgentRuns, refreshInterval]);

  // Initial fetch
  useEffect(() => {
    fetchAgentRuns();
  }, [fetchAgentRuns]);

  return {
    agentRuns,
    loading,
    error,
    refetch: fetchAgentRuns
  };
}

export function useCreateAgentRun() {
  const { client } = useCodegenClient();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createAgentRun = useCallback(async (
    orgId: number,
    prompt: string,
    images?: string[],
    metadata?: Record<string, any>
  ): Promise<AgentRunResponse | null> => {
    if (!client) return null;

    setLoading(true);
    setError(null);

    try {
      const run = await client.createAgentRun(orgId, prompt, images, metadata);
      return run;
    } catch (err) {
      setError(err as Error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [client]);

  const resumeAgentRun = useCallback(async (
    orgId: number,
    agentRunId: number,
    prompt: string,
    images?: string[]
  ): Promise<AgentRunResponse | null> => {
    if (!client) return null;

    setLoading(true);
    setError(null);

    try {
      const run = await client.resumeAgentRun(orgId, agentRunId, prompt, images);
      return run;
    } catch (err) {
      setError(err as Error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [client]);

  return {
    createAgentRun,
    resumeAgentRun,
    loading,
    error
  };
}

// ============================================================================
// AGENT RUN LOGS HOOK
// ============================================================================

export function useAgentRunLogs(options: UseAgentRunLogsOptions) {
  const { orgId, agentRunId, skip = 0, limit = 100, autoRefresh = false, refreshInterval = 10000 } = options;
  const { client } = useCodegenClient();
  
  const [logs, setLogs] = useState<AgentRunWithLogsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchLogs = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);

    try {
      const logsResponse = await client.getAgentRunLogs(orgId, agentRunId, skip, limit);
      setLogs(logsResponse);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client, orgId, agentRunId, skip, limit]);

  // Auto-refresh logic
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchLogs, refreshInterval);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, fetchLogs, refreshInterval]);

  // Initial fetch
  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return {
    logs,
    loading,
    error,
    refetch: fetchLogs
  };
}

// ============================================================================
// USER HOOKS
// ============================================================================

export function useCurrentUser() {
  const { client } = useCodegenClient();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchUser = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);

    try {
      const currentUser = await client.getCurrentUser();
      setUser(currentUser);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return {
    user,
    loading,
    error,
    refetch: fetchUser
  };
}

export function useOrganizations() {
  const { client } = useCodegenClient();
  const [organizations, setOrganizations] = useState<OrganizationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchOrganizations = useCallback(async (skip: number = 0, limit: number = 100) => {
    if (!client) return;

    setLoading(true);
    setError(null);

    try {
      const orgs = await client.getOrganizations(skip, limit);
      setOrganizations(orgs);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  return {
    organizations,
    loading,
    error,
    refetch: fetchOrganizations
  };
}

// ============================================================================
// BULK OPERATIONS HOOKS
// ============================================================================

export function useBulkOperations() {
  const { client } = useCodegenClient();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [progress, setProgress] = useState<{ completed: number; total: number } | null>(null);

  const progressCallback: ProgressCallback = useCallback((completed, total) => {
    setProgress({ completed, total });
  }, []);

  const bulkCreateAgentRuns = useCallback(async (
    orgId: number,
    runConfigs: Array<{
      prompt: string;
      images?: string[];
      metadata?: Record<string, any>;
    }>
  ): Promise<BulkOperationResult<AgentRunResponse> | null> => {
    if (!client) return null;

    setLoading(true);
    setError(null);
    setProgress(null);

    try {
      const result = await client.bulkCreateAgentRuns(orgId, runConfigs, progressCallback);
      return result;
    } catch (err) {
      setError(err as Error);
      return null;
    } finally {
      setLoading(false);
      setProgress(null);
    }
  }, [client, progressCallback]);

  return {
    bulkCreateAgentRuns,
    loading,
    error,
    progress
  };
}

// ============================================================================
// STREAMING HOOKS
// ============================================================================

export function useStreamingAgentRuns(orgId: number, options: { userId?: number; sourceType?: SourceType } = {}) {
  const { client } = useCodegenClient();
  const [runs, setRuns] = useState<AgentRunResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const startStreaming = useCallback(async () => {
    if (!client || isStreaming) return;

    setLoading(true);
    setError(null);
    setIsStreaming(true);
    setRuns([]);

    try {
      const streamedRuns: AgentRunResponse[] = [];
      
      for await (const run of client.streamAllAgentRuns(orgId, options)) {
        streamedRuns.push(run);
        setRuns([...streamedRuns]); // Create new array to trigger re-render
      }
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
      setIsStreaming(false);
    }
  }, [client, orgId, options, isStreaming]);

  const stopStreaming = useCallback(() => {
    setIsStreaming(false);
  }, []);

  return {
    runs,
    loading,
    error,
    isStreaming,
    startStreaming,
    stopStreaming
  };
}

// ============================================================================
// WEBHOOK HOOKS
// ============================================================================

export function useWebhooks() {
  const { client } = useCodegenClient();
  const [events, setEvents] = useState<Array<{ eventType: string; payload: any; timestamp: Date }>>([]);

  const registerHandler = useCallback((eventType: string, handler?: (payload: any) => void) => {
    if (!client) return;

    const wrappedHandler = (payload: any) => {
      // Add to events list
      setEvents(prev => [...prev, { eventType, payload, timestamp: new Date() }]);
      
      // Call custom handler if provided
      if (handler) {
        handler(payload);
      }
    };

    client.registerWebhookHandler(eventType, wrappedHandler);
  }, [client]);

  const handleWebhook = useCallback(async (payload: Record<string, any>, signature?: string) => {
    if (!client) return;
    
    try {
      await client.handleWebhook(payload, signature);
    } catch (err) {
      console.error('Webhook handling error:', err);
    }
  }, [client]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    events,
    registerHandler,
    handleWebhook,
    clearEvents
  };
}

// ============================================================================
// HEALTH CHECK HOOK
// ============================================================================

export function useHealthCheck(interval: number = 60000) {
  const { client } = useCodegenClient();
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const checkHealth = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    try {
      const healthResponse = await client.healthCheck();
      setHealth(healthResponse);
    } catch (err) {
      setHealth({
        status: 'unhealthy',
        error: err instanceof Error ? err.message : String(err),
        timestamp: new Date().toISOString()
      });
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    checkHealth();
    
    if (interval > 0) {
      intervalRef.current = setInterval(checkHealth, interval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [checkHealth, interval]);

  return {
    health,
    loading,
    checkHealth
  };
}
