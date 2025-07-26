/**
 * Connection Status Component
 * Shows WebSocket connection status
 */

import React from 'react';
import {
  Box,
  Typography,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Wifi as ConnectedIcon,
  WifiOff as DisconnectedIcon,
  Refresh as RefreshIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';

import { useDashboard } from '../../contexts/DashboardContext';

const ConnectionStatus: React.FC = () => {
  const { dashboardState, websocketState } = useDashboard();

  const getStatusConfig = () => {
    switch (websocketState.connectionState) {
      case 'connected':
        return {
          color: 'success' as const,
          icon: <ConnectedIcon />,
          label: 'Connected',
          description: 'Real-time updates active',
        };
      case 'connecting':
        return {
          color: 'warning' as const,
          icon: <RefreshIcon />,
          label: 'Connecting',
          description: 'Establishing connection...',
        };
      case 'error':
        return {
          color: 'error' as const,
          icon: <ErrorIcon />,
          label: 'Error',
          description: 'Connection failed',
        };
      case 'disconnected':
      default:
        return {
          color: 'default' as const,
          icon: <DisconnectedIcon />,
          label: 'Disconnected',
          description: 'Real-time updates unavailable',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Connection Status
      </Typography>
      
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Chip
          size="small"
          color={config.color}
          icon={config.icon}
          label={config.label}
          variant="outlined"
        />
        
        {websocketState.connectionState !== 'connected' && (
          <Tooltip title="Reconnect">
            <IconButton
              size="small"
              onClick={websocketState.reconnect}
              disabled={websocketState.connectionState === 'connecting'}
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
      
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
        {config.description}
      </Typography>
    </Box>
  );
};

export default ConnectionStatus;
