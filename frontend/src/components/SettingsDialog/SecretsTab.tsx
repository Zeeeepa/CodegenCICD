import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Alert,
  Paper,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Divider
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  VpnKey as VpnKeyIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  ContentPaste as ContentPasteIcon
} from '@mui/icons-material';
import { Project, ProjectSecret } from '../../types';
import { useApp } from '../../contexts/AppContext';
import { apiService } from '../../services/api';

interface SecretsTabProps {
  project: Project;
  onError: (error: string | null) => void;
  onUnsavedChanges: (hasChanges: boolean) => void;
}

const SecretsTab: React.FC<SecretsTabProps> = ({
  project,
  onError,
  onUnsavedChanges
}) => {
  const { updateProject } = useApp();
  const [secrets, setSecrets] = useState<ProjectSecret[]>(project.configuration?.secrets || []);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addMode, setAddMode] = useState<'individual' | 'bulk'>('individual');
  const [newSecretKey, setNewSecretKey] = useState('');
  const [newSecretValue, setNewSecretValue] = useState('');
  const [bulkSecrets, setBulkSecrets] = useState('');
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});

  // Track changes
  useEffect(() => {
    const originalSecrets = project.configuration?.secrets || [];
    const hasChanges = JSON.stringify(secrets) !== JSON.stringify(originalSecrets);
    onUnsavedChanges(hasChanges);
  }, [secrets, project.configuration?.secrets, onUnsavedChanges]);

  const handleAddSecret = async () => {
    try {
      setLoading(true);
      onError(null);

      if (addMode === 'individual') {
        if (!newSecretKey.trim() || !newSecretValue.trim()) {
          onError('Both key and value are required');
          return;
        }

        // Check for duplicate keys
        if (secrets.some(s => s.key === newSecretKey.trim())) {
          onError('A secret with this key already exists');
          return;
        }

        // Add secret via API
        await apiService.createSecret(project.id, {
          key: newSecretKey.trim(),
          value: newSecretValue.trim()
        });

        // Add to local state
        const newSecret: ProjectSecret = {
          id: `temp_${Date.now()}`,
          project_id: project.id,
          key: newSecretKey.trim(),
          value: newSecretValue.trim(),
          created_at: new Date().toISOString()
        };

        setSecrets([...secrets, newSecret]);
        setNewSecretKey('');
        setNewSecretValue('');

      } else {
        // Bulk mode
        if (!bulkSecrets.trim()) {
          onError('Please enter environment variables');
          return;
        }

        const lines = bulkSecrets.split('\n').filter(line => line.trim());
        const newSecrets: ProjectSecret[] = [];

        for (const line of lines) {
          const [key, ...valueParts] = line.split('=');
          const value = valueParts.join('=');

          if (!key?.trim() || !value?.trim()) {
            onError(`Invalid format in line: ${line}`);
            return;
          }

          const trimmedKey = key.trim();
          
          // Check for duplicate keys
          if (secrets.some(s => s.key === trimmedKey) || newSecrets.some(s => s.key === trimmedKey)) {
            onError(`Duplicate key found: ${trimmedKey}`);
            return;
          }

          // Add secret via API
          await apiService.createSecret(project.id, {
            key: trimmedKey,
            value: value.trim()
          });

          newSecrets.push({
            id: `temp_${Date.now()}_${newSecrets.length}`,
            project_id: project.id,
            key: trimmedKey,
            value: value.trim(),
            created_at: new Date().toISOString()
          });
        }

        setSecrets([...secrets, ...newSecrets]);
        setBulkSecrets('');
      }

      setAddDialogOpen(false);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);

    } catch (error: any) {
      onError(error.message || 'Failed to add secret');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSecret = async (secretId: string) => {
    if (!window.confirm('Are you sure you want to delete this secret?')) {
      return;
    }

    try {
      setLoading(true);
      onError(null);

      // Delete via API
      await apiService.deleteSecret(project.id, secretId);

      // Remove from local state
      setSecrets(secrets.filter(s => s.id !== secretId));
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);

    } catch (error: any) {
      onError(error.message || 'Failed to delete secret');
    } finally {
      setLoading(false);
    }
  };

  const toggleShowValue = (secretId: string) => {
    setShowValues(prev => ({
      ...prev,
      [secretId]: !prev[secretId]
    }));
  };

  const handleCloseAddDialog = () => {
    setAddDialogOpen(false);
    setNewSecretKey('');
    setNewSecretValue('');
    setBulkSecrets('');
    setAddMode('individual');
  };

  const exampleBulkSecrets = `CODEGEN_ORG_ID=323
CODEGEN_TOKEN=sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
DATABASE_URL=postgresql://user:pass@localhost/db
API_KEY=your-api-key-here`;

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={2}>
        <VpnKeyIcon color="primary" />
        <Typography variant="h6">
          Secrets Management
        </Typography>
      </Box>

      <Typography variant="body2" color="text.secondary" paragraph>
        Manage environment variables and secrets for your project. 
        These will be securely stored and made available during validation runs.
      </Typography>

      {/* Success Alert */}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Secrets updated successfully!
        </Alert>
      )}

      {/* Add Secret Button */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="subtitle1">
          Environment Variables ({secrets.length})
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddDialogOpen(true)}
          disabled={loading}
        >
          Add Secret
        </Button>
      </Box>

      {/* Secrets List */}
      {secrets.length > 0 ? (
        <Paper sx={{ mb: 2 }}>
          <List>
            {secrets.map((secret, index) => (
              <React.Fragment key={secret.id}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="subtitle2" sx={{ fontFamily: 'monospace' }}>
                          {secret.key}
                        </Typography>
                        <Chip size="small" label="encrypted" color="success" variant="outlined" />
                      </Box>
                    }
                    secondary={
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          fontFamily: 'monospace',
                          color: 'text.secondary'
                        }}
                      >
                        {showValues[secret.id] 
                          ? secret.value 
                          : '•'.repeat(Math.min(secret.value.length, 20))
                        }
                      </Typography>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => toggleShowValue(secret.id)}
                      sx={{ mr: 1 }}
                    >
                      {showValues[secret.id] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                    <IconButton
                      edge="end"
                      onClick={() => handleDeleteSecret(secret.id)}
                      color="error"
                      disabled={loading}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
                {index < secrets.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </Paper>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center', mb: 2 }}>
          <VpnKeyIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No Secrets Configured
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Add environment variables and secrets for your project
          </Typography>
        </Paper>
      )}

      {/* Current Status */}
      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Current Status:
        </Typography>
        <Chip
          label={secrets.length > 0 ? `${secrets.length} Secrets Configured` : 'No Secrets Set'}
          color={secrets.length > 0 ? 'success' : 'default'}
          variant="outlined"
        />
      </Box>

      {/* Add Secret Dialog */}
      <Dialog
        open={addDialogOpen}
        onClose={handleCloseAddDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Add Environment Variables</DialogTitle>
        <DialogContent>
          <Tabs
            value={addMode}
            onChange={(e, newValue) => setAddMode(newValue)}
            sx={{ mb: 2 }}
          >
            <Tab label="Individual" value="individual" />
            <Tab label="Bulk Import" value="bulk" />
          </Tabs>

          {addMode === 'individual' ? (
            <Box>
              <TextField
                fullWidth
                label="Environment Variable Name"
                value={newSecretKey}
                onChange={(e) => setNewSecretKey(e.target.value)}
                placeholder="e.g., API_KEY"
                sx={{ mb: 2 }}
                disabled={loading}
              />
              <TextField
                fullWidth
                label="Value"
                value={newSecretValue}
                onChange={(e) => setNewSecretValue(e.target.value)}
                placeholder="Enter the secret value"
                type="password"
                disabled={loading}
              />
            </Box>
          ) : (
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Paste environment variables in KEY=VALUE format (one per line):
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={8}
                value={bulkSecrets}
                onChange={(e) => setBulkSecrets(e.target.value)}
                placeholder={exampleBulkSecrets}
                variant="outlined"
                sx={{ mb: 2, fontFamily: 'monospace' }}
                disabled={loading}
              />
              <Alert severity="info">
                Each line should be in the format: KEY=VALUE
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAddDialog} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleAddSecret}
            disabled={
              loading || 
              (addMode === 'individual' && (!newSecretKey.trim() || !newSecretValue.trim())) ||
              (addMode === 'bulk' && !bulkSecrets.trim())
            }
          >
            Add {addMode === 'bulk' ? 'Secrets' : 'Secret'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SecretsTab;
