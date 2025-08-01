import React, { useState } from 'react';
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
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Save as SaveIcon,
} from '@mui/icons-material';

interface GlobalSettingsProps {
  open: boolean;
  onClose: () => void;
}

export const GlobalSettings: React.FC<GlobalSettingsProps> = ({
  open,
  onClose,
}) => {
  const [settings, setSettings] = useState({
    autoMerge: true,
    notifications: true,
    darkMode: false,
    webhookUrl: '',
    maxConcurrentRuns: 5,
  });

  const handleSave = () => {
    // TODO: Implement settings save functionality
    console.log('Saving global settings:', settings);
    onClose();
  };

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: value,
    }));
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <SettingsIcon />
          <Typography variant="h6">Global Settings</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box display="flex" flexDirection="column" gap={3} sx={{ mt: 1 }}>
          <Alert severity="info">
            Configure global settings for the CodegenCICD Dashboard
          </Alert>

          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Automation Settings
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.autoMerge}
                  onChange={(e) => handleSettingChange('autoMerge', e.target.checked)}
                />
              }
              label="Auto-merge PRs after successful validation"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={settings.notifications}
                  onChange={(e) => handleSettingChange('notifications', e.target.checked)}
                />
              }
              label="Enable webhook notifications"
            />
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Interface Settings
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.darkMode}
                  onChange={(e) => handleSettingChange('darkMode', e.target.checked)}
                />
              }
              label="Dark mode (coming soon)"
              disabled
            />
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Advanced Settings
            </Typography>
            <TextField
              fullWidth
              label="Webhook URL"
              value={settings.webhookUrl}
              onChange={(e) => handleSettingChange('webhookUrl', e.target.value)}
              placeholder="https://your-webhook-url.com"
              margin="normal"
            />
            <TextField
              fullWidth
              label="Max Concurrent Agent Runs"
              type="number"
              value={settings.maxConcurrentRuns}
              onChange={(e) => handleSettingChange('maxConcurrentRuns', parseInt(e.target.value))}
              margin="normal"
              inputProps={{ min: 1, max: 10 }}
            />
          </Box>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          startIcon={<SaveIcon />}
        >
          Save Settings
        </Button>
      </DialogActions>
    </Dialog>
  );
};
