import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Paper,
  Chip,
  LinearProgress,
  Alert,
  Divider,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  CircularProgress
} from '@mui/material';
import {
  Close as CloseIcon,
  Send as SendIcon,
  PlayArrow as PlayIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  ExpandMore as ExpandMoreIcon,
  GitHub as GitHubIcon,
  Code as CodeIcon,
  Build as BuildIcon
} from '@mui/icons-material';
import { 
  Project, 
  AgentRun, 
  AgentRunStatus, 
  AgentResponseType,
  ValidationRun,
  ValidationStatus 
} from '../../types';
import { useApp } from '../../contexts/AppContext';
import { apiService } from '../../services/api';
import ProgressTracker from '../ProgressTracker/ProgressTracker';

interface AgentRunDialogProps {
  open: boolean;
  onClose: () => void;
  project: Project;
  currentRun?: AgentRun | null;
}

const AgentRunDialog: React.FC<AgentRunDialogProps> = ({
  open,
  onClose,
  project,
  currentRun: initialRun
}) => {
  const { state, createAgentRun, resumeAgentRun, addNotification } = useApp();
  const { agentRuns } = state;

  // Local state
  const [targetText, setTargetText] = useState('');
  const [currentRun, setCurrentRun] = useState<AgentRun | null>(initialRun || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationRuns, setValidationRuns] = useState<ValidationRun[]>([]);
  const [showLogs, setShowLogs] = useState(false);

  // Refs
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Get the latest agent run for this project
  const projectAgentRuns = agentRuns.filter(run => run.project_id === project.id);
  const latestRun = projectAgentRuns.sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )[0];

  // Update current run when dialog opens or latest run changes
  useEffect(() => {
    if (open) {
      setCurrentRun(initialRun || latestRun || null);
      setError(null);
      if (!initialRun && !latestRun) {
        setTargetText('');
      }
    }
  }, [open, initialRun, latestRun]);

  // Load validation runs when current run changes
  useEffect(() => {
    if (currentRun) {
      loadValidationRuns();
    }
  }, [currentRun]);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (showLogs && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [currentRun?.logs, showLogs]);

  const loadValidationRuns = async () => {
    if (!currentRun) return;
    
    try {
      const runs = await apiService.getValidationRuns(currentRun.id);
      setValidationRuns(runs);
    } catch (error) {
      console.error('Failed to load validation runs:', error);
    }
  };

  const handleStartAgentRun = async () => {
    if (!targetText.trim()) {
      setError('Please enter a target/goal for the agent run');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Create planning statement prompt
      const planningStatement = project.configuration?.planning_statement || '';
      const fullPrompt = planningStatement 
        ? `${planningStatement}\n\nUser Request: ${targetText}`
        : targetText;

      const newRun = await createAgentRun(project.id, {
        target_text: fullPrompt
      });

      setCurrentRun(newRun);
      setTargetText('');
      
      addNotification({
        type: 'info',
        title: 'Agent Run Started',
        message: `Agent run started for project "${project.name}"`,
        project_id: project.id,
        agent_run_id: newRun.id
      });

    } catch (error: any) {
      setError(error.message || 'Failed to start agent run');
    } finally {
      setLoading(false);
    }
  };

  const handleContinueAgentRun = async () => {
    if (!currentRun || !targetText.trim()) {
      setError('Please enter additional input to continue the agent run');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const updatedRun = await resumeAgentRun(currentRun.id, targetText);
      setCurrentRun(updatedRun);
      setTargetText('');

      addNotification({
        type: 'info',
        title: 'Agent Run Continued',
        message: 'Agent run has been continued with new input',
        project_id: project.id,
        agent_run_id: currentRun.id
      });

    } catch (error: any) {
      setError(error.message || 'Failed to continue agent run');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmPlan = async () => {
    if (!currentRun) return;

    try {
      setLoading(true);
      await resumeAgentRun(currentRun.id, 'Proceed with the proposed plan');
    } catch (error: any) {
      setError(error.message || 'Failed to confirm plan');
    } finally {
      setLoading(false);
    }
  };

  const handleModifyPlan = async () => {
    if (!targetText.trim()) {
      setError('Please enter modifications for the plan');
      return;
    }

    try {
      setLoading(true);
      await resumeAgentRun(currentRun.id, `Please modify the plan: ${targetText}`);
      setTargetText('');
    } catch (error: any) {
      setError(error.message || 'Failed to modify plan');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: AgentRunStatus) => {
    switch (status) {
      case AgentRunStatus.COMPLETED:
        return 'success';
      case AgentRunStatus.RUNNING:
        return 'primary';
      case AgentRunStatus.FAILED:
        return 'error';
      case AgentRunStatus.PENDING:
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: AgentRunStatus) => {
    switch (status) {
      case AgentRunStatus.COMPLETED:
        return <CheckCircleIcon />;
      case AgentRunStatus.RUNNING:
        return <CircularProgress size={24} />;
      case AgentRunStatus.FAILED:
        return <ErrorIcon />;
      default:
        return <ScheduleIcon />;
    }
  };

  const renderResponseContent = () => {
    if (!currentRun || !currentRun.response_data) return null;

    switch (currentRun.response_type) {
      case AgentResponseType.REGULAR:
        return (
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'background.paper' }}>
            <Typography variant="h6" gutterBottom>
              Agent Response
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {currentRun.response_data.content || 'No response content available'}
            </Typography>
          </Paper>
        );

      case AgentResponseType.PLAN:
        return (
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
            <Typography variant="h6" gutterBottom>
              📋 Proposed Plan
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>
              {currentRun.response_data.plan || 'No plan details available'}
            </Typography>
            <Box display="flex" gap={1}>
              <Button
                variant="contained"
                color="success"
                onClick={handleConfirmPlan}
                disabled={loading}
                startIcon={<CheckCircleIcon />}
              >
                Confirm
              </Button>
              <Button
                variant="outlined"
                onClick={() => setShowModifyInput(true)}
                disabled={loading}
                startIcon={<CodeIcon />}
              >
                Modify
              </Button>
            </Box>
          </Paper>
        );

      case AgentResponseType.PR:
        return (
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'success.light', color: 'success.contrastText' }}>
            <Typography variant="h6" gutterBottom>
              🎉 Pull Request Created
            </Typography>
            <Typography variant="body2" sx={{ mb: 2 }}>
              PR #{currentRun.response_data.pr_number} has been created successfully!
            </Typography>
            <Box display="flex" gap={1}>
              <Button
                variant="contained"
                startIcon={<GitHubIcon />}
                component="a"
                href={currentRun.response_data.pr_url}
                target="_blank"
              >
                View PR
              </Button>
              <Button
                variant="outlined"
                startIcon={<BuildIcon />}
                onClick={() => setShowValidation(true)}
              >
                View Validation
              </Button>
            </Box>
          </Paper>
        );

      default:
        return null;
    }
  };

  const [showModifyInput, setShowModifyInput] = useState(false);
  const [showValidation, setShowValidation] = useState(false);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { height: '80vh', display: 'flex', flexDirection: 'column' }
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Agent Run - {project.name}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Current Run Status */}
        {currentRun && (
          <Box mb={2}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <Chip
                icon={getStatusIcon(currentRun.status)}
                label={`Status: ${currentRun.status}`}
                color={getStatusColor(currentRun.status)}
                variant="outlined"
              />
              <Typography variant="caption" color="text.secondary">
                Started: {new Date(currentRun.created_at).toLocaleString()}
              </Typography>
            </Box>
            
            {currentRun.status === AgentRunStatus.RUNNING && (
              <LinearProgress sx={{ mb: 2 }} />
            )}
          </Box>
        )}

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Response Content */}
        {renderResponseContent()}

        {/* Validation Pipeline */}
        {showValidation && validationRuns.length > 0 && (
          <Accordion sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Validation Pipeline</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <ProgressTracker validationRuns={validationRuns} />
            </AccordionDetails>
          </Accordion>
        )}

        {/* Logs */}
        {currentRun && currentRun.logs && currentRun.logs.length > 0 && (
          <Accordion expanded={showLogs} onChange={() => setShowLogs(!showLogs)}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">
                Execution Logs ({currentRun.logs.length})
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Paper 
                sx={{ 
                  maxHeight: 300, 
                  overflow: 'auto', 
                  p: 1, 
                  bgcolor: 'grey.100',
                  fontFamily: 'monospace'
                }}
              >
                <List dense>
                  {currentRun.logs.map((log, index) => (
                    <ListItem key={index} sx={{ py: 0.5 }}>
                      <ListItemText
                        primary={
                          <Typography 
                            variant="caption" 
                            sx={{ 
                              color: log.level === 'error' ? 'error.main' : 
                                     log.level === 'warning' ? 'warning.main' : 
                                     'text.primary'
                            }}
                          >
                            [{new Date(log.timestamp).toLocaleTimeString()}] {log.message}
                          </Typography>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
                <div ref={logsEndRef} />
              </Paper>
            </AccordionDetails>
          </Accordion>
        )}

        {/* Input Section */}
        <Box mt="auto" pt={2}>
          <Divider sx={{ mb: 2 }} />
          
          {/* Modify Plan Input */}
          {showModifyInput && currentRun?.response_type === AgentResponseType.PLAN && (
            <Box mb={2}>
              <Typography variant="subtitle2" gutterBottom>
                Plan Modifications:
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={3}
                value={targetText}
                onChange={(e) => setTargetText(e.target.value)}
                placeholder="Describe how you want to modify the plan..."
                disabled={loading}
              />
              <Box display="flex" gap={1} mt={1}>
                <Button
                  variant="contained"
                  onClick={handleModifyPlan}
                  disabled={loading || !targetText.trim()}
                  startIcon={<SendIcon />}
                >
                  Send Modifications
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => {
                    setShowModifyInput(false);
                    setTargetText('');
                  }}
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          )}

          {/* Main Input */}
          {!showModifyInput && (
            <>
              <Typography variant="subtitle2" gutterBottom>
                {currentRun ? 'Continue Agent Run:' : 'Target / Goal:'}
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={4}
                value={targetText}
                onChange={(e) => setTargetText(e.target.value)}
                placeholder={
                  currentRun 
                    ? "Enter additional requirements or feedback..."
                    : "Describe what you want the agent to accomplish..."
                }
                disabled={loading}
              />
            </>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Close
        </Button>
        
        {!showModifyInput && (
          <>
            {currentRun && currentRun.status === AgentRunStatus.COMPLETED && (
              <Button
                variant="contained"
                onClick={handleContinueAgentRun}
                disabled={loading || !targetText.trim()}
                startIcon={<SendIcon />}
              >
                Continue
              </Button>
            )}
            
            {!currentRun && (
              <Button
                variant="contained"
                onClick={handleStartAgentRun}
                disabled={loading || !targetText.trim()}
                startIcon={<PlayIcon />}
              >
                Start Agent Run
              </Button>
            )}
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AgentRunDialog;
