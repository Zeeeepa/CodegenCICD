import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Alert,
  Paper,
  Chip
} from '@mui/material';
import {
  Save as SaveIcon,
  Description as DescriptionIcon
} from '@mui/icons-material';
import { Project } from '../../types';
import { useApp } from '../../contexts/AppContext';
import { apiService } from '../../services/api';

interface PlanningStatementTabProps {
  project: Project;
  onError: (error: string | null) => void;
  onUnsavedChanges: (hasChanges: boolean) => void;
}

const PlanningStatementTab: React.FC<PlanningStatementTabProps> = ({
  project,
  onError,
  onUnsavedChanges
}) => {
  const { updateProject } = useApp();
  const [statement, setStatement] = useState(project.configuration?.planning_statement || '');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // Track changes
  useEffect(() => {
    const hasChanges = statement !== (project.configuration?.planning_statement || '');
    onUnsavedChanges(hasChanges);
  }, [statement, project.configuration?.planning_statement, onUnsavedChanges]);

  const handleSave = async () => {
    try {
      setLoading(true);
      setSuccess(false);
      onError(null);

      // Update project configuration
      await apiService.updateProjectConfiguration(project.id, {
        planning_statement: statement.trim() || undefined
      });

      // Update local project state
      await updateProject(project.id, {
        configuration: {
          ...project.configuration,
          planning_statement: statement.trim() || undefined
        }
      });

      setSuccess(true);
      onUnsavedChanges(false);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);

    } catch (error: any) {
      onError(error.message || 'Failed to save planning statement');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setStatement(project.configuration?.planning_statement || '');
    onUnsavedChanges(false);
  };

  const exampleStatement = `Project Context: <Project='${project.name}'>

You are working on a ${project.description || 'software project'} located at ${project.github_repository}.

Key Guidelines:
• Follow the repository's coding standards and conventions
• Ensure all changes are well-tested and documented
• Consider the project's architecture and existing patterns
• Write clear, maintainable code with proper error handling
• Include appropriate logging and monitoring
• Follow security best practices
• Update documentation when making significant changes

Project-Specific Instructions:
• Use TypeScript for all frontend code
• Follow React best practices and hooks patterns
• Implement proper error boundaries and loading states
• Ensure responsive design for all UI components
• Write unit tests for new functionality
• Follow the existing API patterns and conventions

When creating or modifying code:
1. Analyze the existing codebase structure
2. Follow established patterns and conventions
3. Ensure compatibility with existing functionality
4. Add appropriate tests and documentation
5. Consider performance and security implications

User Request: `;

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={2}>
        <DescriptionIcon color="primary" />
        <Typography variant="h6">
          Planning Statement
        </Typography>
      </Box>

      <Typography variant="body2" color="text.secondary" paragraph>
        Define a planning statement that will be prepended to every agent run for this project.
        This helps provide consistent context and guidelines to the AI agent.
      </Typography>

      {/* Success Alert */}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Planning statement saved successfully! This will be included in all future agent runs.
        </Alert>
      )}

      {/* Statement Input */}
      <TextField
        fullWidth
        multiline
        rows={15}
        value={statement}
        onChange={(e) => setStatement(e.target.value)}
        placeholder="Enter your planning statement..."
        variant="outlined"
        sx={{ mb: 2 }}
        disabled={loading}
      />

      {/* Character Count */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="caption" color="text.secondary">
          {statement.length} characters
        </Typography>
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            onClick={handleReset}
            disabled={loading || statement === (project.configuration?.planning_statement || '')}
          >
            Reset
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={loading || statement === (project.configuration?.planning_statement || '')}
          >
            Save Statement
          </Button>
        </Box>
      </Box>

      {/* Usage Info */}
      {statement.trim() && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">
            <strong>How it works:</strong> When you start an agent run, this planning statement 
            will be automatically prepended to your target/goal text, providing consistent 
            context and guidelines to the AI agent.
          </Typography>
        </Alert>
      )}

      {/* Example Statement */}
      <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
        <Typography variant="subtitle2" gutterBottom>
          Example Planning Statement:
        </Typography>
        <Typography 
          variant="body2" 
          sx={{ 
            whiteSpace: 'pre-line', 
            fontFamily: 'monospace',
            fontSize: '0.8rem'
          }}
        >
          {exampleStatement}
        </Typography>
      </Paper>

      {/* Current Status */}
      <Box mt={2}>
        <Typography variant="subtitle2" gutterBottom>
          Current Status:
        </Typography>
        <Chip
          label={statement.trim() ? 'Planning Statement Configured' : 'No Planning Statement'}
          color={statement.trim() ? 'success' : 'default'}
          variant="outlined"
        />
      </Box>
    </Box>
  );
};

export default PlanningStatementTab;
