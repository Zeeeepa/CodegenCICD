/**
 * Main Dashboard Layout Component
 */

import React, { useState } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Divider,
  Container,
  Grid,
  Fab,
  Badge,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Folder as ProjectIcon,
  PlayArrow as RunIcon,
  Settings as SettingsIcon,
  Add as AddIcon,
  Wifi as ConnectedIcon,
  WifiOff as DisconnectedIcon,
  GitHub as GitHubIcon,
} from '@mui/icons-material';

import { useDashboard } from '../../contexts/DashboardContext';
import ProjectGrid from '../Project/ProjectGrid';
import ProjectSelector from '../Navigation/ProjectSelector';
import CreateProjectDialog from '../Project/CreateProjectDialog';
import AgentRunDialog from '../AgentRun/AgentRunDialog';
import ConnectionStatus from '../Common/ConnectionStatus';

const DRAWER_WIDTH = 280;

const Dashboard: React.FC = () => {
  const { dashboardState, uiState, updateUIState } = useDashboard();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleTabChange = (tab: string) => {
    updateUIState({ selectedTab: tab });
  };

  const handleCreateProject = () => {
    updateUIState({
      dialogOpen: { ...uiState.dialogOpen, createProject: true }
    });
  };

  const sidebarItems = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <DashboardIcon />,
      badge: null,
    },
    {
      id: 'projects',
      label: 'Projects',
      icon: <ProjectIcon />,
      badge: dashboardState.projects.length,
    },
    {
      id: 'agent-runs',
      label: 'Agent Runs',
      icon: <RunIcon />,
      badge: dashboardState.agentRuns.filter(run => run.status === 'ACTIVE').length,
    },
    {
      id: 'github',
      label: 'GitHub Integration',
      icon: <GitHubIcon />,
      badge: null,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <SettingsIcon />,
      badge: null,
    },
  ];

  const drawer = (
    <Box>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
          CodegenCICD
        </Typography>
        <Typography variant="body2" color="text.secondary">
          AI-Powered CI/CD Dashboard
        </Typography>
      </Box>

      {/* Project Selector */}
      <Box sx={{ p: 2 }}>
        <ProjectSelector />
      </Box>

      <Divider />

      {/* Navigation Items */}
      <List>
        {sidebarItems.map((item) => (
          <ListItem key={item.id} disablePadding>
            <ListItemButton
              selected={uiState.selectedTab === item.id}
              onClick={() => handleTabChange(item.id)}
              sx={{
                mx: 1,
                borderRadius: 1,
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'primary.contrastText',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                  '& .MuiListItemIcon-root': {
                    color: 'primary.contrastText',
                  },
                },
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
              {item.badge !== null && item.badge > 0 && (
                <Badge badgeContent={item.badge} color="secondary" />
              )}
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      <Divider />

      {/* Connection Status */}
      <Box sx={{ p: 2 }}>
        <ConnectionStatus />
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { sm: `${DRAWER_WIDTH}px` },
          backgroundColor: 'background.paper',
          color: 'text.primary',
          boxShadow: 1,
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {uiState.selectedTab.charAt(0).toUpperCase() + uiState.selectedTab.slice(1)}
          </Typography>

          {/* Status Indicators */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {dashboardState.activeAgentRun && (
              <Chip
                label={`Agent Running: ${dashboardState.activeAgentRun.status}`}
                color="primary"
                size="small"
                icon={<RunIcon />}
              />
            )}
            
            <IconButton color="inherit">
              {dashboardState.websocketConnected ? (
                <ConnectedIcon color="success" />
              ) : (
                <DisconnectedIcon color="error" />
              )}
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
      <Box
        component="nav"
        sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile.
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          mt: 8, // Account for AppBar height
        }}
      >
        <Container maxWidth="xl">
          {/* Content based on selected tab */}
          {uiState.selectedTab === 'overview' && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h4" gutterBottom>
                  Welcome to CodegenCICD Dashboard
                </Typography>
                <Typography variant="body1" color="text.secondary" paragraph>
                  Manage your AI-powered CI/CD workflows with Codegen integration.
                  Create projects, run agents, and track progress in real-time.
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <ProjectGrid />
              </Grid>
            </Grid>
          )}

          {uiState.selectedTab === 'projects' && (
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4">
                  Projects ({dashboardState.projects.length})
                </Typography>
                <Fab
                  color="primary"
                  aria-label="add project"
                  onClick={handleCreateProject}
                  size="medium"
                >
                  <AddIcon />
                </Fab>
              </Box>
              <ProjectGrid />
            </Box>
          )}

          {uiState.selectedTab === 'agent-runs' && (
            <Box>
              <Typography variant="h4" gutterBottom>
                Agent Runs
              </Typography>
              <Typography variant="body1" color="text.secondary" paragraph>
                Monitor and manage your Codegen agent runs.
              </Typography>
              {/* Agent runs content will be implemented */}
            </Box>
          )}

          {uiState.selectedTab === 'github' && (
            <Box>
              <Typography variant="h4" gutterBottom>
                GitHub Integration
              </Typography>
              <Typography variant="body1" color="text.secondary" paragraph>
                Manage GitHub repositories, PRs, and webhooks.
              </Typography>
              {/* GitHub integration content will be implemented */}
            </Box>
          )}

          {uiState.selectedTab === 'settings' && (
            <Box>
              <Typography variant="h4" gutterBottom>
                Settings
              </Typography>
              <Typography variant="body1" color="text.secondary" paragraph>
                Configure your dashboard preferences and integrations.
              </Typography>
              {/* Settings content will be implemented */}
            </Box>
          )}
        </Container>
      </Box>

      {/* Dialogs */}
      <CreateProjectDialog />
      <AgentRunDialog />
    </Box>
  );
};

export default Dashboard;
