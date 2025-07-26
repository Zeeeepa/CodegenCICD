import React from 'react';
import {
  Box,
  Typography,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Paper,
  List,
  ListItem,
  ListItemText,
  Chip,
  LinearProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  PlayArrow as PlayIcon,
  CloudDownload as CloudDownloadIcon,
  Build as BuildIcon,
  Verified as VerifiedIcon,
  BugReport as BugReportIcon,
  Merge as MergeIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import {
  ValidationRun,
  ValidationStatus,
  ValidationStepStatus,
  ValidationStep,
  ValidationLog
} from '../../types';

interface ProgressTrackerProps {
  validationRuns: ValidationRun[];
}

const ProgressTracker: React.FC<ProgressTrackerProps> = ({ validationRuns }) => {
  const latestRun = validationRuns.sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )[0];

  if (!latestRun) {
    return (
      <Alert severity="info">
        No validation runs found for this agent run.
      </Alert>
    );
  }

  const getStepIcon = (step: ValidationStep, status: ValidationStepStatus) => {
    const iconProps = { fontSize: 'small' as const };
    
    switch (status) {
      case ValidationStepStatus.SUCCESS:
        return <CheckCircleIcon {...iconProps} color="success" />;
      case ValidationStepStatus.FAILED:
        return <ErrorIcon {...iconProps} color="error" />;
      case ValidationStepStatus.RUNNING:
        return <PlayIcon {...iconProps} color="primary" />;
      default:
        return <ScheduleIcon {...iconProps} color="disabled" />;
    }
  };

  const getStepTitle = (step: ValidationStep) => {
    switch (step) {
      case ValidationStep.SNAPSHOT_CREATION:
        return 'Create Snapshot';
      case ValidationStep.CODE_CLONE:
        return 'Clone PR Code';
      case ValidationStep.DEPLOYMENT:
        return 'Run Deployment';
      case ValidationStep.DEPLOYMENT_VALIDATION:
        return 'Validate Deployment';
      case ValidationStep.UI_TESTING:
        return 'UI Testing';
      case ValidationStep.AUTO_MERGE:
        return 'Auto-merge PR';
      default:
        return step;
    }
  };

  const getStepDescription = (step: ValidationStep) => {
    switch (step) {
      case ValidationStep.SNAPSHOT_CREATION:
        return 'Creating sandbox environment with grainchain + web-eval-agent';
      case ValidationStep.CODE_CLONE:
        return 'Downloading PR branch code to sandbox';
      case ValidationStep.DEPLOYMENT:
        return 'Executing setup commands from project configuration';
      case ValidationStep.DEPLOYMENT_VALIDATION:
        return 'Using Gemini API to verify successful deployment';
      case ValidationStep.UI_TESTING:
        return 'Running web-eval-agent to test all flows and components';
      case ValidationStep.AUTO_MERGE:
        return 'Automatically merging validated pull request';
      default:
        return 'Processing validation step';
    }
  };

  const getStatusColor = (status: ValidationStepStatus) => {
    switch (status) {
      case ValidationStepStatus.SUCCESS:
        return 'success';
      case ValidationStepStatus.RUNNING:
        return 'primary';
      case ValidationStepStatus.FAILED:
        return 'error';
      default:
        return 'default';
    }
  };

  const getOverallStatusColor = (status: ValidationStatus) => {
    switch (status) {
      case ValidationStatus.COMPLETED:
        return 'success';
      case ValidationStatus.RUNNING:
        return 'primary';
      case ValidationStatus.FAILED:
        return 'error';
      default:
        return 'default';
    }
  };

  // Group logs by step
  const logsByStep = latestRun.logs.reduce((acc, log) => {
    if (!acc[log.step]) {
      acc[log.step] = [];
    }
    acc[log.step].push(log);
    return acc;
  }, {} as Record<ValidationStep, ValidationLog[]>);

  const steps = [
    {
      step: ValidationStep.SNAPSHOT_CREATION,
      status: ValidationStepStatus.SUCCESS, // This would come from the validation run
      icon: <CloudDownloadIcon />
    },
    {
      step: ValidationStep.CODE_CLONE,
      status: ValidationStepStatus.SUCCESS,
      icon: <CloudDownloadIcon />
    },
    {
      step: ValidationStep.DEPLOYMENT,
      status: latestRun.deployment_status,
      icon: <BuildIcon />
    },
    {
      step: ValidationStep.DEPLOYMENT_VALIDATION,
      status: latestRun.deployment_status,
      icon: <VerifiedIcon />
    },
    {
      step: ValidationStep.UI_TESTING,
      status: latestRun.ui_test_status,
      icon: <BugReportIcon />
    },
    {
      step: ValidationStep.AUTO_MERGE,
      status: ValidationStepStatus.PENDING,
      icon: <MergeIcon />
    }
  ];

  return (
    <Box>
      {/* Overall Status */}
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Typography variant="h6">
          Validation Pipeline
        </Typography>
        <Chip
          label={`Status: ${latestRun.status}`}
          color={getOverallStatusColor(latestRun.status)}
          variant="outlined"
        />
        {latestRun.pr_number && (
          <Chip
            label={`PR #${latestRun.pr_number}`}
            color="primary"
            variant="outlined"
          />
        )}
      </Box>

      {/* Progress Indicator */}
      {latestRun.status === ValidationStatus.RUNNING && (
        <Box mb={3}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Validation in progress...
          </Typography>
          <LinearProgress />
        </Box>
      )}

      {/* Validation Steps */}
      <Stepper orientation="vertical">
        {steps.map((stepInfo, index) => {
          const stepLogs = logsByStep[stepInfo.step] || [];
          const isActive = stepInfo.status === ValidationStepStatus.RUNNING;
          const isCompleted = stepInfo.status === ValidationStepStatus.SUCCESS;
          const isFailed = stepInfo.status === ValidationStepStatus.FAILED;

          return (
            <Step key={stepInfo.step} active={isActive} completed={isCompleted}>
              <StepLabel
                error={isFailed}
                icon={getStepIcon(stepInfo.step, stepInfo.status)}
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="subtitle2">
                    {getStepTitle(stepInfo.step)}
                  </Typography>
                  <Chip
                    size="small"
                    label={stepInfo.status}
                    color={getStatusColor(stepInfo.status)}
                    variant="outlined"
                  />
                </Box>
              </StepLabel>
              
              <StepContent>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {getStepDescription(stepInfo.step)}
                </Typography>

                {/* Step Logs */}
                {stepLogs.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="caption">
                        View Logs ({stepLogs.length})
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Paper 
                        sx={{ 
                          maxHeight: 200, 
                          overflow: 'auto', 
                          p: 1, 
                          bgcolor: 'grey.50',
                          fontFamily: 'monospace'
                        }}
                      >
                        <List dense>
                          {stepLogs.map((log, logIndex) => (
                            <ListItem key={logIndex} sx={{ py: 0.25 }}>
                              <ListItemText
                                primary={
                                  <Typography 
                                    variant="caption" 
                                    sx={{ 
                                      color: log.level === 'error' ? 'error.main' : 
                                             log.level === 'warning' ? 'warning.main' : 
                                             'text.primary',
                                      fontSize: '0.75rem'
                                    }}
                                  >
                                    [{new Date(log.timestamp).toLocaleTimeString()}] {log.message}
                                  </Typography>
                                }
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Error Details */}
                {isFailed && (
                  <Alert severity="error" sx={{ mt: 1 }}>
                    <Typography variant="body2">
                      Step failed. Check logs for details or the agent will automatically retry with error context.
                    </Typography>
                  </Alert>
                )}

                {/* Success Details */}
                {isCompleted && stepInfo.step === ValidationStep.UI_TESTING && (
                  <Alert severity="success" sx={{ mt: 1 }}>
                    <Typography variant="body2">
                      All UI tests passed successfully! Components and flows are working correctly.
                    </Typography>
                  </Alert>
                )}
              </StepContent>
            </Step>
          );
        })}
      </Stepper>

      {/* Overall Results */}
      {latestRun.status === ValidationStatus.COMPLETED && (
        <Box mt={3}>
          <Alert severity="success">
            <Typography variant="body2">
              🎉 Validation pipeline completed successfully! 
              {latestRun.pr_number && ' Pull request is ready for review or has been auto-merged.'}
            </Typography>
          </Alert>
        </Box>
      )}

      {latestRun.status === ValidationStatus.FAILED && (
        <Box mt={3}>
          <Alert severity="error">
            <Typography variant="body2">
              ❌ Validation pipeline failed. The agent will automatically analyze the errors and update the PR with fixes.
            </Typography>
          </Alert>
        </Box>
      )}

      {/* Timing Information */}
      <Box mt={2} p={2} bgcolor="grey.50" borderRadius={1}>
        <Typography variant="caption" color="text.secondary">
          Started: {new Date(latestRun.created_at).toLocaleString()}
          {latestRun.completed_at && (
            <>
              {' • '}
              Completed: {new Date(latestRun.completed_at).toLocaleString()}
              {' • '}
              Duration: {Math.round((new Date(latestRun.completed_at).getTime() - new Date(latestRun.created_at).getTime()) / 1000)}s
            </>
          )}
        </Typography>
      </Box>
    </Box>
  );
};

export default ProgressTracker;
