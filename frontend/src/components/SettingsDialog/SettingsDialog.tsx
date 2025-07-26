import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  Box,
  Tabs,
  Tab,
  Typography,
  Alert
} from '@mui/material';
import {
  Close as CloseIcon,
  Rule as RuleIcon,
  Build as BuildIcon,
  VpnKey as VpnKeyIcon,
  Description as DescriptionIcon
} from '@mui/icons-material';
import { Project, SettingsTab } from '../../types';
import { useApp } from '../../contexts/AppContext';
import RepositoryRulesTab from './RepositoryRulesTab';
import SetupCommandsTab from './SetupCommandsTab';
import SecretsTab from './SecretsTab';
import PlanningStatementTab from './PlanningStatementTab';

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
  project: Project;
}

const SettingsDialog: React.FC<SettingsDialogProps> = ({
  open,
  onClose,
  project
}) => {
  const { state } = useApp();
  const [activeTab, setActiveTab] = useState<SettingsTab>(SettingsTab.REPOSITORY_RULES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setActiveTab(SettingsTab.REPOSITORY_RULES);
      setError(null);
      setHasUnsavedChanges(false);
    }
  }, [open]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: SettingsTab) => {
    if (hasUnsavedChanges) {
      const confirmSwitch = window.confirm(
        'You have unsaved changes. Are you sure you want to switch tabs?'
      );
      if (!confirmSwitch) return;
    }
    setActiveTab(newValue);
    setHasUnsavedChanges(false);
  };

  const handleClose = () => {
    if (hasUnsavedChanges) {
      const confirmClose = window.confirm(
        'You have unsaved changes. Are you sure you want to close?'
      );
      if (!confirmClose) return;
    }
    onClose();
  };

  const handleSave = async () => {
    // This will be handled by individual tab components
    setHasUnsavedChanges(false);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case SettingsTab.REPOSITORY_RULES:
        return (
          <RepositoryRulesTab
            project={project}
            onError={setError}
            onUnsavedChanges={setHasUnsavedChanges}
          />
        );
      case SettingsTab.SETUP_COMMANDS:
        return (
          <SetupCommandsTab
            project={project}
            onError={setError}
            onUnsavedChanges={setHasUnsavedChanges}
          />
        );
      case SettingsTab.SECRETS:
        return (
          <SecretsTab
            project={project}
            onError={setError}
            onUnsavedChanges={setHasUnsavedChanges}
          />
        );
      case SettingsTab.PLANNING_STATEMENT:
        return (
          <PlanningStatementTab
            project={project}
            onError={setError}
            onUnsavedChanges={setHasUnsavedChanges}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { height: '80vh', display: 'flex', flexDirection: 'column' }
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Project Settings - {project.name}
          </Typography>
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', p: 0 }}>
        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ m: 2, mb: 0 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="fullWidth"
            sx={{ px: 2 }}
          >
            <Tab
              label="Repository Rules"
              value={SettingsTab.REPOSITORY_RULES}
              icon={<RuleIcon />}
              iconPosition="start"
            />
            <Tab
              label="Setup Commands"
              value={SettingsTab.SETUP_COMMANDS}
              icon={<BuildIcon />}
              iconPosition="start"
            />
            <Tab
              label="Secrets"
              value={SettingsTab.SECRETS}
              icon={<VpnKeyIcon />}
              iconPosition="start"
            />
            <Tab
              label="Planning Statement"
              value={SettingsTab.PLANNING_STATEMENT}
              icon={<DescriptionIcon />}
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Tab Content */}
        <Box sx={{ flexGrow: 1, p: 2, overflow: 'auto' }}>
          {renderTabContent()}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleClose} disabled={loading}>
          Close
        </Button>
        {hasUnsavedChanges && (
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={loading}
          >
            Save Changes
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default SettingsDialog;
