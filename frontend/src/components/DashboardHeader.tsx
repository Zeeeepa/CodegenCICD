/**
 * Dashboard Header Component
 */

import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Box,
  Switch,
  FormControlLabel,
  Chip,
  Tooltip
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  GitHub as GitHubIcon,
  Dashboard as DashboardIcon
} from '@mui/icons-material';

// ============================================================================
// INTERFACE
// ============================================================================

interface DashboardHeaderProps {
  onAddProject: () => void;
  onRefreshAll: () => void;
  onOpenSettings: () => void;
  autoRefreshEnabled: boolean;
  onToggleAutoRefresh: (enabled: boolean) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  onAddProject,
  onRefreshAll,
  onOpenSettings,
  autoRefreshEnabled,
  onToggleAutoRefresh
}) => {
  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        {/* Logo and Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
          <DashboardIcon sx={{ mr: 2, fontSize: 32 }} />
          <Box>
            <Typography variant="h5" component="div" sx={{ fontWeight: 'bold' }}>
              CICD Dashboard
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              Automated Development Workflow Management
            </Typography>
          </Box>
        </Box>

        {/* Status Indicators */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mr: 3 }}>
          <Chip
            icon={<GitHubIcon />}
            label="GitHub Connected"
            color="success"
            variant="outlined"
            size="small"
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={autoRefreshEnabled}
                onChange={(e) => onToggleAutoRefresh(e.target.checked)}
                size="small"
                color="secondary"
              />
            }
            label={
              <Typography variant="caption">
                Auto-refresh
              </Typography>
            }
            sx={{ m: 0 }}
          />
        </Box>

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Tooltip title="Refresh all projects">
            <IconButton
              color="inherit"
              onClick={onRefreshAll}
              sx={{ mr: 1 }}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>

          <Button
            color="inherit"
            startIcon={<AddIcon />}
            onClick={onAddProject}
            variant="outlined"
            sx={{ 
              mr: 1,
              borderColor: 'rgba(255, 255, 255, 0.3)',
              '&:hover': {
                borderColor: 'rgba(255, 255, 255, 0.5)',
                bgcolor: 'rgba(255, 255, 255, 0.1)'
              }
            }}
          >
            Add Project
          </Button>

          <Tooltip title="Global settings">
            <IconButton
              color="inherit"
              onClick={onOpenSettings}
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
};
