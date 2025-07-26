/**
 * Project Card Component
 * Displays individual project information with Agent Run button and settings
 */

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  IconButton,
  Box,
  Chip,
  Menu,
  MenuItem,
  LinearProgress,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  Settings as SettingsIcon,
  MoreVert as MoreIcon,
  GitHub as GitHubIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  AutoMode as AutoIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

import { Project, AgentRun } from '../../types/api';
import { useDashboard } from '../../contexts/DashboardContext';
import StatusIndicator from './StatusIndicator';

interface ProjectCardProps {
  project: Project;
  agentRuns?: AgentRun[];
  onAgentRun: (project: Project) => void;
  onSettings: (project: Project) => void;
}

const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  agentRuns = [],
  onAgentRun,
  onSettings,
}) => {
  const { dashboardState } = useDashboard();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const activeRuns = agentRuns.filter(run => run.status === 'ACTIVE');
  const lastRun = agentRuns.length > 0 ? agentRuns[0] : null;
  const hasActiveRun = activeRuns.length > 0;

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleAgentRun = () => {
    onAgentRun(project);
  };

  const handleSettings = () => {
    onSettings(project);
    handleMenuClose();
  };

  const handleViewGitHub = () => {
    window.open(`https://github.com/${project.github_owner}/${project.github_repo}`, '_blank');
    handleMenuClose();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'default';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <SuccessIcon />;
      case 'inactive':
        return <PendingIcon />;
      case 'error':
        return <ErrorIcon />;
      default:
        return <PendingIcon />;
    }
  };

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 4,
        },
        ...(hasActiveRun && {
          borderLeft: 4,
          borderLeftColor: 'primary.main',
        }),
      }}
    >
      {/* Active Run Progress Bar */}
      {hasActiveRun && (
        <LinearProgress
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 3,
          }}
        />
      )}

      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" component="h2" gutterBottom>
              {project.name}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {project.description || 'No description provided'}
            </Typography>
          </Box>
          
          <IconButton
            size="small"
            onClick={handleMenuOpen}
            sx={{ ml: 1 }}
          >
            <MoreIcon />
          </IconButton>
        </Box>

        {/* Repository Info */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <GitHubIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
          <Typography variant="body2" color="text.secondary">
            {project.github_owner}/{project.github_repo}
          </Typography>
        </Box>

        {/* Status and Configuration Indicators */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          <Chip
            size="small"
            label={project.status}
            color={getStatusColor(project.status) as any}
            icon={getStatusIcon(project.status)}
          />
          
          {project.auto_merge_enabled && (
            <Tooltip title="Auto-merge enabled">
              <Chip
                size="small"
                label="Auto-merge"
                color="info"
                icon={<AutoIcon />}
              />
            </Tooltip>
          )}
          
          {project.auto_confirm_plans && (
            <Tooltip title="Auto-confirm plans enabled">
              <Chip
                size="small"
                label="Auto-confirm"
                color="info"
                icon={<CheckCircle />}
              />
            </Tooltip>
          )}
        </Box>

        {/* Agent Run Status */}
        {hasActiveRun && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="primary" sx={{ fontWeight: 600 }}>
              🤖 Agent Running ({activeRuns.length})
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Started {formatDistanceToNow(new Date(activeRuns[0].created_at))} ago
            </Typography>
          </Box>
        )}

        {lastRun && !hasActiveRun && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Last run: {formatDistanceToNow(new Date(lastRun.created_at))} ago
            </Typography>
            <StatusIndicator status={lastRun.status} size="small" />
          </Box>
        )}

        {/* PR Indicators */}
        {agentRuns.some(run => run.pr_number) && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {agentRuns
              .filter(run => run.pr_number)
              .slice(0, 3)
              .map(run => (
                <Badge key={run.id} badgeContent={run.pr_number} color="primary">
                  <Chip
                    size="small"
                    label="PR"
                    color="primary"
                    variant="outlined"
                    onClick={() => window.open(run.pr_url, '_blank')}
                    sx={{ cursor: 'pointer' }}
                  />
                </Badge>
              ))}
          </Box>
        )}
      </CardContent>

      <CardActions sx={{ pt: 0, px: 2, pb: 2 }}>
        <Button
          variant="contained"
          startIcon={<RunIcon />}
          onClick={handleAgentRun}
          disabled={dashboardState.isLoading}
          fullWidth
          sx={{
            borderRadius: 2,
            textTransform: 'none',
            fontWeight: 600,
          }}
        >
          {hasActiveRun ? 'View Progress' : 'Agent Run'}
        </Button>
      </CardActions>

      {/* Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <MenuItem onClick={handleSettings}>
          <SettingsIcon sx={{ mr: 1 }} />
          Settings
        </MenuItem>
        <MenuItem onClick={handleViewGitHub}>
          <GitHubIcon sx={{ mr: 1 }} />
          View on GitHub
        </MenuItem>
      </Menu>
    </Card>
  );
};

export default ProjectCard;
