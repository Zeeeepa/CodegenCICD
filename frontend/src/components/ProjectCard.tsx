// Project card component with agent run functionality
import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Alert,
  LinearProgress,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  PlayArrow as PlayIcon,
  GitHub as GitHubIcon,
  AutoMode as AutoIcon,
  Code as CodeIcon,
} from '@mui/icons-material';
import { Project, AgentRun } from '../types';
import { agentRunsApi } from '../services/api';
import { ConfigurationDialog } from './ConfigurationDialog';

interface ProjectCardProps {
  project: Project;
  onUpdate: (project: Project) => void;
  onDelete: (projectId: string) => void;
  latestAgentRun?: AgentRun;
  onAgentRunUpdate: (agentRun: AgentRun) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onUpdate,
  onDelete,
  latestAgentRun,
  onAgentRunUpdate,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [agentRunDialogOpen, setAgentRunDialogOpen] = useState(false);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [agentRunPrompt, setAgentRunPrompt] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleAgentRunSubmit = async () => {
    if (!agentRunPrompt.trim()) return;

    setIsRunning(true);
    setError(null);

    try {
      const agentRun = await agentRunsApi.create({
        project_id: project.id,
        prompt: agentRunPrompt,
        use_planning_statement: true,
      });

      onAgentRunUpdate(agentRun);
      setAgentRunDialogOpen(false);
      setAgentRunPrompt('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create agent run');
    } finally {
      setIsRunning(false);
    }
  };

  const handleContinueAgentRun = async () => {
    if (!latestAgentRun || !agentRunPrompt.trim()) return;

    setIsRunning(true);
    setError(null);

    try {
      const agentRun = await agentRunsApi.continue(latestAgentRun.id, agentRunPrompt);
      onAgentRunUpdate(agentRun);
      setAgentRunDialogOpen(false);
      setAgentRunPrompt('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to continue agent run');
    } finally {
      setIsRunning(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getResponseTypeIcon = (responseType?: string) => {
    switch (responseType) {
      case 'pr':
        return <GitHubIcon fontSize="small" />;
      case 'plan':
        return <CodeIcon fontSize="small" />;
      default:
        return null;
    }
  };

  return (
    <>
      <Card sx={{ minWidth: 350, maxWidth: 400, m: 1 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              {project.name}
            </Typography>
            <IconButton size="small" onClick={handleMenuOpen}>
              <SettingsIcon />
            </IconButton>
          </Box>

          {project.description && (
            <Typography variant="body2" color="text.secondary" mb={2}>
              {project.description}
            </Typography>
          )}

          <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
            <Chip
              label={project.default_branch}
              size="small"
              variant="outlined"
            />
            {project.auto_merge_enabled && (
              <Chip
                icon={<AutoIcon />}
                label="Auto-merge"
                size="small"
                color="primary"
              />
            )}
          </Box>

          {latestAgentRun && (
            <Box mt={2}>
              <Typography variant="subtitle2" gutterBottom>
                Latest Agent Run
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Chip
                  label={latestAgentRun.status}
                  size="small"
                  color={getStatusColor(latestAgentRun.status) as any}
                />
                {latestAgentRun.response_type && (
                  <Chip
                    icon={getResponseTypeIcon(latestAgentRun.response_type)}
                    label={latestAgentRun.response_type}
                    size="small"
                    variant="outlined"
                  />
                )}
              </Box>
              
              {latestAgentRun.status === 'running' && (
                <LinearProgress sx={{ mt: 1 }} />
              )}

              {latestAgentRun.pr_url && (
                <Button
                  size="small"
                  startIcon={<GitHubIcon />}
                  href={latestAgentRun.pr_url}
                  target="_blank"
                  sx={{ mt: 1 }}
                >
                  View PR
                </Button>
              )}
            </Box>
          )}
        </CardContent>

        <CardActions>
          <Button
            startIcon={<PlayIcon />}
            onClick={() => setAgentRunDialogOpen(true)}
            disabled={isRunning}
          >
            Agent Run
          </Button>
          <Button
            size="small"
            href={project.repository_url}
            target="_blank"
            startIcon={<GitHubIcon />}
          >
            Repository
          </Button>
        </CardActions>
      </Card>

      {/* Settings Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => { setConfigDialogOpen(true); handleMenuClose(); }}>
          Configuration
        </MenuItem>
        <MenuItem onClick={() => { onDelete(project.id); handleMenuClose(); }}>
          Delete Project
        </MenuItem>
      </Menu>

      {/* Agent Run Dialog */}
      <Dialog
        open={agentRunDialogOpen}
        onClose={() => setAgentRunDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {latestAgentRun?.status === 'completed' ? 'Continue Agent Run' : 'New Agent Run'}
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          <TextField
            autoFocus
            margin="dense"
            label="Target / Goal"
            fullWidth
            multiline
            rows={4}
            variant="outlined"
            value={agentRunPrompt}
            onChange={(e) => setAgentRunPrompt(e.target.value)}
            placeholder="Describe what you want the agent to do..."
            disabled={isRunning}
          />
          
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            The planning statement from project configuration will be automatically prepended.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAgentRunDialogOpen(false)} disabled={isRunning}>
            Cancel
          </Button>
          <Button
            onClick={latestAgentRun?.status === 'completed' ? handleContinueAgentRun : handleAgentRunSubmit}
            variant="contained"
            disabled={!agentRunPrompt.trim() || isRunning}
          >
            {isRunning ? 'Starting...' : 'Confirm'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Configuration Dialog */}
      <ConfigurationDialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        project={project}
        onUpdate={onUpdate}
      />
    </>
  );
};

