/**
 * Codegen API Service
 * Handles all interactions with the Codegen API
 */

interface CodegenConfig {
  orgId: string;
  apiToken: string;
  baseUrl?: string;
}

interface AgentRunRequest {
  target: string;
  repo_name: string;
  planning_statement?: string;
  auto_confirm_plans?: boolean;
  max_iterations?: number;
}

interface AgentRunResponse {
  id: number;
  organization_id: number;
  status: string;
  created_at: string;
  web_url: string;
  result?: string;
  source_type: string;
  github_pull_requests: any[];
  metadata: {
    project_name: string;
  };
}

interface AgentRunLogsResponse {
  id: number;
  organization_id: number;
  status: string;
  created_at: string;
  web_url: string;
  result?: string;
  logs: AgentRunLog[];
  total_logs: number;
  page: number;
  size: number;
  pages: number;
}

interface AgentRunLog {
  agent_run_id: number;
  created_at: string;
  message_type: string;
  thought?: string;
  tool_name?: string;
  tool_input?: any;
  tool_output?: any;
  observation?: any;
}

class CodegenAPIError extends Error {
  constructor(message: string, public status?: number, public response?: any) {
    super(message);
    this.name = 'CodegenAPIError';
  }
}

class CodegenService {
  private config: CodegenConfig;
  private baseUrl: string;

  constructor(config: CodegenConfig) {
    this.config = config;
    this.baseUrl = config.baseUrl || 'https://api.codegen.com/v1';
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const headers = {
      'Authorization': `Bearer ${this.config.apiToken}`,
      'Content-Type': 'application/json',
      'User-Agent': 'CodegenCICD-Dashboard/1.0',
      ...options.headers,
    };

    try {
      console.log(`[CodegenService] Making ${options.method || 'GET'} request to: ${url}`);
      
      const response = await fetch(url, {
        ...options,
        headers,
      });

      console.log(`[CodegenService] Response status: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        throw new CodegenAPIError(
          `API request failed: ${response.status} ${response.statusText}`,
          response.status,
          errorText
        );
      }

      // Clone the response to avoid "body stream already read" error
      const responseClone = response.clone();
      
      try {
        const data = await response.json();
        console.log(`[CodegenService] Response data:`, data);
        return data;
      } catch (jsonError) {
        // If JSON parsing fails, try to get text from the cloned response
        const text = await responseClone.text();
        console.error(`[CodegenService] JSON parsing failed, response text:`, text);
        throw new CodegenAPIError(`Invalid JSON response: ${jsonError}`);
      }
    } catch (error) {
      if (error instanceof CodegenAPIError) {
        throw error;
      }
      
      console.error(`[CodegenService] Request failed:`, error);
      throw new CodegenAPIError(`Network error: ${error}`);
    }
  }

  /**
   * Create a new agent run
   */
  async createAgentRun(request: AgentRunRequest): Promise<AgentRunResponse> {
    const endpoint = `/organizations/${this.config.orgId}/agent-runs`;
    
    return this.makeRequest<AgentRunResponse>(endpoint, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get agent run details
   */
  async getAgentRun(runId: number): Promise<AgentRunResponse> {
    const endpoint = `/organizations/${this.config.orgId}/agent-runs/${runId}`;
    
    return this.makeRequest<AgentRunResponse>(endpoint);
  }

  /**
   * Get agent run logs with pagination
   */
  async getAgentRunLogs(
    runId: number,
    skip: number = 0,
    limit: number = 100
  ): Promise<AgentRunLogsResponse> {
    const endpoint = `/organizations/${this.config.orgId}/agent/run/${runId}/logs`;
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: Math.min(limit, 100).toString(),
    });
    
    return this.makeRequest<AgentRunLogsResponse>(`${endpoint}?${params}`);
  }

  /**
   * List agent runs for the organization
   */
  async listAgentRuns(
    limit: number = 50,
    offset: number = 0,
    status?: string
  ): Promise<{ agent_runs: AgentRunResponse[] }> {
    const endpoint = `/organizations/${this.config.orgId}/agent-runs`;
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    if (status) {
      params.append('status', status);
    }
    
    return this.makeRequest<{ agent_runs: AgentRunResponse[] }>(`${endpoint}?${params}`);
  }

  /**
   * Continue an agent run with user input
   */
  async continueAgentRun(runId: number, userInput: string): Promise<AgentRunResponse> {
    const endpoint = `/organizations/${this.config.orgId}/agent-runs/${runId}/continue`;
    
    return this.makeRequest<AgentRunResponse>(endpoint, {
      method: 'POST',
      body: JSON.stringify({ user_input: userInput }),
    });
  }

  /**
   * Cancel an agent run
   */
  async cancelAgentRun(runId: number): Promise<AgentRunResponse> {
    const endpoint = `/organizations/${this.config.orgId}/agent-runs/${runId}/cancel`;
    
    return this.makeRequest<AgentRunResponse>(endpoint, {
      method: 'POST',
    });
  }

  /**
   * Get organization details
   */
  async getOrganization(): Promise<any> {
    const endpoint = `/organizations/${this.config.orgId}`;
    
    return this.makeRequest<any>(endpoint);
  }

  /**
   * List repositories accessible to the organization
   */
  async listRepositories(): Promise<{ repositories: any[] }> {
    const endpoint = `/organizations/${this.config.orgId}/repositories`;
    
    return this.makeRequest<{ repositories: any[] }>(endpoint);
  }
}

// Create a singleton instance
let codegenService: CodegenService | null = null;

export const getCodegenService = (): CodegenService => {
  if (!codegenService) {
    const orgId = process.env.REACT_APP_CODEGEN_ORG_ID || '323';
    const apiToken = process.env.REACT_APP_CODEGEN_API_TOKEN || 'sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99';
    
    codegenService = new CodegenService({
      orgId,
      apiToken,
    });
  }
  
  return codegenService;
};

export { CodegenService, CodegenAPIError };
export type { AgentRunRequest, AgentRunResponse, AgentRunLog, AgentRunLogsResponse };
