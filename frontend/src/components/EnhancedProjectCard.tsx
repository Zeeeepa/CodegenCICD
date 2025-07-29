import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Box,
  Chip,
  IconButton,
  LinearProgress,
  Menu,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Tooltip,
  Badge,
  Avatar,
  Divider,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Settings as SettingsIcon,
  GitHub as GitHubIcon,
  Security as SecurityIcon,
  Build as BuildIcon,
  AutoMode as AutoModeIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  MoreVert as MoreVertIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';

import AgentRunDialog from './AgentRunDialog';
import ProjectSettingsDialog from './ProjectSettingsDialog';
import ValidationFlowDialog from './ValidationFlowDialog';

export interface ProjectData {
  id: number;
  name: string;
  description?: string;
  github_owner: string;
  github_repo: string;
  github_branch: string;
  github_url: string;
  webhook_active: boolean;
  webhook_url: string;
  auto_merge_enabled: boolean;
  auto_confirm_plans: boolean;
  auto_merge_threshold: number;
  is_active: boolean;
  status: 'active' | 'inactive';
  validation_enabled: boolean;
  
  // Configuration indicators
  has_repository_rules: boolean;
  has_setup_commands: boolean;
  has_secrets: boolean;
  has_planning_statement: boolean;
  
  // Current agent run status
  current_agent_run?: {
    id: string;
    status: 'pending' | 'running' | 'waiting_for_input' | 'completed' | 'failed' | 'cancelled';
    progress_percentage: number;
    current_step?: string;
    run_type: 'regular' | 'plan' | 'pr_creation' | 'error_fix';
    pr_number?: number;
    pr_url?: string;
  };
  
  // Recent activity
  last_run_at?: string;
  total_runs: number;
  success_rate: number;
  created_at: string;
  updated_at: string;
}

interface EnhancedProjectCardProps {
  project: ProjectData;
  onAgentRun: (projectId: number, target: string) => void;
  onAgentRunContinue: (projectId: number, runId: number, message: string) => void;
  onUpdateProject: (projectId: number, updates: Partial<ProjectData>) => void;
  onDeleteProject: (projectId: number) => void;
  onRunSetupCommands: (projectId: number) => void;
}

export const EnhancedProjectCard: React.FC<EnhancedProjectCardProps> = ({
  project,
  onAgentRun,
  onAgentRunContinue,
  onUpdateProject,
  onDeleteProject,
  onRunSetupCommands,
}) => {
  const [agentRunDialogOpen, setAgentRunDialogOpen] = useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [currentPrNumber, setCurrentPrNumber] = useState<number | undefined>();
  const [currentPrUrl, setCurrentPrUrl] = useState<string | undefined>();

  // Handle PR notifications and trigger validation
  const handlePrNotification = (prNumber: number, prUrl: string) => {
    setCurrentPrNumber(prNumber);
    setCurrentPrUrl(prUrl);
    setValidationDialogOpen(true);
  };

  // Status indicators
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'primary';
      case 'completed': return 'success';
      case 'failed': return 'error';
      case 'pending': return 'warning';
      case 'cancelled': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return <PendingIcon />;
      case 'completed': return <CheckCircleIcon />;
      case 'failed': return <ErrorIcon />;
      case 'pending': return <PendingIcon />;
      default: return <PendingIcon />;
    }
  };

  // Configuration indicators
  const configurationCount = [
    project.has_repository_rules,
    project.has_setup_commands,
    project.has_secrets,
    project.has_planning_statement,
  ].filter(Boolean).length;

  const handleAgentRun = (data: { target_text: string; planning_statement?: string }) => {
    onAgentRun(project.id, data.target_text);
    setAgentRunDialogOpen(false);
  };

  const handleAutoMergeToggle = (enabled: boolean) => {
    onUpdateProject(project.id, { auto_merge_enabled: enabled });
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const formatLastRun = (timestamp?: string) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <>
      <Card 
        sx={{ 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column',
          border: project.current_agent_run?.status === 'running' ? '2px solid' : '1px solid',
          borderColor: project.current_agent_run?.status === 'running' ? 'primary.main' : 'divider',
          position: 'relative',
          '&:hover': {
            boxShadow: 4,
          }
        }}
      >
        {/* Header */}
        <CardContent sx={{ pb: 1 }}>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
            <Box display="flex" alignItems="center" gap={1}>
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                <GitHubIcon fontSize="small" />
              </Avatar>
              <Box>
                <Typography variant="h6" component="div" noWrap>
                  {project.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {project.github_owner}/{project.github_repo}
                </Typography>
              </Box>
            </Box>
            
            <Box display="flex" alignItems="center" gap={0.5}>
              {/* Configuration indicator */}
              <Tooltip title={`${configurationCount}/4 configurations set`}>
                <Badge badgeContent={configurationCount} color="primary" max={4}>
                  <SettingsIcon fontSize="small" color={configurationCount > 0 ? 'primary' : 'disabled'} />
                </Badge>
              </Tooltip>
              
              {/* Menu */}
              <IconButton size="small" onClick={(e) => setMenuAnchor(e.currentTarget)}>
                <MoreVertIcon />
              </IconButton>
            </Box>
          </Box>

          {/* Description */}
          {project.description && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {project.description}
            </Typography>
          )}

          {/* Status indicators */}
          <Box display="flex" gap={1} mb={1} flexWrap="wrap">
            <Chip
              size="small"
              label={project.is_active ? 'Active' : 'Inactive'}
              color={project.is_active ? 'success' : 'default'}
            />
            {project.webhook_active && (
              <Chip size="small" label="Webhook" color="info" />
            )}
            {project.validation_enabled && (
              <Chip size="small" label="Validation" color="secondary" />
            )}
          </Box>

          {/* Current agent run status */}
          {project.current_agent_run && (
            <Box sx={{ mb: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                {getStatusIcon(project.current_agent_run.status)}
                <Typography variant="body2" fontWeight="medium">
                  {project.current_agent_run.status.replace('_', ' ').toUpperCase()}
                </Typography>
                {project.current_agent_run.pr_number && (
                  <Chip
                    size="small"
                    label={`PR #${project.current_agent_run.pr_number}`}
                    color="info"
                    clickable
                    onClick={() => handlePrNotification(
                      project.current_agent_run!.pr_number!,
                      project.current_agent_run!.pr_url || ''
                    )}
                    icon={<GitHubIcon />}
                  />
                )}
              </Box>
              
              {project.current_agent_run.status === 'running' && (
                <Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={project.current_agent_run.progress_percentage} 
                    sx={{ mb: 0.5 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {project.current_agent_run.current_step || 'Processing...'}
                  </Typography>
                </Box>
              )}
            </Box>
          )}

          {/* Statistics */}
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="caption" color="text.secondary">
              Last run: {formatLastRun(project.last_run_at)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {project.total_runs} runs • {Math.round(project.success_rate)}% success
            </Typography>
          </Box>
        </CardContent>

        <Divider />

        {/* Actions */}
        <CardActions sx={{ p: 2, pt: 1, mt: 'auto' }}>
          <Box display="flex" width="100%" gap={1} alignItems="center">
            {/* Agent Run Button */}
            <Button
              variant="contained"
              startIcon={<PlayIcon />}
              onClick={() => setAgentRunDialogOpen(true)}
              disabled={project.current_agent_run?.status === 'running'}
              sx={{ flexGrow: 1 }}
            >
              Agent Run
            </Button>

            {/* Settings Button */}
            <IconButton
              onClick={() => setSettingsDialogOpen(true)}
              color="primary"
            >
              <SettingsIcon />
            </IconButton>
          </Box>

          {/* Auto-merge toggle */}
          <Box width="100%" mt={1}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={project.auto_merge_enabled}
                  onChange={(e) => handleAutoMergeToggle(e.target.checked)}
                  size="small"
                />
              }
              label={
                <Typography variant="caption">
                  Auto-merge validated PRs
                </Typography>
              }
            />
          </Box>
        </CardActions>

        {/* Menu */}
        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={handleMenuClose}
        >
          <MenuItem onClick={() => { window.location.reload(); handleMenuClose(); }}>
            <RefreshIcon sx={{ mr: 1 }} fontSize="small" />
            Refresh
          </MenuItem>
          <MenuItem onClick={() => { window.open(project.github_url, '_blank'); handleMenuClose(); }}>
            <OpenInNewIcon sx={{ mr: 1 }} fontSize="small" />
            Open in GitHub
          </MenuItem>
          <MenuItem onClick={() => { onDeleteProject(project.id); handleMenuClose(); }} sx={{ color: 'error.main' }}>
            <ErrorIcon sx={{ mr: 1 }} fontSize="small" />
            Remove Project
          </MenuItem>
        </Menu>
      </Card>

      {/* Dialogs */}
      <AgentRunDialog
        open={agentRunDialogOpen}
        onClose={() => setAgentRunDialogOpen(false)}
        onSubmit={handleAgentRun}
        project={project}
        loading={false}
      />

      <ProjectSettingsDialog
        open={settingsDialogOpen}
        onClose={() => setSettingsDialogOpen(false)}
        project={project}
        onUpdate={(updates) => onUpdateProject(project.id, updates)}
        onRunSetupCommands={() => onRunSetupCommands(project.id)}
      />

      <ValidationFlowDialog
        open={validationDialogOpen}
        onClose={() => setValidationDialogOpen(false)}
        projectId={project.id}
        prNumber={currentPrNumber}
        prUrl={currentPrUrl}
      />
    </>
  );
};
