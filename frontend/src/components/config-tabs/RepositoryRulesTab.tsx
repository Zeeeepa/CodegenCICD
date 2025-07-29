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
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { ProjectConfiguration } from '../../services/api';

interface RepositoryRulesTabProps {
  projectId: number;
  configuration: ProjectConfiguration;
  onUpdate: (updates: Partial<ProjectConfiguration>) => Promise<void>;
  onUnsavedChanges: (hasChanges: boolean) => void;
  loading: boolean;
}

const RepositoryRulesTab: React.FC<RepositoryRulesTabProps> = ({
  projectId,
  configuration,
  onUpdate,
  onUnsavedChanges,
  loading,
}) => {
  const [rules, setRules] = useState(configuration.repository_rules || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setRules(configuration.repository_rules || '');
  }, [configuration.repository_rules]);

  useEffect(() => {
    const hasChanges = rules !== (configuration.repository_rules || '');
    onUnsavedChanges(hasChanges);
  }, [rules, configuration.repository_rules, onUnsavedChanges]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      await onUpdate({ repository_rules: rules });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save repository rules');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setRules(configuration.repository_rules || '');
    setError(null);
  };

  const exampleRules = [
    'Use TypeScript for all new code',
    'Follow existing code style conventions',
    'Add proper error handling and logging',
    'Include unit tests for new features',
    'Document all public APIs',
    'Use meaningful variable and function names',
    'Keep functions small and focused',
    'Handle edge cases appropriately',
  ];

  const handleAddExample = (rule: string) => {
    const currentRules = rules.split('\n').filter(r => r.trim());
    if (!currentRules.includes(rule)) {
      setRules(prev => prev ? `${prev}\n${rule}` : rule);
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Repository Rules
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Specify any additional rules you want the agent to follow for this repository.
        These rules will be included in every agent run to ensure consistent behavior.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Repository rules saved successfully!
        </Alert>
      )}

      <TextField
        fullWidth
        multiline
        rows={12}
        label="Repository Rules"
        placeholder="Enter rules, one per line..."
        value={rules}
        onChange={(e) => setRules(e.target.value)}
        sx={{ mb: 2 }}
        helperText="Each line should contain a single rule or guideline"
      />

      <Box display="flex" gap={2} mb={3}>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving || loading || rules === (configuration.repository_rules || '')}
        >
          {saving ? 'Saving...' : 'Save Rules'}
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

      <Divider sx={{ my: 3 }} />

      <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
        <Typography variant="subtitle1" gutterBottom>
          Example Rules
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Click on any example rule to add it to your configuration:
        </Typography>
        
        <Box display="flex" flexWrap="wrap" gap={1}>
          {exampleRules.map((rule, index) => (
            <Chip
              key={index}
              label={rule}
              variant="outlined"
              clickable
              onClick={() => handleAddExample(rule)}
              sx={{ mb: 1 }}
            />
          ))}
        </Box>
      </Paper>

      <Box mt={3}>
        <Alert severity="info">
          <Typography variant="body2">
            <strong>How it works:</strong> These rules will be automatically prepended to every agent run 
            for this project. The agent will consider these rules when generating code, making decisions, 
            and providing recommendations.
          </Typography>
        </Alert>
      </Box>
    </Box>
  );
};

export default RepositoryRulesTab;

