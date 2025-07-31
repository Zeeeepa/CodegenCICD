/**
 * Project Selector Dialog Component
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Autocomplete,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemButton,
  Divider
} from '@mui/material';
import {
  GitHub as GitHubIcon,
  Search as SearchIcon,
  Star as StarIcon,
  ForkRight as ForkIcon,
  Update as UpdateIcon
} from '@mui/icons-material';

import { githubService } from '../services/githubService';
import { useProjectActions } from '../store/projectStore';
import { Project } from '../types/cicd';

// ============================================================================
// INTERFACES
// ============================================================================

interface ProjectSelectorProps {
  open: boolean;
  onClose: () => void;
  onProjectAdded: (project: Project) => void;
}

interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  description: string;
  html_url: string;
  clone_url: string;
  default_branch: string;
  stargazers_count: number;
  forks_count: number;
  updated_at: string;
  language: string;
  owner: {
    login: string;
    avatar_url: string;
  };
}

// ============================================================================
// COMPONENT
// ============================================================================

export const ProjectSelector: React.FC<ProjectSelectorProps> = ({
  open,
  onClose,
  onProjectAdded
}) => {
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [repositories, setRepositories] = useState<GitHubRepo[]>([]);
  const [userRepos, setUserRepos] = useState<GitHubRepo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'user' | 'search'>('user');

  // Actions
  const { createProject } = useProjectActions();

  // ========================================================================
  // EFFECTS
  // ========================================================================

  // Load user repositories when dialog opens
  useEffect(() => {
    if (open && tab === 'user') {
      loadUserRepositories();
    }
  }, [open, tab]);

  // Search repositories when query changes
  useEffect(() => {
    if (searchQuery.trim() && tab === 'search') {
      const timeoutId = setTimeout(() => {
        searchRepositories(searchQuery);
      }, 500);

      return () => clearTimeout(timeoutId);
    } else {
      setRepositories([]);
    }
  }, [searchQuery, tab]);

  // ========================================================================
  // HANDLERS
  // ========================================================================

  const loadUserRepositories = async () => {
    setLoading(true);
    setError(null);

    try {
      const repos = await githubService.getUserRepositories();
      setUserRepos(repos);
    } catch (error) {
      setError('Failed to load your repositories. Please check your GitHub token.');
      console.error('Failed to load user repositories:', error);
    } finally {
      setLoading(false);
    }
  };

  const searchRepositories = async (query: string) => {
    setSearching(true);
    setError(null);

    try {
      const result = await githubService.searchRepositories(query);
      setRepositories(result.items || []);
    } catch (error) {
      setError('Failed to search repositories. Please try again.');
      console.error('Failed to search repositories:', error);
    } finally {
      setSearching(false);
    }
  };

  const handleAddProject = async () => {
    if (!selectedRepo) return;

    setLoading(true);
    setError(null);

    try {
      const project = await createProject(selectedRepo.full_name);
      onProjectAdded(project);
      handleClose();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to add project');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSearchQuery('');
    setSelectedRepo(null);
    setError(null);
    setRepositories([]);
    onClose();
  };

  const handleRepoSelect = (repo: GitHubRepo) => {
    setSelectedRepo(repo);
  };

  // ========================================================================
  // RENDER HELPERS
  // ========================================================================

  const renderRepositoryList = (repos: GitHubRepo[]) => {
    if (repos.length === 0) {
      return (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body2" color="text.secondary">
            {tab === 'user' ? 'No repositories found in your account' : 'No repositories found for this search'}
          </Typography>
        </Box>
      );
    }

    return (
      <List sx={{ maxHeight: 400, overflow: 'auto' }}>
        {repos.map((repo, index) => (
          <React.Fragment key={repo.id}>
            <ListItemButton
              selected={selectedRepo?.id === repo.id}
              onClick={() => handleRepoSelect(repo)}
            >
              <ListItemAvatar>
                <Avatar src={repo.owner.avatar_url} sx={{ width: 40, height: 40 }}>
                  <GitHubIcon />
                </Avatar>
              </ListItemAvatar>
              
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle1" component="span">
                      {repo.full_name}
                    </Typography>
                    {repo.language && (
                      <Chip label={repo.language} size="small" variant="outlined" />
                    )}
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {repo.description || 'No description available'}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <StarIcon sx={{ fontSize: 16 }} />
                        <Typography variant="caption">
                          {repo.stargazers_count}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <ForkIcon sx={{ fontSize: 16 }} />
                        <Typography variant="caption">
                          {repo.forks_count}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <UpdateIcon sx={{ fontSize: 16 }} />
                        <Typography variant="caption">
                          {new Date(repo.updated_at).toLocaleDateString()}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                }
              />
            </ListItemButton>
            {index < repos.length - 1 && <Divider />}
          </React.Fragment>
        ))}
      </List>
    );
  };

  const renderTabButtons = () => (
    <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
      <Button
        variant={tab === 'user' ? 'contained' : 'outlined'}
        onClick={() => setTab('user')}
        size="small"
      >
        Your Repositories
      </Button>
      <Button
        variant={tab === 'search' ? 'contained' : 'outlined'}
        onClick={() => setTab('search')}
        size="small"
      >
        Search GitHub
      </Button>
    </Box>
  );

  const renderSearchField = () => {
    if (tab !== 'search') return null;

    return (
      <TextField
        fullWidth
        placeholder="Search repositories (e.g., 'react typescript')"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        InputProps={{
          startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
        }}
        sx={{ mb: 2 }}
      />
    );
  };

  const renderSelectedRepoInfo = () => {
    if (!selectedRepo) return null;

    return (
      <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
        <Typography variant="subtitle2" gutterBottom>
          Selected Repository:
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar src={selectedRepo.owner.avatar_url} sx={{ width: 32, height: 32 }} />
          <Box>
            <Typography variant="body1" fontWeight="medium">
              {selectedRepo.full_name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Default branch: {selectedRepo.default_branch}
            </Typography>
          </Box>
        </Box>
      </Box>
    );
  };

  // ========================================================================
  // RENDER
  // ========================================================================

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: 600 }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <GitHubIcon />
          Add GitHub Repository
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* Tab Buttons */}
        {renderTabButtons()}

        {/* Search Field */}
        {renderSearchField()}

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Loading Indicator */}
        {(loading || searching) && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}

        {/* Repository List */}
        {!loading && !searching && (
          <>
            {tab === 'user' && renderRepositoryList(userRepos)}
            {tab === 'search' && renderRepositoryList(repositories)}
          </>
        )}

        {/* Selected Repository Info */}
        {renderSelectedRepoInfo()}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>
          Cancel
        </Button>
        <Button
          onClick={handleAddProject}
          variant="contained"
          disabled={!selectedRepo || loading}
          startIcon={loading ? <CircularProgress size={16} /> : <GitHubIcon />}
        >
          {loading ? 'Adding...' : 'Add Project'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
