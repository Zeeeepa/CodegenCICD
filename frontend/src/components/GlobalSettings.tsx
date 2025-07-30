/**
 * Global Settings Component - System-wide configuration dialog
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Switch,
  FormControlLabel,
  TextField,
  Divider,
  Alert,
  Tabs,
  Tab,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Notifications as NotificationsIcon,
  Storage as StorageIcon,
  Close as CloseIcon
} from '@mui/icons-material';

import { SystemHealth } from '../types/cicd';
import { apiClient } from '../services/api';

interface GlobalSettingsProps {
  open: boolean;
  onClose: () => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export const GlobalSettings: React.FC<GlobalSettingsProps> = ({
  open,
  onClose
}) => {
  const [tabValue, setTabValue] = useState(0);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Settings state
  const [settings, setSettings] = useState({
    autoRefresh: true,
    refreshInterval: 30,
    notifications: true,
    darkMode: false,
    compactView: false,
    showSystemStats: true,
    maxConcurrentRuns: 5,
    defaultTimeout: 300,
    enableWebhooks: true,
    enableAutoMerge: false
  });

  useEffect(() => {
    if (open) {
      loadSystemHealth();
      loadSettings();
    }
  }, [open]);

  const loadSystemHealth = async () => {
    try {
      const health = await apiClient.getHealth();
      setSystemHealth(health);
    } catch (err) {
      console.error('Failed to load system health:', err);
    }
  };

  const loadSettings = () => {
    // Load settings from localStorage or API
    const savedSettings = localStorage.getItem('cicd-dashboard-settings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setSettings(prev => ({ ...prev, ...parsed }));
      } catch (err) {
        console.error('Failed to parse saved settings:', err);
      }
    }
  };

  const saveSettings = () => {
    localStorage.setItem('cicd-dashboard-settings', JSON.stringify(settings));
    onClose();
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const getServiceStatusColor = (status: boolean) => {
    return status ? 'success' : 'error';
  };

  const getServiceStatusText = (status: boolean) => {
    return status ? 'Healthy' : 'Unhealthy';
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { height: '80vh' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SettingsIcon />
            <Typography variant="h6">
              Global Settings
            </Typography>
          </Box>
          <Button onClick={onClose} color="inherit">
            <CloseIcon />
          </Button>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ p: 0 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="General" icon={<SettingsIcon />} />
            <Tab label="System Health" icon={<StorageIcon />} />
            <Tab label="Notifications" icon={<NotificationsIcon />} />
            <Tab label="Security" icon={<SecurityIcon />} />
          </Tabs>
        </Box>

        {/* General Settings */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>
            General Settings
          </Typography>
          
          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.autoRefresh}
                  onChange={(e) => handleSettingChange('autoRefresh', e.target.checked)}
                />
              }
              label="Enable auto-refresh"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
              Automatically refresh project data every few seconds
            </Typography>
          </Box>

          <Box sx={{ mb: 3 }}>
            <TextField
              label="Refresh Interval (seconds)"
              type="number"
              value={settings.refreshInterval}
              onChange={(e) => handleSettingChange('refreshInterval', parseInt(e.target.value))}
              disabled={!settings.autoRefresh}
              inputProps={{ min: 10, max: 300 }}
              sx={{ width: 200 }}
            />
          </Box>

          <Divider sx={{ my: 3 }} />

          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.compactView}
                  onChange={(e) => handleSettingChange('compactView', e.target.checked)}
                />
              }
              label="Compact view"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
              Show more projects in less space
            </Typography>
          </Box>

          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.showSystemStats}
                  onChange={(e) => handleSettingChange('showSystemStats', e.target.checked)}
                />
              }
              label="Show system statistics"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
              Display system-wide statistics in the dashboard header
            </Typography>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Box sx={{ mb: 3 }}>
            <TextField
              label="Max Concurrent Runs"
              type="number"
              value={settings.maxConcurrentRuns}
              onChange={(e) => handleSettingChange('maxConcurrentRuns', parseInt(e.target.value))}
              inputProps={{ min: 1, max: 20 }}
              sx={{ width: 200, mr: 2 }}
            />
            <TextField
              label="Default Timeout (seconds)"
              type="number"
              value={settings.defaultTimeout}
              onChange={(e) => handleSettingChange('defaultTimeout', parseInt(e.target.value))}
              inputProps={{ min: 60, max: 3600 }}
              sx={{ width: 200 }}
            />
          </Box>
        </TabPanel>

        {/* System Health */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            System Health
          </Typography>

          {systemHealth && (
            <Box>
              <Paper sx={{ p: 2, mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Overall Status: 
                  <Chip 
                    label={systemHealth.status}
                    color={systemHealth.status === 'healthy' ? 'success' : 'error'}
                    sx={{ ml: 1 }}
                  />
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Uptime: {Math.floor(systemHealth.uptime / 3600)}h {Math.floor((systemHealth.uptime % 3600) / 60)}m
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Version: {systemHealth.version}
                </Typography>
              </Paper>

              <Typography variant="subtitle1" gutterBottom>
                Service Status
              </Typography>
              <List>
                <ListItem>
                  <ListItemText primary="Database" />
                  <ListItemSecondaryAction>
                    <Chip
                      label={getServiceStatusText(systemHealth.services.database)}
                      color={getServiceStatusColor(systemHealth.services.database)}
                      size="small"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="GitHub API" />
                  <ListItemSecondaryAction>
                    <Chip
                      label={getServiceStatusText(systemHealth.services.github)}
                      color={getServiceStatusColor(systemHealth.services.github)}
                      size="small"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="Codegen API" />
                  <ListItemSecondaryAction>
                    <Chip
                      label={getServiceStatusText(systemHealth.services.codegen)}
                      color={getServiceStatusColor(systemHealth.services.codegen)}
                      size="small"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="Grainchain" />
                  <ListItemSecondaryAction>
                    <Chip
                      label={getServiceStatusText(systemHealth.services.grainchain)}
                      color={getServiceStatusColor(systemHealth.services.grainchain)}
                      size="small"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="Web-Eval-Agent" />
                  <ListItemSecondaryAction>
                    <Chip
                      label={getServiceStatusText(systemHealth.services.web_eval_agent)}
                      color={getServiceStatusColor(systemHealth.services.web_eval_agent)}
                      size="small"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </Box>
          )}
        </TabPanel>

        {/* Notifications */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Notification Settings
          </Typography>

          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.notifications}
                  onChange={(e) => handleSettingChange('notifications', e.target.checked)}
                />
              }
              label="Enable notifications"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
              Show toast notifications for important events
            </Typography>
          </Box>

          <Alert severity="info" sx={{ mb: 2 }}>
            Browser notifications require permission. Click "Allow" when prompted.
          </Alert>

          <Typography variant="subtitle2" gutterBottom>
            Notification Types
          </Typography>
          <List>
            <ListItem>
              <ListItemText 
                primary="Agent Run Completion"
                secondary="Notify when agent runs complete successfully"
              />
              <ListItemSecondaryAction>
                <Switch defaultChecked />
              </ListItemSecondaryAction>
            </ListItem>
            <ListItem>
              <ListItemText 
                primary="Agent Run Failures"
                secondary="Notify when agent runs fail"
              />
              <ListItemSecondaryAction>
                <Switch defaultChecked />
              </ListItemSecondaryAction>
            </ListItem>
            <ListItem>
              <ListItemText 
                primary="Webhook Events"
                secondary="Notify on GitHub webhook events"
              />
              <ListItemSecondaryAction>
                <Switch defaultChecked />
              </ListItemSecondaryAction>
            </ListItem>
            <ListItem>
              <ListItemText 
                primary="System Alerts"
                secondary="Notify on system health issues"
              />
              <ListItemSecondaryAction>
                <Switch defaultChecked />
              </ListItemSecondaryAction>
            </ListItem>
          </List>
        </TabPanel>

        {/* Security */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>
            Security Settings
          </Typography>

          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enableWebhooks}
                  onChange={(e) => handleSettingChange('enableWebhooks', e.target.checked)}
                />
              }
              label="Enable webhooks"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
              Allow GitHub webhooks to trigger automated workflows
            </Typography>
          </Box>

          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enableAutoMerge}
                  onChange={(e) => handleSettingChange('enableAutoMerge', e.target.checked)}
                />
              }
              label="Enable auto-merge"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
              Automatically merge PRs that pass all validation checks
            </Typography>
          </Box>

          <Alert severity="warning" sx={{ mb: 2 }}>
            Auto-merge should only be enabled for trusted repositories with comprehensive validation.
          </Alert>

          <Typography variant="subtitle2" gutterBottom>
            API Keys Status
          </Typography>
          <List>
            <ListItem>
              <ListItemText primary="GitHub Token" />
              <ListItemSecondaryAction>
                <Chip label="Configured" color="success" size="small" />
              </ListItemSecondaryAction>
            </ListItem>
            <ListItem>
              <ListItemText primary="Codegen API Token" />
              <ListItemSecondaryAction>
                <Chip label="Configured" color="success" size="small" />
              </ListItemSecondaryAction>
            </ListItem>
            <ListItem>
              <ListItemText primary="Gemini API Key" />
              <ListItemSecondaryAction>
                <Chip label="Configured" color="success" size="small" />
              </ListItemSecondaryAction>
            </ListItem>
            <ListItem>
              <ListItemText primary="Cloudflare API Key" />
              <ListItemSecondaryAction>
                <Chip label="Configured" color="success" size="small" />
              </ListItemSecondaryAction>
            </ListItem>
          </List>
        </TabPanel>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button variant="contained" onClick={saveSettings}>
          Save Settings
        </Button>
      </DialogActions>
    </Dialog>
  );
};

