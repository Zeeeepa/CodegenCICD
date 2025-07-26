/**
 * Agent Run Dialog Component
 * Main interface for starting and monitoring agent runs
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  LinearProgress,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Divider,
} from '@mui/material';
import {
  Close as CloseIcon,
  PlayArrow as RunIcon,
  Pause as PauseIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  GitHub as GitHubIcon,
} from '@mui/icons-material';

import { useDashboard } from '../../contexts/DashboardContext';
import { useAgentRunUpdates } from '../../hooks/useWebSocket';
import ProgressTracker from './ProgressTracker';
import ResponseHandler from './ResponseHandler';

const AgentRunDialog: React.FC = () => {
  const {
    dashboardState,
    uiState,
    updateUIState,
    createAgentRun,
    resumeAgentRun,
  } = useDashboard();

  const [requirements, setRequirements] = useState('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [context, setContext] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { agentRunUpdate } = useAgentRunUpdates(dashboardState.activeAgentRun?.id);

  const isOpen = uiState.dialogOpen.agentRun;
  const selectedProject = dashboardState.selectedProject;
  const activeRun = dashboardState.activeAgentRun;

  useEffect(() => {
    if (agentRunUpdate) {
      // Handle real-time updates
      console.log('Agent run update:', agentRunUpdate);
    }
  }, [agentRunUpdate]);

  const handleClose = () => {
    updateUIState({
      dialogOpen: { ...uiState.dialogOpen, agentRun: false }
    });
    setRequirements('');
    setContext('');
  };

  const handleSubmit = async () => {
    if (!selectedProject || !requirements.trim()) return;

    setIsSubmitting(true);
    try {
      const prompt = buildPrompt();
      await createAgentRun({
        project_id: selectedProject.id,
        prompt,
        metadata: {
          priority,
          context: context.trim() || undefined,
          source: 'dashboard',
        },
      });
      
      // Keep dialog open to show progress
      setRequirements('');
      setContext('');
    } catch (error) {
      console.error('Failed to create agent run:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleContinue = async (additionalPrompt: string) => {
    if (!activeRun) return;

    setIsSubmitting(true);
    try {
      await resumeAgentRun({
        agent_run_id: activeRun.id,
        prompt: additionalPrompt,
      });
    } catch (error) {
      console.error('Failed to resume agent run:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const buildPrompt = () => {
    let prompt = `Project: ${selectedProject?.name}\n\n`;
    
    if (selectedProject?.description) {
      prompt += `Project Description: ${selectedProject.description}\n\n`;
    }
    
    prompt += `Requirements:\n${requirements}\n\n`;
    
    if (context.trim()) {
      prompt += `Additional Context:\n${context}\n\n`;
    }
    
    prompt += `Priority: ${priority.toUpperCase()}\n\n`;
    prompt += `Please analyze these requirements and implement the necessary changes to fulfill them. `;
    prompt += `Follow the project's repository rules and configuration settings.`;
    
    return prompt;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <SuccessIcon color="success" />;
      case 'FAILED':
        return <ErrorIcon color="error" />;
      case 'ACTIVE':
        return <PendingIcon color="primary" />;
      default:
        return <PendingIcon />;
    }
  };

  return (
    <Dialog
      open={isOpen}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '60vh' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h6">
              {activeRun ? 'Agent Run Progress' : 'Start Agent Run'}
            </Typography>
            {selectedProject && (
              <Typography variant="body2" color="text.secondary">
                {selectedProject.name} • {selectedProject.github_owner}/{selectedProject.github_repo}
              </Typography>
            )}
          </Box>
          <IconButton onClick={handleClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {!activeRun ? (
          // New Agent Run Form
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Alert severity="info">
              Describe your requirements and the AI agent will analyze and implement the necessary changes.
            </Alert>

            <TextField
              label="Requirements / Target Goal"
              multiline
              rows={6}
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="Describe what you want to implement, fix, or improve..."
              fullWidth
              required
            />

            <TextField
              label="Additional Context (Optional)"
              multiline
              rows={3}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Any additional context, constraints, or specific instructions..."
              fullWidth
            />

            <Box>
              <Typography variant="body2" gutterBottom>
                Priority Level
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                {(['low', 'medium', 'high', 'critical'] as const).map((level) => (
                  <Chip
                    key={level}
                    label={level.charAt(0).toUpperCase() + level.slice(1)}
                    color={priority === level ? 'primary' : 'default'}
                    onClick={() => setPriority(level)}
                    variant={priority === level ? 'filled' : 'outlined'}
                  />
                ))}
              </Box>
            </Box>
          </Box>
        ) : (
          // Active Agent Run Progress
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Status Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {getStatusIcon(activeRun.status)}
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6">
                  Status: {activeRun.status}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Started: {new Date(activeRun.created_at).toLocaleString()}
                </Typography>
              </Box>
              {activeRun.web_url && (
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => window.open(activeRun.web_url, '_blank')}
                >
                  View Details
                </Button>
              )}
            </Box>

            {/* Progress Indicator */}
            {activeRun.status === 'ACTIVE' && (
              <Box>
                <LinearProgress sx={{ mb: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Agent is working on your requirements...
                </Typography>
              </Box>
            )}

            {/* Progress Tracker */}
            <ProgressTracker agentRun={activeRun} />

            {/* Response Handler */}
            <ResponseHandler
              agentRun={activeRun}
              onContinue={handleContinue}
              isSubmitting={isSubmitting}
            />

            {/* PR Information */}
            {activeRun.pr_number && (
              <Alert severity="success" icon={<GitHubIcon />}>
                <Typography variant="body2">
                  Pull Request Created: #{activeRun.pr_number}
                </Typography>
                {activeRun.pr_url && (
                  <Button
                    size="small"
                    onClick={() => window.open(activeRun.pr_url, '_blank')}
                    sx={{ mt: 1 }}
                  >
                    View PR on GitHub
                  </Button>
                )}
              </Alert>
            )}

            {/* Result */}
            {activeRun.result && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="subtitle1">Agent Result</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {activeRun.result}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        {!activeRun ? (
          <>
            <Button onClick={handleClose}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={!requirements.trim() || isSubmitting}
              startIcon={<RunIcon />}
            >
              {isSubmitting ? 'Starting...' : 'Start Agent Run'}
            </Button>
          </>
        ) : (
          <>
            <Button onClick={handleClose}>
              Close
            </Button>
            {activeRun.status === 'ACTIVE' && (
              <Button
                variant="outlined"
                startIcon={<PauseIcon />}
                disabled
              >
                Cancel (Coming Soon)
              </Button>
            )}
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AgentRunDialog;
