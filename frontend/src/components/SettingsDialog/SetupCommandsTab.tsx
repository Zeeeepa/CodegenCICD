import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Alert,
  Paper,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  Save as SaveIcon,
  PlayArrow as PlayIcon,
  Build as BuildIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { Project } from '../../types';
import { useApp } from '../../contexts/AppContext';
import { apiService } from '../../services/api';

interface SetupCommandsTabProps {
  project: Project;
  onError: (error: string | null) => void;
  onUnsavedChanges: (hasChanges: boolean) => void;
}

interface ExecutionResult {
  success: boolean;
  logs: string[];
  timestamp: string;
  branch: string;
}

const SetupCommandsTab: React.FC<SetupCommandsTabProps> = ({
  project,
  onError,
  onUnsavedChanges
}) => {
  const { updateProject } = useApp();
  const [commands, setCommands] = useState(project.configuration?.setup_commands || '');
  const [selectedBranch, setSelectedBranch] = useState(project.default_branch);
  const [branches, setBranches] = useState<string[]>([project.default_branch]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [success, setSuccess] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);

  // Track changes
  useEffect(() => {
    const hasChanges = commands !== (project.configuration?.setup_commands || '');
    onUnsavedChanges(hasChanges);
  }, [commands, project.configuration?.setup_commands, onUnsavedChanges]);

  // Load branches on mount
  useEffect(() => {
    loadBranches();
  }, []);

  const loadBranches = async () => {
    try {
      // This would fetch branches from GitHub API
      // For now, using default branches
      setBranches([
        project.default_branch,
        'develop',
        'staging',
        'feature/example'
      ]);
    } catch (error) {
      console.error('Failed to load branches:', error);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setSuccess(false);
      onError(null);

      // Update project configuration
      await apiService.updateProjectConfiguration(project.id, {
        setup_commands: commands.trim() || undefined
      });

      // Update local project state
      await updateProject(project.id, {
        configuration: {
          ...project.configuration,
          setup_commands: commands.trim() || undefined
        }
      });

      setSuccess(true);
      onUnsavedChanges(false);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);

    } catch (error: any) {
      onError(error.message || 'Failed to save setup commands');
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if (!commands.trim()) {
      onError('Please enter setup commands before running');
      return;
    }

    try {
      setRunning(true);
      onError(null);
      setExecutionResult(null);

      // Run setup commands
      const result = await apiService.runSetupCommands(project.id, selectedBranch);
      
      setExecutionResult({
        success: result.success,
        logs: result.logs,
        timestamp: new Date().toISOString(),
        branch: selectedBranch
      });

    } catch (error: any) {
      onError(error.message || 'Failed to run setup commands');
      setExecutionResult({
        success: false,
        logs: [error.message || 'Execution failed'],
        timestamp: new Date().toISOString(),
        branch: selectedBranch
      });
    } finally {
      setRunning(false);
    }
  };

  const handleReset = () => {
    setCommands(project.configuration?.setup_commands || '');
    onUnsavedChanges(false);
  };

  const exampleCommands = `cd backend
python -m pip install -r requirements.txt
python api.py &

cd ../frontend
npm install
npm run build
npm start`;

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={2}>
        <BuildIcon color="primary" />
        <Typography variant="h6">
          Setup Commands
        </Typography>
      </Box>

      <Typography variant="body2" color="text.secondary" paragraph>
        Specify the commands to run when setting up the sandbox environment.
        These commands will be executed during the validation pipeline.
      </Typography>

      {/* Success Alert */}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Setup commands saved successfully!
        </Alert>
      )}

      {/* Commands Input */}
      <TextField
        fullWidth
        multiline
        rows={8}
        value={commands}
        onChange={(e) => setCommands(e.target.value)}
        placeholder="Enter setup commands (one per line)..."
        variant="outlined"
        sx={{ mb: 2 }}
        disabled={loading || running}
      />

      {/* Branch Selection */}
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Branch</InputLabel>
        <Select
          value={selectedBranch}
          onChange={(e) => setSelectedBranch(e.target.value)}
          label="Branch"
          disabled={loading || running}
        >
          {branches.map((branch) => (
            <MenuItem key={branch} value={branch}>
              {branch}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Action Buttons */}
      <Box display="flex" gap={1} mb={2}>
        <Button
          variant="outlined"
          onClick={handleReset}
          disabled={loading || running || commands === (project.configuration?.setup_commands || '')}
        >
          Reset
        </Button>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={loading || running || commands === (project.configuration?.setup_commands || '')}
        >
          Save
        </Button>
        <Button
          variant="contained"
          color="success"
          startIcon={running ? <CircularProgress size={20} /> : <PlayIcon />}
          onClick={handleRun}
          disabled={loading || running || !commands.trim()}
        >
          {running ? 'Running...' : 'Run'}
        </Button>
      </Box>

      {/* Execution Result */}
      {executionResult && (
        <Accordion sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" gap={1}>
              {executionResult.success ? (
                <CheckCircleIcon color="success" />
              ) : (
                <ErrorIcon color="error" />
              )}
              <Typography>
                Execution Result - {executionResult.success ? 'Success' : 'Failed'}
              </Typography>
              <Chip
                label={executionResult.branch}
                size="small"
                variant="outlined"
              />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Executed at: {new Date(executionResult.timestamp).toLocaleString()}
            </Typography>
            <Paper 
              sx={{ 
                p: 2, 
                bgcolor: 'grey.100', 
                fontFamily: 'monospace',
                maxHeight: 300,
                overflow: 'auto'
              }}
            >
              <List dense>
                {executionResult.logs.map((log, index) => (
                  <ListItem key={index} sx={{ py: 0.25 }}>
                    <ListItemText
                      primary={
                        <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>
                          {log}
                        </Typography>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Example Commands */}
      <Paper sx={{ p: 2, bgcolor: 'grey.50', mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Example Setup Commands:
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontFamily: 'monospace' }}>
          {exampleCommands}
        </Typography>
      </Paper>

      {/* Current Status */}
      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Current Status:
        </Typography>
        <Chip
          label={commands.trim() ? 'Commands Configured' : 'No Commands Set'}
          color={commands.trim() ? 'success' : 'default'}
          variant="outlined"
        />
      </Box>
    </Box>
  );
};

export default SetupCommandsTab;
