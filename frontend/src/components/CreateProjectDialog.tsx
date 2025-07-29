import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControlLabel,
  Switch,
  Alert,
  Box,
  Autocomplete,
  Typography,
  Divider,
} from '@mui/material';
import { Project, projectsApi } from '../services/api';

interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (project: Partial<Project>) => void;
}

interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  owner: {
    login: string;
  };
  description?: string;
  private: boolean;
}

const CreateProjectDialog: React.FC<CreateProjectDialogProps> = ({
  open,
  onClose,
  onCreate,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    github_owner: '',
    github_repo: '',
    auto_merge_enabled: false,
    auto_confirm_plans: false,
  });
  const [githubRepos, setGithubRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingRepos, setLoadingRepos] = useState(false);

  useEffect(() => {
    if (open) {
      loadGitHubRepos();
    }
  }, [open]);

  const loadGitHubRepos = async () => {
    try {
      setLoadingRepos(true);
      const response = await projectsApi.getGitHubRepos();
      setGithubRepos(response.data);
    } catch (err: any) {
      console.error('Failed to load GitHub repositories:', err);
      setError('Failed to load GitHub repositories. Please check your GitHub token.');
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
    setError(null);
  };

  const handleRepoSelect = (repo: GitHubRepo | null) => {
    if (repo) {
      setFormData(prev => ({
        ...prev,
        name: prev.name || repo.name,
        github_owner: repo.owner.login,
        github_repo: repo.name,
      }));
    }
  };

  const handleSubmit = async () => {
    // Validation
    if (!formData.name.trim()) {
      setError('Project name is required');
      return;
    }
    if (!formData.github_owner.trim()) {
      setError('GitHub owner is required');
      return;
    }
    if (!formData.github_repo.trim()) {
      setError('GitHub repository is required');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Generate webhook URL (this would typically be done on the backend)
      const webhookUrl = `${process.env.REACT_APP_CLOUDFLARE_WORKER_URL || 'https://webhook-gateway.pixeliumperfecto.workers.dev'}/webhook/${formData.github_owner}/${formData.github_repo}`;

      const projectData: Partial<Project> = {
        ...formData,
        webhook_url: webhookUrl,
        status: 'active',
      };

      onCreate(projectData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({
      name: '',
      github_owner: '',
      github_repo: '',
      auto_merge_enabled: false,
      auto_confirm_plans: false,
    });
    setError(null);
    onClose();
  };

  const selectedRepo = githubRepos.find(
    repo => repo.owner.login === formData.github_owner && repo.name === formData.github_repo
  );

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Create New Project</DialogTitle>
      
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ mt: 1 }}>
          {/* GitHub Repository Selection */}
          <Typography variant="subtitle1" gutterBottom>
            GitHub Repository
          </Typography>
          
          <Autocomplete
            options={githubRepos}
            getOptionLabel={(option) => option.full_name}
            loading={loadingRepos}
            onChange={(_, value) => handleRepoSelect(value)}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Select GitHub Repository"
                placeholder="Search repositories..."
                fullWidth
                sx={{ mb: 2 }}
              />
            )}
            renderOption={(props, option) => (
              <Box component="li" {...props}>
                <Box>
                  <Typography variant="body1">{option.full_name}</Typography>
                  {option.description && (
                    <Typography variant="body2" color="text.secondary">
                      {option.description}
                    </Typography>
                  )}
                </Box>
              </Box>
            )}
          />

          {/* Manual Input Fields */}
          <Box display="flex" gap={2} mb={2}>
            <TextField
              label="GitHub Owner"
              value={formData.github_owner}
              onChange={(e) => handleInputChange('github_owner', e.target.value)}
              fullWidth
              required
            />
            <TextField
              label="Repository Name"
              value={formData.github_repo}
              onChange={(e) => handleInputChange('github_repo', e.target.value)}
              fullWidth
              required
            />
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Project Configuration */}
          <Typography variant="subtitle1" gutterBottom>
            Project Configuration
          </Typography>

          <TextField
            label="Project Name"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            fullWidth
            required
            sx={{ mb: 2 }}
            helperText="Display name for this project in the dashboard"
          />

          {/* Auto-settings */}
          <Box>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.auto_merge_enabled}
                  onChange={(e) => handleInputChange('auto_merge_enabled', e.target.checked)}
                />
              }
              label="Auto-merge validated PRs"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4, mb: 1 }}>
              Automatically merge pull requests that pass all validation steps
            </Typography>

            <FormControlLabel
              control={
                <Switch
                  checked={formData.auto_confirm_plans}
                  onChange={(e) => handleInputChange('auto_confirm_plans', e.target.checked)}
                />
              }
              label="Auto-confirm proposed plans"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
              Automatically confirm plans without user intervention
            </Typography>
          </Box>

          {/* Webhook URL Preview */}
          {formData.github_owner && formData.github_repo && (
            <Box mt={2}>
              <Typography variant="subtitle2" gutterBottom>
                Webhook URL (auto-generated):
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ 
                wordBreak: 'break-all',
                backgroundColor: 'grey.100',
                p: 1,
                borderRadius: 1,
              }}>
                {`${process.env.REACT_APP_CLOUDFLARE_WORKER_URL || 'https://webhook-gateway.pixeliumperfecto.workers.dev'}/webhook/${formData.github_owner}/${formData.github_repo}`}
              </Typography>
            </Box>
          )}

          {/* Repository Info */}
          {selectedRepo && (
            <Box mt={2}>
              <Alert severity="info">
                <Typography variant="body2">
                  <strong>Repository:</strong> {selectedRepo.full_name}
                  {selectedRepo.description && (
                    <>
                      <br />
                      <strong>Description:</strong> {selectedRepo.description}
                    </>
                  )}
                  <br />
                  <strong>Visibility:</strong> {selectedRepo.private ? 'Private' : 'Public'}
                </Typography>
              </Alert>
            </Box>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading || !formData.name.trim() || !formData.github_owner.trim() || !formData.github_repo.trim()}
        >
          {loading ? 'Creating...' : 'Create Project'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateProjectDialog;

