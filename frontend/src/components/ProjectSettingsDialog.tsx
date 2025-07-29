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
  Switch,
  FormControlLabel,
  Paper,
  Stack,
  IconButton,
  Chip,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  Save as SaveIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { Project } from '../services/api';

interface ProjectSettingsDialogProps {
  open: boolean;
  onClose: () => void;
  project: Project;
  onUpdate: (updates: Partial<Project>) => void;
  onRunSetupCommands: () => void;
}

interface ProjectSecret {
  id?: number;
  key: string;
  value: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index} style={{ paddingTop: 16 }}>
    {value === index && children}
  </div>
);

const ProjectSettingsDialog: React.FC<ProjectSettingsDialogProps> = ({
  open,
  onClose,
  project,
  onUpdate,
  onRunSetupCommands
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  
  // Form states
  const [autoConfirmPlans, setAutoConfirmPlans] = useState(project.auto_confirm_plans || false);
  const [autoMergeValidatedPR, setAutoMergeValidatedPR] = useState(project.auto_merge_validated_pr || false);
  const [planningStatement, setPlanningStatement] = useState(project.planning_statement || '');
  const [repositoryRules, setRepositoryRules] = useState(project.repository_rules || '');
  const [setupCommands, setSetupCommands] = useState(project.setup_commands || '');
  const [setupBranch, setSetupBranch] = useState(project.setup_branch || 'main');
  const [secrets, setSecrets] = useState<ProjectSecret[]>([]);
  const [secretsText, setSecretsText] = useState('');
  const [showSecretValues, setShowSecretValues] = useState(false);
  const [branches, setBranches] = useState<string[]>(['main', 'develop', 'staging']);

  // Load project secrets
  useEffect(() => {
    if (open) {
      loadSecrets();
      loadBranches();
    }
  }, [open, project.id]);

  const loadSecrets = async () => {
    try {
      const response = await fetch(`/api/projects/${project.id}/secrets`);
      if (response.ok) {
        const data = await response.json();
        setSecrets(data.secrets || []);
        
        // Convert to text format
        const secretsTextFormat = data.secrets
          .map((s: ProjectSecret) => `${s.key}=${s.value}`)
          .join('\n');
        setSecretsText(secretsTextFormat);
      }
    } catch (error) {
      console.error('Failed to load secrets:', error);
    }
  };

  const loadBranches = async () => {
    try {
      // TODO: Implement GitHub API call to get actual branches
      // For now, use default branches
      setBranches(['main', 'develop', 'staging', 'production']);
    } catch (error) {
      console.error('Failed to load branches:', error);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      
      const updates = {
        auto_confirm_plans: autoConfirmPlans,
        auto_merge_validated_pr: autoMergeValidatedPR,
        planning_statement: planningStatement,
        repository_rules: repositoryRules,
        setup_commands: setupCommands,
        setup_branch: setupBranch,
      };
      
      await onUpdate(updates);
      
      // Save secrets if they were modified
      if (secretsText !== secrets.map(s => `${s.key}=${s.value}`).join('\n')) {
        await saveSecrets();
      }
      
      onClose();
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveSecrets = async () => {
    try {
      // Parse secrets from text
      const parsedSecrets = secretsText
        .split('\n')
        .filter(line => line.trim() && line.includes('='))
        .map(line => {
          const [key, ...valueParts] = line.split('=');
          return {
            key: key.trim(),
            value: valueParts.join('=').trim()
          };
        });

      // Save each secret
      for (const secret of parsedSecrets) {
        await fetch(`/api/projects/${project.id}/secrets`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(secret)
        });
      }
      
      // Reload secrets
      await loadSecrets();
    } catch (error) {
      console.error('Failed to save secrets:', error);
    }
  };

  const addSecret = () => {
    setSecrets(prev => [...prev, { key: '', value: '' }]);
  };

  const updateSecret = (index: number, field: 'key' | 'value', value: string) => {
    setSecrets(prev => prev.map((secret, i) => 
      i === index ? { ...secret, [field]: value } : secret
    ));
  };

  const removeSecret = async (index: number) => {
    const secret = secrets[index];
    if (secret.id) {
      try {
        await fetch(`/api/projects/${project.id}/secrets/${secret.id}`, {
          method: 'DELETE'
        });
      } catch (error) {
        console.error('Failed to delete secret:', error);
      }
    }
    setSecrets(prev => prev.filter((_, i) => i !== index));
  };

  const runSetupCommands = async () => {
    try {
      setLoading(true);
      await onRunSetupCommands();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '600px' }
      }}
    >
      <DialogTitle>
        Project Settings - {project.name}
      </DialogTitle>

      <DialogContent>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab label="General" />
            <Tab label="Planning Statement" />
            <Tab label="Repository Rules" />
            <Tab label="Setup Commands" />
            <Tab label="Secrets" />
          </Tabs>
        </Box>

        {/* General Tab */}
        <TabPanel value={activeTab} index={0}>
          <Stack spacing={3}>
            <Typography variant="h6">General Settings</Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={autoConfirmPlans}
                  onChange={(e) => setAutoConfirmPlans(e.target.checked)}
                />
              }
              label="Auto Confirm Proposed Plans"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={autoMergeValidatedPR}
                  onChange={(e) => setAutoMergeValidatedPR(e.target.checked)}
                />
              }
              label="Auto-merge Validated PRs"
            />

            <Alert severity="info">
              <Typography variant="body2">
                When auto-confirm is enabled, the agent will automatically proceed with proposed plans without waiting for user confirmation.
              </Typography>
            </Alert>
          </Stack>
        </TabPanel>

        {/* Planning Statement Tab */}
        <TabPanel value={activeTab} index={1}>
          <Stack spacing={2}>
            <Typography variant="h6">Planning Statement</Typography>
            <Typography variant="body2" color="text.secondary">
              This text will be sent to the Codegen API along with every user request to provide context and guidance.
            </Typography>
            
            <TextField
              fullWidth
              multiline
              rows={8}
              value={planningStatement}
              onChange={(e) => setPlanningStatement(e.target.value)}
              placeholder="Enter planning statement that will be prepended to all agent requests..."
              variant="outlined"
            />
            
            {planningStatement && (
              <Alert severity="success">
                <Typography variant="body2">
                  Planning statement configured. This will be included with all agent runs.
                </Typography>
              </Alert>
            )}
          </Stack>
        </TabPanel>

        {/* Repository Rules Tab */}
        <TabPanel value={activeTab} index={2}>
          <Stack spacing={2}>
            <Typography variant="h6">Repository Rules</Typography>
            <Typography variant="body2" color="text.secondary">
              Specify any additional rules you want the agent to follow for this repository.
            </Typography>
            
            <TextField
              fullWidth
              multiline
              rows={8}
              value={repositoryRules}
              onChange={(e) => setRepositoryRules(e.target.value)}
              placeholder="Enter repository-specific rules and guidelines..."
              variant="outlined"
            />
            
            {repositoryRules && (
              <Alert severity="warning">
                <Typography variant="body2">
                  Repository rules configured. The project card will show a visual indicator.
                </Typography>
              </Alert>
            )}
          </Stack>
        </TabPanel>

        {/* Setup Commands Tab */}
        <TabPanel value={activeTab} index={3}>
          <Stack spacing={2}>
            <Typography variant="h6">Setup Commands</Typography>
            <Typography variant="body2" color="text.secondary">
              Specify the commands to run when setting up the sandbox environment.
            </Typography>
            
            <TextField
              fullWidth
              multiline
              rows={8}
              value={setupCommands}
              onChange={(e) => setSetupCommands(e.target.value)}
              placeholder={`cd backend\npython api.py\ncd ..\ncd frontend\nnpm install\nnpm run dev`}
              variant="outlined"
            />
            
            <FormControl fullWidth>
              <InputLabel>Branch</InputLabel>
              <Select
                value={setupBranch}
                onChange={(e) => setSetupBranch(e.target.value)}
                label="Branch"
              >
                {branches.map((branch) => (
                  <MenuItem key={branch} value={branch}>
                    {branch}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                startIcon={<PlayIcon />}
                onClick={runSetupCommands}
                disabled={!setupCommands || loading}
              >
                {loading ? <CircularProgress size={20} /> : 'Run'}
              </Button>
              <Button
                variant="outlined"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                disabled={loading}
              >
                Save
              </Button>
            </Stack>
          </Stack>
        </TabPanel>

        {/* Secrets Tab */}
        <TabPanel value={activeTab} index={4}>
          <Stack spacing={2}>
            <Typography variant="h6">Environment Variables / Secrets</Typography>
            <Typography variant="body2" color="text.secondary">
              Manage environment variables that will be available during agent runs and validation.
            </Typography>
            
            {/* Individual Secret Management */}
            <Paper sx={{ p: 2 }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
                <Typography variant="subtitle1">Individual Secrets</Typography>
                <Button
                  startIcon={<AddIcon />}
                  onClick={addSecret}
                  size="small"
                >
                  Add Secret
                </Button>
              </Stack>
              
              {secrets.map((secret, index) => (
                <Stack key={index} direction="row" spacing={1} sx={{ mb: 1 }}>
                  <TextField
                    size="small"
                    placeholder="ENV_VAR_NAME"
                    value={secret.key}
                    onChange={(e) => updateSecret(index, 'key', e.target.value)}
                    sx={{ flex: 1 }}
                  />
                  <TextField
                    size="small"
                    placeholder="value"
                    type={showSecretValues ? 'text' : 'password'}
                    value={secret.value}
                    onChange={(e) => updateSecret(index, 'value', e.target.value)}
                    sx={{ flex: 2 }}
                  />
                  <IconButton
                    size="small"
                    onClick={() => removeSecret(index)}
                    color="error"
                  >
                    <DeleteIcon />
                  </IconButton>
                </Stack>
              ))}
              
              <Button
                startIcon={showSecretValues ? <VisibilityOffIcon /> : <VisibilityIcon />}
                onClick={() => setShowSecretValues(!showSecretValues)}
                size="small"
                sx={{ mt: 1 }}
              >
                {showSecretValues ? 'Hide' : 'Show'} Values
              </Button>
            </Paper>
            
            <Divider />
            
            {/* Text Format */}
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" sx={{ mb: 2 }}>
                Paste as Text
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={8}
                value={secretsText}
                onChange={(e) => setSecretsText(e.target.value)}
                placeholder={`CODEGEN_ORG_ID=323\nCODEGEN_TOKEN=sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99\nGEMINI_API_KEY=your-key-here`}
                variant="outlined"
                sx={{ fontFamily: 'monospace' }}
              />
            </Paper>
            
            {secrets.length > 0 && (
              <Alert severity="info">
                <Typography variant="body2">
                  {secrets.length} secret(s) configured for this project.
                </Typography>
              </Alert>
            )}
          </Stack>
        </TabPanel>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
        >
          {loading ? 'Saving...' : 'Save Settings'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProjectSettingsDialog;
