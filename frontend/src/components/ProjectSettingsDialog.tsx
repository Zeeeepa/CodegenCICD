import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Tabs,
  Tab,
  TextField,
  Chip,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Divider,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Rule as RuleIcon,
  Build as BuildIcon,
  Security as SecurityIcon,
  Psychology as PsychologyIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  PlayArrow as PlayIcon,
  ExpandMore as ExpandMoreIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';

import { ProjectData } from './EnhancedProjectCard';

interface ProjectSettingsDialogProps {
  open: boolean;
  onClose: () => void;
  project: ProjectData;
  onUpdate: (updates: Partial<ProjectData>) => void;
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
      id={`project-settings-tabpanel-${index}`}
      aria-labelledby={`project-settings-tab-${index}`}
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

export const ProjectSettingsDialog: React.FC<ProjectSettingsDialogProps> = ({
  open,
  onClose,
  project,
  onUpdate,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [repositoryRules, setRepositoryRules] = useState('');
  const [setupCommands, setSetupCommands] = useState('');
  const [planningStatement, setPlanningStatement] = useState('');
  const [secrets, setSecrets] = useState<Array<{id: string, name: string, value: string, isNew?: boolean}>>([]);
  const [selectedBranch, setSelectedBranch] = useState(project.github_branch);
  const [setupCommandsStatus, setSetupCommandsStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle');
  const [setupCommandsOutput, setSetupCommandsOutput] = useState('');
  const [showSecretValues, setShowSecretValues] = useState<{[key: string]: boolean}>({});

  // Load project settings when dialog opens
  useEffect(() => {
    if (open) {
      loadProjectSettings();
    }
  }, [open, project.id]);

  const loadProjectSettings = async () => {
    try {
      // In a real implementation, these would be API calls
      setRepositoryRules(project.has_repository_rules ? 'Follow TypeScript best practices\nUse proper error handling\nWrite comprehensive tests' : '');
      setSetupCommands(project.has_setup_commands ? 'cd backend\npython -m pip install -r requirements.txt\ncd ../frontend\nnpm install\nnpm run dev' : '');
      setPlanningStatement(project.has_planning_statement ? `<Project='${project.name}'>\n\nYou are working on the ${project.name} project.\nPlease follow the repository rules and coding standards.` : '');
      setSecrets(project.has_secrets ? [
        { id: '1', name: 'DATABASE_URL', value: 'postgresql://...' },
        { id: '2', name: 'API_KEY', value: 'sk-...' }
      ] : []);
    } catch (error) {
      console.error('Failed to load project settings:', error);
    }
  };

  const handleSave = async () => {
    try {
      // In a real implementation, this would make API calls to save each setting
      const updates = {
        has_repository_rules: repositoryRules.trim().length > 0,
        has_setup_commands: setupCommands.trim().length > 0,
        has_planning_statement: planningStatement.trim().length > 0,
        has_secrets: secrets.length > 0,
        github_branch: selectedBranch,
      };
      
      onUpdate(updates);
      onClose();
    } catch (error) {
      console.error('Failed to save project settings:', error);
    }
  };

  const handleRunSetupCommands = async () => {
    setSetupCommandsStatus('running');
    setSetupCommandsOutput('');
    
    try {
      // Simulate running setup commands
      setSetupCommandsOutput('Running setup commands...\n');
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSetupCommandsOutput(prev => prev + 'Installing dependencies...\n');
      await new Promise(resolve => setTimeout(resolve, 1500));
      setSetupCommandsOutput(prev => prev + 'Setup completed successfully!\n');
      setSetupCommandsStatus('success');
    } catch (error) {
      setSetupCommandsOutput(prev => prev + `Error: ${error}\n`);
      setSetupCommandsStatus('error');
    }
  };

  const handleAddSecret = () => {
    const newSecret = {
      id: Date.now().toString(),
      name: '',
      value: '',
      isNew: true
    };
    setSecrets([...secrets, newSecret]);
  };

  const handleUpdateSecret = (id: string, field: 'name' | 'value', value: string) => {
    setSecrets(secrets.map(secret => 
      secret.id === id ? { ...secret, [field]: value } : secret
    ));
  };

  const handleDeleteSecret = (id: string) => {
    setSecrets(secrets.filter(secret => secret.id !== id));
  };

  const toggleSecretVisibility = (id: string) => {
    setShowSecretValues(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const handlePasteSecrets = () => {
    const text = prompt('Paste your environment variables (KEY=value format):');
    if (text) {
      const lines = text.split('\n').filter(line => line.includes('='));
      const newSecrets = lines.map((line, index) => {
        const [name, ...valueParts] = line.split('=');
        return {
          id: (Date.now() + index).toString(),
          name: name.trim(),
          value: valueParts.join('=').trim(),
          isNew: true
        };
      });
      setSecrets([...secrets, ...newSecrets]);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { height: '80vh' }
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <SettingsIcon color="primary" />
          <Typography variant="h6">
            Project Settings
          </Typography>
          <Chip 
            label={project.name} 
            size="small" 
            color="primary" 
            variant="outlined" 
          />
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab 
              icon={<RuleIcon />} 
              label="Repository Rules" 
              iconPosition="start"
            />
            <Tab 
              icon={<BuildIcon />} 
              label="Setup Commands" 
              iconPosition="start"
            />
            <Tab 
              icon={<SecurityIcon />} 
              label="Secrets" 
              iconPosition="start"
            />
            <Tab 
              icon={<PsychologyIcon />} 
              label="Planning Statement" 
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Repository Rules Tab */}
        <TabPanel value={activeTab} index={0}>
          <Typography variant="h6" gutterBottom>
            Repository Rules
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Specify any additional rules you want the agent to follow for this repository.
          </Typography>
          
          <TextField
            fullWidth
            multiline
            rows={12}
            value={repositoryRules}
            onChange={(e) => setRepositoryRules(e.target.value)}
            placeholder="Enter repository-specific rules and guidelines:

• Follow TypeScript best practices
• Use proper error handling with try-catch blocks
• Write comprehensive unit tests for all functions
• Use semantic commit messages
• Follow the existing code style and patterns
• Update documentation when making changes
• Ensure all PRs pass CI/CD checks before merging"
            variant="outlined"
            sx={{ mb: 2 }}
          />

          <Alert severity="info">
            These rules will be included in the agent's context when working on this project.
          </Alert>
        </TabPanel>

        {/* Setup Commands Tab */}
        <TabPanel value={activeTab} index={1}>
          <Typography variant="h6" gutterBottom>
            Setup Commands
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Specify the commands to run when setting up the sandbox environment.
          </Typography>

          <Box display="flex" gap={2} mb={2} alignItems="center">
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Branch</InputLabel>
              <Select
                value={selectedBranch}
                onChange={(e) => setSelectedBranch(e.target.value)}
                label="Branch"
              >
                <MenuItem value="main">main</MenuItem>
                <MenuItem value="develop">develop</MenuItem>
                <MenuItem value="staging">staging</MenuItem>
              </Select>
            </FormControl>
            
            <Button
              variant="outlined"
              startIcon={<PlayIcon />}
              onClick={handleRunSetupCommands}
              disabled={setupCommandsStatus === 'running' || !setupCommands.trim()}
            >
              {setupCommandsStatus === 'running' ? 'Running...' : 'Test Run'}
            </Button>
            
            <Button
              variant="outlined"
              startIcon={<SaveIcon />}
              onClick={handleSave}
            >
              Save
            </Button>
          </Box>

          <TextField
            fullWidth
            multiline
            rows={8}
            value={setupCommands}
            onChange={(e) => setSetupCommands(e.target.value)}
            placeholder="Enter setup commands (one per line):

cd backend
python -m pip install -r requirements.txt
python manage.py migrate

cd ../frontend
npm install
npm run build"
            variant="outlined"
            sx={{ mb: 2 }}
          />

          {setupCommandsOutput && (
            <Paper sx={{ p: 2, bgcolor: 'grey.900', color: 'white', fontFamily: 'monospace' }}>
              <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                {setupCommandsOutput}
              </Typography>
            </Paper>
          )}

          {setupCommandsStatus === 'success' && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Setup commands executed successfully!
            </Alert>
          )}

          {setupCommandsStatus === 'error' && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Setup commands failed. Check the output above for details.
            </Alert>
          )}
        </TabPanel>

        {/* Secrets Tab */}
        <TabPanel value={activeTab} index={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Box>
              <Typography variant="h6">
                Environment Variables
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Manage sensitive configuration values for this project.
              </Typography>
            </Box>
            <Box display="flex" gap={1}>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={handleAddSecret}
                size="small"
              >
                Add Secret
              </Button>
              <Button
                variant="outlined"
                onClick={handlePasteSecrets}
                size="small"
              >
                Paste Text
              </Button>
            </Box>
          </Box>

          <List>
            {secrets.map((secret, index) => (
              <React.Fragment key={secret.id}>
                <ListItem sx={{ px: 0 }}>
                  <Box display="flex" width="100%" gap={2} alignItems="center">
                    <TextField
                      size="small"
                      label="Variable Name"
                      value={secret.name}
                      onChange={(e) => handleUpdateSecret(secret.id, 'name', e.target.value)}
                      placeholder="DATABASE_URL"
                      sx={{ flex: 1 }}
                    />
                    <TextField
                      size="small"
                      label="Value"
                      type={showSecretValues[secret.id] ? 'text' : 'password'}
                      value={secret.value}
                      onChange={(e) => handleUpdateSecret(secret.id, 'value', e.target.value)}
                      placeholder="Enter secret value"
                      sx={{ flex: 2 }}
                      InputProps={{
                        endAdornment: (
                          <IconButton
                            size="small"
                            onClick={() => toggleSecretVisibility(secret.id)}
                          >
                            {showSecretValues[secret.id] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                          </IconButton>
                        )
                      }}
                    />
                    <IconButton
                      color="error"
                      onClick={() => handleDeleteSecret(secret.id)}
                      size="small"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </ListItem>
                {index < secrets.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>

          {secrets.length === 0 && (
            <Alert severity="info">
              No environment variables configured. Click "Add Secret" to add your first variable.
            </Alert>
          )}

          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Security Note:</strong> All secrets are encrypted before storage and are only accessible during agent runs.
            </Typography>
          </Alert>
        </TabPanel>

        {/* Planning Statement Tab */}
        <TabPanel value={activeTab} index={3}>
          <Typography variant="h6" gutterBottom>
            Planning Statement
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            This text will be prepended to every agent run request as context.
          </Typography>

          <TextField
            fullWidth
            multiline
            rows={12}
            value={planningStatement}
            onChange={(e) => setPlanningStatement(e.target.value)}
            placeholder={`Enter a planning statement for this project:

<Project='${project.name}'>

You are working on the ${project.name} project (${project.github_owner}/${project.github_repo}).

Project Context:
- This is a [describe your project type]
- Built with [technology stack]
- Follows [coding standards/patterns]

Guidelines:
- Always follow the repository rules
- Test your changes thoroughly
- Update documentation when needed
- Use semantic commit messages`}
            variant="outlined"
            sx={{ mb: 2 }}
          />

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2">
                Preview: How this will appear to the agent
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                  {planningStatement || 'No planning statement configured'}
                  {planningStatement && '\n\nUser Request: [Your target text will appear here]'}
                </Typography>
              </Paper>
            </AccordionDetails>
          </Accordion>
        </TabPanel>
      </DialogContent>

      <Divider />

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          startIcon={<SaveIcon />}
        >
          Save Settings
        </Button>
      </DialogActions>
    </Dialog>
  );
};
