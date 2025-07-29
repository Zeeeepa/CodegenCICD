import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  Save as SaveIcon,
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Terminal as TerminalIcon,
} from '@mui/icons-material';
import { ProjectConfiguration, configurationsApi } from '../../services/api';

interface SetupCommandsTabProps {
  projectId: number;
  configuration: ProjectConfiguration;
  onUpdate: (updates: Partial<ProjectConfiguration>) => Promise<void>;
  onUnsavedChanges: (hasChanges: boolean) => void;
  loading: boolean;
}

interface TestResult {
  success: boolean;
  output: string;
  error?: string;
  duration: number;
}

const SetupCommandsTab: React.FC<SetupCommandsTabProps> = ({
  projectId,
  configuration,
  onUpdate,
  onUnsavedChanges,
  loading,
}) => {
  const [commands, setCommands] = useState(configuration.setup_commands || '');
  const [branchName, setBranchName] = useState(configuration.branch_name || 'main');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setCommands(configuration.setup_commands || '');
    setBranchName(configuration.branch_name || 'main');
  }, [configuration]);

  useEffect(() => {
    const hasChanges = 
      commands !== (configuration.setup_commands || '') ||
      branchName !== (configuration.branch_name || 'main');
    onUnsavedChanges(hasChanges);
  }, [commands, branchName, configuration, onUnsavedChanges]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      await onUpdate({ 
        setup_commands: commands,
        branch_name: branchName,
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save setup commands');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!commands.trim()) {
      setError('Please enter setup commands to test');
      return;
    }

    try {
      setTesting(true);
      setError(null);
      setTestResult(null);

      const startTime = Date.now();
      const response = await configurationsApi.testSetupCommands(projectId, {
        commands,
        branch: branchName,
      });
      const duration = Date.now() - startTime;

      setTestResult({
        success: response.data.success,
        output: response.data.output,
        error: response.data.error,
        duration,
      });
    } catch (err: any) {
      const duration = Date.now();
      setTestResult({
        success: false,
        output: '',
        error: err.response?.data?.detail || 'Failed to test setup commands',
        duration,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleReset = () => {
    setCommands(configuration.setup_commands || '');
    setBranchName(configuration.branch_name || 'main');
    setError(null);
    setTestResult(null);
  };

  const exampleCommands = [
    {
      name: 'Node.js Frontend',
      commands: `cd frontend
npm install
npm run build
npm start`,
    },
    {
      name: 'Python Backend',
      commands: `cd backend
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver`,
    },
    {
      name: 'Full Stack',
      commands: `# Backend setup
cd backend
python -m pip install -r requirements.txt
python manage.py migrate

# Frontend setup
cd ../frontend
npm install
npm run build

# Start services
npm run dev`,
    },
    {
      name: 'Python + React',
      commands: `cd backend
source venv/bin/activate
pip install -r requirements.txt
python main.py &

cd ../frontend
npm install
npm start`,
    },
  ];

  const handleUseExample = (example: typeof exampleCommands[0]) => {
    setCommands(example.commands);
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Setup Commands
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Specify the commands to run when setting up the sandbox environment for validation.
        These commands will be executed in sequence during the validation pipeline.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Setup commands saved successfully!
        </Alert>
      )}

      <Box display="flex" gap={2} mb={2}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Target Branch</InputLabel>
          <Select
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
            label="Target Branch"
          >
            <MenuItem value="main">main</MenuItem>
            <MenuItem value="master">master</MenuItem>
            <MenuItem value="develop">develop</MenuItem>
            <MenuItem value="staging">staging</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <TextField
        fullWidth
        multiline
        rows={12}
        label="Setup Commands"
        placeholder="Enter commands, one per line..."
        value={commands}
        onChange={(e) => setCommands(e.target.value)}
        sx={{ mb: 2 }}
        helperText="Commands will be executed in the order specified. Use # for comments."
      />

      <Box display="flex" gap={2} mb={3}>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving || loading}
        >
          {saving ? 'Saving...' : 'Save Commands'}
        </Button>
        
        <Button
          variant="outlined"
          startIcon={testing ? <CircularProgress size={16} /> : <PlayIcon />}
          onClick={handleTest}
          disabled={testing || loading || !commands.trim()}
          color="success"
        >
          {testing ? 'Testing...' : 'Test Commands'}
        </Button>

        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleReset}
          disabled={saving || testing || loading}
        >
          Reset
        </Button>
      </Box>

      {/* Test Results */}
      {testResult && (
        <Accordion sx={{ mb: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" gap={1}>
              {testResult.success ? (
                <CheckCircleIcon color="success" />
              ) : (
                <ErrorIcon color="error" />
              )}
              <Typography>
                Test Result: {testResult.success ? 'Success' : 'Failed'}
              </Typography>
              <Chip 
                label={`${testResult.duration}ms`} 
                size="small" 
                variant="outlined" 
              />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Box>
              {testResult.output && (
                <Box mb={2}>
                  <Typography variant="subtitle2" gutterBottom>
                    Output:
                  </Typography>
                  <Paper sx={{ p: 2, backgroundColor: 'grey.100' }}>
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                      {testResult.output}
                    </Typography>
                  </Paper>
                </Box>
              )}
              
              {testResult.error && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom color="error">
                    Error:
                  </Typography>
                  <Paper sx={{ p: 2, backgroundColor: 'error.light', color: 'error.contrastText' }}>
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                      {testResult.error}
                    </Typography>
                  </Paper>
                </Box>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Example Commands */}
      <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
        <Typography variant="subtitle1" gutterBottom>
          Example Command Sets
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Click on any example to use it as a starting point:
        </Typography>
        
        <List>
          {exampleCommands.map((example, index) => (
            <ListItem
              key={index}
              button
              onClick={() => handleUseExample(example)}
              sx={{ 
                border: 1, 
                borderColor: 'divider', 
                borderRadius: 1, 
                mb: 1,
                '&:hover': { backgroundColor: 'action.hover' }
              }}
            >
              <ListItemIcon>
                <TerminalIcon />
              </ListItemIcon>
              <ListItemText
                primary={example.name}
                secondary={
                  <Typography variant="body2" component="pre" sx={{ 
                    whiteSpace: 'pre-wrap',
                    fontSize: '0.75rem',
                    mt: 1,
                  }}>
                    {example.commands.split('\n').slice(0, 3).join('\n')}
                    {example.commands.split('\n').length > 3 && '\n...'}
                  </Typography>
                }
              />
            </ListItem>
          ))}
        </List>
      </Paper>

      <Box mt={3}>
        <Alert severity="info">
          <Typography variant="body2">
            <strong>How it works:</strong> These commands will be executed in the grainchain sandbox 
            environment during the validation pipeline. Make sure they can run independently and 
            don't require interactive input.
          </Typography>
        </Alert>
      </Box>
    </Box>
  );
};

export default SetupCommandsTab;
