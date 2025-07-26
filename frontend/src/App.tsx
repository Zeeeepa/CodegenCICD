// Main App component for CodegenCICD Dashboard
import React, { useState, useEffect } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Grid,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { ProjectCard } from './components/ProjectCard';
import { Project, AgentRun, WebSocketMessage } from './types';
import { projectsApi, agentRunsApi } from './services/api';
import { useWebSocket } from './hooks/useWebSocket';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [agentRuns, setAgentRuns] = useState<Record<string, AgentRun>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Create project dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    repository_url: '',
    default_branch: 'main',
    auto_merge_enabled: false,
  });

  // WebSocket connection
  const clientId = `dashboard_${Date.now()}`;
  const { isConnected, lastMessage, subscribe, unsubscribe } = useWebSocket(clientId, {
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      console.log('WebSocket connected');
      // Subscribe to all project updates
      projects.forEach(project => {
        subscribe(`project_${project.id}`);
      });
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected');
    },
  });

  function handleWebSocketMessage(message: WebSocketMessage) {
    console.log('WebSocket message:', message);
    
    switch (message.type) {
      case 'agent_run_status':
      case 'agent_run_completed':
      case 'agent_run_failed':
        if (message.agent_run_id) {
          // Refresh the specific agent run
          refreshAgentRun(message.agent_run_id);
        }
        break;
      
      case 'pr_webhook':
        if (message.project_id) {
          setSuccess(`PR ${message.action} detected for project: ${message.pr_url}`);
        }
        break;
      
      default:
        console.log('Unhandled message type:', message.type);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (projects.length > 0) {
      loadLatestAgentRuns();
      
      // Subscribe to project updates via WebSocket
      projects.forEach(project => {
        subscribe(`project_${project.id}`);
      });
    }
  }, [projects, subscribe]);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const projectList = await projectsApi.list(0, 50);
      setProjects(projectList);
      
      if (projectList.length > 0 && !selectedProject) {
        setSelectedProject(projectList[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const loadLatestAgentRuns = async () => {
    try {
      const allRuns = await agentRunsApi.list(undefined, 0, 100);
      
      // Group by project and keep only the latest run per project
      const latestRuns: Record<string, AgentRun> = {};
      allRuns.forEach(run => {
        if (!latestRuns[run.project_id] || 
            new Date(run.created_at) > new Date(latestRuns[run.project_id].created_at)) {
          latestRuns[run.project_id] = run;
        }
      });
      
      setAgentRuns(latestRuns);
    } catch (err: any) {
      console.error('Failed to load agent runs:', err);
    }
  };

  const refreshAgentRun = async (agentRunId: string) => {
    try {
      const agentRun = await agentRunsApi.get(agentRunId);
      setAgentRuns(prev => ({
        ...prev,
        [agentRun.project_id]: agentRun,
      }));
    } catch (err: any) {
      console.error('Failed to refresh agent run:', err);
    }
  };

  const handleCreateProject = async () => {
    if (!newProject.name.trim() || !newProject.repository_url.trim()) {
      setError('Name and repository URL are required');
      return;
    }

    try {
      const project = await projectsApi.create(newProject);
      setProjects(prev => [...prev, project]);
      setCreateDialogOpen(false);
      setNewProject({
        name: '',
        description: '',
        repository_url: '',
        default_branch: 'main',
        auto_merge_enabled: false,
      });
      setSuccess('Project created successfully');
      
      // Subscribe to new project updates
      subscribe(`project_${project.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project');
    }
  };

  const handleUpdateProject = (updatedProject: Project) => {
    setProjects(prev => prev.map(p => p.id === updatedProject.id ? updatedProject : p));
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!window.confirm('Are you sure you want to delete this project?')) {
      return;
    }

    try {
      await projectsApi.delete(projectId);
      setProjects(prev => prev.filter(p => p.id !== projectId));
      setAgentRuns(prev => {
        const { [projectId]: removed, ...rest } = prev;
        return rest;
      });
      
      // Unsubscribe from project updates
      unsubscribe(`project_${projectId}`);
      
      setSuccess('Project deleted successfully');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete project');
    }
  };

  const handleAgentRunUpdate = (agentRun: AgentRun) => {
    setAgentRuns(prev => ({
      ...prev,
      [agentRun.project_id]: agentRun,
    }));
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            CodegenCICD Dashboard
          </Typography>
          
          <FormControl sx={{ minWidth: 200, mr: 2 }}>
            <InputLabel>Selected Project</InputLabel>
            <Select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              label="Selected Project"
              size="small"
            >
              {projects.map(project => (
                <MenuItem key={project.id} value={project.id}>
                  {project.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <Button
            color="inherit"
            startIcon={<RefreshIcon />}
            onClick={loadProjects}
            disabled={loading}
          >
            Refresh
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4" component="h1">
            Projects
          </Typography>
          
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="body2" color={isConnected ? 'success.main' : 'error.main'}>
              WebSocket: {isConnected ? 'Connected' : 'Disconnected'}
            </Typography>
          </Box>
        </Box>

        {loading ? (
          <Typography>Loading projects...</Typography>
        ) : projects.length === 0 ? (
          <Box textAlign="center" py={8}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No projects found
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Create your first project to get started with AI-powered CI/CD.
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              Create Project
            </Button>
          </Box>
        ) : (
          <Grid container spacing={3}>
            {projects.map(project => (
              <Grid item key={project.id}>
                <ProjectCard
                  project={project}
                  onUpdate={handleUpdateProject}
                  onDelete={handleDeleteProject}
                  latestAgentRun={agentRuns[project.id]}
                  onAgentRunUpdate={handleAgentRunUpdate}
                />
              </Grid>
            ))}
          </Grid>
        )}
      </Container>

      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="add project"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={() => setCreateDialogOpen(true)}
      >
        <AddIcon />
      </Fab>

      {/* Create Project Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Project</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Project Name"
            fullWidth
            variant="outlined"
            value={newProject.name}
            onChange={(e) => setNewProject(prev => ({ ...prev, name: e.target.value }))}
            sx={{ mb: 2 }}
          />
          
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={2}
            variant="outlined"
            value={newProject.description}
            onChange={(e) => setNewProject(prev => ({ ...prev, description: e.target.value }))}
            sx={{ mb: 2 }}
          />
          
          <TextField
            margin="dense"
            label="Repository URL"
            fullWidth
            variant="outlined"
            placeholder="https://github.com/username/repository"
            value={newProject.repository_url}
            onChange={(e) => setNewProject(prev => ({ ...prev, repository_url: e.target.value }))}
            sx={{ mb: 2 }}
          />
          
          <TextField
            margin="dense"
            label="Default Branch"
            fullWidth
            variant="outlined"
            value={newProject.default_branch}
            onChange={(e) => setNewProject(prev => ({ ...prev, default_branch: e.target.value }))}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateProject} variant="contained">
            Create Project
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess(null)}
        message={success}
      />
    </ThemeProvider>
  );
};

export default App;

