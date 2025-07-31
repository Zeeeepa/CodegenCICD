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
  Switch,
  FormControlLabel,
  Box,
  Tooltip,
  Badge
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  GitHub as GitHubIcon
} from '@mui/icons-material';

interface DashboardHeaderProps {
  onAddProject: () => void;
  onRefreshAll: () => void;
  onOpenSettings: () => void;
  autoRefreshEnabled: boolean;
  onToggleAutoRefresh: (enabled: boolean) => void;
  notificationCount?: number;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  onAddProject,
  onRefreshAll,
  onOpenSettings,
  autoRefreshEnabled,
  onToggleAutoRefresh,
  notificationCount = 0
}) => {
  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        {/* Logo and Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
          <GitHubIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div">
            CICD Dashboard
          </Typography>
        </Box>

        {/* Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* Auto Refresh Toggle */}
          <FormControlLabel
            control={
              <Switch
                checked={autoRefreshEnabled}
                onChange={(e) => onToggleAutoRefresh(e.target.checked)}
                size="small"
              />
            }
            label="Auto Refresh"
            sx={{ 
              color: 'inherit',
              '& .MuiFormControlLabel-label': {
                fontSize: '0.875rem'
              }
            }}
          />

          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton color="inherit">
              <Badge badgeContent={notificationCount} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* Refresh All */}
          <Tooltip title="Refresh All Projects">
            <IconButton color="inherit" onClick={onRefreshAll}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>

          {/* Settings */}
          <Tooltip title="Global Settings">
            <IconButton color="inherit" onClick={onOpenSettings}>
              <SettingsIcon />
            </IconButton>
          </Tooltip>

          {/* Add Project */}
          <Button
            variant="contained"
            color="secondary"
            startIcon={<AddIcon />}
            onClick={onAddProject}
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.1)',
              '&:hover': {
                bgcolor: 'rgba(255, 255, 255, 0.2)',
              }
            }}
          >
            Add Project
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

