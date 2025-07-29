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
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { projectsApi, Project } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import ProjectCard from './ProjectCard';
import CreateProjectDialog from './CreateProjectDialog';
import ProjectConfigDialog from './ProjectConfigDialog';

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

  const { isConnected } = useWebSocket();

  // Load projects on component mount
  useEffect(() => {
    loadProjects();
  }, []);

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

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity });
  };

  const selectedProject = projects.find(p => p.id === selectedProjectId);

  return (
    <>
      {/* Header */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            🚀 CodegenCICD Dashboard
          </Typography>
          
          {/* Connection Status */}
          <Chip
            label={isConnected ? 'Connected' : 'Disconnected'}
            color={isConnected ? 'success' : 'error'}
            size="small"
            sx={{ mr: 2 }}
          />

          {/* Project Selector */}
          <FormControl sx={{ minWidth: 200, mr: 2 }}>
            <InputLabel id="project-select-label" sx={{ color: 'white' }}>
              Select Project
            </InputLabel>
            <Select
              labelId="project-select-label"
              value={selectedProjectId || ''}
              onChange={(e) => handleProjectSelect(e.target.value as number)}
              label="Select Project"
              sx={{ 
                color: 'white',
                '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.23)' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.5)' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'white' },
                '.MuiSvgIcon-root': { color: 'white' }
              }}
            >
              {projects.map((project) => (
                <MenuItem key={project.id} value={project.id}>
                  {project.name} ({project.github_owner}/{project.github_repo})
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Action Buttons */}
          <Button
            color="inherit"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{ mr: 1 }}
          >
            Add Project
          </Button>
          
          <Button
            color="inherit"
            startIcon={<RefreshIcon />}
            onClick={loadProjects}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>

          {selectedProject && (
            <Button
              color="inherit"
              startIcon={<SettingsIcon />}
              onClick={() => handleOpenConfig(selectedProject.id)}
            >
              Settings
            </Button>
          )}
        </Toolbar>
      </AppBar>

      {/* Main Content */}
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
        ) : projects.length === 0 ? (
          <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="400px">
            <Typography variant="h5" gutterBottom>
              No Projects Found
            </Typography>
            <Typography variant="body1" color="text.secondary" gutterBottom>
              Get started by creating your first project
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
              sx={{ mt: 2 }}
            >
              Create First Project
            </Button>
          </Box>
        ) : (
          <Grid container spacing={3}>
            {projects.map((project) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
                <ProjectCard
                  project={project}
                  isSelected={project.id === selectedProjectId}
                  onSelect={() => handleProjectSelect(project.id)}
                  onUpdate={(data) => handleUpdateProject(project.id, data)}
                  onDelete={() => handleDeleteProject(project.id)}
                  onOpenConfig={() => handleOpenConfig(project.id)}
                />
              </Grid>
            ))}
          </Grid>
        )}
      </Container>

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

