import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Grid,
  Button,
  Box,
  Alert,
  Snackbar,
  Menu,
  MenuItem,
  IconButton,
  Badge,
  CircularProgress,
  Paper,
  Stack,
} from '@mui/material';
import {
  GitHub as GitHubIcon,
  ExpandMore as ExpandMoreIcon,
  Notifications as NotificationsIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useWebSocket } from '../hooks/useWebSocket';
import { EnhancedProjectCard, ProjectData } from './EnhancedProjectCard';
import SettingsDialog from './SettingsDialog';

// API interfaces
interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  description?: string;
  html_url: string;
  owner: {
    login: string;
  };
  default_branch: string;
  is_pinned?: boolean;
}

interface WebhookNotification {
  id: string;
  type: string;
  repository: string;
  pr_number?: number;
  pr_title?: string;
  pr_url?: string;
  action?: string;
  timestamp: string;
  read: boolean;
}

const Dashboard: React.FC = () => {
  // State management
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [githubRepos, setGithubRepos] = useState<GitHubRepository[]>([]);
  const [loading, setLoading] = useState(true);
  const [reposLoading, setReposLoading] = useState(false);
  
  // UI state
  const [projectMenuAnchor, setProjectMenuAnchor] = useState<null | HTMLElement>(null);
  const [notifications, setNotifications] = useState<WebhookNotification[]>([]);
  const [notificationMenuAnchor, setNotificationMenuAnchor] = useState<null | HTMLElement>(null);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info'
  });

  const { isConnected } = useWebSocket();

  // Load data on component mount
  useEffect(() => {
    loadProjects();
    loadGithubRepos();
  }, []);

  // WebSocket message handler
  useEffect(() => {
    // TODO: Set up WebSocket listener for real-time notifications
    // This would listen for webhook events and update notifications
  }, []);

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'warning' | 'info' = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/projects');
      if (response.ok) {
        const data = await response.json();
        setProjects(data.projects || []);
      } else {
        throw new Error('Failed to load projects');
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
      showSnackbar('Failed to load projects', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadGithubRepos = async () => {
    try {
      setReposLoading(true);
      const response = await fetch('/api/projects/github-repos');
      if (response.ok) {
        const data = await response.json();
        setGithubRepos(data.repositories || []);
      } else {
        throw new Error('Failed to load GitHub repositories');
      }
    } catch (error) {
      console.error('Failed to load GitHub repos:', error);
      showSnackbar('Failed to load GitHub repositories', 'error');
    } finally {
      setReposLoading(false);
    }
  };

  const handleProjectSelect = async (repo: GitHubRepository) => {
    try {
      const projectData = {
        github_id: repo.id,
        name: repo.name,
        full_name: repo.full_name,
        description: repo.description,
        github_owner: repo.owner.login,
        github_repo: repo.name,
        github_url: repo.html_url,
        default_branch: repo.default_branch
      };

      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectData)
      });

      if (response.ok) {
        const data = await response.json();
        setProjects(prev => [...prev, data.project]);
        showSnackbar(`${repo.name} added to dashboard`, 'success');
        
        // Update the repo list to show it's pinned
        setGithubRepos(prev => prev.map(r => 
          r.id === repo.id ? { ...r, is_pinned: true } : r
        ));
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to add project');
      }
    } catch (error) {
      console.error('Failed to add project:', error);
      showSnackbar(error instanceof Error ? error.message : 'Failed to add project', 'error');
    } finally {
      setProjectMenuAnchor(null);
    }
  };

  const handleProjectUpdate = async (projectId: number, updates: Partial<ProjectData>) => {
    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        const data = await response.json();
        setProjects(prev => prev.map(p => 
          p.id === projectId ? data.project : p
        ));
        showSnackbar('Project updated successfully', 'success');
      } else {
        throw new Error('Failed to update project');
      }
    } catch (error) {
      console.error('Failed to update project:', error);
      showSnackbar('Failed to update project', 'error');
    }
  };

  const handleProjectDelete = async (projectId: number) => {
    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setProjects(prev => prev.filter(p => p.id !== projectId));
        showSnackbar('Project removed from dashboard', 'success');
        
        // Update GitHub repos list
        const project = projects.find(p => p.id === projectId);
        if (project) {
          setGithubRepos(prev => prev.map(r => 
            r.id === project.id ? { ...r, is_pinned: false } : r
          ));
        }
      } else {
        throw new Error('Failed to remove project');
      }
    } catch (error) {
      console.error('Failed to remove project:', error);
      showSnackbar('Failed to remove project', 'error');
    }
  };

  const handleAgentRun = async (projectId: number, targetText: string) => {
    try {
      const response = await fetch(`/api/projects/${projectId}/agent-runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_text: targetText })
      });

      if (response.ok) {
        const data = await response.json();
        showSnackbar('Agent run started successfully', 'success');
        
        // Update project with current agent run
        setProjects(prev => prev.map(p => 
          p.id === projectId 
            ? { ...p, current_agent_run: data.agent_run }
            : p
        ));
      } else {
        throw new Error('Failed to start agent run');
      }
    } catch (error) {
      console.error('Failed to start agent run:', error);
      showSnackbar('Failed to start agent run', 'error');
    }
  };

  const handleAgentRunContinue = async (projectId: number, runId: number, message: string) => {
    try {
      const response = await fetch(`/api/projects/${projectId}/agent-runs/${runId}/continue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });

      if (response.ok) {
        showSnackbar('Agent run continued', 'success');
        // Refresh project data to get updated run status
        loadProjects();
      } else {
        throw new Error('Failed to continue agent run');
      }
    } catch (error) {
      console.error('Failed to continue agent run:', error);
      showSnackbar('Failed to continue agent run', 'error');
    }
  };

  const handleRunSetupCommands = async (projectId: number) => {
    try {
      const response = await fetch(`/api/projects/${projectId}/setup-commands/run`, {
        method: 'POST'
      });

      if (response.ok) {
        showSnackbar('Setup commands execution started', 'success');
      } else {
        throw new Error('Failed to run setup commands');
      }
    } catch (error) {
      console.error('Failed to run setup commands:', error);
      showSnackbar('Failed to run setup commands', 'error');
    }
  };

  const unreadNotificationCount = notifications.filter(n => !n.read).length;

  const availableRepos = githubRepos.filter(repo => !repo.is_pinned);

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Header */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          {/* Project Selector */}
          <Button
            color="inherit"
            startIcon={<GitHubIcon />}
            endIcon={<ExpandMoreIcon />}
            onClick={(e) => setProjectMenuAnchor(e.currentTarget)}
            disabled={reposLoading}
          >
            {reposLoading ? 'Loading...' : 'Select Project'}
          </Button>

          <Box sx={{ flexGrow: 1 }} />

          {/* Notifications */}
          <IconButton
            color="inherit"
            onClick={(e) => setNotificationMenuAnchor(e.currentTarget)}
          >
            <Badge badgeContent={unreadNotificationCount} color="error">
              <NotificationsIcon />
            </Badge>
          </IconButton>

          {/* Settings */}
          <IconButton
            color="inherit"
            onClick={() => setSettingsDialogOpen(true)}
          >
            <SettingsIcon />
          </IconButton>

          {/* Connection Status */}
          <Box sx={{ ml: 2, display: 'flex', alignItems: 'center' }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: isConnected ? 'success.main' : 'error.main',
                mr: 1
              }}
            />
            <Typography variant="body2">
              {isConnected ? 'Connected' : 'Disconnected'}
            </Typography>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Project Selection Menu */}
      <Menu
        anchorEl={projectMenuAnchor}
        open={Boolean(projectMenuAnchor)}
        onClose={() => setProjectMenuAnchor(null)}
        PaperProps={{
          sx: { maxHeight: 400, width: 350 }
        }}
      >
        {availableRepos.length === 0 ? (
          <MenuItem disabled>
            <Typography color="text.secondary">
              {reposLoading ? 'Loading repositories...' : 'No available repositories'}
            </Typography>
          </MenuItem>
        ) : (
          availableRepos.map((repo) => (
            <MenuItem
              key={repo.id}
              onClick={() => handleProjectSelect(repo)}
            >
              <Box>
                <Typography variant="subtitle2">{repo.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {repo.full_name}
                </Typography>
                {repo.description && (
                  <Typography variant="caption" color="text.secondary">
                    {repo.description.length > 60 
                      ? `${repo.description.substring(0, 60)}...` 
                      : repo.description
                    }
                  </Typography>
                )}
              </Box>
            </MenuItem>
          ))
        )}
      </Menu>

      {/* Notifications Menu */}
      <Menu
        anchorEl={notificationMenuAnchor}
        open={Boolean(notificationMenuAnchor)}
        onClose={() => setNotificationMenuAnchor(null)}
        PaperProps={{
          sx: { maxHeight: 400, width: 400 }
        }}
      >
        {notifications.length === 0 ? (
          <MenuItem disabled>
            <Typography color="text.secondary">No notifications</Typography>
          </MenuItem>
        ) : (
          notifications.slice(0, 10).map((notification) => (
            <MenuItem key={notification.id}>
              <Box>
                <Typography variant="subtitle2">
                  {notification.type === 'pull_request' && 'PR '}
                  {notification.action} in {notification.repository}
                </Typography>
                {notification.pr_title && (
                  <Typography variant="body2" color="text.secondary">
                    #{notification.pr_number}: {notification.pr_title}
                  </Typography>
                )}
                <Typography variant="caption" color="text.secondary">
                  {new Date(notification.timestamp).toLocaleString()}
                </Typography>
              </Box>
            </MenuItem>
          ))
        )}
      </Menu>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
            <CircularProgress />
          </Box>
        ) : projects.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              No Projects Pinned
            </Typography>
            <Typography variant="body1" color="text.secondary" gutterBottom>
              Select a GitHub project from the header dropdown to add it to your dashboard.
            </Typography>
            <Button
              variant="contained"
              startIcon={<GitHubIcon />}
              onClick={(e) => setProjectMenuAnchor(e.currentTarget)}
              sx={{ mt: 2 }}
            >
              Select Project
            </Button>
          </Paper>
        ) : (
          <Grid container spacing={3}>
            {projects.map((project) => (
              <Grid item xs={12} md={6} lg={4} key={project.id}>
                <EnhancedProjectCard
                  project={project}
                  onAgentRun={handleAgentRun}
                  onAgentRunContinue={handleAgentRunContinue}
                  onUpdateProject={handleProjectUpdate}
                  onDeleteProject={handleProjectDelete}
                  onRunSetupCommands={handleRunSetupCommands}
                />
              </Grid>
            ))}
          </Grid>
        )}
      </Container>

      {/* Settings Dialog */}
      <SettingsDialog
        open={settingsDialogOpen}
        onClose={() => setSettingsDialogOpen(false)}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Dashboard;
