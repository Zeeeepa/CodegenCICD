/**
 * Project Service - handles project management operations
 */

import { Project, ProjectSettings, ProjectStatus, WorkflowRun } from '../types/cicd';

class ProjectService {
  private projects: Map<string, Project> = new Map();

  getAllProjects(): Project[] {
    return Array.from(this.projects.values());
  }

  getProject(projectId: string): Project | undefined {
    return this.projects.get(projectId);
  }

  async createProject(repoFullName: string): Promise<Project> {
    const projectId = `project-${Date.now()}`;
    const [owner, repo] = repoFullName.split('/');
    const project: Project = {
      id: projectId,
      name: repo || repoFullName,
      fullName: repoFullName,
      owner: owner || '',
      repo: repo || repoFullName,
      description: '',
      defaultBranch: 'main',
      url: `https://github.com/${repoFullName}`,
      cloneUrl: `https://github.com/${repoFullName}.git`,
      status: ProjectStatus.ACTIVE,
      webhookUrl: '',
      webhookSecret: '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      settings: {
        autoConfirmPlan: false,
        planningStatement: '',
        repositoryRules: '',
        setupCommands: '',
        selectedBranch: 'main',
        availableBranches: ['main', 'master'],
        secrets: {},
        environmentVariables: {},
        autoMergeValidatedPR: false,
        validationTimeout: 30,
        retryAttempts: 3,
        webhookEnabled: false,
        webhookEvents: []
      },
      currentWorkflow: undefined,
      lastValidation: undefined,
      activePRs: [],
      stats: {
        totalRuns: 0,
        successfulRuns: 0,
        failedRuns: 0,
        averageValidationTime: 0,
        lastRunDate: undefined,
        successRate: 0
      }
    };

    this.projects.set(projectId, project);
    return project;
  }

  async updateProject(projectId: string, updates: Partial<Project>): Promise<Project> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project ${projectId} not found`);
    }

    const updatedProject = {
      ...project,
      ...updates,
      updatedAt: new Date().toISOString()
    };

    this.projects.set(projectId, updatedProject);
    return updatedProject;
  }

  async deleteProject(projectId: string): Promise<void> {
    this.projects.delete(projectId);
  }

  async updateSettings(projectId: string, settings: Partial<ProjectSettings>): Promise<Project> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project ${projectId} not found`);
    }

    const updatedProject = {
      ...project,
      settings: {
        ...project.settings,
        ...settings
      },
      updatedAt: new Date().toISOString()
    };

    this.projects.set(projectId, updatedProject);
    return updatedProject;
  }

  async updateSecret(projectId: string, key: string, value: string): Promise<void> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project ${projectId} not found`);
    }

    project.settings.secrets[key] = value;
    project.updatedAt = new Date().toISOString();
    this.projects.set(projectId, project);
  }

  async removeSecret(projectId: string, key: string): Promise<void> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project ${projectId} not found`);
    }

    delete project.settings.secrets[key];
    project.updatedAt = new Date().toISOString();
    this.projects.set(projectId, project);
  }

  async testSetupCommands(projectId: string, commands: string, branch?: string): Promise<{ success: boolean; output: string }> {
    // Mock implementation
    return {
      success: true,
      output: `Successfully tested setup commands on branch ${branch || 'main'}`
    };
  }

  async refreshProject(projectId: string): Promise<Project> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project ${projectId} not found`);
    }

    // Mock refresh - in real implementation, this would fetch latest data
    project.updatedAt = new Date().toISOString();
    this.projects.set(projectId, project);
    return project;
  }
}

export const projectService = new ProjectService();
