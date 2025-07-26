/**
 * Status Indicator Component
 * Shows status with appropriate colors and icons
 */

import React from 'react';
import { Chip, ChipProps } from '@mui/material';
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  Cancel as CancelledIcon,
  PlayArrow as ActiveIcon,
} from '@mui/icons-material';

interface StatusIndicatorProps {
  status: string;
  size?: ChipProps['size'];
  variant?: ChipProps['variant'];
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  size = 'medium',
  variant = 'filled',
}) => {
  const getStatusConfig = (status: string) => {
    const normalizedStatus = status.toLowerCase();
    
    switch (normalizedStatus) {
      case 'completed':
      case 'success':
      case 'active':
        return {
          color: 'success' as const,
          icon: <SuccessIcon />,
          label: 'Completed',
        };
      case 'active':
      case 'running':
        return {
          color: 'primary' as const,
          icon: <ActiveIcon />,
          label: 'Active',
        };
      case 'failed':
      case 'error':
        return {
          color: 'error' as const,
          icon: <ErrorIcon />,
          label: 'Failed',
        };
      case 'cancelled':
      case 'canceled':
        return {
          color: 'default' as const,
          icon: <CancelledIcon />,
          label: 'Cancelled',
        };
      case 'pending':
      case 'waiting':
        return {
          color: 'warning' as const,
          icon: <PendingIcon />,
          label: 'Pending',
        };
      default:
        return {
          color: 'default' as const,
          icon: <PendingIcon />,
          label: status,
        };
    }
  };

  const config = getStatusConfig(status);

  return (
    <Chip
      size={size}
      variant={variant}
      color={config.color}
      icon={config.icon}
      label={config.label}
    />
  );
};

export default StatusIndicator;
