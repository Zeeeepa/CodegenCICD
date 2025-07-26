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
  Rule as RuleIcon
} from '@mui/icons-material';
import { Project } from '../../types';
import { useApp } from '../../contexts/AppContext';
import { apiService } from '../../services/api';

interface RepositoryRulesTabProps {
  project: Project;
  onError: (error: string | null) => void;
  onUnsavedChanges: (hasChanges: boolean) => void;
}

const RepositoryRulesTab: React.FC<RepositoryRulesTabProps> = ({
  project,
  onError,
  onUnsavedChanges
}) => {
  const { updateProject } = useApp();
  const [rules, setRules] = useState(project.configuration?.repository_rules || '');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // Track changes
  useEffect(() => {
    const hasChanges = rules !== (project.configuration?.repository_rules || '');
    onUnsavedChanges(hasChanges);
  }, [rules, project.configuration?.repository_rules, onUnsavedChanges]);

  const handleSave = async () => {
    try {
      setLoading(true);
      setSuccess(false);
      onError(null);

      // Update project configuration
      await apiService.updateProjectConfiguration(project.id, {
        repository_rules: rules.trim() || undefined
      });

      // Update local project state
      await updateProject(project.id, {
        configuration: {
          ...project.configuration,
          repository_rules: rules.trim() || undefined
        }
      });

      setSuccess(true);
      onUnsavedChanges(false);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);

    } catch (error: any) {
      onError(error.message || 'Failed to save repository rules');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setRules(project.configuration?.repository_rules || '');
    onUnsavedChanges(false);
  };

  const exampleRules = `Example repository rules:
• Use TypeScript for all new code
• Follow conventional commit format
• Include unit tests for new features
• Update documentation for API changes
• Use semantic versioning for releases
• Ensure all CI checks pass before merging`;

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={2}>
        <RuleIcon color="primary" />
        <Typography variant="h6">
          Repository Rules
        </Typography>
      </Box>

      <Typography variant="body2" color="text.secondary" paragraph>
        Specify any additional rules you want the agent to follow for this repository.
        These rules will be included in every agent run to ensure consistent behavior.
      </Typography>

      {/* Success Alert */}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Repository rules saved successfully! The project card will now show a colored border.
        </Alert>
      )}

      {/* Rules Input */}
      <TextField
        fullWidth
        multiline
        rows={12}
        value={rules}
        onChange={(e) => setRules(e.target.value)}
        placeholder="Enter repository-specific rules and guidelines..."
        variant="outlined"
        sx={{ mb: 2 }}
        disabled={loading}
      />

      {/* Character Count */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="caption" color="text.secondary">
          {rules.length} characters
        </Typography>
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            onClick={handleReset}
            disabled={loading || rules === (project.configuration?.repository_rules || '')}
          >
            Reset
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={loading || rules === (project.configuration?.repository_rules || '')}
          >
            Save Rules
          </Button>
        </Box>
      </Box>

      {/* Visual Indicator Info */}
      {rules.trim() && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">
            <strong>Visual Indicator:</strong> When repository rules are configured, 
            the project card will display a colored border to indicate that custom rules are active.
          </Typography>
        </Alert>
      )}

      {/* Example Rules */}
      <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
        <Typography variant="subtitle2" gutterBottom>
          Example Repository Rules:
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontFamily: 'monospace' }}>
          {exampleRules}
        </Typography>
      </Paper>

      {/* Current Status */}
      <Box mt={2}>
        <Typography variant="subtitle2" gutterBottom>
          Current Status:
        </Typography>
        <Chip
          label={rules.trim() ? 'Rules Configured' : 'No Rules Set'}
          color={rules.trim() ? 'success' : 'default'}
          variant="outlined"
        />
      </Box>
    </Box>
  );
};

export default RepositoryRulesTab;
