/**
 * Example component demonstrating the TypeScript Codegen client usage
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  CircularProgress,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
  Grid,
  LinearProgress,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  PlayArrow as PlayArrowIcon,
  Refresh as RefreshIcon,
  LocalHospital as HealthIcon,
  Code as CodeIcon,
  Timeline as TimelineIcon
} from '@mui/icons-material';

import {
  useCodegenClient,
  useCurrentUser,
  useOrganizations,
  useCreateAgentRun,
  useAgentRun,
  useAgentRuns,
  useAgentRunLogs,
  useBulkOperations,
  useWebhooks,
  useHealthCheck
} from '../hooks/useCodegenClient';

import { ConfigPresets } from '../services/codegenConfig';
import { AgentRunStatus } from '../services/codegenTypes';

const CodegenExample: React.FC = () => {
  const [prompt, setPrompt] = useState('Create a simple React component that displays "Hello, World!"');
  const [selectedOrgId, setSelectedOrgId] = useState<number | null>(null);
  const [selectedAgentRunId, setSelectedAgentRunId] = useState<number | null>(null);

  // Initialize client with development config
  const { isConnected, isConnecting, error: clientError, stats, connect, refreshStats } = useCodegenClient({
    config: ConfigPresets.development,
    autoConnect: true
  });

  // User and organization data
  const { user, loading: userLoading, error: userError } = useCurrentUser();
  const { organizations, loading: orgsLoading, error: orgsError } = useOrganizations();

  // Agent run operations
  const { createAgentRun, loading: createLoading, error: createError } = useCreateAgentRun();

  // Health monitoring
  const { health } = useHealthCheck(30000);

  // Webhooks
  const { events: webhookEvents, registerHandler, clearEvents } = useWebhooks();

  // Bulk operations
  const { bulkCreateAgentRuns, loading: bulkLoading, error: bulkError, progress } = useBulkOperations();

  // Set default org ID when organizations load
  useEffect(() => {
    if (organizations?.items.length && !selectedOrgId) {
      setSelectedOrgId(organizations.items[0].id);
    }
  }, [organizations, selectedOrgId]);

  // Register webhook handlers
  useEffect(() => {
    registerHandler('agent_run.completed', (payload) => {
      console.log('Agent run completed:', payload);
    });

    registerHandler('agent_run.failed', (payload) => {
      console.log('Agent run failed:', payload);
    });
  }, [registerHandler]);

  const handleCreateAgentRun = async () => {
    if (!selectedOrgId || !prompt.trim()) return;

    const run = await createAgentRun(selectedOrgId, prompt, undefined, {
      source: 'typescript_example',
      timestamp: new Date().toISOString()
    });

    if (run) {
      setSelectedAgentRunId(run.id);
    }
  };

  const handleBulkCreate = async () => {
    if (!selectedOrgId) return;

    const configs = [
      { prompt: 'Create a TypeScript interface for a user', metadata: { type: 'interface' } },
      { prompt: 'Create a React hook for API calls', metadata: { type: 'hook' } },
      { prompt: 'Create a utility function for date formatting', metadata: { type: 'utility' } }
    ];

    await bulkCreateAgentRuns(selectedOrgId, configs);
  };



  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        🚀 Enhanced TypeScript Codegen Client Demo
      </Typography>

      <Grid container spacing={3}>
        {/* Connection Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <HealthIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Connection Status
              </Typography>
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Chip
                  label={isConnected ? 'Connected' : 'Disconnected'}
                  color={isConnected ? 'success' : 'error'}
                  variant="outlined"
                />
                {isConnecting && <CircularProgress size={20} />}
                <Button onClick={connect} disabled={isConnecting} size="small">
                  Reconnect
                </Button>
              </Box>

              {health && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Health: {health.status} ({health.response_time_seconds?.toFixed(2)}s)
                  </Typography>
                  {health.user_id && (
                    <Typography variant="body2" color="text.secondary">
                      User ID: {health.user_id}
                    </Typography>
                  )}
                </Box>
              )}

              {clientError && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {clientError}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* User Info */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                👤 Current User
              </Typography>
              
              {userLoading ? (
                <CircularProgress size={24} />
              ) : user ? (
                <Box>
                  <Typography variant="body1">{user.github_username}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {user.full_name || user.email}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    ID: {user.id}
                  </Typography>
                </Box>
              ) : (
                <Typography color="error">Failed to load user</Typography>
              )}

              {userError && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {userError}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Organizations */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                🏢 Organizations
              </Typography>
              
              {orgsLoading ? (
                <CircularProgress size={24} />
              ) : organizations?.items.length ? (
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {organizations.items.map((org) => (
                    <Chip
                      key={org.id}
                      label={`${org.name} (${org.id})`}
                      onClick={() => setSelectedOrgId(org.id)}
                      color={selectedOrgId === org.id ? 'primary' : 'default'}
                      variant={selectedOrgId === org.id ? 'filled' : 'outlined'}
                    />
                  ))}
                </Box>
              ) : (
                <Typography color="error">No organizations found</Typography>
              )}

              {orgsError && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {orgsError}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Create Agent Run */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <CodeIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Create Agent Run
              </Typography>
              
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                sx={{ mb: 2 }}
                placeholder="Enter your coding request here..."
              />

              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <Button
                  variant="contained"
                  onClick={handleCreateAgentRun}
                  disabled={!selectedOrgId || !prompt.trim() || createLoading}
                  startIcon={createLoading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                >
                  Create Agent Run
                </Button>

                <Button
                  variant="outlined"
                  onClick={handleBulkCreate}
                  disabled={!selectedOrgId || bulkLoading}
                  startIcon={bulkLoading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                >
                  Bulk Create (3 runs)
                </Button>
              </Box>

              {progress && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    Progress: {progress.completed}/{progress.total}
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={(progress.completed / progress.total) * 100}
                  />
                </Box>
              )}

              {createError && (
                <Alert severity="error">
                  {createError}
                </Alert>
              )}

              {bulkError && (
                <Alert severity="error">
                  {bulkError}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Agent Runs List */}
        {selectedOrgId && (
          <Grid item xs={12}>
            <AgentRunsList orgId={selectedOrgId} onSelectRun={setSelectedAgentRunId} />
          </Grid>
        )}

        {/* Selected Agent Run Details */}
        {selectedOrgId && selectedAgentRunId && (
          <Grid item xs={12}>
            <AgentRunDetails orgId={selectedOrgId} agentRunId={selectedAgentRunId} />
          </Grid>
        )}

        {/* Client Statistics */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                📊 Client Statistics
              </Typography>
              
              <Button onClick={refreshStats} size="small" sx={{ mb: 2 }}>
                <RefreshIcon sx={{ mr: 1 }} />
                Refresh Stats
              </Button>

              {stats && (
                <Box>
                  <Typography variant="body2">
                    Base URL: {stats.config?.base_url}
                  </Typography>
                  <Typography variant="body2">
                    Timeout: {stats.config?.timeout}ms
                  </Typography>
                  {stats.metrics && (
                    <>
                      <Typography variant="body2">
                        Total Requests: {stats.metrics.total_requests}
                      </Typography>
                      <Typography variant="body2">
                        Error Rate: {(stats.metrics.error_rate * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="body2">
                        Avg Response Time: {stats.metrics.average_response_time?.toFixed(2)}s
                      </Typography>
                    </>
                  )}
                  {stats.cache && (
                    <Typography variant="body2">
                      Cache Hit Rate: {stats.cache.hit_rate_percentage?.toFixed(1)}%
                    </Typography>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Webhook Events */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                🔔 Webhook Events
              </Typography>
              
              <Button onClick={clearEvents} size="small" sx={{ mb: 2 }}>
                Clear Events
              </Button>

              <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                {webhookEvents.length > 0 ? (
                  <List dense>
                    {webhookEvents.slice(-10).map((event, index) => (
                      <ListItem key={index}>
                        <ListItemText
                          primary={event.eventType}
                          secondary={event.timestamp.toLocaleTimeString()}
                        />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No webhook events received
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

// Helper component for agent runs list
const AgentRunsList: React.FC<{ orgId: number; onSelectRun: (id: number) => void }> = ({ orgId, onSelectRun }) => {
  const { agentRuns, loading, error, refetch } = useAgentRuns({
    orgId,
    autoRefresh: true,
    refreshInterval: 10000
  });

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            <TimelineIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Recent Agent Runs
          </Typography>
          <Button onClick={refetch} disabled={loading} size="small">
            <RefreshIcon />
          </Button>
        </Box>

        {loading && <CircularProgress size={24} />}
        
        {error && (
          <Alert severity="error">
            {error}
          </Alert>
        )}

        {agentRuns?.items.length ? (
          <List>
            {agentRuns.items.slice(0, 5).map((run, index) => (
              <React.Fragment key={run.id}>
                <ListItem
                  button
                  onClick={() => onSelectRun(run.id)}
                  sx={{ cursor: 'pointer' }}
                >
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body1">
                          Run #{run.id}
                        </Typography>
                        <Chip
                          label={run.status || 'unknown'}
                          color={getStatusColor(run.status) as any}
                          size="small"
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Created: {run.created_at ? new Date(run.created_at).toLocaleString() : 'Unknown'}
                        </Typography>
                        {run.result && (
                          <Typography variant="body2" noWrap>
                            Result: {run.result.substring(0, 100)}...
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                {index < agentRuns.items.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No agent runs found
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

// Helper component for agent run details
const AgentRunDetails: React.FC<{ orgId: number; agentRunId: number }> = ({ orgId, agentRunId }) => {
  const { agentRun, loading, error, waitForCompletion } = useAgentRun({
    orgId,
    agentRunId,
    autoRefresh: true
  });

  const { logs, loading: logsLoading, error: logsError } = useAgentRunLogs({
    orgId,
    agentRunId,
    autoRefresh: true
  });

  const handleWaitForCompletion = async () => {
    await waitForCompletion(300000); // 5 minute timeout
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Agent Run #{agentRunId} Details
        </Typography>

        {loading && <CircularProgress size={24} />}
        
        {error && (
          <Alert severity="error">
            {error}
          </Alert>
        )}

        {agentRun && (
          <Box>
            <Box sx={{ mb: 2 }}>
              <Chip
                label={agentRun.status || 'unknown'}
                color={getStatusColor(agentRun.status) as any}
                sx={{ mr: 1 }}
              />
              {agentRun.status === AgentRunStatus.RUNNING && (
                <Button onClick={handleWaitForCompletion} size="small">
                  Wait for Completion
                </Button>
              )}
            </Box>

            <Typography variant="body2" gutterBottom>
              <strong>Created:</strong> {agentRun.created_at ? new Date(agentRun.created_at).toLocaleString() : 'Unknown'}
            </Typography>

            {agentRun.web_url && (
              <Typography variant="body2" gutterBottom>
                <strong>Web URL:</strong>{' '}
                <a href={agentRun.web_url} target="_blank" rel="noopener noreferrer">
                  View in Codegen
                </a>
              </Typography>
            )}

            {agentRun.result && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography>Result</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                      {agentRun.result}
                    </Typography>
                  </Paper>
                </AccordionDetails>
              </Accordion>
            )}

            {agentRun.github_pull_requests?.length && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography>Pull Requests ({agentRun.github_pull_requests.length})</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List>
                    {agentRun.github_pull_requests.map((pr) => (
                      <ListItem key={pr.id}>
                        <ListItemText
                          primary={
                            <a href={pr.url} target="_blank" rel="noopener noreferrer">
                              {pr.title}
                            </a>
                          }
                          secondary={`Created: ${new Date(pr.created_at).toLocaleString()}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </AccordionDetails>
              </Accordion>
            )}

            {logs && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography>Logs ({logs.total_logs || logs.logs.length})</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {logsLoading && <CircularProgress size={24} />}
                  {logsError && <Alert severity="error">{logsError}</Alert>}
                  
                  <List sx={{ maxHeight: 400, overflow: 'auto' }}>
                    {logs.logs.map((log, index) => (
                      <ListItem key={index}>
                        <ListItemText
                          primary={
                            <Box>
                              <Chip label={log.message_type} size="small" sx={{ mr: 1 }} />
                              {log.tool_name && (
                                <Chip label={log.tool_name} size="small" variant="outlined" />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="caption" color="text.secondary">
                                {new Date(log.created_at).toLocaleTimeString()}
                              </Typography>
                              {log.thought && (
                                <Typography variant="body2" sx={{ mt: 0.5 }}>
                                  {log.thought}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                </AccordionDetails>
              </Accordion>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

// Helper function (moved outside component to avoid recreation)
const getStatusColor = (status?: string) => {
  switch (status) {
    case AgentRunStatus.COMPLETED:
      return 'success';
    case AgentRunStatus.FAILED:
      return 'error';
    case AgentRunStatus.RUNNING:
      return 'primary';
    case AgentRunStatus.PENDING:
      return 'warning';
    default:
      return 'default';
  }
};

export default CodegenExample;
