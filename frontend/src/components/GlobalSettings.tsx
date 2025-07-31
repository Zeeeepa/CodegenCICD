import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Tab,
  Tabs,
  Paper,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Notifications as NotificationsIcon,
} from '@mui/icons-material';

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
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export const GlobalSettings: React.FC<GlobalSettingsProps> = ({ open, onClose }) => {
  const [tabValue, setTabValue] = useState(0);
  const [settings, setSettings] = useState({
    // General settings
    autoRefresh: true,
    refreshInterval: 30,
    theme: 'light',
    
    // Notification settings
    enableNotifications: true,
    emailNotifications: true,
    webhookNotifications: true,
    
    // API settings
    apiTimeout: 30,
    maxRetries: 3,
    
    // Security settings
    sessionTimeout: 60,
    requireAuth: false,
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = () => {
    // Save settings to backend
    console.log('Saving global settings:', settings);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <SettingsIcon />
          Global Settings
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Paper elevation={0}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="settings tabs">
            <Tab label="General" icon={<SettingsIcon />} />
            <Tab label="Notifications" icon={<NotificationsIcon />} />
            <Tab label="Security" icon={<SecurityIcon />} />
          </Tabs>
          
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
                label="Auto-refresh dashboard"
              />
            </Box>
            
            <TextField
              label="Refresh Interval (seconds)"
              type="number"
              value={settings.refreshInterval}
              onChange={(e) => handleSettingChange('refreshInterval', parseInt(e.target.value))}
              fullWidth
              sx={{ mb: 3 }}
              inputProps={{ min: 5, max: 300 }}
            />
            
            <TextField
              label="API Timeout (seconds)"
              type="number"
              value={settings.apiTimeout}
              onChange={(e) => handleSettingChange('apiTimeout', parseInt(e.target.value))}
              fullWidth
              sx={{ mb: 3 }}
              inputProps={{ min: 5, max: 120 }}
            />
            
            <TextField
              label="Max Retries"
              type="number"
              value={settings.maxRetries}
              onChange={(e) => handleSettingChange('maxRetries', parseInt(e.target.value))}
              fullWidth
              inputProps={{ min: 1, max: 10 }}
            />
          </TabPanel>
          
          <TabPanel value={tabValue} index={1}>
            <Typography variant="h6" gutterBottom>
              Notification Settings
            </Typography>
            
            <Box sx={{ mb: 3 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enableNotifications}
                    onChange={(e) => handleSettingChange('enableNotifications', e.target.checked)}
                  />
                }
                label="Enable notifications"
              />
            </Box>
            
            <Box sx={{ mb: 3 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.emailNotifications}
                    onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
                    disabled={!settings.enableNotifications}
                  />
                }
                label="Email notifications"
              />
            </Box>
            
            <Box sx={{ mb: 3 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.webhookNotifications}
                    onChange={(e) => handleSettingChange('webhookNotifications', e.target.checked)}
                    disabled={!settings.enableNotifications}
                  />
                }
                label="Webhook notifications"
              />
            </Box>
            
            <Alert severity="info">
              Notifications help you stay updated on project status changes and CI/CD pipeline events.
            </Alert>
          </TabPanel>
          
          <TabPanel value={tabValue} index={2}>
            <Typography variant="h6" gutterBottom>
              Security Settings
            </Typography>
            
            <TextField
              label="Session Timeout (minutes)"
              type="number"
              value={settings.sessionTimeout}
              onChange={(e) => handleSettingChange('sessionTimeout', parseInt(e.target.value))}
              fullWidth
              sx={{ mb: 3 }}
              inputProps={{ min: 5, max: 480 }}
            />
            
            <Box sx={{ mb: 3 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.requireAuth}
                    onChange={(e) => handleSettingChange('requireAuth', e.target.checked)}
                  />
                }
                label="Require authentication"
              />
            </Box>
            
            <Alert severity="warning">
              Security settings affect how users access and interact with the dashboard.
            </Alert>
          </TabPanel>
        </Paper>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">
          Save Settings
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default GlobalSettings;
