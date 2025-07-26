/**
 * Project Grid Component
 * Displays projects in a responsive grid layout
 */

import React from 'react';
import {
  Grid,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';

import { useDashboard } from '../../contexts/DashboardContext';
import ProjectCard from './ProjectCard';

const ProjectGrid: React.FC = () => {
  const { dashboardState, updateUIState, setSelectedProject } = useDashboard();

  const handleAgentRun = (project: any) => {
    setSelectedProject(project);
    updateUIState({
      dialogOpen: { ...dashboardState, agentRun: true }
    });
  };

  const handleSettings = (project: any) => {
    setSelectedProject(project);
    updateUIState({
      dialogOpen: { ...dashboardState, settings: true }
    });
  };

  const handleCreateProject = () => {
    updateUIState({
      dialogOpen: { ...dashboardState, createProject: true }
    });
  };

  if (dashboardState.isLoading && dashboardState.projects.length === 0) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: 200,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (dashboardState.error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {dashboardState.error}
      </Alert>
    );
  }

  if (dashboardState.projects.length === 0) {
    return (
      <Box
        sx={{
          textAlign: 'center',
          py: 8,
          px: 2,
        }}
      >
        <Typography variant="h5" gutterBottom color="text.secondary">
          No projects yet
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Create your first project to get started with AI-powered CI/CD workflows.
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreateProject}
          size="large"
          sx={{ mt: 2 }}
        >
          Create Project
        </Button>
      </Box>
    );
  }

  return (
    <Grid container spacing={3}>
      {dashboardState.projects.map((project) => {
        // Get agent runs for this project
        const projectAgentRuns = dashboardState.agentRuns.filter(
          run => run.project_id === project.id
        );

        return (
          <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
            <ProjectCard
              project={project}
              agentRuns={projectAgentRuns}
              onAgentRun={handleAgentRun}
              onSettings={handleSettings}
            />
          </Grid>
        );
      })}
    </Grid>
  );
};

export default ProjectGrid;
