import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Grid,
  Fab,
  Alert,
  Snackbar,
  CircularProgress,
  AppBar,
  Toolbar,
  IconButton,
  Badge,
  Menu,
  MenuItem,
  Chip,
  FormControl,
  InputLabel,
  Select
} from '@mui/material';
import {
  Add as AddIcon,
  Notifications as NotificationsIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  GitHub as GitHubIcon
} from '@mui/icons-material';
import { useApp } from '../../contexts/AppContext';
import ProjectCard from '../ProjectCard/ProjectCard';
import CreateProjectDialog from './CreateProjectDialog';
import NotificationPanel from './NotificationPanel';
import { Project } from '../../types';

const Dashboard: React.FC = () => {
  const { state, loadProjects, addNotification } = useApp();
  const { projects, loading, error, wsConnected, notifications } = state;

  // Local state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [notificationAnchor, setNotificationAnchor] = useState<null | HTMLElement>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<string>('all');

  // Load projects on component mount
  useEffect(() => {
    loadProjects();
  }, []);

  // Show error snackbar when error occurs
  useEffect(() => {
    if (error) {
      setSnackbarMessage(error);
      setSnackbarOpen(true);
    }
  }, [error]);

  const handleRefresh = () => {
    loadProjects();
  };

  const handleCreateProject = () => {
    setCreateDialogOpen(true);
  };

  const handleNotificationClick = (event: React.MouseEvent<HTMLElement>) => {
    setNotificationAnchor(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setNotificationAnchor(null);
  };

  const unreadNotifications = notifications.filter(n => !n.read);

  // Filter projects based on selection
  const displayProjects = selectedProjectId === 'all' 
    ? projects 
    : projects.filter(p => p.id === selectedProjectId);

  const selectedProject = selectedProjectId !== 'all' 
    ? projects.find(p => p.id === selectedProjectId) 
    : null;

  return (
    <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* App Bar */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ mr: 3 }}>
            CodegenCICD Dashboard
          </Typography>
          
          {/* Project Selector */}
          {projects.length > 0 && (
            <FormControl variant="outlined" size="small" sx={{ minWidth: 200, mr: 2 }}>
              <InputLabel sx={{ color: 'white' }}>Select Project</InputLabel>
              <Select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                label="Select Project"
                sx={{ 
                  color: 'white',
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'rgba(255, 255, 255, 0.23)',
                  },
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'rgba(255, 255, 255, 0.5)',
                  },
                  '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'white',
                  },
                  '& .MuiSvgIcon-root': {
                    color: 'white',
                  }
                }}
              >
                <MenuItem value="all">All Projects</MenuItem>
                {projects.map((project) => (
                  <MenuItem key={project.id} value={project.id}>
                    {project.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <Box sx={{ flexGrow: 1 }} />
          
          {/* WebSocket Connection Status */}
          <Chip
            label={wsConnected ? 'Connected' : 'Disconnected'}
            color={wsConnected ? 'success' : 'error'}
            size="small"
            sx={{ mr: 2 }}
          />

          {/* Refresh Button */}
          <IconButton
            color="inherit"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh Projects"
          >
            <RefreshIcon />
          </IconButton>

          {/* Notifications */}
          <IconButton
            color="inherit"
            onClick={handleNotificationClick}
            title="Notifications"
          >
            <Badge badgeContent={unreadNotifications.length} color="error">
              <NotificationsIcon />
            </Badge>
          </IconButton>

          {/* Settings */}
          <IconButton
            color="inherit"
            title="Settings"
          >
            <SettingsIcon />
          </IconButton>

          {/* GitHub Link */}
          <IconButton
            color="inherit"
            component="a"
            href="https://github.com/Zeeeepa/CodegenCICD"
            target="_blank"
            title="View on GitHub"
          >
            <GitHubIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            {selectedProject ? `Project: ${selectedProject.name}` : 'Projects'}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {selectedProject 
              ? `Manage ${selectedProject.name} with AI-powered CI/CD workflows and validation pipelines.`
              : 'Manage your AI-powered CI/CD projects with real-time agent runs and validation pipelines.'
            }
          </Typography>
        </Box>

        {/* Loading State */}
        {loading && displayProjects.length === 0 && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
            <CircularProgress />
          </Box>
        )}

        {/* Empty State */}
        {!loading && displayProjects.length === 0 && selectedProjectId === 'all' && (
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            minHeight="400px"
            textAlign="center"
          >
            <Typography variant="h5" gutterBottom color="text.secondary">
              No Projects Yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Create your first project to start using AI-powered CI/CD workflows.
            </Typography>
            <Fab
              color="primary"
              variant="extended"
              onClick={handleCreateProject}
              size="large"
            >
              <AddIcon sx={{ mr: 1 }} />
              Create First Project
            </Fab>
          </Box>
        )}

        {/* Projects Grid */}
        {displayProjects.length > 0 && (
          <Grid container spacing={3}>
            {displayProjects.map((project: Project) => (
              <Grid item xs={12} sm={6} md={4} lg={selectedProject ? 12 : 3} key={project.id}>
                <ProjectCard project={project} />
              </Grid>
            ))}
          </Grid>
        )}

        {/* Add Project FAB */}
        {projects.length > 0 && (
          <Fab
            color="primary"
            aria-label="add project"
            onClick={handleCreateProject}
            sx={{
              position: 'fixed',
              bottom: 16,
              right: 16,
            }}
          >
            <AddIcon />
          </Fab>
        )}
      </Container>

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
      />

      {/* Notification Panel */}
      <NotificationPanel
        anchorEl={notificationAnchor}
        open={Boolean(notificationAnchor)}
        onClose={handleNotificationClose}
      />

      {/* Error Snackbar */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      >
        <Alert
          onClose={() => setSnackbarOpen(false)}
          severity="error"
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Dashboard;
