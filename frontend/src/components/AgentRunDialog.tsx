import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  LinearProgress,
  Alert,
  Chip,
  Paper,
  Stack,
  IconButton,
  Collapse,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  GitHub as GitHubIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { ProjectData } from './EnhancedProjectCard';

interface AgentRunDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { target_text: string; planning_statement?: string }) => void;
  onContinue?: (message: string) => void;
  project: ProjectData;
  loading: boolean;
}

interface AgentRunStatus {
  id: number;
  status: string;
  run_type: string;
  response_data?: any;
  pr_number?: number;
  pr_url?: string;
  validation_status?: string;
  progress_percentage?: number;
  current_step?: string;
}

const AgentRunDialog: React.FC<AgentRunDialogProps> = ({
  open,
  onClose,
  onSubmit,
  onContinue,
  project,
  loading
}) => {
  const [targetText, setTargetText] = useState('');
  const [continueMessage, setContinueMessage] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [currentRun, setCurrentRun] = useState<AgentRunStatus | null>(null);
  const [runLogs, setRunLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);

  // Load current agent run status
  useEffect(() => {
    if (open && project.current_agent_run) {
      setCurrentRun(project.current_agent_run);
      loadRunDetails(project.current_agent_run.id);
    }
  }, [open, project.current_agent_run]);

  const loadRunDetails = async (runId: number) => {
    try {
      const response = await fetch(`/api/projects/${project.id}/agent-runs/${runId}`);
      if (response.ok) {
        const data = await response.json();
        setCurrentRun(data.agent_run);
      }
    } catch (error) {
      console.error('Failed to load run details:', error);
    }
  };

  const handleSubmit = () => {
    if (!targetText.trim()) return;
    
    onSubmit({
      target_text: targetText,
      planning_statement: project.planning_statement
    });
    
    setTargetText('');
  };

  const handleContinue = () => {
    if (!continueMessage.trim() || !onContinue) return;
    
    onContinue(continueMessage);
    setContinueMessage('');
  };

  const handleClose = () => {
    setTargetText('');
    setContinueMessage('');
    setShowAdvanced(false);
    setShowLogs(false);
    onClose();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'primary';
      case 'failed': return 'error';
      case 'cancelled': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircleIcon />;
      case 'running': return <CircularProgress size={20} />;
      case 'failed': return <ErrorIcon />;
      case 'cancelled': return <StopIcon />;
      default: return <WarningIcon />;
    }
  };

  const renderRunTypeActions = () => {
    if (!currentRun) return null;

    switch (currentRun.run_type) {
      case 'regular':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Continue Conversation
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={3}
              value={continueMessage}
              onChange={(e) => setContinueMessage(e.target.value)}
              placeholder="Add additional instructions or feedback..."
              variant="outlined"
              size="small"
            />
            <Button
              variant="contained"
              onClick={handleContinue}
              disabled={!continueMessage.trim() || loading}
              sx={{ mt: 1 }}
            >
              Continue
            </Button>
          </Box>
        );

      case 'plan':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Plan Response
            </Typography>
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                color="success"
                onClick={() => onContinue && onContinue('Proceed with the plan')}
                disabled={loading}
              >
                Confirm Plan
              </Button>
              <Button
                variant="outlined"
                onClick={() => setShowAdvanced(true)}
                disabled={loading}
              >
                Modify Plan
              </Button>
            </Stack>
            
            {showAdvanced && (
              <Box sx={{ mt: 2 }}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  value={continueMessage}
                  onChange={(e) => setContinueMessage(e.target.value)}
                  placeholder="Describe modifications to the plan..."
                  variant="outlined"
                  size="small"
                />
                <Button
                  variant="contained"
                  onClick={handleContinue}
                  disabled={!continueMessage.trim() || loading}
                  sx={{ mt: 1 }}
                >
                  Submit Modifications
                </Button>
              </Box>
            )}
          </Box>
        );

      case 'pr':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Pull Request Created
            </Typography>
            <Paper sx={{ p: 2, bgcolor: 'success.light', color: 'success.contrastText' }}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <GitHubIcon />
                <Typography variant="body2">
                  PR #{currentRun.pr_number} created successfully
                </Typography>
              </Stack>
              {currentRun.pr_url && (
                <Button
                  variant="contained"
                  size="small"
                  href={currentRun.pr_url}
                  target="_blank"
                  sx={{ mt: 1 }}
                >
                  View on GitHub
                </Button>
              )}
            </Paper>
            
            {/* Validation Status */}
            {currentRun.validation_status && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Validation Status
                </Typography>
                <Chip
                  icon={getStatusIcon(currentRun.validation_status)}
                  label={currentRun.validation_status.toUpperCase()}
                  color={getStatusColor(currentRun.validation_status) as any}
                  variant="outlined"
                />
                
                {currentRun.validation_status === 'passed' && (
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    <Button
                      variant="contained"
                      color="success"
                      size="small"
                      onClick={() => {
                        // TODO: Implement merge to main
                        console.log('Merge to main');
                      }}
                    >
                      Merge to Main
                    </Button>
                    <Button
                      variant="outlined"
                      size="small"
                      href={currentRun.pr_url}
                      target="_blank"
                    >
                      Open GitHub
                    </Button>
                  </Stack>
                )}
              </Box>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '400px' }
      }}
    >
      <DialogTitle>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">
            Agent Run - {project.name}
          </Typography>
          {currentRun && (
            <Chip
              icon={getStatusIcon(currentRun.status)}
              label={currentRun.status.toUpperCase()}
              color={getStatusColor(currentRun.status) as any}
              size="small"
            />
          )}
        </Stack>
      </DialogTitle>

      <DialogContent>
        {/* Current Run Status */}
        {currentRun && (
          <Box sx={{ mb: 3 }}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Current Run Status
              </Typography>
              
              {currentRun.progress_percentage !== undefined && (
                <Box sx={{ mb: 2 }}>
                  <LinearProgress 
                    variant="determinate" 
                    value={currentRun.progress_percentage} 
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    {currentRun.progress_percentage}% complete
                    {currentRun.current_step && ` - ${currentRun.current_step}`}
                  </Typography>
                </Box>
              )}

              {renderRunTypeActions()}
            </Paper>

            {/* Show Logs Toggle */}
            <Button
              startIcon={showLogs ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              onClick={() => setShowLogs(!showLogs)}
              size="small"
            >
              {showLogs ? 'Hide' : 'Show'} Logs
            </Button>

            <Collapse in={showLogs}>
              <Paper sx={{ p: 2, mt: 1, bgcolor: 'grey.50', maxHeight: 200, overflow: 'auto' }}>
                {runLogs.length > 0 ? (
                  runLogs.map((log, index) => (
                    <Typography key={index} variant="body2" component="pre" sx={{ mb: 0.5 }}>
                      {log}
                    </Typography>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No logs available
                  </Typography>
                )}
              </Paper>
            </Collapse>

            <Divider sx={{ my: 2 }} />
          </Box>
        )}

        {/* New Run Form */}
        <Box>
          <Typography variant="subtitle1" gutterBottom>
            Start New Agent Run
          </Typography>
          
          {/* Planning Statement Preview */}
          {project.planning_statement && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Planning Statement:</strong> {project.planning_statement}
              </Typography>
            </Alert>
          )}

          {/* Repository Rules Preview */}
          {project.repository_rules && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Repository Rules:</strong> {project.repository_rules}
              </Typography>
            </Alert>
          )}

          <TextField
            fullWidth
            multiline
            rows={4}
            value={targetText}
            onChange={(e) => setTargetText(e.target.value)}
            placeholder="Describe what you want the agent to do..."
            label="Target / Goal"
            variant="outlined"
            disabled={loading}
          />

          {/* Auto Confirm Plans Checkbox */}
          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Auto Confirm Plans: {project.auto_confirm_plans ? 'Enabled' : 'Disabled'}
            </Typography>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Close
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!targetText.trim() || loading}
          startIcon={loading ? <CircularProgress size={20} /> : <PlayIcon />}
        >
          {loading ? 'Starting...' : 'Start Agent Run'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AgentRunDialog;

