import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  Paper,
  Chip,
  Divider,
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Preview as PreviewIcon,
} from '@mui/icons-material';
import { ProjectConfiguration } from '../../services/api';

interface PlanningStatementTabProps {
  projectId: number;
  configuration: ProjectConfiguration;
  onUpdate: (updates: Partial<ProjectConfiguration>) => Promise<void>;
  onUnsavedChanges: (hasChanges: boolean) => void;
  loading: boolean;
}

const PlanningStatementTab: React.FC<PlanningStatementTabProps> = ({
  projectId,
  configuration,
  onUpdate,
  onUnsavedChanges,
  loading,
}) => {
  const [planningStatement, setPlanningStatement] = useState(configuration.planning_statement || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    setPlanningStatement(configuration.planning_statement || '');
  }, [configuration.planning_statement]);

  useEffect(() => {
    const hasChanges = planningStatement !== (configuration.planning_statement || '');
    onUnsavedChanges(hasChanges);
  }, [planningStatement, configuration.planning_statement, onUnsavedChanges]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      await onUpdate({ planning_statement: planningStatement });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save planning statement');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setPlanningStatement(configuration.planning_statement || '');
    setError(null);
  };

  const exampleStatements = [
    {
      name: 'React/TypeScript Project',
      statement: `You are working on a React TypeScript project. Always follow these guidelines:
- Use TypeScript for all components and utilities
- Follow React best practices and hooks patterns
- Use Material-UI for consistent styling
- Implement proper error handling and loading states
- Write clean, maintainable, and well-documented code
- Ensure responsive design for all components
- Use proper TypeScript types and interfaces`,
    },
    {
      name: 'Python/FastAPI Backend',
      statement: `You are working on a Python FastAPI backend project. Follow these guidelines:
- Use Python 3.11+ features and type hints
- Follow FastAPI best practices for API design
- Implement proper async/await patterns
- Use SQLAlchemy for database operations
- Add comprehensive error handling and logging
- Write unit tests for all endpoints
- Follow PEP 8 style guidelines
- Use proper dependency injection patterns`,
    },
    {
      name: 'Full Stack Application',
      statement: `You are working on a full-stack application with React frontend and Python backend:
- Maintain consistency between frontend and backend
- Use RESTful API conventions
- Implement proper authentication and authorization
- Follow security best practices
- Ensure proper error handling on both ends
- Write comprehensive tests
- Use proper logging and monitoring
- Optimize for performance and scalability`,
    },
    {
      name: 'Code Quality Focus',
      statement: `Focus on code quality and maintainability:
- Write self-documenting code with clear variable names
- Keep functions small and focused on single responsibilities
- Implement proper error handling and edge case management
- Add comprehensive comments for complex logic
- Follow established coding conventions and patterns
- Ensure code is testable and well-tested
- Optimize for readability over cleverness
- Consider future maintainability in all decisions`,
    },
  ];

  const handleUseExample = (example: typeof exampleStatements[0]) => {
    setPlanningStatement(example.statement);
  };

  const previewText = `Project Context: ${configuration.repository_rules || 'No repository rules set'}

Planning Statement:
${planningStatement}

User Target: [This will be replaced with the user's actual target text]`;

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Planning Statement
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Define the default context and instructions that will be sent to the Codegen agent 
        along with the user's target text. This helps ensure consistent behavior across all agent runs.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Planning statement saved successfully!
        </Alert>
      )}

      <TextField
        fullWidth
        multiline
        rows={12}
        label="Planning Statement"
        placeholder="Enter the context and instructions for the AI agent..."
        value={planningStatement}
        onChange={(e) => setPlanningStatement(e.target.value)}
        sx={{ mb: 2 }}
        helperText="This text will be prepended to every agent run for this project"
      />

      <Box display="flex" gap={2} mb={3}>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving || loading || planningStatement === (configuration.planning_statement || '')}
        >
          {saving ? 'Saving...' : 'Save Statement'}
        </Button>
        
        <Button
          variant="outlined"
          startIcon={<PreviewIcon />}
          onClick={() => setShowPreview(!showPreview)}
        >
          {showPreview ? 'Hide Preview' : 'Show Preview'}
        </Button>

        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleReset}
          disabled={saving || loading}
        >
          Reset
        </Button>
      </Box>

      {/* Preview */}
      {showPreview && (
        <Paper sx={{ p: 2, mb: 3, backgroundColor: 'grey.50' }}>
          <Typography variant="subtitle1" gutterBottom>
            Preview: Complete Agent Prompt
          </Typography>
          <Typography variant="body2" component="pre" sx={{ 
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace',
            fontSize: '0.875rem',
          }}>
            {previewText}
          </Typography>
        </Paper>
      )}

      <Divider sx={{ my: 3 }} />

      {/* Example Statements */}
      <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
        <Typography variant="subtitle1" gutterBottom>
          Example Planning Statements
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Click on any example to use it as a starting point:
        </Typography>
        
        <Box display="flex" flexDirection="column" gap={2}>
          {exampleStatements.map((example, index) => (
            <Paper
              key={index}
              sx={{ 
                p: 2, 
                cursor: 'pointer',
                border: 1,
                borderColor: 'divider',
                '&:hover': { backgroundColor: 'action.hover' }
              }}
              onClick={() => handleUseExample(example)}
            >
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="subtitle2">{example.name}</Typography>
                <Chip label="Click to use" size="small" variant="outlined" />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ 
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}>
                {example.statement}
              </Typography>
            </Paper>
          ))}
        </Box>
      </Paper>

      <Box mt={3}>
        <Alert severity="info">
          <Typography variant="body2">
            <strong>How it works:</strong> When a user starts an agent run, the complete prompt 
            sent to Codegen will include: Repository Rules + Planning Statement + User's Target Text. 
            This ensures the agent has full context about your project and requirements.
          </Typography>
        </Alert>
      </Box>
    </Box>
  );
};

export default PlanningStatementTab;

