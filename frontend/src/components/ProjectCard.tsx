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
  Checkbox
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
  AutoMode as AutoModeIcon
} from '@mui/icons-material';

import { ProjectSettings } from './ProjectSettings';
import { AgentRunDialog } from './AgentRunDialog';
import { ValidationFlow } from './ValidationFlow';

import { useProjectActions } from '../store/projectStore';
import { useWorkflowActions, useActiveWorkflows } from '../store/workflowStore';
import { Project, Notification, NotificationType, ProjectStatus, WorkflowStatus } from '../types/cicd';

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

  return (
    <>
      <Card
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          border: isSelected ? 2 : 1,
          borderColor: isSelected ? 'primary.main' : 'divider',
          cursor: 'pointer',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            elevation: 4,
            transform: 'translateY(-2px)',
          },
          backgroundColor: hasRepositoryRules ? 'action.hover' : 'background.paper',
        }}
        onClick={onSelect}
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
                handleMenuClick(e);
              }}
            >
              <MoreVertIcon />
            </IconButton>
          </Box>

          {/* Repository Info */}
          <Box display="flex" alignItems="center" mb={2}>
            <GitHubIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary" noWrap>
              {project.github_owner}/{project.github_repo}
            </Typography>
          </Box>

          {/* Status Indicators */}
          <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
            <Chip
              icon={getStatusIcon()}
              label={project.status}
              color={getStatusColor()}
              size="small"
            />
            
            {project.auto_merge_enabled && (
              <Chip
                icon={<AutoModeIcon />}
                label="Auto-merge"
                color="primary"
                size="small"
                variant="outlined"
              />
            )}
            
            {project.auto_confirm_plans && (
              <Chip
                label="Auto-confirm"
                color="secondary"
                size="small"
                variant="outlined"
              />
            )}
          </Box>

          {/* Progress Indicators */}
          {runningRuns.length > 0 && (
            <Box mb={2}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Agent runs in progress: {runningRuns.length}
              </Typography>
              <LinearProgress />
            </Box>
          )}

          {/* Recent Activity */}
          {recentPRs.length > 0 && (
            <Box mb={1}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Recent PRs:
              </Typography>
              {recentPRs.slice(0, 2).map((run) => (
                <Box key={run.id} display="flex" alignItems="center" mb={0.5}>
                  <Badge
                    badgeContent={run.pr_number}
                    color="primary"
                    sx={{ mr: 1 }}
                  >
                    <GitHubIcon sx={{ fontSize: 16 }} />
                  </Badge>
                  <Typography variant="body2" noWrap sx={{ flexGrow: 1 }}>
                    {run.target_text.substring(0, 30)}...
                  </Typography>
                </Box>
              ))}
            </Box>
          )}

          {/* Error Messages */}
          {hasErrors && (
            <Alert severity="error" sx={{ mt: 1 }}>
              Some agent runs have failed. Check logs for details.
            </Alert>
          )}
        </CardContent>

        <CardActions sx={{ pt: 0, px: 2, pb: 2 }}>
          <Button
            variant="contained"
            startIcon={<PlayIcon />}
            onClick={(e) => {
              e.stopPropagation();
              handleAgentRunStart();
            }}
            disabled={loading}
            fullWidth
          >
            Agent Run
          </Button>
        </CardActions>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => { handleMenuClose(); onOpenConfig(); }}>
          <SettingsIcon sx={{ mr: 1 }} />
          Settings
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); handleToggleAutoMerge(); }}>
          <AutoModeIcon sx={{ mr: 1 }} />
          {project.auto_merge_enabled ? 'Disable' : 'Enable'} Auto-merge
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); handleToggleAutoConfirm(); }}>
          <CheckCircleIcon sx={{ mr: 1 }} />
          {project.auto_confirm_plans ? 'Disable' : 'Enable'} Auto-confirm
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); onDelete(); }} sx={{ color: 'error.main' }}>
          Delete Project
        </MenuItem>
      </Menu>

      {/* Agent Run Dialog */}
      <AgentRunDialog
        open={agentRunDialogOpen}
        onClose={() => setAgentRunDialogOpen(false)}
        onSubmit={handleAgentRunCreate}
        project={project}
        loading={loading}
      />
    </>
  );
};

export default ProjectCard;
