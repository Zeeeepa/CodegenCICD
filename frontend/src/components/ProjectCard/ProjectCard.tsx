import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  IconButton,
  Box,
  Chip,
  Menu,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Badge,
  Tooltip,
  LinearProgress,
  Alert
} from '@mui/material';
import {
  Settings as SettingsIcon,
  PlayArrow as PlayIcon,
  GitHub as GitHubIcon,
  MoreVert as MoreVertIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Code as CodeIcon
} from '@mui/icons-material';
import { Project, AgentRun, AgentRunStatus, PullRequest } from '../../types';
import { useApp } from '../../contexts/AppContext';
import { apiService } from '../../services/api';
import AgentRunDialog from '../AgentRunDialog/AgentRunDialog';
import SettingsDialog from '../SettingsDialog/SettingsDialog';

interface ProjectCardProps {
  project: Project;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ project }) => {
  const { state, updateProject, loadAgentRuns } = useApp();
  const { agentRuns } = state;

  // Local state
  const [agentRunDialogOpen, setAgentRunDialogOpen] = useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [currentAgentRun, setCurrentAgentRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(false);

  // Get project-specific agent runs
  const projectAgentRuns = agentRuns.filter(run => run.project_id === project.id);
  const latestAgentRun = projectAgentRuns.sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )[0];

  // Load pull requests and agent runs on mount
  useEffect(() => {
    loadPullRequests();
    loadAgentRuns(project.id);
  }, [project.id]);

  const loadPullRequests = async () => {
    try {
      const prs = await apiService.getPullRequests(project.id);
      setPullRequests(prs);
    } catch (error) {
      console.error('Failed to load pull requests:', error);
    }
  };

  const handleAgentRunClick = () => {
    setAgentRunDialogOpen(true);
  };

  const handleSettingsClick = () => {
    setSettingsDialogOpen(true);
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleAutoConfirmToggle = async () => {
    try {
      await updateProject(project.id, {
        auto_confirm_plan: !project.auto_confirm_plan
      });
    } catch (error) {
      console.error('Failed to update auto-confirm setting:', error);
    }
  };

  const handleAutoMergeToggle = async () => {
    try {
      await updateProject(project.id, {
        auto_merge_validated_pr: !project.auto_merge_validated_pr
      });
    } catch (error) {
      console.error('Failed to update auto-merge setting:', error);
    }
  };

  const handleDeleteProject = async () => {
    if (window.confirm(`Are you sure you want to delete project "${project.name}"?`)) {
      try {
        // This would be handled by the parent component or context
        console.log('Delete project:', project.id);
      } catch (error) {
        console.error('Failed to delete project:', error);
      }
    }
    handleMenuClose();
  };

  const getStatusColor = (status: AgentRunStatus) => {
    switch (status) {
      case AgentRunStatus.COMPLETED:
        return 'success';
      case AgentRunStatus.RUNNING:
        return 'primary';
      case AgentRunStatus.FAILED:
        return 'error';
      case AgentRunStatus.PENDING:
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: AgentRunStatus) => {
    switch (status) {
      case AgentRunStatus.COMPLETED:
        return <CheckCircleIcon fontSize="small" />;
      case AgentRunStatus.RUNNING:
        return <ScheduleIcon fontSize="small" />;
      case AgentRunStatus.FAILED:
        return <ErrorIcon fontSize="small" />;
      default:
        return <ScheduleIcon fontSize="small" />;
    }
  };

  const hasRepositoryRules = project.configuration?.repository_rules?.trim();
  const hasSetupCommands = project.configuration?.setup_commands?.trim();
  const hasSecrets = project.configuration?.secrets && project.configuration.secrets.length > 0;

  return (
    <>
      <Card 
        sx={{ 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column',
          position: 'relative',
          border: hasRepositoryRules ? '2px solid' : '1px solid',
          borderColor: hasRepositoryRules ? 'primary.main' : 'divider',
          '&:hover': {
            boxShadow: 4,
            transform: 'translateY(-2px)',
            transition: 'all 0.2s ease-in-out'
          }
        }}
      >
        {/* Loading Progress */}
        {loading && (
          <LinearProgress 
            sx={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              right: 0,
              zIndex: 1
            }} 
          />
        )}

        <CardContent sx={{ flexGrow: 1, pb: 1 }}>
          {/* Header */}
          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
            <Typography variant="h6" component="h2" noWrap sx={{ flexGrow: 1, mr: 1 }}>
              {project.name}
            </Typography>
            
            <Box display="flex" alignItems="center">
              {/* Pull Request Badge */}
              {pullRequests.length > 0 && (
                <Tooltip title={`${pullRequests.length} open PR(s)`}>
                  <Badge badgeContent={pullRequests.length} color="primary">
                    <IconButton
                      size="small"
                      component="a"
                      href={`https://github.com/${project.github_repository}/pulls`}
                      target="_blank"
                      sx={{ mr: 1 }}
                    >
                      <GitHubIcon fontSize="small" />
                    </IconButton>
                  </Badge>
                </Tooltip>
              )}

              {/* Settings */}
              <IconButton
                size="small"
                onClick={handleSettingsClick}
                sx={{ mr: 1 }}
              >
                <SettingsIcon fontSize="small" />
              </IconButton>

              {/* Menu */}
              <IconButton size="small" onClick={handleMenuClick}>
                <MoreVertIcon fontSize="small" />
              </IconButton>
            </Box>
          </Box>

          {/* Description */}
          {project.description && (
            <Typography 
              variant="body2" 
              color="text.secondary" 
              sx={{ mb: 2, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
            >
              {project.description}
            </Typography>
          )}

          {/* Repository Info */}
          <Box display="flex" alignItems="center" mb={2}>
            <GitHubIcon fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary" noWrap>
              {project.github_repository}
            </Typography>
          </Box>

          {/* Configuration Indicators */}
          <Box display="flex" flexWrap="wrap" gap={0.5} mb={2}>
            {hasRepositoryRules && (
              <Chip 
                label="Rules" 
                size="small" 
                color="primary" 
                variant="outlined"
              />
            )}
            {hasSetupCommands && (
              <Chip 
                label="Setup" 
                size="small" 
                color="secondary" 
                variant="outlined"
              />
            )}
            {hasSecrets && (
              <Chip 
                label="Secrets" 
                size="small" 
                color="warning" 
                variant="outlined"
              />
            )}
          </Box>

          {/* Latest Agent Run Status */}
          {latestAgentRun && (
            <Box display="flex" alignItems="center" mb={2}>
              <Chip
                icon={getStatusIcon(latestAgentRun.status)}
                label={`Last run: ${latestAgentRun.status}`}
                color={getStatusColor(latestAgentRun.status)}
                size="small"
                variant="outlined"
              />
            </Box>
          )}

          {/* Auto Settings */}
          <Box>
            <FormControlLabel
              control={
                <Checkbox
                  checked={project.auto_confirm_plan}
                  onChange={handleAutoConfirmToggle}
                  size="small"
                />
              }
              label={
                <Typography variant="caption">
                  Auto-confirm Plan
                </Typography>
              }
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={project.auto_merge_validated_pr}
                  onChange={handleAutoMergeToggle}
                  size="small"
                />
              }
              label={
                <Typography variant="caption">
                  Auto-merge Validated PR
                </Typography>
              }
            />
          </Box>
        </CardContent>

        <CardActions sx={{ pt: 0, px: 2, pb: 2 }}>
          <Button
            variant="contained"
            startIcon={<PlayIcon />}
            onClick={handleAgentRunClick}
            fullWidth
            disabled={loading}
          >
            Agent Run
          </Button>
        </CardActions>

        {/* Menu */}
        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={handleMenuClose}
        >
          <MenuItem onClick={() => {
            window.open(`https://github.com/${project.github_repository}`, '_blank');
            handleMenuClose();
          }}>
            <GitHubIcon sx={{ mr: 1 }} fontSize="small" />
            View Repository
          </MenuItem>
          <MenuItem onClick={() => {
            window.open(`https://github.com/${project.github_repository}/pulls`, '_blank');
            handleMenuClose();
          }}>
            <CodeIcon sx={{ mr: 1 }} fontSize="small" />
            View Pull Requests
          </MenuItem>
          <MenuItem onClick={handleDeleteProject} sx={{ color: 'error.main' }}>
            <ErrorIcon sx={{ mr: 1 }} fontSize="small" />
            Delete Project
          </MenuItem>
        </Menu>
      </Card>

      {/* Agent Run Dialog */}
      <AgentRunDialog
        open={agentRunDialogOpen}
        onClose={() => setAgentRunDialogOpen(false)}
        project={project}
        currentRun={currentAgentRun}
      />

      {/* Settings Dialog */}
      <SettingsDialog
        open={settingsDialogOpen}
        onClose={() => setSettingsDialogOpen(false)}
        project={project}
      />
    </>
  );
};

export default ProjectCard;
