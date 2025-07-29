import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  PlayArrow as PlayIcon,
  Save as SaveIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Terminal as TerminalIcon
} from '@mui/icons-material';

interface SetupCommandsDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: number;
  projectName: string;
  currentCommands: string[];
  availableBranches: string[];
  selectedBranch: string;
  onSave: (commands: string[], branch: string) => Promise<void>;
  onRun: (commands: string[], branch: string) => Promise<any>;
}

interface CommandExecution {
  command: string;
  status: 'pending' | 'running' | 'success' | 'error';
  output: string;
  error?: string;
  duration?: number;
}

const SetupCommandsDialog: React.FC<SetupCommandsDialogProps> = ({
  open,
  onClose,
  projectId,
  projectName,
  currentCommands,
  availableBranches,
  selectedBranch,
  onSave,
  onRun
}) => {
  const [commands, setCommands] = useState<string[]>(currentCommands);
  const [branch, setBranch] = useState(selectedBranch);
  const [newCommand, setNewCommand] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [executionResults, setExecutionResults] = useState<CommandExecution[]>([]);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    setCommands(currentCommands);
    setBranch(selectedBranch);
  }, [currentCommands, selectedBranch]);

  const handleAddCommand = () => {
    if (newCommand.trim()) {
      setCommands([...commands, newCommand.trim()]);
      setNewCommand('');
    }
  };

  const handleRemoveCommand = (index: number) => {
    setCommands(commands.filter((_, i) => i !== index));
  };

  const handleEditCommand = (index: number, newValue: string) => {
    const updatedCommands = [...commands];
    updatedCommands[index] = newValue;
    setCommands(updatedCommands);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(commands, branch);
    } catch (error) {
      console.error('Failed to save setup commands:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRun = async () => {
    if (commands.length === 0) {
      return;
    }

    setIsRunning(true);
    setShowResults(true);
    
    // Initialize execution results
    const initialResults: CommandExecution[] = commands.map(cmd => ({
      command: cmd,
      status: 'pending',
      output: ''
    }));
    setExecutionResults(initialResults);

    try {
      const result = await onRun(commands, branch);
      
      if (result.success) {
        // Update results with actual execution data
        const updatedResults = commands.map((cmd, index) => ({
          command: cmd,
          status: 'success' as const,
          output: result.logs?.[index] || 'Command executed successfully',
          duration: result.duration || 0
        }));
        setExecutionResults(updatedResults);
      } else {
        // Handle execution failure
        const failedResults = commands.map((cmd, index) => ({
          command: cmd,
          status: index === 0 ? 'error' as const : 'pending' as const,
          output: index === 0 ? (result.error || 'Command failed') : '',
          error: index === 0 ? result.error : undefined
        }));
        setExecutionResults(failedResults);
      }
    } catch (error) {
      // Handle unexpected error
      const errorResults = commands.map((cmd, index) => ({
        command: cmd,
        status: index === 0 ? 'error' as const : 'pending' as const,
        output: index === 0 ? `Error: ${error}` : '',
        error: index === 0 ? String(error) : undefined
      }));
      setExecutionResults(errorResults);
    } finally {
      setIsRunning(false);
    }
  };

  const getStatusColor = (status: CommandExecution['status']) => {
    switch (status) {
      case 'success': return 'success';
      case 'error': return 'error';
      case 'running': return 'primary';
      case 'pending': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: CommandExecution['status']) => {
    switch (status) {
      case 'running': return <CircularProgress size={16} />;
      case 'success': return '✓';
      case 'error': return '✗';
      case 'pending': return '○';
      default: return '○';
    }
  };

  const predefinedCommands = [
    'cd backend && pip install -r requirements.txt',
    'cd frontend && npm install',
    'cd frontend && npm run build',
    'python manage.py migrate',
    'npm run dev',
    'docker-compose up -d',
    'make install',
    'yarn install && yarn build'
  ];

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
        <Box display="flex" alignItems="center" gap={1}>
          <TerminalIcon />
          <Typography variant="h6">
            Setup Commands - {projectName}
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box display="flex" flexDirection="column" gap={3}>
          {/* Branch Selection */}
          <FormControl fullWidth>
            <InputLabel>Branch</InputLabel>
            <Select
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              label="Branch"
            >
              {availableBranches.map((branchName) => (
                <MenuItem key={branchName} value={branchName}>
                  {branchName}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Commands Section */}
          <Box>
            <Typography variant="h6" gutterBottom>
              Setup Commands
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Specify the commands to run when setting up the sandbox environment.
            </Typography>

            {/* Add New Command */}
            <Box display="flex" gap={1} mb={2}>
              <TextField
                fullWidth
                placeholder="Enter a command (e.g., npm install)"
                value={newCommand}
                onChange={(e) => setNewCommand(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleAddCommand();
                  }
                }}
              />
              <Button
                variant="outlined"
                onClick={handleAddCommand}
                disabled={!newCommand.trim()}
                startIcon={<AddIcon />}
              >
                Add
              </Button>
            </Box>

            {/* Predefined Commands */}
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2">Common Commands</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {predefinedCommands.map((cmd, index) => (
                    <Chip
                      key={index}
                      label={cmd}
                      variant="outlined"
                      size="small"
                      onClick={() => {
                        if (!commands.includes(cmd)) {
                          setCommands([...commands, cmd]);
                        }
                      }}
                      sx={{ cursor: 'pointer' }}
                    />
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>

            {/* Current Commands List */}
            <Box mt={2}>
              {commands.length === 0 ? (
                <Alert severity="info">
                  No setup commands configured. Add commands above to get started.
                </Alert>
              ) : (
                <List>
                  {commands.map((command, index) => (
                    <ListItem
                      key={index}
                      sx={{
                        border: '1px solid',
                        borderColor: 'divider',
                        borderRadius: 1,
                        mb: 1
                      }}
                    >
                      <ListItemText
                        primary={
                          <TextField
                            fullWidth
                            value={command}
                            onChange={(e) => handleEditCommand(index, e.target.value)}
                            variant="standard"
                            InputProps={{
                              disableUnderline: true
                            }}
                          />
                        }
                        secondary={`Command ${index + 1}`}
                      />
                      <Tooltip title="Remove command">
                        <IconButton
                          edge="end"
                          onClick={() => handleRemoveCommand(index)}
                          size="small"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>
          </Box>

          {/* Execution Results */}
          {showResults && (
            <Accordion expanded={showResults}>
              <AccordionSummary>
                <Typography variant="h6">Execution Results</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <List>
                  {executionResults.map((result, index) => (
                    <ListItem key={index} sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                      <Box display="flex" alignItems="center" gap={1} width="100%">
                        <Chip
                          icon={getStatusIcon(result.status)}
                          label={result.status}
                          color={getStatusColor(result.status)}
                          size="small"
                        />
                        <Typography variant="body2" fontFamily="monospace">
                          {result.command}
                        </Typography>
                        {result.duration && (
                          <Typography variant="caption" color="text.secondary">
                            ({result.duration}ms)
                          </Typography>
                        )}
                      </Box>
                      {result.output && (
                        <Box
                          mt={1}
                          p={1}
                          bgcolor="grey.100"
                          borderRadius={1}
                          width="100%"
                          sx={{
                            fontFamily: 'monospace',
                            fontSize: '0.875rem',
                            whiteSpace: 'pre-wrap',
                            maxHeight: '200px',
                            overflow: 'auto'
                          }}
                        >
                          {result.output}
                        </Box>
                      )}
                      {result.error && (
                        <Alert severity="error" sx={{ mt: 1, width: '100%' }}>
                          {result.error}
                        </Alert>
                      )}
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          disabled={isSaving}
          startIcon={isSaving ? <CircularProgress size={16} /> : <SaveIcon />}
        >
          Save
        </Button>
        <Button
          variant="contained"
          onClick={handleRun}
          disabled={isRunning || commands.length === 0}
          startIcon={isRunning ? <CircularProgress size={16} /> : <PlayIcon />}
        >
          Run
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SetupCommandsDialog;

