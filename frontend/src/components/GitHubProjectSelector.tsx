import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemButton,
  Avatar,
  Chip,
  CircularProgress,
  Alert,
  InputAdornment,
  Divider,
  FormControlLabel,
  Switch
} from '@mui/material';
import {
  Search as SearchIcon,
  GitHub as GitHubIcon,
  Star as StarIcon,
  Lock as LockIcon,
  Public as PublicIcon,
  Add as AddIcon
} from '@mui/icons-material';

interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  owner: string;
  description: string;
  private: boolean;
  clone_url: string;
  html_url: string;
  default_branch: string;
  updated_at: string;
  language: string;
  topics: string[];
  stars?: number;
  forks?: number;
}

interface GitHubProjectSelectorProps {
  open: boolean;
  onClose: () => void;
  onSelectProject: (repository: GitHubRepository, options: ProjectOptions) => Promise<void>;
}

interface ProjectOptions {
  validation_enabled: boolean;
  auto_merge_enabled: boolean;
  auto_confirm_plans: boolean;
}

const GitHubProjectSelector: React.FC<GitHubProjectSelectorProps> = ({
  open,
  onClose,
  onSelectProject
}) => {
  const [repositories, setRepositories] = useState<GitHubRepository[]>([]);
  const [filteredRepositories, setFilteredRepositories] = useState<GitHubRepository[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepository | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Project options
  const [validationEnabled, setValidationEnabled] = useState(true);
  const [autoMergeEnabled, setAutoMergeEnabled] = useState(false);
  const [autoConfirmPlans, setAutoConfirmPlans] = useState(true);

  useEffect(() => {
    if (open) {
      fetchRepositories();
    }
  }, [open]);

  useEffect(() => {
    // Filter repositories based on search query
    if (!searchQuery.trim()) {
      setFilteredRepositories(repositories);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = repositories.filter(repo =>
        repo.name.toLowerCase().includes(query) ||
        repo.full_name.toLowerCase().includes(query) ||
        repo.description?.toLowerCase().includes(query) ||
        repo.language?.toLowerCase().includes(query) ||
        repo.topics.some(topic => topic.toLowerCase().includes(query))
      );
      setFilteredRepositories(filtered);
    }
  }, [searchQuery, repositories]);

  const fetchRepositories = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/github/repositories');
      if (!response.ok) {
        throw new Error(`Failed to fetch repositories: ${response.status}`);
      }
      
      const data = await response.json();
      setRepositories(data.repositories || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch repositories');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRepository = (repository: GitHubRepository) => {
    setSelectedRepo(repository);
  };

  const handleConfirmSelection = async () => {
    if (!selectedRepo) return;

    const options: ProjectOptions = {
      validation_enabled: validationEnabled,
      auto_merge_enabled: autoMergeEnabled,
      auto_confirm_plans: autoConfirmPlans
    };

    try {
      await onSelectProject(selectedRepo, options);
      onClose();
      setSelectedRepo(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to add project');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getLanguageColor = (language: string) => {
    const colors: Record<string, string> = {
      'JavaScript': '#f1e05a',
      'TypeScript': '#2b7489',
      'Python': '#3572A5',
      'Java': '#b07219',
      'Go': '#00ADD8',
      'Rust': '#dea584',
      'C++': '#f34b7d',
      'C#': '#239120',
      'PHP': '#4F5D95',
      'Ruby': '#701516',
      'Swift': '#ffac45',
      'Kotlin': '#F18E33'
    };
    return colors[language] || '#586069';
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="md" 
      fullWidth
      PaperProps={{
        sx: { minHeight: '700px' }
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <GitHubIcon />
          <Typography variant="h6">
            Select GitHub Project
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box display="flex" flexDirection="column" gap={3}>
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
              )
            }}
          />

          {/* Error Alert */}
          {error && (
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* Loading */}
          {loading && (
            <Box display="flex" justifyContent="center" p={3}>
              <CircularProgress />
            </Box>
          )}

          {/* Repository List */}
          {!loading && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Available Repositories ({filteredRepositories.length})
              </Typography>
              
              {filteredRepositories.length === 0 ? (
                <Alert severity="info">
                  {repositories.length === 0 
                    ? "No repositories found. Make sure your GitHub token has the correct permissions."
                    : "No repositories match your search criteria."
                  }
                </Alert>
              ) : (
                <List sx={{ maxHeight: '300px', overflow: 'auto' }}>
                  {filteredRepositories.map((repo) => (
                    <ListItem key={repo.id} disablePadding>
                      <ListItemButton
                        selected={selectedRepo?.id === repo.id}
                        onClick={() => handleSelectRepository(repo)}
                        sx={{
                          border: selectedRepo?.id === repo.id ? 2 : 1,
                          borderColor: selectedRepo?.id === repo.id ? 'primary.main' : 'divider',
                          borderRadius: 1,
                          mb: 1
                        }}
                      >
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: 'primary.main' }}>
                            {repo.private ? <LockIcon /> : <PublicIcon />}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="body1" fontWeight="medium">
                                {repo.full_name}
                              </Typography>
                              {repo.private && (
                                <Chip label="Private" size="small" color="warning" />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary" gutterBottom>
                                {repo.description || 'No description available'}
                              </Typography>
                              <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
                                {repo.language && (
                                  <Box display="flex" alignItems="center" gap={0.5}>
                                    <Box
                                      sx={{
                                        width: 12,
                                        height: 12,
                                        borderRadius: '50%',
                                        bgcolor: getLanguageColor(repo.language)
                                      }}
                                    />
                                    <Typography variant="caption">
                                      {repo.language}
                                    </Typography>
                                  </Box>
                                )}
                                {repo.stars !== undefined && (
                                  <Box display="flex" alignItems="center" gap={0.5}>
                                    <StarIcon sx={{ fontSize: 14 }} />
                                    <Typography variant="caption">
                                      {repo.stars}
                                    </Typography>
                                  </Box>
                                )}
                                <Typography variant="caption" color="text.secondary">
                                  Updated {formatDate(repo.updated_at)}
                                </Typography>
                              </Box>
                              {repo.topics.length > 0 && (
                                <Box display="flex" gap={0.5} mt={1} flexWrap="wrap">
                                  {repo.topics.slice(0, 3).map((topic) => (
                                    <Chip
                                      key={topic}
                                      label={topic}
                                      size="small"
                                      variant="outlined"
                                      sx={{ fontSize: '0.7rem', height: '20px' }}
                                    />
                                  ))}
                                  {repo.topics.length > 3 && (
                                    <Typography variant="caption" color="text.secondary">
                                      +{repo.topics.length - 3} more
                                    </Typography>
                                  )}
                                </Box>
                              )}
                            </Box>
                          }
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>
          )}

          {/* Project Configuration */}
          {selectedRepo && (
            <>
              <Divider />
              <Box>
                <Typography variant="h6" gutterBottom>
                  Project Configuration
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Configure how this project will behave in the dashboard.
                </Typography>
                
                <Box display="flex" flexDirection="column" gap={2} mt={2}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={validationEnabled}
                        onChange={(e) => setValidationEnabled(e.target.checked)}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">Enable Validation Pipeline</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Run comprehensive validation when PRs are created
                        </Typography>
                      </Box>
                    }
                  />
                  
                  <FormControlLabel
                    control={
                      <Switch
                        checked={autoConfirmPlans}
                        onChange={(e) => setAutoConfirmPlans(e.target.checked)}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">Auto-Confirm Plans</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Automatically confirm agent-generated plans without manual approval
                        </Typography>
                      </Box>
                    }
                  />
                  
                  <FormControlLabel
                    control={
                      <Switch
                        checked={autoMergeEnabled}
                        onChange={(e) => setAutoMergeEnabled(e.target.checked)}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">Auto-Merge Validated PRs</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Automatically merge PRs that pass all validation checks
                        </Typography>
                      </Box>
                    }
                  />
                </Box>
              </Box>
            </>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirmSelection}
          disabled={!selectedRepo}
          startIcon={<AddIcon />}
        >
          Add Project to Dashboard
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default GitHubProjectSelector;

