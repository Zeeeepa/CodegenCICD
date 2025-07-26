/**
 * Project Selector Component
 * Dropdown to select active project
 */

import React from 'react';
import {
  FormControl,
  Select,
  MenuItem,
  Typography,
  Box,
  Chip,
} from '@mui/material';
import { Folder as ProjectIcon } from '@mui/icons-material';

import { useDashboard } from '../../contexts/DashboardContext';

const ProjectSelector: React.FC = () => {
  const { dashboardState, setSelectedProject } = useDashboard();

  const handleProjectChange = (event: any) => {
    const projectId = event.target.value;
    const project = dashboardState.projects.find(p => p.id === projectId);
    setSelectedProject(project);
  };

  if (dashboardState.projects.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 2 }}>
        <Typography variant="body2" color="text.secondary">
          No projects available
        </Typography>
      </Box>
    );
  }

  return (
    <FormControl fullWidth size="small">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Active Project
      </Typography>
      <Select
        value={dashboardState.selectedProject?.id || ''}
        onChange={handleProjectChange}
        displayEmpty
        sx={{
          '& .MuiSelect-select': {
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          },
        }}
      >
        <MenuItem value="">
          <Typography color="text.secondary">Select a project</Typography>
        </MenuItem>
        {dashboardState.projects.map((project) => (
          <MenuItem key={project.id} value={project.id}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
              <ProjectIcon sx={{ fontSize: 16 }} />
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="body2">{project.name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {project.github_owner}/{project.github_repo}
                </Typography>
              </Box>
              <Chip
                size="small"
                label={project.status}
                color={project.status === 'active' ? 'success' : 'default'}
              />
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default ProjectSelector;
