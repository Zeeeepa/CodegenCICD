/**
 * Create Project Dialog Component
 * Form for creating new projects
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  FormControlLabel,
  Switch,
  Alert,
  IconButton,
} from '@mui/material';
import {
  Close as CloseIcon,
  Add as AddIcon,
  GitHub as GitHubIcon,
} from '@mui/icons-material';

import { useDashboard } from '../../contexts/DashboardContext';
import { CreateProjectRequest } from '../../types/api';

const CreateProjectDialog: React.FC = () => {
  const { uiState, updateUIState, createProject } = useDashboard();
  
  const [formData, setFormData] = useState<CreateProjectRequest>({
    name: '',
    description: '',
    github_repo: '',
    github_owner: '',
    auto_merge_enabled: false,
    auto_confirm_plans: false,
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const isOpen = uiState.dialogOpen.createProject;

  const handleClose = () => {
    updateUIState({
      dialogOpen: { ...uiState.dialogOpen, createProject: false }
    });
    resetForm();
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      github_repo: '',
      github_owner: '',
      auto_merge_enabled: false,
      auto_confirm_plans: false,
    });
    setErrors({});
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    }

    if (!formData.github_owner.trim()) {
      newErrors.github_owner = 'GitHub owner is required';
    }

    if (!formData.github_repo.trim()) {
      newErrors.github_repo = 'GitHub repository is required';
    }

    // Validate GitHub owner/repo format
    if (formData.github_owner && !/^[a-zA-Z0-9\-_.]+$/.test(formData.github_owner)) {
      newErrors.github_owner = 'Invalid GitHub owner format';
    }

    if (formData.github_repo && !/^[a-zA-Z0-9\-_.]+$/.test(formData.github_repo)) {
      newErrors.github_repo = 'Invalid GitHub repository format';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await createProject(formData);
      handleClose();
    } catch (error) {
      console.error('Failed to create project:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: keyof CreateProjectRequest) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: '',
      }));
    }
  };

  const parseGitHubUrl = (url: string) => {
    // Extract owner/repo from GitHub URL
    const match = url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
    if (match) {
      const [, owner, repo] = match;
      setFormData(prev => ({
        ...prev,
        github_owner: owner,
        github_repo: repo.replace('.git', ''),
      }));
    }
  };

  return (
    <Dialog
      open={isOpen}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            Create New Project
          </Typography>
          <IconButton onClick={handleClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <Alert severity="info">
            Create a new project to start managing AI-powered CI/CD workflows with Codegen integration.
          </Alert>

          <TextField
            label="Project Name"
            value={formData.name}
            onChange={handleInputChange('name')}
            error={!!errors.name}
            helperText={errors.name || 'A descriptive name for your project'}
            fullWidth
            required
          />

          <TextField
            label="Description"
            value={formData.description}
            onChange={handleInputChange('description')}
            multiline
            rows={3}
            placeholder="Brief description of what this project does..."
            fullWidth
          />

          <Box>
            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <GitHubIcon />
              GitHub Repository
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Owner"
                value={formData.github_owner}
                onChange={handleInputChange('github_owner')}
                error={!!errors.github_owner}
                helperText={errors.github_owner}
                placeholder="username or organization"
                fullWidth
                required
              />
              <TextField
                label="Repository"
                value={formData.github_repo}
                onChange={handleInputChange('github_repo')}
                error={!!errors.github_repo}
                helperText={errors.github_repo}
                placeholder="repository-name"
                fullWidth
                required
              />
            </Box>

            <TextField
              label="Or paste GitHub URL"
              placeholder="https://github.com/owner/repository"
              onChange={(e) => parseGitHubUrl(e.target.value)}
              fullWidth
              size="small"
              sx={{ mt: 2 }}
              helperText="Paste a GitHub URL to auto-fill owner and repository"
            />
          </Box>

          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Automation Settings
            </Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={formData.auto_merge_enabled}
                  onChange={handleInputChange('auto_merge_enabled')}
                />
              }
              label="Auto-merge validated PRs"
              sx={{ mb: 1 }}
            />
            
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, ml: 4 }}>
              Automatically merge pull requests that pass validation pipeline
            </Typography>

            <FormControlLabel
              control={
                <Switch
                  checked={formData.auto_confirm_plans}
                  onChange={handleInputChange('auto_confirm_plans')}
                />
              }
              label="Auto-confirm proposed plans"
            />
            
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
              Automatically confirm agent-proposed plans without manual approval
            </Typography>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isSubmitting}
          startIcon={<AddIcon />}
        >
          {isSubmitting ? 'Creating...' : 'Create Project'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateProjectDialog;
