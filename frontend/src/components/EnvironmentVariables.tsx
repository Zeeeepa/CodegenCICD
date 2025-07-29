import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Alert,
  Tooltip,
  Grid,
} from '@mui/material';
import {
  Search as SearchIcon,
  ContentCopy as ContentCopyIcon,
  ExpandMore as ExpandMoreIcon,
  Visibility as VisibilityIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface EnvironmentData {
  environment_variables: {
    [category: string]: {
      [key: string]: string;
    };
  };
  timestamp: number;
  total_variables: number;
}

const EnvironmentVariables: React.FC = () => {
  const [envData, setEnvData] = useState<EnvironmentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const fetchEnvironmentVariables = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/validation/environment');
      setEnvData(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch environment variables');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEnvironmentVariables();
  }, []);

  const handleCopyToClipboard = async (key: string, value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const filterVariables = (variables: { [key: string]: string }) => {
    if (!searchTerm) return variables;
    
    return Object.entries(variables).reduce((filtered, [key, value]) => {
      if (
        key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        value.toLowerCase().includes(searchTerm.toLowerCase())
      ) {
        filtered[key] = value;
      }
      return filtered;
    }, {} as { [key: string]: string });
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'codegen':
        return '🤖';
      case 'github':
        return '🐙';
      case 'gemini':
        return '💎';
      case 'cloudflare':
        return '☁️';
      case 'service_config':
        return '⚙️';
      case 'external_services':
        return '🔗';
      default:
        return '📝';
    }
  };

  const getCategoryDisplayName = (category: string) => {
    switch (category) {
      case 'codegen':
        return 'Codegen API';
      case 'github':
        return 'GitHub Integration';
      case 'gemini':
        return 'Gemini AI';
      case 'cloudflare':
        return 'Cloudflare Services';
      case 'service_config':
        return 'Service Configuration';
      case 'external_services':
        return 'External Services';
      default:
        return category.replace('_', ' ').toUpperCase();
    }
  };

  const getVariableStatus = (key: string, value: string) => {
    if (!value || value.trim() === '') {
      return { status: 'empty', color: 'error' as const, label: 'Empty' };
    }
    
    // Check for placeholder values
    const placeholders = ['your_', 'YOUR_', 'change_me', 'CHANGE_ME', 'example'];
    if (placeholders.some(placeholder => value.includes(placeholder))) {
      return { status: 'placeholder', color: 'warning' as const, label: 'Placeholder' };
    }
    
    // Check for proper format based on key
    if (key.includes('TOKEN') || key.includes('KEY')) {
      if (key.includes('CODEGEN') && !value.startsWith('sk-')) {
        return { status: 'invalid_format', color: 'warning' as const, label: 'Invalid Format' };
      }
      if (key.includes('GITHUB') && !value.startsWith('ghp_') && !value.startsWith('github_pat_')) {
        return { status: 'invalid_format', color: 'warning' as const, label: 'Invalid Format' };
      }
      if (key.includes('GEMINI') && !value.startsWith('AIza')) {
        return { status: 'invalid_format', color: 'warning' as const, label: 'Invalid Format' };
      }
    }
    
    return { status: 'valid', color: 'success' as const, label: 'Valid' };
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="center" py={4}>
            <Typography>Loading environment variables...</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
          <Box display="flex" justifyContent="center">
            <IconButton onClick={fetchEnvironmentVariables}>
              <RefreshIcon />
            </IconButton>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (!envData) {
    return null;
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
          <Box display="flex" alignItems="center" gap={1}>
            <VisibilityIcon color="primary" />
            <Typography variant="h5" component="div">
              Environment Variables
            </Typography>
            <Chip 
              label={`${envData.total_variables} variables`} 
              size="small" 
              color="primary" 
            />
          </Box>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchEnvironmentVariables}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>

        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search variables..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 3 }}
        />

        {Object.entries(envData.environment_variables).map(([category, variables]) => {
          const filteredVars = filterVariables(variables);
          const hasVisibleVars = Object.keys(filteredVars).length > 0;
          
          if (!hasVisibleVars && searchTerm) {
            return null;
          }

          return (
            <Accordion key={category} defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="h6">
                    {getCategoryIcon(category)} {getCategoryDisplayName(category)}
                  </Typography>
                  <Chip 
                    label={`${Object.keys(filteredVars).length} vars`} 
                    size="small" 
                    variant="outlined"
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  {Object.entries(filteredVars).map(([key, value]) => {
                    const status = getVariableStatus(key, value);
                    
                    return (
                      <Grid item xs={12} key={key}>
                        <Card variant="outlined" sx={{ backgroundColor: 'background.default' }}>
                          <CardContent sx={{ py: 2 }}>
                            <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                              <Box display="flex" alignItems="center" gap={1}>
                                <Typography variant="subtitle2" color="primary">
                                  {key}
                                </Typography>
                                <Chip 
                                  label={status.label} 
                                  size="small" 
                                  color={status.color}
                                  variant="outlined"
                                />
                              </Box>
                              <Tooltip title={copiedKey === key ? 'Copied!' : 'Copy value'}>
                                <IconButton
                                  size="small"
                                  onClick={() => handleCopyToClipboard(key, value)}
                                  color={copiedKey === key ? 'success' : 'default'}
                                >
                                  <ContentCopyIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                            <Box
                              sx={{
                                backgroundColor: 'surface.main',
                                border: '1px solid',
                                borderColor: 'divider',
                                borderRadius: 1,
                                p: 1,
                                fontFamily: 'monospace',
                                fontSize: '0.875rem',
                                wordBreak: 'break-all',
                                maxHeight: 100,
                                overflow: 'auto',
                              }}
                            >
                              {value || <em style={{ color: '#666' }}>Empty</em>}
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    );
                  })}
                </Grid>
              </AccordionDetails>
            </Accordion>
          );
        })}

        <Box mt={2} display="flex" justifyContent="center">
          <Typography variant="body2" color="text.secondary">
            Last updated: {new Date(envData.timestamp * 1000).toLocaleString()}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default EnvironmentVariables;
