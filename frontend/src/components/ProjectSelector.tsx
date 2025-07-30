/**
 * Project Selector Component - GitHub Repository Selection Dialog
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
  InputAdornment,
  Divider
} from '@mui/material';
import {
  Search as SearchIcon,
  GitHub as GitHubIcon,
  Lock as LockIcon,
  Public as PublicIcon
} from '@mui/icons-material';

import { GitHubRepository, Project, CreateProjectRequest } from '../types/cicd';
import { apiClient } from '../services/api';

interface ProjectSelectorProps {
  open: boolean;
  onClose: () => void;
  onProjectAdded: (project: Project) => void;
}

export const ProjectSelector: React.FC<ProjectSelectorProps> = ({
  open,
  onClose,
  onProjectAdded
}) => {
  const [repositories, setRepositories] = useState<GitHubRepository[]>([]);
  const [filteredRepos, setFilteredRepos] = useState<GitHubRepository[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepository | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load repositories when dialog opens
  useEffect(() => {
    if (open) {
      loadRepositories();
    }
  }, [open]);

  // Filter repositories based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredRepos(repositories);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = repositories.filter(repo =>
        repo.name.toLowerCase().includes(query) ||
        repo.full_name.toLowerCase().includes(query) ||
        repo.description?.toLowerCase().includes(query)
      );
      setFilteredRepos(filtered);
    }
  }, [searchQuery, repositories]);

  const loadRepositories = async () => {
    setLoading(true);
    setError(null);
    try {
      const repos = await apiClient.getGitHubRepositories();
      setRepositories(repos);
      setFilteredRepos(repos);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load repositories');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async () => {
    if (!selectedRepo) return;

    setCreating(true);
    setError(null);

    try {
      const projectData: CreateProjectRequest = {
        name: selectedRepo.name,
        github_owner: selectedRepo.owner.login,
        github_repo: selectedRepo.name,
        auto_merge_enabled: false,
        auto_confirm_plans: false,
        settings: {
          branch_name: selectedRepo.default_branch,
          planning_statement: `Automated CICD for ${selectedRepo.full_name}`,
          repository_rules: '',
          setup_commands: ''
        }
      };

      const project = await apiClient.createProject(projectData);
      onProjectAdded(project);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setCreating(false);
    }
  };

  const handleClose = () => {
    setSearchQuery('');
    setSelectedRepo(null);
    setError(null);
    onClose();
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { height: '80vh' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <GitHubIcon />
          <Typography variant="h6">
            Add GitHub Repository
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {/* Search */}
        <TextField
          fullWidth
          placeholder="Search repositories..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 2 }}
        />

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Loading */}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Repository List */}
        {!loading && (
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {filteredRepos.length === 0 ? (
              <ListItem>
                <ListItemText
                  primary="No repositories found"
                  secondary={searchQuery ? "Try adjusting your search query" : "No repositories available"}
                />
              </ListItem>
            ) : (
              filteredRepos.map((repo) => (
                <React.Fragment key={repo.id}>
                  <ListItem
                    button
                    selected={selectedRepo?.id === repo.id}
                    onClick={() => setSelectedRepo(repo)}
                    sx={{
                      borderRadius: 1,
                      mb: 1,
                      '&.Mui-selected': {
                        bgcolor: 'primary.light',
                        '&:hover': {
                          bgcolor: 'primary.light',
                        },
                      },
                    }}
                  >
                    <ListItemAvatar>
                      <Avatar src={repo.owner.avatar_url} alt={repo.owner.login}>
                        <GitHubIcon />
                      </Avatar>
                    </ListItemAvatar>
                    
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle1" fontWeight="medium">
                            {repo.full_name}
                          </Typography>
                          <Chip
                            icon={repo.private ? <LockIcon /> : <PublicIcon />}
                            label={repo.private ? 'Private' : 'Public'}
                            size="small"
                            variant="outlined"
                            color={repo.private ? 'warning' : 'success'}
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          {repo.description && (
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                              {repo.description}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary">
                            Default branch: {repo.default_branch} • Updated {formatDate(repo.updated_at)}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                  <Divider variant="inset" component="li" />
                </React.Fragment>
              ))
            )}
          </List>
        )}

        {/* Selected Repository Details */}
        {selectedRepo && (
          <Box sx={{ mt: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1, border: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2" gutterBottom>
              Selected Repository:
            </Typography>
            <Typography variant="body1" fontWeight="medium">
              {selectedRepo.full_name}
            </Typography>
            {selectedRepo.description && (
              <Typography variant="body2" color="text.secondary">
                {selectedRepo.description}
              </Typography>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleCreateProject}
          disabled={!selectedRepo || creating}
          startIcon={creating ? <CircularProgress size={20} /> : <GitHubIcon />}
        >
          {creating ? 'Creating...' : 'Add Project'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

