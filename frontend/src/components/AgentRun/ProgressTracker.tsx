/**
 * Progress Tracker Component
 * Shows real-time progress of agent runs
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  PlayArrow as ActiveIcon,
  Code as CodeIcon,
  Build as BuildIcon,
  Search as SearchIcon,
} from '@mui/icons-material';

import { AgentRun, AgentRunLog } from '../../types/api';
import apiService from '../../services/apiService';

interface ProgressTrackerProps {
  agentRun: AgentRun;
}

const ProgressTracker: React.FC<ProgressTrackerProps> = ({ agentRun }) => {
  const [logs, setLogs] = useState<AgentRunLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (expanded && agentRun.id) {
      fetchLogs();
    }
  }, [expanded, agentRun.id]);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.getAgentRunLogs(agentRun.id);
      setLogs(response.logs || []);
    } catch (error) {
      console.error('Failed to fetch agent run logs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStepIcon = (messageType: string, toolName?: string) => {
    switch (messageType) {
      case 'ACTION':
        if (toolName?.includes('search')) return <SearchIcon />;
        if (toolName?.includes('build') || toolName?.includes('run')) return <BuildIcon />;
        return <CodeIcon />;
      case 'PLAN_EVALUATION':
        return <PendingIcon />;
      case 'FINAL_ANSWER':
        return <SuccessIcon />;
      case 'ERROR':
        return <ErrorIcon />;
      default:
        return <ActiveIcon />;
    }
  };

  const getStepColor = (messageType: string) => {
    switch (messageType) {
      case 'FINAL_ANSWER':
        return 'success';
      case 'ERROR':
        return 'error';
      case 'ACTION':
        return 'primary';
      default:
        return 'default';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getStepTitle = (log: AgentRunLog) => {
    if (log.tool_name) {
      return `${log.tool_name} - ${log.message_type}`;
    }
    return log.message_type;
  };

  const getStepDescription = (log: AgentRunLog) => {
    if (log.thought) {
      return log.thought;
    }
    if (log.observation && typeof log.observation === 'string') {
      return log.observation;
    }
    return 'Processing...';
  };

  return (
    <Accordion expanded={expanded} onChange={() => setExpanded(!expanded)}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
          <Typography variant="subtitle1">
            Execution Progress
          </Typography>
          {agentRun.status === 'ACTIVE' && (
            <CircularProgress size={16} />
          )}
          <Box sx={{ flexGrow: 1 }} />
          <Chip
            size="small"
            label={`${logs.length} steps`}
            color="primary"
            variant="outlined"
          />
        </Box>
      </AccordionSummary>
      
      <AccordionDetails>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress />
          </Box>
        ) : logs.length > 0 ? (
          <List dense>
            {logs.map((log, index) => (
              <ListItem key={index} sx={{ pl: 0 }}>
                <ListItemIcon sx={{ minWidth: 40 }}>
                  {getStepIcon(log.message_type, log.tool_name)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {getStepTitle(log)}
                      </Typography>
                      <Chip
                        size="small"
                        label={log.message_type}
                        color={getStepColor(log.message_type) as any}
                        variant="outlined"
                      />
                      <Typography variant="caption" color="text.secondary">
                        {formatTimestamp(log.created_at)}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        mt: 0.5,
                        maxWidth: '100%',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                      }}
                    >
                      {getStepDescription(log)}
                    </Typography>
                  }
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
            No execution logs available yet
          </Typography>
        )}
      </AccordionDetails>
    </Accordion>
  );
};

export default ProgressTracker;
