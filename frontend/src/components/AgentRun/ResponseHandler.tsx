/**
 * Response Handler Component
 * Handles different types of agent responses (regular, plan, PR)
 */

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  Alert,
  Card,
  CardContent,
  CardActions,
  Chip,
  Divider,
} from '@mui/material';
import {
  PlayArrow as ContinueIcon,
  CheckCircle as ConfirmIcon,
  Edit as ModifyIcon,
  GitHub as GitHubIcon,
  AutoMode as AutoIcon,
} from '@mui/icons-material';

import { AgentRun } from '../../types/api';

interface ResponseHandlerProps {
  agentRun: AgentRun;
  onContinue: (prompt: string) => Promise<void>;
  isSubmitting: boolean;
}

const ResponseHandler: React.FC<ResponseHandlerProps> = ({
  agentRun,
  onContinue,
  isSubmitting,
}) => {
  const [continuePrompt, setContinuePrompt] = useState('');
  const [showContinueInput, setShowContinueInput] = useState(false);
  const [planModification, setPlanModification] = useState('');
  const [showPlanModification, setShowPlanModification] = useState(false);

  const handleContinue = async () => {
    if (continuePrompt.trim()) {
      await onContinue(continuePrompt);
      setContinuePrompt('');
      setShowContinueInput(false);
    }
  };

  const handleConfirmPlan = async () => {
    await onContinue('Proceed with the proposed plan.');
  };

  const handleModifyPlan = async () => {
    if (planModification.trim()) {
      await onContinue(`Please modify the plan: ${planModification}`);
      setPlanModification('');
      setShowPlanModification(false);
    }
  };

  const renderRegularResponse = () => (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Chip label="Regular Response" color="primary" size="small" />
          <Typography variant="body2" color="text.secondary">
            Agent completed the task
          </Typography>
        </Box>
        
        {agentRun.result && (
          <Typography variant="body2" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
            {agentRun.result}
          </Typography>
        )}
      </CardContent>
      
      <CardActions>
        {!showContinueInput ? (
          <Button
            startIcon={<ContinueIcon />}
            onClick={() => setShowContinueInput(true)}
            disabled={isSubmitting}
          >
            Continue
          </Button>
        ) : (
          <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Additional instructions"
              multiline
              rows={3}
              value={continuePrompt}
              onChange={(e) => setContinuePrompt(e.target.value)}
              placeholder="Provide additional requirements or modifications..."
              fullWidth
              size="small"
            />
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="contained"
                onClick={handleContinue}
                disabled={!continuePrompt.trim() || isSubmitting}
                size="small"
              >
                {isSubmitting ? 'Sending...' : 'Continue'}
              </Button>
              <Button
                onClick={() => {
                  setShowContinueInput(false);
                  setContinuePrompt('');
                }}
                size="small"
              >
                Cancel
              </Button>
            </Box>
          </Box>
        )}
      </CardActions>
    </Card>
  );

  const renderPlanResponse = () => (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Chip label="Plan Proposed" color="warning" size="small" />
          <Typography variant="body2" color="text.secondary">
            Agent is waiting for plan confirmation
          </Typography>
        </Box>
        
        <Alert severity="info" sx={{ mb: 2 }}>
          The agent has proposed a plan and is waiting for your confirmation before proceeding.
        </Alert>
        
        {agentRun.result && (
          <Typography variant="body2" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
            {agentRun.result}
          </Typography>
        )}
      </CardContent>
      
      <CardActions>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, width: '100%' }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              startIcon={<ConfirmIcon />}
              onClick={handleConfirmPlan}
              disabled={isSubmitting}
              color="success"
            >
              {isSubmitting ? 'Confirming...' : 'Confirm Plan'}
            </Button>
            <Button
              variant="outlined"
              startIcon={<ModifyIcon />}
              onClick={() => setShowPlanModification(!showPlanModification)}
              disabled={isSubmitting}
            >
              Modify Plan
            </Button>
          </Box>
          
          {showPlanModification && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Plan modifications"
                multiline
                rows={3}
                value={planModification}
                onChange={(e) => setPlanModification(e.target.value)}
                placeholder="Describe how you want to modify the proposed plan..."
                fullWidth
                size="small"
              />
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  onClick={handleModifyPlan}
                  disabled={!planModification.trim() || isSubmitting}
                  size="small"
                >
                  {isSubmitting ? 'Modifying...' : 'Submit Modifications'}
                </Button>
                <Button
                  onClick={() => {
                    setShowPlanModification(false);
                    setPlanModification('');
                  }}
                  size="small"
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          )}
        </Box>
      </CardActions>
    </Card>
  );

  const renderPRResponse = () => (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Chip label="PR Created" color="success" size="small" icon={<GitHubIcon />} />
          <Typography variant="body2" color="text.secondary">
            Pull request has been created
          </Typography>
        </Box>
        
        <Alert severity="success" sx={{ mb: 2 }}>
          A pull request has been created with the implemented changes. 
          {agentRun.pr_number && ` PR #${agentRun.pr_number}`}
        </Alert>
        
        {agentRun.result && (
          <Typography variant="body2" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
            {agentRun.result}
          </Typography>
        )}
        
        <Divider sx={{ my: 2 }} />
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AutoIcon color="primary" />
          <Typography variant="body2">
            Validation pipeline will be triggered automatically
          </Typography>
        </Box>
      </CardContent>
      
      <CardActions>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {agentRun.pr_url && (
            <Button
              variant="contained"
              startIcon={<GitHubIcon />}
              onClick={() => window.open(agentRun.pr_url, '_blank')}
            >
              View PR on GitHub
            </Button>
          )}
          
          {!showContinueInput ? (
            <Button
              variant="outlined"
              startIcon={<ContinueIcon />}
              onClick={() => setShowContinueInput(true)}
              disabled={isSubmitting}
            >
              Continue with Changes
            </Button>
          ) : (
            <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Additional changes"
                multiline
                rows={3}
                value={continuePrompt}
                onChange={(e) => setContinuePrompt(e.target.value)}
                placeholder="Request additional changes to the same PR..."
                fullWidth
                size="small"
              />
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  onClick={handleContinue}
                  disabled={!continuePrompt.trim() || isSubmitting}
                  size="small"
                >
                  {isSubmitting ? 'Updating...' : 'Update PR'}
                </Button>
                <Button
                  onClick={() => {
                    setShowContinueInput(false);
                    setContinuePrompt('');
                  }}
                  size="small"
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          )}
        </Box>
      </CardActions>
    </Card>
  );

  // Only show response handler for completed runs
  if (agentRun.status !== 'COMPLETED') {
    return null;
  }

  // Determine response type based on agent run data
  const responseType = agentRun.response_type || 'regular';

  switch (responseType) {
    case 'plan':
      return renderPlanResponse();
    case 'pr':
      return renderPRResponse();
    case 'regular':
    default:
      return renderRegularResponse();
  }
};

export default ResponseHandler;
