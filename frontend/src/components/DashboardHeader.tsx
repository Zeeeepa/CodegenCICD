/**
 * Dashboard Header Component
 */

import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Button,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Add as AddIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

interface DashboardHeaderProps {
  onSettingsClick?: () => void;
  onNotificationsClick?: () => void;
  onAddProject?: () => void;
  onRefreshAll?: () => Promise<void>;
  onOpenSettings?: () => void;
  autoRefreshEnabled?: boolean;
  onToggleAutoRefresh?: (enabled: boolean) => void;
  title?: string;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  onSettingsClick,
  onNotificationsClick,
  onAddProject,
  onRefreshAll,
  onOpenSettings,
  autoRefreshEnabled = false,
  onToggleAutoRefresh,
  title = "CodegenCICD Dashboard"
}) => {
  const handleRefresh = async () => {
    if (onRefreshAll) {
      await onRefreshAll();
    }
  };

  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          {title}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {onToggleAutoRefresh && (
            <FormControlLabel
              control={
                <Switch
                  checked={autoRefreshEnabled}
                  onChange={(e) => onToggleAutoRefresh(e.target.checked)}
                  color="default"
                />
              }
              label="Auto Refresh"
              sx={{ color: 'inherit', mr: 1 }}
            />
          )}
          
          {onAddProject && (
            <Button
              color="inherit"
              startIcon={<AddIcon />}
              onClick={onAddProject}
              variant="outlined"
              sx={{ borderColor: 'rgba(255, 255, 255, 0.5)' }}
            >
              Add Project
            </Button>
          )}
          
          {onRefreshAll && (
            <IconButton
              color="inherit"
              onClick={handleRefresh}
              aria-label="refresh all"
            >
              <RefreshIcon />
            </IconButton>
          )}
          
          {onNotificationsClick && (
            <IconButton
              color="inherit"
              onClick={onNotificationsClick}
              aria-label="notifications"
            >
              <NotificationsIcon />
            </IconButton>
          )}
          
          {(onSettingsClick || onOpenSettings) && (
            <IconButton
              color="inherit"
              onClick={onSettingsClick || onOpenSettings}
              aria-label="settings"
            >
              <SettingsIcon />
            </IconButton>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
};
