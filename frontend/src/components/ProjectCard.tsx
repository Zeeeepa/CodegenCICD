/**
 * Project Card Component - Individual project display with status indicators
 */

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  IconButton,
  Menu,
  MenuItem,
  LinearProgress,
  Avatar,
  Tooltip,
  Badge
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  GitHub as GitHubIcon,
  PlayArrow as PlayArrowIcon,
  Settings as SettingsIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Webhook as WebhookIcon
} from '@mui/icons-material';

import { Project, Notification, NotificationType } from '../types/cicd';
import { useProjectActions } from '../store/projectStore';

interface ProjectCardProps {
  project: Project;
  onNotification: (notification: Notification) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onNotification
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [loading, setLoading] = useState(false);
  
  const { refreshProject, deleteProject } = useProjectActions();

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await refreshProject(project.id);
      onNotification({
        id: `refresh_${project.id}_${Date.now()}`,
        type: NotificationType.SUCCESS,
        title: 'Project Refreshed',
        message: `${project.name} has been refreshed successfully`,
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 3000
      });
    } catch (error) {
      onNotification({
        id: `refresh_error_${project.id}_${Date.now()}`,
        type: NotificationType.ERROR,
        title: 'Refresh Failed',
        message: `Failed to refresh ${project.name}`,
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 5000
      });
    } finally {
      setLoading(false);
    }
    handleMenuClose();
  };

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete ${project.name}?`)) {
      try {
        await deleteProject(project.id);
        onNotification({
          id: `delete_${project.id}_${Date.now()}`,
          type: NotificationType.SUCCESS,
          title: 'Project Deleted',
          message: `${project.name} has been deleted successfully`,
          timestamp: new Date().toISOString(),
          read: false,
          autoDismiss: true,
          dismissAfter: 3000
        });
      } catch (error) {
        onNotification({
          id: `delete_error_${project.id}_${Date.now()}`,
          type: NotificationType.ERROR,
          title: 'Delete Failed',
          message: `Failed to delete ${project.name}`,
          timestamp: new Date().toISOString(),
          read: false,
          autoDismiss: true,
          dismissAfter: 5000
        });
      }
    }
    handleMenuClose();
  };

  const handleRunAgent = () => {
    // This would open the agent run dialog
    onNotification({
      id: `agent_run_${project.id}_${Date.now()}`,
      type: NotificationType.INFO,
      title: 'Agent Run',
      message: 'Agent run dialog would open here',
      timestamp: new Date().toISOString(),
      read: false,
      autoDismiss: true,
      dismissAfter: 3000
    });
  };

  const handleSettings = () => {
    // This would open the project settings dialog
    onNotification({
      id: `settings_${project.id}_${Date.now()}`,
      type: NotificationType.INFO,
      title: 'Settings',
      message: 'Project settings dialog would open here',
      timestamp: new Date().toISOString(),
      read: false,
      autoDismiss: true,
      dismissAfter: 3000
    });
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
        return <CheckCircleIcon />;
      case 'error':
        return <ErrorIcon />;
      default:
        return <ScheduleIcon />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Card 
      sx={{ 
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        '&:hover': {
          boxShadow: 4,
        }
      }}
    >
      {loading && (
        <LinearProgress 
          sx={{ 
            position: 'absolute', 
            top: 0, 
            left: 0, 
            right: 0,
            zIndex: 1
          }} 
        />
      )}

      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
              <GitHubIcon fontSize="small" />
            </Avatar>
            <Box sx={{ minWidth: 0, flexGrow: 1 }}>
              <Typography variant="h6" noWrap title={project.name}>
                {project.name}
              </Typography>
              <Typography variant="body2" color="text.secondary" noWrap>
                {project.github_owner}/{project.github_repo}
              </Typography>
            </Box>
          </Box>
          
          <IconButton size="small" onClick={handleMenuOpen}>
            <MoreVertIcon />
          </IconButton>
        </Box>

        {/* Status and Webhook */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          <Chip
            icon={getStatusIcon(project.status)}
            label={project.status}
            color={getStatusColor(project.status) as any}
            size="small"
            variant="outlined"
          />
          
          {project.webhook_url && (
            <Tooltip title="Webhook configured">
              <Chip
                icon={<WebhookIcon />}
                label="Webhook"
                size="small"
                variant="outlined"
                color="info"
              />
            </Tooltip>
          )}

          {project.auto_merge_enabled && (
            <Chip
              label="Auto-merge"
              size="small"
              variant="outlined"
              color="secondary"
            />
          )}
        </Box>

        {/* Statistics */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Statistics
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">Total Runs:</Typography>
            <Typography variant="body2" fontWeight="medium">
              {project.stats.totalRuns}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">Success Rate:</Typography>
            <Typography variant="body2" fontWeight="medium" color="success.main">
              {project.stats.successRate}%
            </Typography>
          </Box>
          {project.stats.lastRunAt && (
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2">Last Run:</Typography>
              <Typography variant="body2" fontWeight="medium">
                {formatDate(project.stats.lastRunAt)}
              </Typography>
            </Box>
          )}
        </Box>

        {/* Dates */}
        <Typography variant="caption" color="text.secondary">
          Created: {formatDate(project.created_at)}
        </Typography>
      </CardContent>

      <CardActions sx={{ pt: 0, justifyContent: 'space-between' }}>
        <Button
          size="small"
          startIcon={<PlayArrowIcon />}
          onClick={handleRunAgent}
          variant="contained"
          color="primary"
        >
          Run Agent
        </Button>
        
        <Button
          size="small"
          startIcon={<SettingsIcon />}
          onClick={handleSettings}
          variant="outlined"
        >
          Settings
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
        <MenuItem onClick={handleRefresh}>
          <RefreshIcon sx={{ mr: 1 }} fontSize="small" />
          Refresh
        </MenuItem>
        <MenuItem onClick={handleSettings}>
          <SettingsIcon sx={{ mr: 1 }} fontSize="small" />
          Settings
        </MenuItem>
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
          Delete
        </MenuItem>
      </Menu>
    </Card>
  );
};

