/**
 * API client for Simple Pinned Projects endpoints
 * Handles communication with backend/routers/simple_projects.py
 */

import { PinnedProject, PinProjectRequest, UpdateProjectRequest, ApiError } from '../types/pinnedProjects';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const SIMPLE_PROJECTS_BASE = `${API_BASE_URL}/api/simple-projects`;

class PinnedProjectsApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: string
  ) {
    super(message);
    this.name = 'PinnedProjectsApiError';
  }
}

export class PinnedProjectsApi {
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      let errorDetails = '';
      
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorDetails = errorData.detail;
          errorMessage = errorData.detail;
        }
      } catch {
        // If we can't parse the error response, use the default message
      }
      
      throw new PinnedProjectsApiError(
        errorMessage,
        response.status,
        errorDetails
      );
    }

    // Handle 204 No Content responses
    if (response.status === 204) {
      return undefined as T;
    }

    try {
      return await response.json();
    } catch (error) {
      throw new PinnedProjectsApiError(
        'Failed to parse response JSON',
        response.status
      );
    }
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${SIMPLE_PROJECTS_BASE}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    const config: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      return await this.handleResponse<T>(response);
    } catch (error) {
      if (error instanceof PinnedProjectsApiError) {
        throw error;
      }
      
      // Network or other errors
      throw new PinnedProjectsApiError(
        `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        0
      );
    }
  }

  /**
   * Get all pinned projects for the authenticated user
   */
  async getPinnedProjects(): Promise<PinnedProject[]> {
    return this.makeRequest<PinnedProject[]>('/pinned');
  }

  /**
   * Pin a project to the user's dashboard
   */
  async pinProject(project: PinProjectRequest): Promise<PinnedProject> {
    return this.makeRequest<PinnedProject>('/pin', {
      method: 'POST',
      body: JSON.stringify(project),
    });
  }

  /**
   * Unpin a project from the user's dashboard
   */
  async unpinProject(projectId: number): Promise<void> {
    return this.makeRequest<void>(`/unpin/${projectId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Update a pinned project's metadata
   */
  async updateProject(projectId: number, updates: UpdateProjectRequest): Promise<PinnedProject> {
    return this.makeRequest<PinnedProject>(`/pinned/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  /**
   * Health check for the simple projects service
   */
  async healthCheck(): Promise<{ status: string; service: string }> {
    return this.makeRequest<{ status: string; service: string }>('/health');
  }
}

// Export singleton instance
export const pinnedProjectsApi = new PinnedProjectsApi();

// Export error class for error handling
export { PinnedProjectsApiError };
