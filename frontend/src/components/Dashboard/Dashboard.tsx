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
  Chip
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

  return (
    <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* App Bar */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            CodegenCICD Dashboard
          </Typography>
          
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
            Projects
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your AI-powered CI/CD projects with real-time agent runs and validation pipelines.
          </Typography>
        </Box>

        {/* Loading State */}
        {loading && projects.length === 0 && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
            <CircularProgress />
          </Box>
        )}

        {/* Empty State */}
        {!loading && projects.length === 0 && (
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
        {projects.length > 0 && (
          <Grid container spacing={3}>
            {projects.map((project: Project) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
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
