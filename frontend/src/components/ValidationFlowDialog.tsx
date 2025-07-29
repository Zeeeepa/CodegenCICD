import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  LinearProgress,
  Alert,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  PlayArrow as PlayIcon,
  Code as CodeIcon,
  Build as BuildIcon,
  TestTube as TestIcon,
  Merge as MergeIcon,
  GitHub as GitHubIcon,
  CloudQueue as CloudIcon,
} from '@mui/icons-material';

interface ValidationFlowDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: number;
  prNumber?: number;
  prUrl?: string;
}

interface ValidationStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  logs: string[];
  duration?: number;
  error?: string;
}

interface ValidationResult {
  step_id: string;
  status: 'success' | 'error' | 'running';
  message: string;
  logs: string[];
  duration: number;
}

const ValidationFlowDialog: React.FC<ValidationFlowDialogProps> = ({
  open,
  onClose,
  projectId,
  prNumber,
  prUrl
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [validationRunning, setValidationRunning] = useState(false);
  const [validationComplete, setValidationComplete] = useState(false);
  const [validationSuccess, setValidationSuccess] = useState(false);
  const [errorContext, setErrorContext] = useState<string | null>(null);

  const [steps, setSteps] = useState<ValidationStep[]>([
    {
      id: 'snapshot_creation',
      title: 'Create Grainchain Snapshot',
      description: 'Creating isolated environment with graph-sitter and web-eval-agent pre-installed',
      status: 'pending',
      logs: []
    },
    {
      id: 'codebase_cloning',
      title: 'Clone PR Codebase',
      description: 'Cloning the PR branch to the sandbox environment',
      status: 'pending',
      logs: []
    },
    {
      id: 'setup_commands',
      title: 'Run Setup Commands',
      description: 'Executing deployment and setup commands',
      status: 'pending',
      logs: []
    },
    {
      id: 'deployment_validation',
      title: 'Validate Deployment',
      description: 'Verifying deployment success using Gemini API context analysis',
      status: 'pending',
      logs: []
    },
    {
      id: 'graph_sitter_analysis',
      title: 'Graph-Sitter Analysis',
      description: 'Running static code analysis and quality checks',
      status: 'pending',
      logs: []
    },
    {
      id: 'web_eval_testing',
      title: 'Web-Eval-Agent Testing',
      description: 'Comprehensive UI testing and flow validation',
      status: 'pending',
      logs: []
    },
    {
      id: 'final_validation',
      title: 'Final Validation',
      description: 'Confirming all features are functional and ready for merge',
      status: 'pending',
      logs: []
    }
  ]);

  useEffect(() => {
    if (open && prNumber) {
      startValidation();
    }
  }, [open, prNumber]);

  const startValidation = async () => {
    setValidationRunning(true);
    setValidationComplete(false);
    setValidationSuccess(false);
    setErrorContext(null);
    setActiveStep(0);

    try {
      // Reset all steps to pending
      setSteps(prev => prev.map(step => ({ ...step, status: 'pending', logs: [] })));

      // Start validation pipeline
      const response = await fetch(`/api/projects/${projectId}/validation/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pr_number: prNumber,
          pr_url: prUrl,
          enable_comprehensive_testing: true,
          auto_merge_on_success: false // Will be handled by user decision
        })
      });

      if (response.ok) {
        const data = await response.json();
        const validationId = data.validation_id;
        
        // Start polling for validation updates
        pollValidationStatus(validationId);
      } else {
        throw new Error('Failed to start validation');
      }
    } catch (error) {
      console.error('Validation start failed:', error);
      setErrorContext(error instanceof Error ? error.message : 'Unknown error');
      setValidationRunning(false);
    }
  };

  const pollValidationStatus = async (validationId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/validation/${validationId}/status`);
        if (response.ok) {
          const data = await response.json();
          
          // Update steps based on validation results
          updateStepsFromResults(data.results);
          
          // Check if validation is complete
          if (data.status === 'completed') {
            clearInterval(pollInterval);
            setValidationRunning(false);
            setValidationComplete(true);
            setValidationSuccess(data.success);
            
            if (!data.success && data.error_context) {
              setErrorContext(data.error_context);
              // Automatically send error context to agent for resolution
              await sendErrorContextToAgent(data.error_context);
            }
          } else if (data.status === 'failed') {
            clearInterval(pollInterval);
            setValidationRunning(false);
            setValidationComplete(true);
            setValidationSuccess(false);
            setErrorContext(data.error_message);
          }
        }
      } catch (error) {
        console.error('Failed to poll validation status:', error);
        clearInterval(pollInterval);
        setValidationRunning(false);
      }
    }, 2000); // Poll every 2 seconds
  };

  const updateStepsFromResults = (results: ValidationResult[]) => {
    setSteps(prev => prev.map(step => {
      const result = results.find(r => r.step_id === step.id);
      if (result) {
        return {
          ...step,
          status: result.status === 'success' ? 'completed' : 
                 result.status === 'error' ? 'failed' : 'running',
          logs: result.logs,
          duration: result.duration,
          error: result.status === 'error' ? result.message : undefined
        };
      }
      return step;
    }));

    // Update active step
    const runningStepIndex = results.findIndex(r => r.status === 'running');
    if (runningStepIndex >= 0) {
      setActiveStep(runningStepIndex);
    } else {
      const completedSteps = results.filter(r => r.status === 'success').length;
      setActiveStep(Math.min(completedSteps, steps.length - 1));
    }
  };

  const sendErrorContextToAgent = async (errorContext: string) => {
    try {
      const response = await fetch(`/api/projects/${projectId}/agent-runs/continue-with-error`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pr_number: prNumber,
          error_context: errorContext,
          message: `Please update the PR to resolve the following validation errors:\n\n${errorContext}`
        })
      });

      if (response.ok) {
        console.log('Error context sent to agent for resolution');
      }
    } catch (error) {
      console.error('Failed to send error context to agent:', error);
    }
  };

  const handleMergeToMain = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/merge-pr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pr_number: prNumber,
          merge_method: 'squash' // or 'merge', 'rebase'
        })
      });

      if (response.ok) {
        onClose();
        // Show success notification
      } else {
        throw new Error('Failed to merge PR');
      }
    } catch (error) {
      console.error('Failed to merge PR:', error);
    }
  };

  const getStepIcon = (step: ValidationStep) => {
    switch (step.status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'running':
        return <CircularProgress size={24} />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  const getStepColor = (step: ValidationStep) => {
    switch (step.status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'primary';
      default:
        return 'grey';
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{ sx: { height: '90vh' } }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Validation Flow - PR #{prNumber}
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            {validationRunning && <CircularProgress size={20} />}
            <Chip
              label={validationRunning ? 'Running' : validationComplete ? 
                (validationSuccess ? 'Success' : 'Failed') : 'Ready'}
              color={validationRunning ? 'primary' : validationComplete ? 
                (validationSuccess ? 'success' : 'error') : 'default'}
            />
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Alert severity="info">
            <Typography variant="body2">
              This validation flow will create a Grainchain snapshot with graph-sitter and web-eval-agent,
              clone the PR codebase, run setup commands, and perform comprehensive testing.
            </Typography>
          </Alert>
        </Box>

        <Stepper activeStep={activeStep} orientation="vertical">
          {steps.map((step, index) => (
            <Step key={step.id}>
              <StepLabel
                StepIconComponent={() => getStepIcon(step)}
                sx={{
                  '& .MuiStepLabel-label': {
                    color: `${getStepColor(step)}.main`
                  }
                }}
              >
                <Typography variant="subtitle1">{step.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {step.description}
                </Typography>
                {step.duration && (
                  <Typography variant="caption" color="text.secondary">
                    Duration: {step.duration}ms
                  </Typography>
                )}
              </StepLabel>
              <StepContent>
                {step.logs.length > 0 && (
                  <Paper sx={{ p: 2, mt: 1, maxHeight: 200, overflow: 'auto' }}>
                    <Typography variant="subtitle2" gutterBottom>Logs:</Typography>
                    {step.logs.map((log, logIndex) => (
                      <Typography
                        key={logIndex}
                        variant="body2"
                        component="pre"
                        sx={{ fontFamily: 'monospace', fontSize: '0.75rem', mb: 0.5 }}
                      >
                        {log}
                      </Typography>
                    ))}
                  </Paper>
                )}
                {step.error && (
                  <Alert severity="error" sx={{ mt: 1 }}>
                    {step.error}
                  </Alert>
                )}
              </StepContent>
            </Step>
          ))}
        </Stepper>

        {errorContext && (
          <Box sx={{ mt: 2 }}>
            <Alert severity="error">
              <Typography variant="subtitle2" gutterBottom>
                Validation Failed - Error Context Sent to Agent
              </Typography>
              <Typography variant="body2" component="pre" sx={{ fontFamily: 'monospace' }}>
                {errorContext}
              </Typography>
            </Alert>
          </Box>
        )}

        {validationComplete && validationSuccess && (
          <Box sx={{ mt: 2 }}>
            <Alert severity="success">
              <Typography variant="subtitle2" gutterBottom>
                🎉 Validation Successful!
              </Typography>
              <Typography variant="body2">
                All tests passed. The PR is ready to be merged to the main branch.
              </Typography>
            </Alert>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        
        {prUrl && (
          <Button
            startIcon={<GitHubIcon />}
            onClick={() => window.open(prUrl, '_blank')}
            variant="outlined"
          >
            Open GitHub
          </Button>
        )}

        {!validationRunning && !validationComplete && (
          <Button
            startIcon={<PlayIcon />}
            onClick={startValidation}
            variant="contained"
            color="primary"
          >
            Start Validation
          </Button>
        )}

        {validationComplete && validationSuccess && (
          <Button
            startIcon={<MergeIcon />}
            onClick={handleMergeToMain}
            variant="contained"
            color="success"
          >
            Merge to Main
          </Button>
        )}

        {validationComplete && !validationSuccess && (
          <Button
            startIcon={<PlayIcon />}
            onClick={startValidation}
            variant="contained"
            color="primary"
          >
            Retry Validation
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ValidationFlowDialog;
