import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Box,
  Alert,
  Snackbar,
  Chip,
  Tabs,
  Tab,
  Paper,
  Card,
  CardContent,
  Menu,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Settings as SettingsIcon,
  Dashboard as DashboardIcon,
  Visibility as VisibilityIcon,
  Security as SecurityIcon,
  Code as CodeIcon,
  GitHub as GitHubIcon,
  Cloud as CloudIcon,
  Psychology as PsychologyIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { projectsApi, Project } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import ProjectCard from './ProjectCard';
import CreateProjectDialog from './CreateProjectDialog';
import ProjectConfigDialog from './ProjectConfigDialog';
import ServiceValidator from './ServiceValidator';
import EnvironmentVariables from './EnvironmentVariables';
import axios from 'axios';

interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  private: boolean;
  url: string;
  owner: string;
  description?: string;
  updated_at?: string;
  language?: string;
  stars?: number;
  forks?: number;
}

const Dashboard: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [configProjectId, setConfigProjectId] = useState<number | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });
  const [activeTab, setActiveTab] = useState(0);
  const [githubRepos, setGithubRepos] = useState<GitHubRepository[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [pinnedProjects, setPinnedProjects] = useState<GitHubRepository[]>([]);
  const [projectMenuAnchor, setProjectMenuAnchor] = useState<null | HTMLElement>(null);
  const [variablesDialogOpen, setVariablesDialogOpen] = useState(false);

  const { isConnected } = useWebSocket();

  // Load projects on component mount
  useEffect(() => {
    loadProjects();
    loadGithubRepos();
    loadPinnedProjects();
  }, []);

  const loadPinnedProjects = () => {
    const saved = localStorage.getItem('pinnedProjects');
    if (saved) {
      setPinnedProjects(JSON.parse(saved));
    }
  };

  const pinProject = (repo: GitHubRepository) => {
    const newPinned = [...pinnedProjects, repo];
    setPinnedProjects(newPinned);
    localStorage.setItem('pinnedProjects', JSON.stringify(newPinned));
    showSnackbar(`${repo.name} pinned to dashboard`, 'success');
  };

  const unpinProject = (repoId: number) => {
    const newPinned = pinnedProjects.filter(p => p.id !== repoId);
    setPinnedProjects(newPinned);
    localStorage.setItem('pinnedProjects', JSON.stringify(newPinned));
    showSnackbar('Project unpinned from dashboard', 'success');
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await projectsApi.getAll();
      setProjects(response.data);
      
      // Auto-select first project if none selected
      if (response.data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(response.data[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load projects');
      showSnackbar('Failed to load projects', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSelect = (projectId: number) => {
    setSelectedProjectId(projectId);
  };

  const handleCreateProject = async (projectData: Partial<Project>) => {
    try {
      const response = await projectsApi.create(projectData);
      setProjects(prev => [...prev, response.data]);
      setSelectedProjectId(response.data.id);
      setCreateDialogOpen(false);
      showSnackbar('Project created successfully!', 'success');
    } catch (err: any) {
      showSnackbar(err.response?.data?.detail || 'Failed to create project', 'error');
    }
  };

  const handleUpdateProject = async (projectId: number, projectData: Partial<Project>) => {
    try {
      const response = await projectsApi.update(projectId, projectData);
      setProjects(prev => prev.map(p => p.id === projectId ? response.data : p));
      showSnackbar('Project updated successfully!', 'success');
    } catch (err: any) {
      showSnackbar(err.response?.data?.detail || 'Failed to update project', 'error');
    }
  };

  const handleDeleteProject = async (projectId: number) => {
    try {
      await projectsApi.delete(projectId);
      setProjects(prev => prev.filter(p => p.id !== projectId));
      if (selectedProjectId === projectId) {
        setSelectedProjectId(projects.length > 1 ? projects.find(p => p.id !== projectId)?.id || null : null);
      }
      showSnackbar('Project deleted successfully!', 'success');
    } catch (err: any) {
      showSnackbar(err.response?.data?.detail || 'Failed to delete project', 'error');
    }
  };

  const handleOpenConfig = (projectId: number) => {
    setConfigProjectId(projectId);
    setConfigDialogOpen(true);
  };

  const loadGithubRepos = async () => {
    try {
      setReposLoading(true);
      const response = await axios.get('/api/validation/github-repositories');
      setGithubRepos(response.data.repositories);
    } catch (err: any) {
      console.error('Failed to load GitHub repositories:', err);
      showSnackbar('Failed to load GitHub repositories', 'error');
    } finally {
      setReposLoading(false);
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const selectedProject = projects.find(p => p.id === selectedProjectId);

  const renderTabContent = () => {
    switch (activeTab) {
      case 0:
        return (
          <Container maxWidth="xl" sx={{ mt: 3 }}>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {loading ? (
              <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                <Typography variant="h6">Loading projects...</Typography>
              </Box>
            ) : pinnedProjects.length === 0 ? (
              <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="400px">
                <Typography variant="h5" gutterBottom>
                  No Pinned Projects
                </Typography>
                <Typography variant="body1" color="text.secondary" gutterBottom>
                  Pin GitHub repositories to your dashboard using the selector above
                </Typography>
              </Box>
            ) : (
              <Grid container spacing={3}>
                {pinnedProjects.map((repo) => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={repo.id}>
                    <Card>
                      <CardContent>
                        <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                          <Typography variant="h6" gutterBottom>
                            {repo.name}
                          </Typography>
                          <Button
                            size="small"
                            color="error"
                            onClick={() => unpinProject(repo.id)}
                          >
                            Unpin
                          </Button>
                        </Box>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {repo.description || 'No description available'}
                        </Typography>
                        <Box display="flex" alignItems="center" gap={1} mt={2}>
                          <Chip 
                            label={repo.private ? 'Private' : 'Public'} 
                            size="small" 
                            color={repo.private ? 'warning' : 'success'}
                          />
                          {repo.language && (
                            <Chip 
                              label={repo.language} 
                              size="small" 
                              variant="outlined"
                            />
                          )}
                        </Box>
                        <Box display="flex" justifyContent="space-between" mt={2}>
                          <Typography variant="body2" color="text.secondary">
                            ⭐ {repo.stars || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            🍴 {repo.forks || 0}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Container>
        );
      case 1:
        return (
          <Container maxWidth="xl" sx={{ mt: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                <ServiceValidator
                  serviceName="codegen"
                  displayName="Codegen API"
                  icon={<CodeIcon color="primary" />}
                  autoRefresh={true}
                  refreshInterval={60000}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <ServiceValidator
                  serviceName="github"
                  displayName="GitHub API"
                  icon={<GitHubIcon color="primary" />}
                  autoRefresh={true}
                  refreshInterval={60000}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <ServiceValidator
                  serviceName="gemini"
                  displayName="Gemini AI"
                  icon={<PsychologyIcon color="primary" />}
                  autoRefresh={true}
                  refreshInterval={60000}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <ServiceValidator
                  serviceName="cloudflare"
                  displayName="Cloudflare"
                  icon={<CloudIcon color="primary" />}
                  autoRefresh={true}
                  refreshInterval={60000}
                />
              </Grid>
            </Grid>
          </Container>
        );
      case 2:
        return (
          <Container maxWidth="xl" sx={{ mt: 3 }}>
            <EnvironmentVariables />
          </Container>
        );
      default:
        return null;
    }
  };

  return (
    <>
      {/* Header */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          {/* Connection Status */}
          <Chip
            label={isConnected ? 'Connected' : 'Disconnected'}
            color={isConnected ? 'success' : 'error'}
            size="small"
            sx={{ mr: 2 }}
          />

          <Box sx={{ flexGrow: 1 }} />

          {/* GitHub Projects Dropdown */}
          <Button
            color="inherit"
            startIcon={<GitHubIcon />}
            endIcon={<ExpandMoreIcon />}
            onClick={(e) => setProjectMenuAnchor(e.currentTarget)}
            sx={{ mr: 2 }}
          >
            Select Project
          </Button>

          {/* Variables Settings Gear Icon */}
          <IconButton
            color="inherit"
            onClick={() => setVariablesDialogOpen(true)}
            sx={{ mr: 1 }}
          >
            <SettingsIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* GitHub Projects Menu */}
      <Menu
        anchorEl={projectMenuAnchor}
        open={Boolean(projectMenuAnchor)}
        onClose={() => setProjectMenuAnchor(null)}
        PaperProps={{
          style: {
            maxHeight: 400,
            width: '300px',
          },
        }}
      >
        {reposLoading ? (
          <MenuItem disabled>Loading repositories...</MenuItem>
        ) : githubRepos.length === 0 ? (
          <MenuItem disabled>No repositories found</MenuItem>
        ) : (
          githubRepos
            .filter(repo => !pinnedProjects.find(p => p.id === repo.id))
            .map((repo) => (
              <MenuItem
                key={repo.id}
                onClick={() => {
                  pinProject(repo);
                  setProjectMenuAnchor(null);
                }}
              >
                <ListItemIcon>
                  <GitHubIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={repo.name}
                  secondary={repo.description || 'No description'}
                />
              </MenuItem>
            ))
        )}
      </Menu>

      {/* Navigation Tabs */}
      <Paper square elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab 
            icon={<DashboardIcon />} 
            label="PINNED" 
            iconPosition="start"
          />
          <Tab 
            icon={<SecurityIcon />} 
            label="Service Status" 
            iconPosition="start"
          />
          <Tab 
            icon={<VisibilityIcon />} 
            label="Environment" 
            iconPosition="start"
          />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {renderTabContent()}

      {/* Dialogs */}
      <CreateProjectDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onCreate={handleCreateProject}
      />

      {configProjectId && (
        <ProjectConfigDialog
          open={configDialogOpen}
          onClose={() => {
            setConfigDialogOpen(false);
            setConfigProjectId(null);
          }}
          projectId={configProjectId}
        />
      )}

      {/* Variables Management Dialog */}
      <Dialog
        open={variablesDialogOpen}
        onClose={() => setVariablesDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Environment Variables</DialogTitle>
        <DialogContent>
          <List>
            <ListItem>
              <ListItemIcon>
                <CodeIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Codegen API"
                secondary="CODEGEN_ORG_ID, CODEGEN_API_TOKEN"
              />
              <Chip label="Configured" color="success" size="small" />
            </ListItem>
            <Divider />
            <ListItem>
              <ListItemIcon>
                <GitHubIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="GitHub API"
                secondary="GITHUB_TOKEN"
              />
              <Chip label="Error" color="error" size="small" />
            </ListItem>
            <Divider />
            <ListItem>
              <ListItemIcon>
                <PsychologyIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Gemini AI"
                secondary="GEMINI_API_KEY"
              />
              <Chip label="Configured" color="success" size="small" />
            </ListItem>
            <Divider />
            <ListItem>
              <ListItemIcon>
                <CloudIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Cloudflare"
                secondary="CLOUDFLARE_API_KEY, CLOUDFLARE_ACCOUNT_ID"
              />
              <Chip label="Error" color="error" size="small" />
            </ListItem>
          </List>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Note: Environment variables can be edited in the Environment tab or through your deployment configuration.
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVariablesDialogOpen(false)}>Close</Button>
          <Button 
            onClick={() => {
              setVariablesDialogOpen(false);
              setActiveTab(2); // Switch to Environment tab
            }}
            variant="contained"
          >
            Edit Variables
          </Button>
        </DialogActions>
      </Dialog>

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
    </>
  );
};

export default Dashboard;
