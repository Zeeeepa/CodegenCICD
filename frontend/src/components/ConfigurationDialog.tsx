// Project configuration dialog with 4-tab system
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
  Chip,
  IconButton,
  Paper,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  PlayArrow as PlayIcon,
} from '@mui/icons-material';
import { Project, ProjectConfiguration } from '../types';
import { projectsApi } from '../services/api';

interface ConfigurationDialogProps {
  open: boolean;
  onClose: () => void;
  project: Project;
  onUpdate: (project: Project) => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`config-tabpanel-${index}`}
      aria-labelledby={`config-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
};

export const ConfigurationDialog: React.FC<ConfigurationDialogProps> = ({
  open,
  onClose,
  project,
  onUpdate,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [configuration, setConfiguration] = useState<ProjectConfiguration>({
    repository_rules: '',
    setup_commands: '',
    planning_statement: '',
    secrets: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Secret management state
  const [newSecretKey, setNewSecretKey] = useState('');
  const [newSecretValue, setNewSecretValue] = useState('');
  const [secretsText, setSecretsText] = useState('');

  useEffect(() => {
    if (open) {
      loadConfiguration();
    }
  }, [open, project.id]);

  const loadConfiguration = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const config = await projectsApi.getConfiguration(project.id);
      setConfiguration(config);
      
      // Convert secrets array to text format for bulk editing
      if (config.secrets && Array.isArray(config.secrets)) {
        setSecretsText(config.secrets.map(key => `${key}=`).join('\n'));
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const saveConfiguration = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Parse secrets from text format
      const secretsObj: Record<string, string> = {};
      if (secretsText.trim()) {
        secretsText.split('\n').forEach(line => {
          const [key, ...valueParts] = line.split('=');
          if (key.trim()) {
            secretsObj[key.trim()] = valueParts.join('=').trim();
          }
        });
      }

      const configToSave = {
        ...configuration,
        secrets: secretsObj,
      };

      await projectsApi.updateConfiguration(project.id, configToSave);
      setSuccess('Configuration saved successfully');
      
      // Update project to reflect configuration changes (visual indicator)
      onUpdate({ ...project, updated_at: new Date().toISOString() });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setLoading(false);
    }
  };

  const addSecret = () => {
    if (newSecretKey.trim() && newSecretValue.trim()) {
      const newLine = `${newSecretKey}=${newSecretValue}`;
      setSecretsText(prev => prev ? `${prev}\n${newLine}` : newLine);
      setNewSecretKey('');
      setNewSecretValue('');
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const runSetupCommands = async () => {
    // This would integrate with the validation service to test setup commands
    setSuccess('Setup commands would be executed in sandbox environment');
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Project Configuration - {project.name}
      </DialogTitle>
      
      <DialogContent sx={{ p: 0 }}>
        {error && (
          <Alert severity="error" sx={{ m: 2 }}>
            {error}
          </Alert>
        )}
        
        {success && (
          <Alert severity="success" sx={{ m: 2 }}>
            {success}
          </Alert>
        )}

        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          aria-label="configuration tabs"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Repository Rules" />
          <Tab label="Setup Commands" />
          <Tab label="Secrets" />
          <Tab label="Planning Statement" />
        </Tabs>

        {/* Repository Rules Tab */}
        <TabPanel value={activeTab} index={0}>
          <Typography variant="h6" gutterBottom>
            Repository Rules
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Specify any additional rules you want the agent to follow for this repository.
          </Typography>
          
          <TextField
            fullWidth
            multiline
            rows={8}
            variant="outlined"
            placeholder="Enter repository-specific rules and guidelines..."
            value={configuration.repository_rules || ''}
            onChange={(e) => setConfiguration(prev => ({ ...prev, repository_rules: e.target.value }))}
            disabled={loading}
          />
          
          {configuration.repository_rules && (
            <Chip
              label="Rules Configured"
              color="primary"
              size="small"
              sx={{ mt: 2 }}
            />
          )}
        </TabPanel>

        {/* Setup Commands Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Setup Commands
            </Typography>
            <Button
              startIcon={<PlayIcon />}
              onClick={runSetupCommands}
              disabled={loading || !configuration.setup_commands}
            >
              Test Run
            </Button>
          </Box>
          
          <Typography variant="body2" color="text.secondary" paragraph>
            Specify the commands to run when setting up the sandbox environment.
          </Typography>
          
          <TextField
            fullWidth
            multiline
            rows={6}
            variant="outlined"
            placeholder={`cd backend\npython api.py\ncd ..\ncd frontend\nnpm install\nnpm run dev`}
            value={configuration.setup_commands || ''}
            onChange={(e) => setConfiguration(prev => ({ ...prev, setup_commands: e.target.value }))}
            disabled={loading}
            sx={{ fontFamily: 'monospace' }}
          />
          
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Commands will be executed in the sandbox environment during validation.
          </Typography>
        </TabPanel>

        {/* Secrets Tab */}
        <TabPanel value={activeTab} index={2}>
          <Typography variant="h6" gutterBottom>
            Environment Variables & Secrets
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Add environment variables and secrets for your project. Values are encrypted.
          </Typography>

          {/* Add individual secret */}
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Add Secret
            </Typography>
            <Box display="flex" gap={2} alignItems="center">
              <TextField
                label="Variable Name"
                value={newSecretKey}
                onChange={(e) => setNewSecretKey(e.target.value)}
                size="small"
                placeholder="API_KEY"
              />
              <TextField
                label="Value"
                type="password"
                value={newSecretValue}
                onChange={(e) => setNewSecretValue(e.target.value)}
                size="small"
                placeholder="secret-value"
              />
              <IconButton onClick={addSecret} disabled={!newSecretKey.trim() || !newSecretValue.trim()}>
                <AddIcon />
              </IconButton>
            </Box>
          </Paper>

          <Divider sx={{ my: 2 }} />

          {/* Bulk edit secrets */}
          <Typography variant="subtitle2" gutterBottom>
            Bulk Edit (Key=Value format)
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={8}
            variant="outlined"
            placeholder={`CODEGEN_ORG_ID=323\nCODEGEN_TOKEN=sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99\nGITHUB_TOKEN=github_pat_...\nGEMINI_API_KEY=AIzaSy...`}
            value={secretsText}
            onChange={(e) => setSecretsText(e.target.value)}
            disabled={loading}
            sx={{ fontFamily: 'monospace' }}
          />
          
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            One variable per line in KEY=VALUE format. Values are encrypted when saved.
          </Typography>
        </TabPanel>

        {/* Planning Statement Tab */}
        <TabPanel value={activeTab} index={3}>
          <Typography variant="h6" gutterBottom>
            Planning Statement
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            This text is automatically prepended to all agent run prompts for this project.
            Use it to provide consistent context and guidelines.
          </Typography>
          
          <TextField
            fullWidth
            multiline
            rows={8}
            variant="outlined"
            placeholder="You are working on a React/Node.js project. Always follow these guidelines:&#10;- Use TypeScript for all new code&#10;- Follow the existing code style&#10;- Add proper error handling&#10;- Include unit tests for new features"
            value={configuration.planning_statement || ''}
            onChange={(e) => setConfiguration(prev => ({ ...prev, planning_statement: e.target.value }))}
            disabled={loading}
          />
          
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            This statement will be automatically included in all agent runs for consistent behavior.
          </Typography>
        </TabPanel>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={saveConfiguration}
          variant="contained"
          startIcon={<SaveIcon />}
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Save Configuration'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

