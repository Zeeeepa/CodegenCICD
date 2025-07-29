import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Grid,
  Tooltip,
  IconButton,
  Collapse,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface ServiceStatus {
  status: 'success' | 'error' | 'loading';
  message: string;
  response_time: number;
  details: any;
  timestamp?: number;
}

interface ServiceValidatorProps {
  serviceName: string;
  displayName: string;
  icon: React.ReactNode;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const ServiceValidator: React.FC<ServiceValidatorProps> = ({
  serviceName,
  displayName,
  icon,
  autoRefresh = false,
  refreshInterval = 30000,
}) => {
  const [status, setStatus] = useState<ServiceStatus>({
    status: 'loading',
    message: 'Checking service...',
    response_time: 0,
    details: {}
  });
  const [expanded, setExpanded] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const validateService = async () => {
    setStatus(prev => ({ ...prev, status: 'loading' }));
    
    try {
      const response = await axios.get(`/api/validation/services/${serviceName}`);
      setStatus(response.data);
      setLastRefresh(new Date());
    } catch (error: any) {
      setStatus({
        status: 'error',
        message: error.response?.data?.detail || `Failed to validate ${displayName}`,
        response_time: 0,
        details: { error: error.message }
      });
      setLastRefresh(new Date());
    }
  };

  useEffect(() => {
    validateService();
  }, [serviceName]);

  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(validateService, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  const getStatusColor = () => {
    switch (status.status) {
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      case 'loading':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = () => {
    switch (status.status) {
      case 'success':
        return <CheckCircleIcon color="success" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'loading':
        return <CircularProgress size={24} />;
      default:
        return null;
    }
  };

  const formatResponseTime = (time: number) => {
    if (time < 1000) {
      return `${time}ms`;
    }
    return `${(time / 1000).toFixed(2)}s`;
  };

  const formatLastRefresh = () => {
    if (!lastRefresh) return 'Never';
    const now = new Date();
    const diff = now.getTime() - lastRefresh.getTime();
    const seconds = Math.floor(diff / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  return (
    <Card 
      sx={{ 
        height: '100%',
        transition: 'all 0.3s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 4,
        }
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            {icon}
            <Typography variant="h6" component="div">
              {displayName}
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            {getStatusIcon()}
            <Tooltip title="Refresh">
              <IconButton 
                size="small" 
                onClick={validateService}
                disabled={status.status === 'loading'}
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <Box mb={2}>
          <Chip
            label={status.status === 'loading' ? 'Checking...' : status.message}
            color={getStatusColor() as any}
            size="small"
            sx={{ mb: 1, width: '100%' }}
          />
        </Box>

        <Grid container spacing={1} mb={2}>
          {status.response_time > 0 && (
            <Grid item xs={6}>
              <Box display="flex" alignItems="center" gap={0.5}>
                <SpeedIcon fontSize="small" color="action" />
                <Typography variant="body2" color="text.secondary">
                  {formatResponseTime(status.response_time)}
                </Typography>
              </Box>
            </Grid>
          )}
          <Grid item xs={6}>
            <Typography variant="body2" color="text.secondary">
              {formatLastRefresh()}
            </Typography>
          </Grid>
        </Grid>

        {Object.keys(status.details).length > 0 && (
          <>
            <Button
              size="small"
              onClick={() => setExpanded(!expanded)}
              endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              sx={{ mb: 1 }}
            >
              Details
            </Button>
            
            <Collapse in={expanded}>
              <Box sx={{ mt: 1 }}>
                {status.status === 'error' && status.details.error && (
                  <Alert severity="error" sx={{ mb: 1, fontSize: '0.75rem' }}>
                    {status.details.error}
                  </Alert>
                )}
                
                <Box 
                  sx={{ 
                    backgroundColor: 'background.paper',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    p: 1,
                    maxHeight: 200,
                    overflow: 'auto'
                  }}
                >
                  <pre style={{ 
                    margin: 0, 
                    fontSize: '0.75rem', 
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}>
                    {JSON.stringify(status.details, null, 2)}
                  </pre>
                </Box>
              </Box>
            </Collapse>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default ServiceValidator;
