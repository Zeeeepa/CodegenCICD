import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  IconButton,
  Menu,
  MenuItem,
  LinearProgress,
  Badge,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Settings as SettingsIcon,
  MoreVert as MoreVertIcon,
  GitHub as GitHubIcon,
  AutoMode as AutoModeIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
} from '@mui/icons-material';
import { Project, AgentRun, agentRunsApi } from '../services/api';
import { useAgentRunUpdates, useValidationUpdates } from '../hooks/useWebSocket';
import AgentRunDialog from './AgentRunDialog';

interface ProjectCardProps {
  project: Project;
  isSelected: boolean;
  onSelect: () => void;
  onUpdate: (data: Partial<Project>) => void;
  onDelete: () => void;
  onOpenConfig: () => void;
}

const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  isSelected,
  onSelect,
  onUpdate,
  onDelete,
  onOpenConfig,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [agentRunDialogOpen, setAgentRunDialogOpen] = useState(false);
  const [currentAgentRuns, setCurrentAgentRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(false);

  // WebSocket hooks for real-time updates
  const agentRunUpdates = useAgentRunUpdates(project.id);
  const validationUpdates = useValidationUpdates();

  // Load current agent runs
  useEffect(() => {
    loadAgentRuns();
  }, [project.id]);

  // Update agent runs from WebSocket
  useEffect(() => {
    if (agentRunUpdates.length > 0) {
      setCurrentAgentRuns(prev => {
        const updated = [...prev];
        agentRunUpdates.forEach(update => {
          const index = updated.findIndex(run => run.id === update.id);
          if (index >= 0) {
            updated[index] = { ...updated[index], ...update };
          } else if (update.project_id === project.id) {
            updated.push(update);
          }
        });
        return updated;
      });
    }
  }, [agentRunUpdates, project.id]);

  const loadAgentRuns = async () => {
    try {
      const response = await agentRunsApi.getByProject(project.id);
      setCurrentAgentRuns(response.data);
    } catch (error) {
      console.error('Failed to load agent runs:', error);
    }
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleAgentRunStart = () => {
    setAgentRunDialogOpen(true);
  };

  const handleAgentRunCreate = async (data: { target_text: string; planning_statement?: string }) => {
    try {
      setLoading(true);
      await agentRunsApi.create({
        project_id: project.id,
        ...data,
      });
      setAgentRunDialogOpen(false);
      await loadAgentRuns();
    } catch (error) {
      console.error('Failed to create agent run:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAutoMerge = () => {
    onUpdate({ auto_merge_enabled: !project.auto_merge_enabled });
  };

  const handleToggleAutoConfirm = () => {
    onUpdate({ auto_confirm_plans: !project.auto_confirm_plans });
  };

  // Get current status
  const runningRuns = currentAgentRuns.filter(run => run.status === 'running');
  const pendingRuns = currentAgentRuns.filter(run => run.status === 'pending');
  const recentPRs = currentAgentRuns.filter(run => run.pr_number && run.pr_url);
  const hasRepositoryRules = false; // This would come from configuration
  const hasErrors = currentAgentRuns.some(run => run.status === 'failed');

  const getStatusColor = () => {
    if (hasErrors) return 'error';
    if (runningRuns.length > 0) return 'warning';
    if (pendingRuns.length > 0) return 'info';
    return 'success';
  };

  const getStatusIcon = () => {
    if (hasErrors) return <ErrorIcon />;
    if (runningRuns.length > 0) return <PendingIcon />;
    return <CheckCircleIcon />;
  };

  return (
    <>
      <Card
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          border: isSelected ? 2 : 1,
          borderColor: isSelected ? 'primary.main' : 'divider',
          cursor: 'pointer',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            elevation: 4,
            transform: 'translateY(-2px)',
          },
          backgroundColor: hasRepositoryRules ? 'action.hover' : 'background.paper',
        }}
        onClick={onSelect}
      >
        <CardContent sx={{ flexGrow: 1, pb: 1 }}>
          {/* Header */}
          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
            <Typography variant="h6" component="h2" noWrap sx={{ flexGrow: 1, mr: 1 }}>
              {project.name}
            </Typography>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                handleMenuClick(e);
              }}
            >
              <MoreVertIcon />
            </IconButton>
          </Box>

          {/* Repository Info */}
          <Box display="flex" alignItems="center" mb={2}>
            <GitHubIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary" noWrap>
              {project.github_owner}/{project.github_repo}
            </Typography>
          </Box>

          {/* Status Indicators */}
          <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
            <Chip
              icon={getStatusIcon()}
              label={project.status}
              color={getStatusColor()}
              size="small"
            />
            
            {project.auto_merge_enabled && (
              <Chip
                icon={<AutoModeIcon />}
                label="Auto-merge"
                color="primary"
                size="small"
                variant="outlined"
              />
            )}
            
            {project.auto_confirm_plans && (
              <Chip
                label="Auto-confirm"
                color="secondary"
                size="small"
                variant="outlined"
              />
            )}
          </Box>

          {/* Progress Indicators */}
          {runningRuns.length > 0 && (
            <Box mb={2}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Agent runs in progress: {runningRuns.length}
              </Typography>
              <LinearProgress />
            </Box>
          )}

          {/* Recent Activity */}
          {recentPRs.length > 0 && (
            <Box mb={1}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Recent PRs:
              </Typography>
              {recentPRs.slice(0, 2).map((run) => (
                <Box key={run.id} display="flex" alignItems="center" mb={0.5}>
                  <Badge
                    badgeContent={run.pr_number}
                    color="primary"
                    sx={{ mr: 1 }}
                  >
                    <GitHubIcon sx={{ fontSize: 16 }} />
                  </Badge>
                  <Typography variant="body2" noWrap sx={{ flexGrow: 1 }}>
                    {run.target_text.substring(0, 30)}...
                  </Typography>
                </Box>
              ))}
            </Box>
          )}

          {/* Error Messages */}
          {hasErrors && (
            <Alert severity="error" sx={{ mt: 1 }}>
              Some agent runs have failed. Check logs for details.
            </Alert>
          )}
        </CardContent>

        <CardActions sx={{ pt: 0, px: 2, pb: 2 }}>
          <Button
            variant="contained"
            startIcon={<PlayIcon />}
            onClick={(e) => {
              e.stopPropagation();
              handleAgentRunStart();
            }}
            disabled={loading}
            fullWidth
          >
            Agent Run
          </Button>
        </CardActions>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => { handleMenuClose(); onOpenConfig(); }}>
          <SettingsIcon sx={{ mr: 1 }} />
          Settings
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); handleToggleAutoMerge(); }}>
          <AutoModeIcon sx={{ mr: 1 }} />
          {project.auto_merge_enabled ? 'Disable' : 'Enable'} Auto-merge
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); handleToggleAutoConfirm(); }}>
          <CheckCircleIcon sx={{ mr: 1 }} />
          {project.auto_confirm_plans ? 'Disable' : 'Enable'} Auto-confirm
        </MenuItem>
        <MenuItem onClick={() => { handleMenuClose(); onDelete(); }} sx={{ color: 'error.main' }}>
          Delete Project
        </MenuItem>
      </Menu>

      {/* Agent Run Dialog */}
      <AgentRunDialog
        open={agentRunDialogOpen}
        onClose={() => setAgentRunDialogOpen(false)}
        onSubmit={handleAgentRunCreate}
        project={project}
        loading={loading}
      />
    </>
  );
};

export default ProjectCard;
