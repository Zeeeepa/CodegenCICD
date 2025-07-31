/**
 * GitHub API service for repository management
 */

// ============================================================================
// GITHUB SERVICE CLASS
// ============================================================================

class GitHubService {
  private token: string;
  private baseUrl = 'https://api.github.com';

  constructor() {
    this.token = process.env.REACT_APP_GITHUB_TOKEN || '';
    if (!this.token) {
      console.warn('GitHub token not configured. Some features may not work.');
    }
  }

  // ========================================================================
  // AUTHENTICATION
  // ========================================================================

  /**
   * Set GitHub token
   */
  setToken(token: string): void {
    this.token = token;
  }

  /**
   * Check if authenticated
   */
  isAuthenticated(): boolean {
    return !!this.token;
  }

  // ========================================================================
  // API HELPERS
  // ========================================================================

  /**
   * Make authenticated request to GitHub API
   */
  private async makeRequest(endpoint: string, options: RequestInit = {}): Promise<any> {
    if (!this.token) {
      throw new Error('GitHub token not configured');
    }

    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Authorization': `Bearer ${this.token}`,
      'Accept': 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
      ...options.headers
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`GitHub API error: ${response.status} - ${errorData.message || response.statusText}`);
      }

      return response.json();
    } catch (error) {
      console.error(`GitHub API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // ========================================================================
  // USER OPERATIONS
  // ========================================================================

  /**
   * Get current authenticated user
   */
  async getCurrentUser(): Promise<any> {
    return this.makeRequest('/user');
  }

  /**
   * Get user repositories
   */
  async getUserRepositories(username?: string, type: 'all' | 'owner' | 'member' = 'owner'): Promise<any[]> {
    const endpoint = username ? `/users/${username}/repos` : '/user/repos';
    const params = new URLSearchParams({
      type,
      sort: 'updated',
      per_page: '100'
    });

    return this.makeRequest(`${endpoint}?${params}`);
  }

  /**
   * Get organization repositories
   */
  async getOrganizationRepositories(org: string): Promise<any[]> {
    const params = new URLSearchParams({
      sort: 'updated',
      per_page: '100'
    });

    return this.makeRequest(`/orgs/${org}/repos?${params}`);
  }

  // ========================================================================
  // REPOSITORY OPERATIONS
  // ========================================================================

  /**
   * Get repository details
   */
  async getRepository(fullName: string): Promise<any> {
    return this.makeRequest(`/repos/${fullName}`);
  }

  /**
   * Get repository branches
   */
  async getBranches(fullName: string): Promise<any[]> {
    return this.makeRequest(`/repos/${fullName}/branches`);
  }

  /**
   * Get repository contents
   */
  async getContents(fullName: string, path: string = '', ref?: string): Promise<any> {
    const params = new URLSearchParams();
    if (ref) params.append('ref', ref);
    
    const query = params.toString() ? `?${params}` : '';
    return this.makeRequest(`/repos/${fullName}/contents/${path}${query}`);
  }

  /**
   * Search repositories
   */
  async searchRepositories(query: string, sort: 'stars' | 'forks' | 'updated' = 'updated'): Promise<any> {
    const params = new URLSearchParams({
      q: query,
      sort,
      order: 'desc',
      per_page: '50'
    });

    return this.makeRequest(`/search/repositories?${params}`);
  }

  // ========================================================================
  // PULL REQUEST OPERATIONS
  // ========================================================================

  /**
   * Get pull requests
   */
  async getPullRequests(
    fullName: string, 
    state: 'open' | 'closed' | 'all' = 'open',
    sort: 'created' | 'updated' | 'popularity' = 'updated'
  ): Promise<any[]> {
    const params = new URLSearchParams({
      state,
      sort,
      direction: 'desc',
      per_page: '50'
    });

    return this.makeRequest(`/repos/${fullName}/pulls?${params}`);
  }

  /**
   * Get pull request details
   */
  async getPullRequest(fullName: string, prNumber: number): Promise<any> {
    return this.makeRequest(`/repos/${fullName}/pulls/${prNumber}`);
  }

  /**
   * Get pull request files
   */
  async getPullRequestFiles(fullName: string, prNumber: number): Promise<any[]> {
    return this.makeRequest(`/repos/${fullName}/pulls/${prNumber}/files`);
  }

  /**
   * Merge pull request
   */
  async mergePullRequest(
    fullName: string, 
    prNumber: number, 
    options: {
      commit_title?: string;
      commit_message?: string;
      merge_method?: 'merge' | 'squash' | 'rebase';
    } = {}
  ): Promise<any> {
    return this.makeRequest(`/repos/${fullName}/pulls/${prNumber}/merge`, {
      method: 'PUT',
      body: JSON.stringify({
        merge_method: 'merge',
        ...options
      })
    });
  }

  // ========================================================================
  // WEBHOOK OPERATIONS
  // ========================================================================

  /**
   * Get repository webhooks
   */
  async getWebhooks(fullName: string): Promise<any[]> {
    return this.makeRequest(`/repos/${fullName}/hooks`);
  }

  /**
   * Create webhook
   */
  async createWebhook(
    fullName: string,
    config: {
      url: string;
      secret?: string;
      events?: string[];
      active?: boolean;
    }
  ): Promise<any> {
    const webhookData = {
      name: 'web',
      active: config.active ?? true,
      events: config.events || ['push', 'pull_request'],
      config: {
        url: config.url,
        content_type: 'json',
        ...(config.secret && { secret: config.secret })
      }
    };

    return this.makeRequest(`/repos/${fullName}/hooks`, {
      method: 'POST',
      body: JSON.stringify(webhookData)
    });
  }

  /**
   * Update webhook
   */
  async updateWebhook(
    fullName: string,
    hookId: number,
    config: {
      url?: string;
      secret?: string;
      events?: string[];
      active?: boolean;
    }
  ): Promise<any> {
    const webhookData: any = {};
    
    if (config.active !== undefined) {
      webhookData.active = config.active;
    }
    
    if (config.events) {
      webhookData.events = config.events;
    }
    
    if (config.url || config.secret) {
      webhookData.config = {};
      if (config.url) webhookData.config.url = config.url;
      if (config.secret) webhookData.config.secret = config.secret;
    }

    return this.makeRequest(`/repos/${fullName}/hooks/${hookId}`, {
      method: 'PATCH',
      body: JSON.stringify(webhookData)
    });
  }

  /**
   * Delete webhook
   */
  async deleteWebhook(fullName: string, hookId: number): Promise<void> {
    await this.makeRequest(`/repos/${fullName}/hooks/${hookId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Test webhook
   */
  async testWebhook(fullName: string, hookId: number): Promise<any> {
    return this.makeRequest(`/repos/${fullName}/hooks/${hookId}/tests`, {
      method: 'POST'
    });
  }

  // ========================================================================
  // ISSUE OPERATIONS
  // ========================================================================

  /**
   * Get repository issues
   */
  async getIssues(
    fullName: string,
    state: 'open' | 'closed' | 'all' = 'open',
    labels?: string[]
  ): Promise<any[]> {
    const params = new URLSearchParams({
      state,
      sort: 'updated',
      direction: 'desc',
      per_page: '50'
    });

    if (labels && labels.length > 0) {
      params.append('labels', labels.join(','));
    }

    return this.makeRequest(`/repos/${fullName}/issues?${params}`);
  }

  /**
   * Create issue
   */
  async createIssue(
    fullName: string,
    title: string,
    body?: string,
    labels?: string[],
    assignees?: string[]
  ): Promise<any> {
    const issueData: any = { title };
    if (body) issueData.body = body;
    if (labels) issueData.labels = labels;
    if (assignees) issueData.assignees = assignees;

    return this.makeRequest(`/repos/${fullName}/issues`, {
      method: 'POST',
      body: JSON.stringify(issueData)
    });
  }

  // ========================================================================
  // CHECK OPERATIONS
  // ========================================================================

  /**
   * Get check runs for a commit
   */
  async getCheckRuns(fullName: string, ref: string): Promise<any> {
    return this.makeRequest(`/repos/${fullName}/commits/${ref}/check-runs`);
  }

  /**
   * Get check suites for a commit
   */
  async getCheckSuites(fullName: string, ref: string): Promise<any> {
    return this.makeRequest(`/repos/${fullName}/commits/${ref}/check-suites`);
  }

  /**
   * Get combined status for a commit
   */
  async getCombinedStatus(fullName: string, ref: string): Promise<any> {
    return this.makeRequest(`/repos/${fullName}/commits/${ref}/status`);
  }

  // ========================================================================
  // UTILITY METHODS
  // ========================================================================

  /**
   * Check if repository exists and is accessible
   */
  async checkRepositoryAccess(fullName: string): Promise<boolean> {
    try {
      await this.getRepository(fullName);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get repository languages
   */
  async getRepositoryLanguages(fullName: string): Promise<Record<string, number>> {
    return this.makeRequest(`/repos/${fullName}/languages`);
  }

  /**
   * Get repository topics
   */
  async getRepositoryTopics(fullName: string): Promise<string[]> {
    const response = await this.makeRequest(`/repos/${fullName}/topics`, {
      headers: {
        'Accept': 'application/vnd.github.mercy-preview+json'
      }
    });
    return response.names || [];
  }

  /**
   * Get repository collaborators
   */
  async getCollaborators(fullName: string): Promise<any[]> {
    return this.makeRequest(`/repos/${fullName}/collaborators`);
  }

  /**
   * Get rate limit status
   */
  async getRateLimit(): Promise<any> {
    return this.makeRequest('/rate_limit');
  }

  /**
   * Parse GitHub URL to extract owner and repo
   */
  parseGitHubUrl(url: string): { owner: string; repo: string } | null {
    const patterns = [
      /github\.com\/([^\/]+)\/([^\/]+)/,
      /github\.com\/([^\/]+)\/([^\/]+)\.git/,
      /git@github\.com:([^\/]+)\/([^\/]+)\.git/
    ];

    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) {
        return {
          owner: match[1],
          repo: match[2].replace(/\.git$/, '')
        };
      }
    }

    return null;
  }

  /**
   * Format repository full name
   */
  formatFullName(owner: string, repo: string): string {
    return `${owner}/${repo}`;
  }
}

// ============================================================================
// EXPORT SINGLETON INSTANCE
// ============================================================================

export const githubService = new GitHubService();
