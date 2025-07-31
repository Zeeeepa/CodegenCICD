/**
 * Project management service for CICD dashboard
 */

import { Project, ProjectSettings, ProjectStatus, ProjectStats, PullRequest } from '../types/cicd';
import { githubService } from './githubService';
import { webhookService } from './webhookService';

// ============================================================================
// PROJECT SERVICE CLASS
// ============================================================================

class ProjectService {
  private projects: Map<string, Project> = new Map();
  private storageKey = 'cicd_projects';

  constructor() {
    this.loadProjects();
  }

  // ========================================================================
  // PROJECT MANAGEMENT
  // ========================================================================

  /**
   * Get all projects
   */
  getAllProjects(): Project[] {
    return Array.from(this.projects.values());
  }

  /**
   * Get project by ID
   */
  getProject(projectId: string): Project | undefined {
    return this.projects.get(projectId);
  }

  /**
   * Create a new project from GitHub repository
   */
  async createProject(repoFullName: string): Promise<Project> {
    try {
      // Get repository details from GitHub
      const repoData = await githubService.getRepository(repoFullName);
      
      // Generate project ID
      const projectId = this.generateProjectId(repoFullName);
      
      // Create default settings
      const defaultSettings: ProjectSettings = {
        autoConfirmPlan: false,
        planningStatement: this.getDefaultPlanningStatement(repoData.name),
        repositoryRules: '',
        setupCommands: this.getDefaultSetupCommands(repoData),
        selectedBranch: repoData.default_branch,
        availableBranches: [repoData.default_branch],
        secrets: {},
        environmentVariables: {},
        autoMergeValidatedPR: false,
        validationTimeout: 30,
        retryAttempts: 3,
        webhookEnabled: true,
        webhookEvents: ['pull_request', 'push']
      };

      // Create project
      const project: Project = {
        id: projectId,
        name: repoData.name,
        fullName: repoData.full_name,
        owner: repoData.owner.login,
        repo: repoData.name,
        description: repoData.description,
        defaultBranch: repoData.default_branch,
        url: repoData.html_url,
        cloneUrl: repoData.clone_url,
        status: ProjectStatus.CONFIGURING,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        settings: defaultSettings,
        activePRs: [],
        stats: this.createDefaultStats()
      };

      // Set up webhook
      await this.setupWebhook(project);

      // Load branches
      await this.loadBranches(project);

      // Load active PRs
      await this.loadActivePRs(project);

      // Save project
      this.projects.set(projectId, project);
      this.saveProjects();

      // Update status to active
      project.status = ProjectStatus.ACTIVE;
      project.updatedAt = new Date().toISOString();

      console.log(`Created project: ${project.fullName}`);
      return project;

    } catch (error) {
      console.error('Failed to create project:', error);
      throw new Error(`Failed to create project: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update project settings
   */
  async updateProject(projectId: string, updates: Partial<Project>): Promise<Project> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    // Merge updates
    const updatedProject = {
      ...project,
      ...updates,
      updatedAt: new Date().toISOString()
    };

    // Handle webhook updates
    if (updates.settings?.webhookEnabled !== undefined) {
      if (updates.settings.webhookEnabled && !project.webhookUrl) {
        await this.setupWebhook(updatedProject);
      } else if (!updates.settings.webhookEnabled && project.webhookUrl) {
        await this.removeWebhook(updatedProject);
      }
    }

    this.projects.set(projectId, updatedProject);
    this.saveProjects();

    return updatedProject;
  }

  /**
   * Delete project
   */
  async deleteProject(projectId: string): Promise<void> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    try {
      // Remove webhook
      if (project.webhookUrl) {
        await this.removeWebhook(project);
      }

      // Remove from storage
      this.projects.delete(projectId);
      this.saveProjects();

      console.log(`Deleted project: ${project.fullName}`);
    } catch (error) {
      console.error('Failed to delete project:', error);
      throw new Error(`Failed to delete project: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // ========================================================================
  // PROJECT CONFIGURATION
  // ========================================================================

  /**
   * Update project settings
   */
  async updateSettings(projectId: string, settings: Partial<ProjectSettings>): Promise<Project> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    const updatedSettings = {
      ...project.settings,
      ...settings
    };

    return this.updateProject(projectId, { settings: updatedSettings });
  }

  /**
   * Add or update secret
   */
  async updateSecret(projectId: string, key: string, value: string): Promise<void> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    const updatedSecrets = {
      ...project.settings.secrets,
      [key]: value
    };

    await this.updateSettings(projectId, { secrets: updatedSecrets });
  }

  /**
   * Remove secret
   */
  async removeSecret(projectId: string, key: string): Promise<void> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    const updatedSecrets = { ...project.settings.secrets };
    delete updatedSecrets[key];

    await this.updateSettings(projectId, { secrets: updatedSecrets });
  }

  /**
   * Test setup commands
   */
  async testSetupCommands(projectId: string, commands: string, branch?: string): Promise<{
    success: boolean;
    output: string;
    error?: string;
  }> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    try {
      // This would integrate with grainchain service to test commands
      // For now, return a mock response
      console.log(`Testing setup commands for ${project.fullName}:`, commands);
      
      return {
        success: true,
        output: 'Setup commands executed successfully\nAll dependencies installed\nApplication started'
      };
    } catch (error) {
      return {
        success: false,
        output: '',
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  // ========================================================================
  // WEBHOOK MANAGEMENT
  // ========================================================================

  /**
   * Set up webhook for project
   */
  private async setupWebhook(project: Project): Promise<void> {
    try {
      const webhookConfig = await webhookService.createWebhook(
        project.fullName,
        project.settings.webhookEvents
      );

      project.webhookUrl = webhookConfig.url;
      project.webhookSecret = webhookConfig.secret;

      console.log(`Webhook configured for ${project.fullName}: ${webhookConfig.url}`);
    } catch (error) {
      console.error(`Failed to setup webhook for ${project.fullName}:`, error);
      throw error;
    }
  }

  /**
   * Remove webhook for project
   */
  private async removeWebhook(project: Project): Promise<void> {
    if (!project.webhookUrl) return;

    try {
      await webhookService.removeWebhook(project.fullName);
      project.webhookUrl = undefined;
      project.webhookSecret = undefined;

      console.log(`Webhook removed for ${project.fullName}`);
    } catch (error) {
      console.error(`Failed to remove webhook for ${project.fullName}:`, error);
      throw error;
    }
  }

  // ========================================================================
  // DATA LOADING
  // ========================================================================

  /**
   * Load available branches for project
   */
  private async loadBranches(project: Project): Promise<void> {
    try {
      const branches = await githubService.getBranches(project.fullName);
      project.settings.availableBranches = branches.map(branch => branch.name);
    } catch (error) {
      console.error(`Failed to load branches for ${project.fullName}:`, error);
      // Keep default branch if loading fails
    }
  }

  /**
   * Load active pull requests for project
   */
  private async loadActivePRs(project: Project): Promise<void> {
    try {
      const prs = await githubService.getPullRequests(project.fullName, 'open');
      project.activePRs = prs.map(pr => this.mapGitHubPRToPullRequest(pr));
    } catch (error) {
      console.error(`Failed to load PRs for ${project.fullName}:`, error);
      project.activePRs = [];
    }
  }

  /**
   * Refresh project data
   */
  async refreshProject(projectId: string): Promise<Project> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    try {
      // Reload branches and PRs
      await this.loadBranches(project);
      await this.loadActivePRs(project);

      // Update timestamp
      project.updatedAt = new Date().toISOString();

      this.saveProjects();
      return project;
    } catch (error) {
      console.error(`Failed to refresh project ${projectId}:`, error);
      throw error;
    }
  }

  // ========================================================================
  // UTILITY METHODS
  // ========================================================================

  /**
   * Generate unique project ID
   */
  private generateProjectId(repoFullName: string): string {
    return repoFullName.replace('/', '_').toLowerCase();
  }

  /**
   * Get default planning statement for project
   */
  private getDefaultPlanningStatement(projectName: string): string {
    return `You are an expert software engineer working on the project: <Project='${projectName}'>. 

Please analyze the following requirements and create a comprehensive implementation plan:

{userInput}

Consider the project's existing codebase, architecture, and best practices. Provide a detailed plan that includes:
1. Technical approach and implementation strategy
2. File changes and new components needed
3. Testing requirements and validation criteria
4. Potential risks and mitigation strategies
5. Timeline and dependencies

Ensure the solution is production-ready, well-tested, and follows the project's coding standards.`;
  }

  /**
   * Get default setup commands based on repository
   */
  private getDefaultSetupCommands(repoData: any): string {
    // Detect project type and provide appropriate setup commands
    const hasPackageJson = repoData.has_package_json || false;
    const hasRequirementsTxt = repoData.has_requirements_txt || false;
    const hasDockerfile = repoData.has_dockerfile || false;

    if (hasDockerfile) {
      return 'docker build -t app .\ndocker run -p 3000:3000 app';
    } else if (hasPackageJson) {
      return 'npm install\nnpm run dev';
    } else if (hasRequirementsTxt) {
      return 'pip install -r requirements.txt\npython app.py';
    } else {
      return '# Add your setup commands here\n# Example:\n# npm install\n# npm start';
    }
  }

  /**
   * Create default project statistics
   */
  private createDefaultStats(): ProjectStats {
    return {
      totalRuns: 0,
      successfulRuns: 0,
      failedRuns: 0,
      averageValidationTime: 0,
      successRate: 0
    };
  }

  /**
   * Map GitHub PR to internal PullRequest interface
   */
  private mapGitHubPRToPullRequest(githubPR: any): PullRequest {
    return {
      id: githubPR.id.toString(),
      number: githubPR.number,
      title: githubPR.title,
      description: githubPR.body || '',
      url: githubPR.html_url,
      branch: githubPR.head.ref,
      baseBranch: githubPR.base.ref,
      author: githubPR.user.login,
      status: githubPR.state,
      createdAt: githubPR.created_at,
      updatedAt: githubPR.updated_at,
      autoMergeEligible: false,
      filesChanged: githubPR.changed_files || 0,
      additions: githubPR.additions || 0,
      deletions: githubPR.deletions || 0,
      checksStatus: 'pending',
      reviewsStatus: 'pending'
    };
  }

  // ========================================================================
  // PERSISTENCE
  // ========================================================================

  /**
   * Load projects from localStorage
   */
  private loadProjects(): void {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        const projectsData = JSON.parse(stored);
        this.projects = new Map(Object.entries(projectsData));
        console.log(`Loaded ${this.projects.size} projects from storage`);
      }
    } catch (error) {
      console.error('Failed to load projects from storage:', error);
      this.projects = new Map();
    }
  }

  /**
   * Save projects to localStorage
   */
  private saveProjects(): void {
    try {
      const projectsData = Object.fromEntries(this.projects);
      localStorage.setItem(this.storageKey, JSON.stringify(projectsData));
    } catch (error) {
      console.error('Failed to save projects to storage:', error);
    }
  }

  /**
   * Export projects data
   */
  exportProjects(): string {
    const projectsData = Object.fromEntries(this.projects);
    return JSON.stringify(projectsData, null, 2);
  }

  /**
   * Import projects data
   */
  importProjects(data: string): void {
    try {
      const projectsData = JSON.parse(data);
      this.projects = new Map(Object.entries(projectsData));
      this.saveProjects();
      console.log(`Imported ${this.projects.size} projects`);
    } catch (error) {
      console.error('Failed to import projects:', error);
      throw new Error('Invalid projects data format');
    }
  }

  /**
   * Clear all projects
   */
  clearAllProjects(): void {
    this.projects.clear();
    this.saveProjects();
    console.log('All projects cleared');
  }
}

// ============================================================================
// EXPORT SINGLETON INSTANCE
// ============================================================================

export const projectService = new ProjectService();
