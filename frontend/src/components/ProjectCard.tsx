/**
 * Project Card Component with all CICD features
 */

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Box,
  Button,
  IconButton,
  Chip,
  Avatar,
  LinearProgress,
  Badge,
  Tooltip,
  Menu,
  MenuItem,
  Divider,
  FormControlLabel,
  Checkbox,
  Alert
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  Settings as SettingsIcon,
  GitHub as GitHubIcon,
  Refresh as RefreshIcon,
  MoreVert as MoreVertIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Schedule as ScheduleIcon,
  Code as CodeIcon,
  Security as SecurityIcon,
  Terminal as TerminalIcon,
  AutoMode as AutoModeIcon,
  Info as InfoIcon
} from '@mui/icons-material';


import AgentRunDialog from './AgentRunDialog';
import { Project as ApiProject } from '../services/api';

import { useProjectActions } from '../store/projectStore';
import { useWorkflowActions, useActiveWorkflows } from '../store/workflowStore';
import { Project, Notification, NotificationType, ProjectStatus, WorkflowStatus, AgentRunType } from '../types/cicd';

// ============================================================================
// INTERFACES
// ============================================================================

interface ProjectCardProps {
  project: Project;
  onNotification: (notification: Notification) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onNotification
}) => {
  // State
  const [showSettings, setShowSettings] = useState(false);
  const [showAgentRun, setShowAgentRun] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);

  // Store hooks
  const { updateSettings, refreshProject, deleteProject } = useProjectActions();
  const { createWorkflow } = useWorkflowActions();
  const activeWorkflows = useActiveWorkflows(project.id);

  // ========================================================================
  // COMPUTED VALUES
  // ========================================================================

  const hasActiveWorkflow = activeWorkflows.length > 0;
  const currentWorkflow = activeWorkflows[0]; // Most recent workflow
  const hasCustomRules = project.settings.repositoryRules.trim().length > 0;
  const hasSecrets = Object.keys(project.settings.secrets).length > 0;
  const hasSetupCommands = project.settings.setupCommands.trim().length > 0;

  // Status color mapping
  const getStatusColor = (status: ProjectStatus) => {
    switch (status) {
      case ProjectStatus.ACTIVE:
        return 'success';
      case ProjectStatus.ERROR:
        return 'error';
      case ProjectStatus.CONFIGURING:
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status?: ProjectStatus) => {
    switch (status || project.status) {
      case ProjectStatus.ACTIVE:
        return <CheckCircleIcon />;
      case ProjectStatus.ERROR:
        return <ErrorIcon />;
      case ProjectStatus.CONFIGURING:
        return <SettingsIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const getWorkflowStatusColor = (status?: WorkflowStatus) => {
    switch (status) {
      case WorkflowStatus.COMPLETED:
        return 'success';
      case WorkflowStatus.FAILED:
        return 'error';
      case WorkflowStatus.RUNNING:
      case WorkflowStatus.VALIDATING:
        return 'primary';
      default:
        return 'default';
    }
  };

  // ========================================================================
  // HANDLERS
  // ========================================================================

  const handleAgentRun = () => {
    setShowAgentRun(true);
  };

  const handleAgentRunSubmit = async (target: string) => {
    try {
      const workflow = createWorkflow(
        project.id,
        target,
        project.settings.planningStatement,
        'manual'
      );

      onNotification({
        id: `agent_run_${Date.now()}`,
        type: NotificationType.INFO,
        title: 'Agent Run Started',
        message: `Started agent run for ${project.name}`,
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 3000
      });

      setShowAgentRun(false);
    } catch (error) {
      onNotification({
        id: `agent_run_error_${Date.now()}`,
        type: NotificationType.ERROR,
        title: 'Agent Run Failed',
        message: 'Failed to start agent run. Please try again.',
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 5000
      });
    }
  };

  const handleAutoMergeToggle = async (enabled: boolean) => {
    try {
      await updateSettings(project.id, { autoMergeValidatedPR: enabled });
      
      onNotification({
        id: `auto_merge_${Date.now()}`,
        type: NotificationType.SUCCESS,
        title: 'Auto-merge Updated',
        message: `Auto-merge ${enabled ? 'enabled' : 'disabled'} for ${project.name}`,
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 3000
      });
    } catch (error) {
      onNotification({
        id: `auto_merge_error_${Date.now()}`,
        type: NotificationType.ERROR,
        title: 'Update Failed',
        message: 'Failed to update auto-merge setting',
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 5000
      });
    }
  };

  const handleRefresh = async () => {
    try {
      await refreshProject(project.id);
      
      onNotification({
        id: `refresh_${Date.now()}`,
        type: NotificationType.SUCCESS,
        title: 'Project Refreshed',
        message: `${project.name} has been refreshed`,
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 2000
      });
    } catch (error) {
      onNotification({
        id: `refresh_error_${Date.now()}`,
        type: NotificationType.ERROR,
        title: 'Refresh Failed',
        message: 'Failed to refresh project data',
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 5000
      });
    }
  };

  const handleDeleteProject = async () => {
    if (window.confirm(`Are you sure you want to remove ${project.name} from the dashboard?`)) {
      try {
        await deleteProject(project.id);
        
        onNotification({
          id: `delete_${Date.now()}`,
          type: NotificationType.INFO,
          title: 'Project Removed',
          message: `${project.name} has been removed from dashboard`,
          timestamp: new Date().toISOString(),
          read: false,
          autoDismiss: true,
          dismissAfter: 3000
        });
      } catch (error) {
        onNotification({
          id: `delete_error_${Date.now()}`,
          type: NotificationType.ERROR,
          title: 'Delete Failed',
          message: 'Failed to remove project',
          timestamp: new Date().toISOString(),
          read: false,
          autoDismiss: true,
          dismissAfter: 5000
        });
      }
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handlePRClick = (prNumber: number) => {
    // This would open the validation flow for the specific PR
    setShowValidation(true);
  };

  const handleAgentRunDialogSubmit = (data: { target_text: string; planning_statement?: string }) => {
    handleAgentRunSubmit(data.target_text);
  };

  // Convert cicd.ts Project to api.ts Project format for AgentRunDialog
  const convertToApiProject = (project: Project): ApiProject => {
    // Convert WorkflowStatus to expected status strings
    const convertStatus = (status: WorkflowStatus): string => {
      switch (status) {
        case WorkflowStatus.IDLE: return 'pending';
        case WorkflowStatus.RUNNING: return 'running';
        case WorkflowStatus.VALIDATING: return 'running';
        case WorkflowStatus.COMPLETED: return 'completed';
        case WorkflowStatus.FAILED: return 'failed';
        case WorkflowStatus.CANCELLED: return 'cancelled';
        default: return 'pending';
      }
    };

    // Convert AgentRunType to expected run_type strings
    const convertRunType = (runType: AgentRunType): string => {
      switch (runType) {
        case AgentRunType.REGULAR: return 'regular';
        case AgentRunType.PLAN: return 'plan';
        case AgentRunType.PR: return 'pr';
        default: return 'regular';
      }
    };

    return {
      id: parseInt(project.id),
      name: project.name,
      description: '',
      github_repo: project.repo,
      github_owner: project.owner,
      github_branch: project.defaultBranch,
      github_url: `https://github.com/${project.owner}/${project.repo}`,
      webhook_url: '',
      webhook_active: project.settings.webhookEnabled,
      auto_merge_enabled: project.settings.autoMergeValidatedPR,
      auto_confirm_plans: project.settings.autoConfirmPlan,
      auto_merge_threshold: project.settings.validationTimeout || 30,
      auto_merge_validated_pr: project.settings.autoMergeValidatedPR,
      planning_statement: project.settings.planningStatement,
      repository_rules: project.settings.repositoryRules,
      setup_commands: project.settings.setupCommands,
      setup_branch: project.settings.selectedBranch,
      is_active: true,
      status: 'active' as const,
      validation_enabled: true,
      has_repository_rules: !!project.settings.repositoryRules,
      has_setup_commands: !!project.settings.setupCommands,
      has_secrets: Object.keys(project.settings.secrets || {}).length > 0,
      has_planning_statement: !!project.settings.planningStatement,
      current_agent_run: project.currentWorkflow ? {
        id: project.currentWorkflow.id,
        status: convertStatus(project.currentWorkflow.status) as any,
        run_type: convertRunType(project.currentWorkflow.agentRunType) as any,
        progress_percentage: 0,
        current_step: project.currentWorkflow.stage,
      } : undefined,
      last_run_at: project.currentWorkflow?.startedAt,
      total_runs: project.stats.totalRuns,
      success_rate: project.stats.totalRuns > 0 ? (project.stats.successfulRuns / project.stats.totalRuns) * 100 : 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  };

  return (
    <>
      <Card
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          border: 1,
          borderColor: 'divider',
          cursor: 'pointer',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            elevation: 4,
            transform: 'translateY(-2px)',
          },
          backgroundColor: project.settings.repositoryRules ? 'action.hover' : 'background.paper',
        }}

      >
        <CardContent sx={{ flexGrow: 1, pb: 1 }}>
          {/* Header */}
          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
            <Typography variant="h6" component="h2" noWrap sx={{ flexGrow: 1, mr: 1 }}>
              {project.name}
            </Typography>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                handleMenuOpen(e);
              }}
            >
              <MoreVertIcon />
            </IconButton>
          </Box>

          {/* Repository Info */}
          <Box display="flex" alignItems="center" mb={2}>
            <GitHubIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary" noWrap>
              {project.owner}/{project.repo}
            </Typography>
          </Box>

          {/* Status Indicators */}
          <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
            <Chip
              icon={getStatusIcon(project.status)}
              label={project.status}
              color={getStatusColor(project.status)}
              size="small"
            />
            
            {project.settings.autoMergeValidatedPR && (
              <Chip
                icon={<AutoModeIcon />}
                label="Auto-merge"
                color="primary"
                size="small"
                variant="outlined"
              />
            )}
            
            {project.settings.autoConfirmPlan && (
              <Chip
                label="Auto-confirm"
                color="secondary"
                size="small"
                variant="outlined"
              />
            )}
          </Box>

          {/* Progress Indicators */}
          {(project.currentWorkflow || project.activePRs.length > 0) && (
            <Box mb={2}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {project.currentWorkflow ? 'Workflow in progress' : `Active PRs: ${project.activePRs.length}`}
              </Typography>
              <LinearProgress />
            </Box>
          )}

          {/* Recent Activity */}
          {project.activePRs.length > 0 && (
            <Box mb={1}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Recent PRs:
              </Typography>
              {project.activePRs.slice(0, 2).map((pr) => (
                <Box key={pr.id} display="flex" alignItems="center" mb={0.5}>
                  <Badge
                    badgeContent={pr.number}
                    color="primary"
                    sx={{ mr: 1 }}
                  >
                    <GitHubIcon sx={{ fontSize: 16 }} />
                  </Badge>
                  <Typography variant="body2" noWrap sx={{ flexGrow: 1 }}>
                    {pr.title.substring(0, 30)}...
                  </Typography>
                </Box>
              ))}
            </Box>
          )}

          {/* Error Messages */}
          {project.status === ProjectStatus.ERROR && (
            <Alert severity="error" sx={{ mt: 1 }}>
              Some agent runs have failed. Check logs for details.
            </Alert>
          )}
        </CardContent>

        <CardActions sx={{ pt: 0, px: 2, pb: 2 }}>
          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={(e) => {
              e.stopPropagation();
              createWorkflow(
                project.id,
                'Quick workflow run',
                project.settings.planningStatement,
                'manual'
              );
            }}
            disabled={hasActiveWorkflow}
            fullWidth
          >
            Agent Run
          </Button>
        </CardActions>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => { handleMenuClose(); setShowSettings(true); }}>
          <SettingsIcon sx={{ mr: 1 }} />
          Settings
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); handleAutoMergeToggle(!project.settings.autoMergeValidatedPR); }}>
          <AutoModeIcon sx={{ mr: 1 }} />
          {project.settings.autoMergeValidatedPR ? 'Disable' : 'Enable'} Auto-merge
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); updateSettings(project.id, { autoConfirmPlan: !project.settings.autoConfirmPlan }); }}>
          <CheckCircleIcon sx={{ mr: 1 }} />
          {project.settings.autoConfirmPlan ? 'Disable' : 'Enable'} Auto-confirm
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); handleDeleteProject(); }} sx={{ color: 'error.main' }}>
          Delete Project
        </MenuItem>
      </Menu>

      {/* Agent Run Dialog */}
      <AgentRunDialog
        open={showAgentRun}
        onClose={() => setShowAgentRun(false)}
        onSubmit={handleAgentRunDialogSubmit}
        project={convertToApiProject(project)}
        loading={hasActiveWorkflow}
      />
    </>
  );
};

export default ProjectCard;
