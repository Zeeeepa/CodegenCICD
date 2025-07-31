/**
 * Main CICD Dashboard Component
 */

import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Grid,
  Alert,
  Fab,
  Snackbar,
  CircularProgress,
  Backdrop
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

import { DashboardHeader } from './DashboardHeader';
import { ProjectSelector } from './ProjectSelector';
import { ProjectCard } from './ProjectCard';
import { GlobalSettings } from './GlobalSettings';

import { useProjectStore, useProjectActions, useActiveProjects } from '../store/projectStore';
import { useWorkflowStore } from '../store/workflowStore';
import { Project, Notification, NotificationType } from '../types/cicd';

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

const CICDDashboard: React.FC = () => {
  // State
  const [showProjectSelector, setShowProjectSelector] = useState(false);
  const [showGlobalSettings, setShowGlobalSettings] = useState(false);
  const [notification, setNotification] = useState<Notification | null>(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);

  // Store hooks
  const { loading, error } = useProjectStore();
  const activeProjects = useActiveProjects();
  const { 
    loadProjects, 
    refreshAllProjects, 
    clearError 
  } = useProjectActions();

  const activeWorkflows = useWorkflowStore(state => 
    Object.values(state.activeWorkflows)
  );

  // ========================================================================
  // EFFECTS
  // ========================================================================

  // Load projects on mount
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Auto-refresh projects every 30 seconds
  useEffect(() => {
    if (!autoRefreshEnabled) return;

    const interval = setInterval(() => {
      refreshAllProjects();
    }, 30000);

    return () => clearInterval(interval);
  }, [autoRefreshEnabled, refreshAllProjects]);

  // Clear error after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        clearError();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  // ========================================================================
  // HANDLERS
  // ========================================================================

  const handleAddProject = () => {
    setShowProjectSelector(true);
  };

  const handleProjectAdded = (project: Project) => {
    setShowProjectSelector(false);
    showNotification({
      id: `project_added_${Date.now()}`,
      type: NotificationType.SUCCESS,
      title: 'Project Added',
      message: `Successfully added ${project.name} to dashboard`,
      timestamp: new Date().toISOString(),
      read: false,
      autoDismiss: true,
      dismissAfter: 5000
    });
  };

  const handleRefreshAll = async () => {
    try {
      await refreshAllProjects();
      showNotification({
        id: `refresh_${Date.now()}`,
        type: NotificationType.SUCCESS,
        title: 'Projects Refreshed',
        message: 'All projects have been refreshed successfully',
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 3000
      });
    } catch (error) {
      showNotification({
        id: `refresh_error_${Date.now()}`,
        type: NotificationType.ERROR,
        title: 'Refresh Failed',
        message: 'Failed to refresh projects. Please try again.',
        timestamp: new Date().toISOString(),
        read: false,
        autoDismiss: true,
        dismissAfter: 5000
      });
    }
  };

  const showNotification = (notif: Notification) => {
    setNotification(notif);
  };

  const handleCloseNotification = () => {
    setNotification(null);
  };

  // ========================================================================
  // RENDER HELPERS
  // ========================================================================

  const renderProjectCards = () => {
    if (activeProjects.length === 0) {
      return (
        <Grid item xs={12}>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 400,
              textAlign: 'center',
              bgcolor: 'background.paper',
              borderRadius: 2,
              border: '2px dashed',
              borderColor: 'divider',
              p: 4
            }}
          >
            <Typography variant="h5" gutterBottom color="text.secondary">
              No Projects Added Yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Get started by adding your first GitHub repository to the dashboard
            </Typography>
            <Fab
              color="primary"
              variant="extended"
              onClick={handleAddProject}
              sx={{ minWidth: 200 }}
            >
              <AddIcon sx={{ mr: 1 }} />
              Add Your First Project
            </Fab>
          </Box>
        </Grid>
      );
    }

    return activeProjects.map((project) => (
      <Grid item xs={12} md={6} lg={4} key={project.id}>
        <ProjectCard 
          project={project}
          onNotification={showNotification}
        />
      </Grid>
    ));
  };

  const renderLoadingOverlay = () => {
    if (!loading) return null;

    return (
      <Backdrop
        sx={{ 
          color: '#fff', 
          zIndex: (theme) => theme.zIndex.drawer + 1,
          flexDirection: 'column',
          gap: 2
        }}
        open={loading}
      >
        <CircularProgress color="inherit" size={60} />
        <Typography variant="h6">
          Loading Projects...
        </Typography>
      </Backdrop>
    );
  };

  const renderErrorAlert = () => {
    if (!error) return null;

    return (
      <Alert 
        severity="error" 
        onClose={clearError}
        sx={{ mb: 3 }}
      >
        {error}
      </Alert>
    );
  };

  const renderStats = () => {
    const totalProjects = activeProjects.length;
    const runningWorkflows = activeWorkflows.length;
    const totalRuns = activeProjects.reduce((sum, project) => sum + project.stats.totalRuns, 0);
    const successRate = activeProjects.length > 0 
      ? Math.round(activeProjects.reduce((sum, project) => sum + project.stats.successRate, 0) / activeProjects.length)
      : 0;

    return (
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
            <Typography variant="h4" color="primary.main">
              {totalProjects}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Active Projects
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
            <Typography variant="h4" color="warning.main">
              {runningWorkflows}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Running Workflows
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
            <Typography variant="h4" color="info.main">
              {totalRuns}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Total Runs
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
            <Typography variant="h4" color="success.main">
              {successRate}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Success Rate
            </Typography>
          </Box>
        </Grid>
      </Grid>
    );
  };

  // ========================================================================
  // RENDER
  // ========================================================================

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Header */}
      <DashboardHeader
        onAddProject={handleAddProject}
        onRefreshAll={handleRefreshAll}
        onOpenSettings={() => setShowGlobalSettings(true)}
        autoRefreshEnabled={autoRefreshEnabled}
        onToggleAutoRefresh={setAutoRefreshEnabled}
      />

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ py: 3 }}>
        {/* Error Alert */}
        {renderErrorAlert()}

        {/* Statistics */}
        {renderStats()}

        {/* Project Cards Grid */}
        <Grid container spacing={3}>
          {renderProjectCards()}
        </Grid>
      </Container>

      {/* Floating Action Buttons */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 2
        }}
      >
        <Fab
          color="secondary"
          onClick={handleRefreshAll}
          disabled={loading}
          title="Refresh All Projects"
        >
          <RefreshIcon />
        </Fab>
        
        <Fab
          color="primary"
          onClick={handleAddProject}
          title="Add New Project"
        >
          <AddIcon />
        </Fab>
      </Box>

      {/* Dialogs */}
      <ProjectSelector
        open={showProjectSelector}
        onClose={() => setShowProjectSelector(false)}
        onProjectAdded={handleProjectAdded}
      />

      <GlobalSettings
        open={showGlobalSettings}
        onClose={() => setShowGlobalSettings(false)}
      />

      {/* Notifications */}
      <Snackbar
        open={!!notification}
        autoHideDuration={notification?.autoDismiss ? notification.dismissAfter : null}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseNotification}
          severity={notification?.type as any}
          variant="filled"
          sx={{ width: '100%' }}
        >
          <Typography variant="subtitle2">
            {notification?.title}
          </Typography>
          {notification?.message && (
            <Typography variant="body2">
              {notification.message}
            </Typography>
          )}
        </Alert>
      </Snackbar>

      {/* Loading Overlay */}
      {renderLoadingOverlay()}
    </Box>
  );
};

export default CICDDashboard;

