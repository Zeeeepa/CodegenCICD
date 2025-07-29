import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  Box,
  Chip,
  Alert,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  GitHub as GitHubIcon,
  Code as CodeIcon,
} from '@mui/icons-material';
import { Project, AgentRun, agentRunsApi, configurationsApi } from '../services/api';
import { useAgentRunUpdates, useValidationUpdates } from '../hooks/useWebSocket';

interface AgentRunDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { target_text: string; planning_statement?: string }) => void;
  project: Project;
  loading: boolean;
}

const AgentRunDialog: React.FC<AgentRunDialogProps> = ({
  open,
  onClose,
  onSubmit,
  project,
  loading,
}) => {
  const [targetText, setTargetText] = useState('');
  const [planningStatement, setPlanningStatement] = useState('');
  const [currentRun, setCurrentRun] = useState<AgentRun | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // WebSocket updates
  const agentRunUpdates = useAgentRunUpdates(project.id);
  const validationUpdates = useValidationUpdates(currentRun?.id);

  // Load default planning statement
  useEffect(() => {
    if (open) {
      loadPlanningStatement();
    }
  }, [open, project.id]);

  // Update current run from WebSocket
  useEffect(() => {
    if (currentRun && agentRunUpdates.length > 0) {
      const update = agentRunUpdates.find(run => run.id === currentRun.id);
      if (update) {
        setCurrentRun(prev => prev ? { ...prev, ...update } : null);
      }
    }
  }, [agentRunUpdates, currentRun]);

  const loadPlanningStatement = async () => {
    try {
      const response = await configurationsApi.getByProject(project.id);
      if (response.data.planning_statement) {
        setPlanningStatement(response.data.planning_statement);
      }
    } catch (error) {
      // Planning statement is optional, so we don't show an error
      console.log('No planning statement found for project');
    }
  };

  const handleSubmit = () => {
    if (!targetText.trim()) {
      setError('Target text is required');
      return;
    }

    setError(null);
    onSubmit({
      target_text: targetText.trim(),
      planning_statement: planningStatement.trim() || undefined,
    });
  };

  const handleContinue = async (message: string) => {
    if (!currentRun) return;

    try {
      await agentRunsApi.continue(currentRun.id, { message });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to continue agent run');
    }
  };

  const handleCancel = async () => {
    if (!currentRun) return;

    try {
      await agentRunsApi.cancel(currentRun.id);
      setCurrentRun(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to cancel agent run');
    }
  };

  const handleClose = () => {
    setTargetText('');
    setPlanningStatement('');
    setCurrentRun(null);
    setError(null);
    setShowAdvanced(false);
    onClose();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'running':
        return <PendingIcon color="warning" />;
      default:
        return <PendingIcon />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'warning';
      default:
        return 'default';
    }
  };

  const renderRunTypeResponse = () => {
    if (!currentRun || !currentRun.result) return null;

    switch (currentRun.run_type) {
      case 'regular':
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Agent Response
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              {currentRun.result}
            </Alert>
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Continue with additional instructions"
              placeholder="Add more details or modifications..."
              sx={{ mb: 2 }}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleContinue((e.target as HTMLInputElement).value);
                  (e.target as HTMLInputElement).value = '';
                }
              }}
            />
            <Button
              variant="contained"
              onClick={() => {
                const input = document.querySelector('textarea[placeholder*="Add more details"]') as HTMLTextAreaElement;
                if (input?.value.trim()) {
                  handleContinue(input.value.trim());
                  input.value = '';
                }
              }}
            >
              Continue
            </Button>
          </Box>
        );

      case 'plan':
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Proposed Plan
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              {currentRun.result}
            </Alert>
            <Box display="flex" gap={2}>
              <Button
                variant="contained"
                color="success"
                onClick={() => handleContinue('Proceed')}
              >
                Confirm Plan
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  const modification = prompt('Enter plan modifications:');
                  if (modification) {
                    handleContinue(modification);
                  }
                }}
              >
                Modify Plan
              </Button>
            </Box>
          </Box>
        );

      case 'pr':
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Pull Request Created
            </Typography>
            <Alert severity="success" sx={{ mb: 2 }}>
              PR #{currentRun.pr_number} has been created successfully!
            </Alert>
            <Box display="flex" alignItems="center" gap={2} mb={2}>
              <Chip
                icon={<GitHubIcon />}
                label={`PR #${currentRun.pr_number}`}
                color="primary"
                clickable
                onClick={() => window.open(currentRun.pr_url, '_blank')}
              />
              {validationUpdates && (
                <Chip
                  label={`Validation: ${validationUpdates.status}`}
                  color={validationUpdates.status === 'completed' ? 'success' : 'warning'}
                />
              )}
            </Box>
            
            {/* Validation Progress */}
            {validationUpdates && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography>Validation Pipeline Progress</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    {validationUpdates.steps?.map((step: any, index: number) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          {getStatusIcon(step.status)}
                        </ListItemIcon>
                        <ListItemText
                          primary={step.name}
                          secondary={step.description}
                        />
                      </ListItem>
                    ))}
                  </List>
                </AccordionDetails>
              </Accordion>
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
        sx: { minHeight: '500px' }
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">
            Agent Run - {project.name}
          </Typography>
          {currentRun && (
            <Chip
              icon={getStatusIcon(currentRun.status)}
              label={currentRun.status}
              color={getStatusColor(currentRun.status) as any}
            />
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {!currentRun ? (
          // Initial form
          <Box>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Target / Goal"
              placeholder="Describe what you want the AI agent to accomplish..."
              value={targetText}
              onChange={(e) => setTargetText(e.target.value)}
              sx={{ mb: 2 }}
              required
            />

            <Accordion expanded={showAdvanced} onChange={() => setShowAdvanced(!showAdvanced)}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Advanced Settings</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <TextField
                  fullWidth
                  multiline
                  rows={6}
                  label="Planning Statement"
                  placeholder="Custom instructions for the AI agent..."
                  value={planningStatement}
                  onChange={(e) => setPlanningStatement(e.target.value)}
                  helperText="This will be prepended to your target text as context for the agent"
                />
              </AccordionDetails>
            </Accordion>

            <Box mt={2}>
              <Typography variant="body2" color="text.secondary">
                Project Settings:
              </Typography>
              <Box display="flex" gap={1} mt={1}>
                {project.auto_confirm_plans && (
                  <Chip label="Auto-confirm Plans" size="small" color="primary" />
                )}
                {project.auto_merge_enabled && (
                  <Chip label="Auto-merge PRs" size="small" color="secondary" />
                )}
              </Box>
            </Box>
          </Box>
        ) : (
          // Show current run progress and results
          <Box>
            <Box mb={2}>
              <Typography variant="subtitle1" gutterBottom>
                Target: {currentRun.target_text}
              </Typography>
              <Divider />
            </Box>

            {currentRun.status === 'running' && (
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Agent is working...
                </Typography>
                <LinearProgress />
              </Box>
            )}

            {currentRun.error_message && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {currentRun.error_message}
              </Alert>
            )}

            {renderRunTypeResponse()}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        {!currentRun ? (
          <>
            <Button onClick={handleClose}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={loading || !targetText.trim()}
              startIcon={<PlayIcon />}
            >
              Start Agent Run
            </Button>
          </>
        ) : (
          <>
            {currentRun.status === 'running' && (
              <Button
                onClick={handleCancel}
                color="error"
                startIcon={<StopIcon />}
              >
                Cancel Run
              </Button>
            )}
            <Button onClick={handleClose}>Close</Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AgentRunDialog;

