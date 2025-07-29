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
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Divider,
  Chip,
  Tooltip,
  InputAdornment
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Save as SaveIcon,
  Security as SecurityIcon,
  ContentPaste as PasteIcon
} from '@mui/icons-material';

interface Secret {
  key: string;
  value: string;
  description?: string;
  sensitive: boolean;
}

interface SecretsDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: number;
  projectName: string;
  currentSecrets: Secret[];
  onSave: (secrets: Secret[]) => Promise<void>;
}

const SecretsDialog: React.FC<SecretsDialogProps> = ({
  open,
  onClose,
  projectId,
  projectName,
  currentSecrets,
  onSave
}) => {
  const [secrets, setSecrets] = useState<Secret[]>(currentSecrets);
  const [tabValue, setTabValue] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [visibleSecrets, setVisibleSecrets] = useState<Set<string>>(new Set());
  
  // Individual secret form
  const [newSecretKey, setNewSecretKey] = useState('');
  const [newSecretValue, setNewSecretValue] = useState('');
  const [newSecretDescription, setNewSecretDescription] = useState('');
  
  // Bulk paste form
  const [bulkSecretsText, setBulkSecretsText] = useState('');

  useEffect(() => {
    setSecrets(currentSecrets);
  }, [currentSecrets]);

  const handleAddSecret = () => {
    if (newSecretKey.trim() && newSecretValue.trim()) {
      const newSecret: Secret = {
        key: newSecretKey.trim(),
        value: newSecretValue.trim(),
        description: newSecretDescription.trim() || undefined,
        sensitive: true
      };
      
      // Check if key already exists
      const existingIndex = secrets.findIndex(s => s.key === newSecret.key);
      if (existingIndex >= 0) {
        // Update existing secret
        const updatedSecrets = [...secrets];
        updatedSecrets[existingIndex] = newSecret;
        setSecrets(updatedSecrets);
      } else {
        // Add new secret
        setSecrets([...secrets, newSecret]);
      }
      
      // Clear form
      setNewSecretKey('');
      setNewSecretValue('');
      setNewSecretDescription('');
    }
  };

  const handleRemoveSecret = (key: string) => {
    setSecrets(secrets.filter(s => s.key !== key));
    setVisibleSecrets(prev => {
      const newSet = new Set(prev);
      newSet.delete(key);
      return newSet;
    });
  };

  const handleToggleVisibility = (key: string) => {
    setVisibleSecrets(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };

  const handleBulkPaste = () => {
    if (!bulkSecretsText.trim()) return;

    const lines = bulkSecretsText.trim().split('\n');
    const newSecrets: Secret[] = [];
    
    for (const line of lines) {
      const trimmedLine = line.trim();
      if (!trimmedLine || trimmedLine.startsWith('#')) continue;
      
      const equalIndex = trimmedLine.indexOf('=');
      if (equalIndex > 0) {
        const key = trimmedLine.substring(0, equalIndex).trim();
        const value = trimmedLine.substring(equalIndex + 1).trim();
        
        if (key && value) {
          newSecrets.push({
            key,
            value,
            sensitive: true
          });
        }
      }
    }
    
    if (newSecrets.length > 0) {
      // Merge with existing secrets, updating duplicates
      const updatedSecrets = [...secrets];
      
      for (const newSecret of newSecrets) {
        const existingIndex = updatedSecrets.findIndex(s => s.key === newSecret.key);
        if (existingIndex >= 0) {
          updatedSecrets[existingIndex] = newSecret;
        } else {
          updatedSecrets.push(newSecret);
        }
      }
      
      setSecrets(updatedSecrets);
      setBulkSecretsText('');
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(secrets);
    } catch (error) {
      console.error('Failed to save secrets:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const commonSecrets = [
    { key: 'CODEGEN_ORG_ID', description: 'Codegen organization ID' },
    { key: 'CODEGEN_API_TOKEN', description: 'Codegen API token' },
    { key: 'GITHUB_TOKEN', description: 'GitHub personal access token' },
    { key: 'GEMINI_API_KEY', description: 'Gemini API key for web-eval-agent' },
    { key: 'DATABASE_URL', description: 'Database connection string' },
    { key: 'REDIS_URL', description: 'Redis connection string' },
    { key: 'JWT_SECRET', description: 'JWT signing secret' },
    { key: 'ENCRYPTION_KEY', description: 'Data encryption key' }
  ];

  const maskValue = (value: string) => {
    if (value.length <= 8) {
      return '*'.repeat(value.length);
    }
    return value.substring(0, 4) + '*'.repeat(value.length - 8) + value.substring(value.length - 4);
  };

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
          <SecurityIcon />
          <Typography variant="h6">
            Secrets - {projectName}
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box display="flex" flexDirection="column" gap={3}>
          <Alert severity="info">
            Secrets are encrypted and stored securely. They will be available as environment variables during deployment and validation.
          </Alert>

          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab label="Add Individual Secret" />
            <Tab label="Bulk Paste" />
          </Tabs>

          {/* Individual Secret Tab */}
          {tabValue === 0 && (
            <Box display="flex" flexDirection="column" gap={2}>
              <Typography variant="h6">Add New Secret</Typography>
              
              <TextField
                fullWidth
                label="Environment Variable Name"
                placeholder="e.g., API_KEY, DATABASE_URL"
                value={newSecretKey}
                onChange={(e) => setNewSecretKey(e.target.value.toUpperCase())}
                helperText="Use UPPERCASE with underscores (e.g., MY_API_KEY)"
              />
              
              <TextField
                fullWidth
                label="Value"
                type="password"
                placeholder="Enter the secret value"
                value={newSecretValue}
                onChange={(e) => setNewSecretValue(e.target.value)}
              />
              
              <TextField
                fullWidth
                label="Description (Optional)"
                placeholder="Brief description of what this secret is for"
                value={newSecretDescription}
                onChange={(e) => setNewSecretDescription(e.target.value)}
              />
              
              <Button
                variant="outlined"
                onClick={handleAddSecret}
                disabled={!newSecretKey.trim() || !newSecretValue.trim()}
                startIcon={<AddIcon />}
              >
                Add Secret
              </Button>

              {/* Common Secrets */}
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Common Secrets
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {commonSecrets.map((secret) => (
                    <Tooltip key={secret.key} title={secret.description}>
                      <Chip
                        label={secret.key}
                        variant="outlined"
                        size="small"
                        onClick={() => {
                          setNewSecretKey(secret.key);
                          setNewSecretDescription(secret.description);
                        }}
                        sx={{ cursor: 'pointer' }}
                      />
                    </Tooltip>
                  ))}
                </Box>
              </Box>
            </Box>
          )}

          {/* Bulk Paste Tab */}
          {tabValue === 1 && (
            <Box display="flex" flexDirection="column" gap={2}>
              <Typography variant="h6">Paste Environment Variables</Typography>
              <Typography variant="body2" color="text.secondary">
                Paste your environment variables in KEY=VALUE format, one per line.
              </Typography>
              
              <TextField
                fullWidth
                multiline
                rows={8}
                placeholder={`CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99
GITHUB_TOKEN=github_pat_11BPJSHDQ0...
GEMINI_API_KEY=AIzaSyBXmhlHudrD4zXiv...

# Comments are ignored
DATABASE_URL=postgresql://user:pass@localhost/db`}
                value={bulkSecretsText}
                onChange={(e) => setBulkSecretsText(e.target.value)}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <Tooltip title="Paste from clipboard">
                        <IconButton
                          onClick={async () => {
                            try {
                              const text = await navigator.clipboard.readText();
                              setBulkSecretsText(text);
                            } catch (err) {
                              console.error('Failed to read clipboard:', err);
                            }
                          }}
                        >
                          <PasteIcon />
                        </IconButton>
                      </Tooltip>
                    </InputAdornment>
                  )
                }}
              />
              
              <Button
                variant="outlined"
                onClick={handleBulkPaste}
                disabled={!bulkSecretsText.trim()}
                startIcon={<AddIcon />}
              >
                Parse and Add Secrets
              </Button>
            </Box>
          )}

          <Divider />

          {/* Current Secrets List */}
          <Box>
            <Typography variant="h6" gutterBottom>
              Current Secrets ({secrets.length})
            </Typography>
            
            {secrets.length === 0 ? (
              <Alert severity="info">
                No secrets configured. Add secrets above to get started.
              </Alert>
            ) : (
              <List>
                {secrets.map((secret) => (
                  <ListItem
                    key={secret.key}
                    sx={{
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 1,
                      mb: 1
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1" fontWeight="medium">
                            {secret.key}
                          </Typography>
                          <Chip label="encrypted" size="small" color="success" />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography
                            variant="body2"
                            fontFamily="monospace"
                            sx={{ mt: 0.5 }}
                          >
                            {visibleSecrets.has(secret.key) ? secret.value : maskValue(secret.value)}
                          </Typography>
                          {secret.description && (
                            <Typography variant="caption" color="text.secondary">
                              {secret.description}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title={visibleSecrets.has(secret.key) ? "Hide value" : "Show value"}>
                        <IconButton
                          edge="end"
                          onClick={() => handleToggleVisibility(secret.key)}
                          size="small"
                        >
                          {visibleSecrets.has(secret.key) ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Remove secret">
                        <IconButton
                          edge="end"
                          onClick={() => handleRemoveSecret(secret.key)}
                          size="small"
                          sx={{ ml: 1 }}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            )}
          </Box>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={isSaving}
          startIcon={isSaving ? <CircularProgress size={16} /> : <SaveIcon />}
        >
          Save Secrets
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SecretsDialog;

