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
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Dashboard as DashboardIcon,
  Visibility as VisibilityIcon,
  Security as SecurityIcon,
  Code as CodeIcon,
  GitHub as GitHubIcon,
  Cloud as CloudIcon,
  Psychology as PsychologyIcon,
  Cancel as CancelIcon,
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

  const { isConnected } = useWebSocket();

  // Load projects on component mount
  useEffect(() => {
    loadProjects();
    loadGithubRepos();
    loadPinnedProjects();
  }, []);

  const loadPinnedProjects = () => {
    try {
      const saved = localStorage.getItem('pinnedProjects');
      if (saved) {
        setPinnedProjects(JSON.parse(saved));
      }
    } catch (error) {
      console.error('Failed to load pinned projects:', error);
    }
  };

  const savePinnedProjects = (projects: GitHubRepository[]) => {
    try {
      localStorage.setItem('pinnedProjects', JSON.stringify(projects));
      setPinnedProjects(projects);
    } catch (error) {
      console.error('Failed to save pinned projects:', error);
    }
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

  const handleProjectSelect = (repoId: number) => {
    const repo = githubRepos.find(r => r.id === repoId);
    if (repo) {
      // Check if already pinned
      const isAlreadyPinned = pinnedProjects.some(p => p.id === repo.id);
      if (!isAlreadyPinned) {
        const newPinned = [...pinnedProjects, repo];
        savePinnedProjects(newPinned);
        showSnackbar(`Pinned ${repo.name} to dashboard!`, 'success');
      } else {
        showSnackbar(`${repo.name} is already pinned!`, 'error');
      }
    }
    setSelectedProjectId(repoId);
  };

  const handleUnpinProject = (repoId: number) => {
    const newPinned = pinnedProjects.filter(p => p.id !== repoId);
    savePinnedProjects(newPinned);
    const repo = pinnedProjects.find(p => p.id === repoId);
    if (repo) {
      showSnackbar(`Unpinned ${repo.name} from dashboard!`, 'success');
    }
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
            {pinnedProjects.length === 0 ? (
              <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="400px">
                <Typography variant="h5" gutterBottom>
                  No Pinned Projects
                </Typography>
                <Typography variant="body1" color="text.secondary" gutterBottom>
                  Use the project selector in the header to pin GitHub repositories to your dashboard
                </Typography>
                <GitHubIcon sx={{ fontSize: 64, color: 'text.secondary', mt: 2 }} />
              </Box>
            ) : (
              <Grid container spacing={3}>
                {pinnedProjects.map((repo) => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={repo.id}>
                    <Card 
                      sx={{ 
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        transition: 'all 0.3s ease',
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: 4,
                        }
                      }}
                    >
                      <CardContent sx={{ flexGrow: 1 }}>
                        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                          <Typography variant="h6" component="div" noWrap>
                            {repo.name}
                          </Typography>
                          <Tooltip title="Unpin project">
                            <IconButton 
                              size="small" 
                              onClick={() => handleUnpinProject(repo.id)}
                              color="error"
                            >
                              <CancelIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                        
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {repo.description || 'No description'}
                        </Typography>
                        
                        <Box display="flex" alignItems="center" gap={1} mt={2} mb={2}>
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
                        
                        <Box display="flex" justifyContent="space-between" alignItems="center" mt={2}>
                          <Box display="flex" gap={2}>
                            <Typography variant="body2" color="text.secondary">
                              ⭐ {repo.stars || 0}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              🍴 {repo.forks || 0}
                            </Typography>
                          </Box>
                          <Button
                            variant="contained"
                            size="small"
                            startIcon={<CodeIcon />}
                          >
                            Agent Run
                          </Button>
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

          {/* Project Selector */}
          <FormControl sx={{ minWidth: 300, flexGrow: 1 }}>
            <InputLabel id="project-select-label" sx={{ color: 'white' }}>
              Select Project to Pin to Dashboard
            </InputLabel>
            <Select
              labelId="project-select-label"
              value={selectedProjectId || ''}
              onChange={(e) => handleProjectSelect(e.target.value as number)}
              label="Select Project to Pin to Dashboard"
              sx={{ 
                color: 'white',
                '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.23)' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.5)' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'white' },
                '.MuiSvgIcon-root': { color: 'white' }
              }}
            >
              {githubRepos.map((repo) => (
                <MenuItem key={repo.id} value={repo.id}>
                  {repo.full_name} - {repo.description || 'No description'}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Toolbar>
      </AppBar>

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
            label="Projects" 
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
