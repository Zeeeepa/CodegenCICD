import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Typography,
  Alert,
  Paper,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  ContentPaste as PasteIcon,
} from '@mui/icons-material';
import { ProjectConfiguration, ProjectSecret, configurationsApi } from '../../services/api';

interface SecretsTabProps {
  projectId: number;
  configuration: ProjectConfiguration;
  onUpdate: (updates: Partial<ProjectConfiguration>) => Promise<void>;
  onUnsavedChanges: (hasChanges: boolean) => void;
  loading: boolean;
}

interface SecretDialogData {
  key: string;
  value: string;
}

const SecretsTab: React.FC<SecretsTabProps> = ({
  projectId,
  configuration,
  onUpdate,
  onUnsavedChanges,
  loading,
}) => {
  const [secrets, setSecrets] = useState<ProjectSecret[]>([]);
  const [secretDialogOpen, setSecretDialogOpen] = useState(false);
  const [editingSecret, setEditingSecret] = useState<ProjectSecret | null>(null);
  const [secretDialogData, setSecretDialogData] = useState<SecretDialogData>({ key: '', value: '' });
  const [bulkSecretsText, setBulkSecretsText] = useState('');
  const [visibleSecrets, setVisibleSecrets] = useState<Set<number>>(new Set());
  const [activeTab, setActiveTab] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (projectId) {
      loadSecrets();
    }
  }, [projectId]);

  const loadSecrets = async () => {
    try {
      const response = await configurationsApi.getSecrets(projectId);
      setSecrets(response.data);
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load secrets');
      }
    }
  };

  const handleAddSecret = () => {
    setEditingSecret(null);
    setSecretDialogData({ key: '', value: '' });
    setSecretDialogOpen(true);
  };

  const handleEditSecret = (secret: ProjectSecret) => {
    setEditingSecret(secret);
    setSecretDialogData({ key: secret.key, value: secret.value });
    setSecretDialogOpen(true);
  };

  const handleDeleteSecret = async (secretId: number) => {
    if (!window.confirm('Are you sure you want to delete this secret?')) {
      return;
    }

    try {
      await configurationsApi.deleteSecret(projectId, secretId);
      setSecrets(prev => prev.filter(s => s.id !== secretId));
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete secret');
    }
  };

  const handleSaveSecret = async () => {
    if (!secretDialogData.key.trim() || !secretDialogData.value.trim()) {
      setError('Both key and value are required');
      return;
    }

    try {
      setError(null);
      
      if (editingSecret) {
        // Update existing secret
        const response = await configurationsApi.updateSecret(
          projectId,
          editingSecret.id,
          secretDialogData
        );
        setSecrets(prev => prev.map(s => s.id === editingSecret.id ? response.data : s));
      } else {
        // Create new secret
        const response = await configurationsApi.createSecret(projectId, secretDialogData);
        setSecrets(prev => [...prev, response.data]);
      }

      setSecretDialogOpen(false);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save secret');
    }
  };

  const handleBulkImport = async () => {
    if (!bulkSecretsText.trim()) {
      setError('Please enter secrets in KEY=VALUE format');
      return;
    }

    try {
      setError(null);
      const lines = bulkSecretsText.split('\n').filter(line => line.trim());
      const secretsToCreate: SecretDialogData[] = [];

      for (const line of lines) {
        const [key, ...valueParts] = line.split('=');
        if (key && valueParts.length > 0) {
          const value = valueParts.join('='); // Handle values with = signs
          secretsToCreate.push({ key: key.trim(), value: value.trim() });
        }
      }

      if (secretsToCreate.length === 0) {
        setError('No valid KEY=VALUE pairs found');
        return;
      }

      // Create secrets one by one
      const createdSecrets: ProjectSecret[] = [];
      for (const secretData of secretsToCreate) {
        try {
          const response = await configurationsApi.createSecret(projectId, secretData);
          createdSecrets.push(response.data);
        } catch (err) {
          console.error(`Failed to create secret ${secretData.key}:`, err);
        }
      }

      setSecrets(prev => [...prev, ...createdSecrets]);
      setBulkSecretsText('');
      setActiveTab(0); // Switch back to individual secrets tab
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to import secrets');
    }
  };

  const toggleSecretVisibility = (secretId: number) => {
    setVisibleSecrets(prev => {
      const newSet = new Set(prev);
      if (newSet.has(secretId)) {
        newSet.delete(secretId);
      } else {
        newSet.add(secretId);
      }
      return newSet;
    });
  };

  const exampleSecrets = `CODEGEN_ORG_ID=323
CODEGEN_TOKEN=sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99
GITHUB_TOKEN=github_pat_your-token-here
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://user:pass@localhost:5432/db`;

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Secrets Management
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Manage environment variables and secrets for this project. All values are encrypted and 
        securely stored. These will be available during validation pipeline execution.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Secrets updated successfully!
        </Alert>
      )}

      <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 2 }}>
        <Tab label="Individual Secrets" />
        <Tab label="Bulk Import" />
      </Tabs>

      {activeTab === 0 && (
        <Box>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="subtitle1">
              Environment Variables ({secrets.length})
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleAddSecret}
            >
              Add Secret
            </Button>
          </Box>

          {secrets.length === 0 ? (
            <Paper sx={{ p: 3, textAlign: 'center', backgroundColor: 'grey.50' }}>
              <Typography variant="body1" color="text.secondary" gutterBottom>
                No secrets configured
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Add your first secret to get started
              </Typography>
            </Paper>
          ) : (
            <List>
              {secrets.map((secret) => (
                <ListItem
                  key={secret.id}
                  sx={{
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 1,
                    mb: 1,
                  }}
                >
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="subtitle2">{secret.key}</Typography>
                        <Chip label="Encrypted" size="small" color="success" />
                      </Box>
                    }
                    secondary={
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {visibleSecrets.has(secret.id)
                          ? secret.value
                          : '•'.repeat(Math.min(secret.value.length, 20))
                        }
                      </Typography>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      size="small"
                      onClick={() => toggleSecretVisibility(secret.id)}
                    >
                      {visibleSecrets.has(secret.id) ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleEditSecret(secret)}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDeleteSecret(secret.id)}
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      )}

      {activeTab === 1 && (
        <Box>
          <Typography variant="subtitle1" gutterBottom>
            Bulk Import Secrets
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Paste your environment variables in KEY=VALUE format, one per line:
          </Typography>

          <TextField
            fullWidth
            multiline
            rows={12}
            label="Environment Variables"
            placeholder={exampleSecrets}
            value={bulkSecretsText}
            onChange={(e) => setBulkSecretsText(e.target.value)}
            sx={{ mb: 2 }}
            helperText="Format: KEY=VALUE (one per line)"
          />

          <Box display="flex" gap={2}>
            <Button
              variant="contained"
              startIcon={<PasteIcon />}
              onClick={handleBulkImport}
              disabled={!bulkSecretsText.trim()}
            >
              Import Secrets
            </Button>
            <Button
              variant="outlined"
              onClick={() => setBulkSecretsText(exampleSecrets)}
            >
              Use Example
            </Button>
          </Box>
        </Box>
      )}

      {/* Secret Dialog */}
      <Dialog open={secretDialogOpen} onClose={() => setSecretDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingSecret ? 'Edit Secret' : 'Add New Secret'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Environment Variable Name"
            placeholder="e.g., API_KEY, DATABASE_URL"
            value={secretDialogData.key}
            onChange={(e) => setSecretDialogData(prev => ({ ...prev, key: e.target.value }))}
            sx={{ mb: 2, mt: 1 }}
            required
          />
          <TextField
            fullWidth
            label="Value"
            placeholder="Enter the secret value"
            value={secretDialogData.value}
            onChange={(e) => setSecretDialogData(prev => ({ ...prev, value: e.target.value }))}
            type="password"
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSecretDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveSecret}
            disabled={!secretDialogData.key.trim() || !secretDialogData.value.trim()}
          >
            {editingSecret ? 'Update' : 'Add'} Secret
          </Button>
        </DialogActions>
      </Dialog>

      <Box mt={3}>
        <Alert severity="info">
          <Typography variant="body2">
            <strong>Security:</strong> All secrets are encrypted using Fernet encryption before 
            storage. They are only decrypted during validation pipeline execution and are never 
            logged or exposed in plain text.
          </Typography>
        </Alert>
      </Box>
    </Box>
  );
};

export default SecretsTab;

