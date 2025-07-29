import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tabs,
  Tab,
  Box,
  TextField,
  Typography,
  Alert,
  Paper,
  Stack,
  IconButton,
  Divider,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  TestTube as TestIcon,
} from '@mui/icons-material';

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

interface EnvironmentVariable {
  key: string;
  value: string;
  category: string;
  description: string;
  sensitive: boolean;
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

const SettingsDialog: React.FC<SettingsDialogProps> = ({ open, onClose }) => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>({});
  
  // Environment variables state
  const [envVars, setEnvVars] = useState<EnvironmentVariable[]>([
    // Codegen API
    { key: 'CODEGEN_ORG_ID', value: '', category: 'codegen', description: 'Codegen organization ID', sensitive: false },
    { key: 'CODEGEN_API_TOKEN', value: '', category: 'codegen', description: 'Codegen API token for agent coordination', sensitive: true },
    
    // GitHub Integration
    { key: 'GITHUB_TOKEN', value: '', category: 'github', description: 'GitHub personal access token', sensitive: true },
    
    // AI Services
    { key: 'GEMINI_API_KEY', value: '', category: 'ai', description: 'Gemini API key for web-eval-agent', sensitive: true },
    
    // Cloudflare Workers
    { key: 'CLOUDFLARE_API_KEY', value: '', category: 'cloudflare', description: 'Cloudflare API key', sensitive: true },
    { key: 'CLOUDFLARE_ACCOUNT_ID', value: '', category: 'cloudflare', description: 'Cloudflare account ID', sensitive: false },
    { key: 'CLOUDFLARE_WORKER_NAME', value: 'webhook-gateway', category: 'cloudflare', description: 'Cloudflare worker name', sensitive: false },
    { key: 'CLOUDFLARE_WORKER_URL', value: '', category: 'cloudflare', description: 'Cloudflare worker webhook URL', sensitive: false },
    
    // Service URLs
    { key: 'GRAINCHAIN_URL', value: '', category: 'services', description: 'Grainchain service URL for sandboxing', sensitive: false },
    { key: 'GRAPH_SITTER_URL', value: '', category: 'services', description: 'Graph-sitter service URL for code analysis', sensitive: false },
    { key: 'WEB_EVAL_AGENT_URL', value: '', category: 'services', description: 'Web-eval-agent service URL for UI testing', sensitive: false },
  ]);

  // Global settings
  const [globalSettings, setGlobalSettings] = useState({
    autoTestComponents: true,
    enableWebhookNotifications: true,
    autoMergeValidatedPRs: false,
    enableComprehensiveTesting: true,
  });

  useEffect(() => {
    if (open) {
      loadSettings();
    }
  }, [open]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/settings/environment');
      if (response.ok) {
        const data = await response.json();
        
        // Update environment variables with loaded values
        setEnvVars(prev => prev.map(envVar => ({
          ...envVar,
          value: data.environment_variables[envVar.category]?.[envVar.key] || envVar.value
        })));
        
        // Load global settings
        const settingsResponse = await fetch('/api/settings/global');
        if (settingsResponse.ok) {
          const settingsData = await settingsResponse.json();
          setGlobalSettings(settingsData.settings || globalSettings);
        }
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
      setMessage({ text: 'Failed to load settings', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      
      // Prepare environment variables for saving
      const envVarsByCategory = envVars.reduce((acc, envVar) => {
        if (!acc[envVar.category]) acc[envVar.category] = {};
        acc[envVar.category][envVar.key] = envVar.value;
        return acc;
      }, {} as Record<string, Record<string, string>>);

      // Save environment variables
      const envResponse = await fetch('/api/settings/environment', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ environment_variables: envVarsByCategory })
      });

      // Save global settings
      const settingsResponse = await fetch('/api/settings/global', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: globalSettings })
      });

      if (envResponse.ok && settingsResponse.ok) {
        setMessage({ text: 'Settings saved successfully', type: 'success' });
      } else {
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      setMessage({ text: 'Failed to save settings', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestServices = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/settings/test-services', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          environment_variables: envVars.reduce((acc, envVar) => {
            acc[envVar.key] = envVar.value;
            return acc;
          }, {} as Record<string, string>)
        })
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ 
          text: `Service test completed. ${data.passed}/${data.total} services passed`, 
          type: data.passed === data.total ? 'success' : 'error' 
        });
      } else {
        throw new Error('Service test failed');
      }
    } catch (error) {
      console.error('Service test failed:', error);
      setMessage({ text: 'Service test failed', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const updateEnvVar = (key: string, value: string) => {
    setEnvVars(prev => prev.map(envVar => 
      envVar.key === key ? { ...envVar, value } : envVar
    ));
  };

  const toggleSensitiveVisibility = (key: string) => {
    setShowSensitive(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const renderEnvironmentVariables = (category: string, title: string) => {
    const categoryVars = envVars.filter(envVar => envVar.category === category);
    
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>{title}</Typography>
        <Stack spacing={2}>
          {categoryVars.map((envVar) => (
            <Box key={envVar.key}>
              <TextField
                fullWidth
                label={envVar.key}
                value={envVar.value}
                onChange={(e) => updateEnvVar(envVar.key, e.target.value)}
                type={envVar.sensitive && !showSensitive[envVar.key] ? 'password' : 'text'}
                helperText={envVar.description}
                InputProps={{
                  endAdornment: envVar.sensitive && (
                    <IconButton
                      onClick={() => toggleSensitiveVisibility(envVar.key)}
                      edge="end"
                    >
                      {showSensitive[envVar.key] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  )
                }}
              />
            </Box>
          ))}
        </Stack>
      </Paper>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{ sx: { height: '80vh' } }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">System Settings</Typography>
          <Box>
            <IconButton onClick={loadSettings} disabled={loading}>
              <RefreshIcon />
            </IconButton>
            <Button
              startIcon={<TestIcon />}
              onClick={handleTestServices}
              disabled={loading}
              variant="outlined"
              size="small"
              sx={{ mr: 1 }}
            >
              Test Services
            </Button>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        {message && (
          <Alert 
            severity={message.type} 
            onClose={() => setMessage(null)}
            sx={{ mb: 2 }}
          >
            {message.text}
          </Alert>
        )}

        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="Environment Variables" />
          <Tab label="Global Settings" />
          <Tab label="Service Integration" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          {renderEnvironmentVariables('codegen', 'Codegen API Configuration')}
          {renderEnvironmentVariables('github', 'GitHub Integration')}
          {renderEnvironmentVariables('ai', 'AI Services')}
          {renderEnvironmentVariables('cloudflare', 'Cloudflare Workers')}
          {renderEnvironmentVariables('services', 'Service URLs')}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Global Settings</Typography>
            <Stack spacing={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={globalSettings.autoTestComponents}
                    onChange={(e) => setGlobalSettings(prev => ({ 
                      ...prev, 
                      autoTestComponents: e.target.checked 
                    }))}
                  />
                }
                label="Automatically test all new components with web-eval-agent"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={globalSettings.enableWebhookNotifications}
                    onChange={(e) => setGlobalSettings(prev => ({ 
                      ...prev, 
                      enableWebhookNotifications: e.target.checked 
                    }))}
                  />
                }
                label="Enable webhook notifications for PR events"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={globalSettings.autoMergeValidatedPRs}
                    onChange={(e) => setGlobalSettings(prev => ({ 
                      ...prev, 
                      autoMergeValidatedPRs: e.target.checked 
                    }))}
                  />
                }
                label="Auto-merge validated PRs by default"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={globalSettings.enableComprehensiveTesting}
                    onChange={(e) => setGlobalSettings(prev => ({ 
                      ...prev, 
                      enableComprehensiveTesting: e.target.checked 
                    }))}
                  />
                }
                label="Enable comprehensive testing with full CI/CD pipeline"
              />
            </Stack>
          </Paper>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Service Integration Status</Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              This tab shows the integration status of all external services. Use the "Test Services" button to validate connectivity.
            </Typography>
            
            <Alert severity="info">
              <Typography variant="body2">
                <strong>Required Services:</strong>
              </Typography>
              <ul>
                <li><strong>Codegen SDK:</strong> Agent coordination & code generation</li>
                <li><strong>Graph-Sitter:</strong> Static analysis & code quality metrics</li>
                <li><strong>Grainchain:</strong> Sandboxing & snapshot creation</li>
                <li><strong>Web-Eval-Agent:</strong> UI testing & browser automation</li>
                <li><strong>GitHub:</strong> Repository management & webhook handling</li>
                <li><strong>Cloudflare Workers:</strong> Webhook gateway & notifications</li>
              </ul>
            </Alert>
          </Paper>
        </TabPanel>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          startIcon={<SaveIcon />}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SettingsDialog;
