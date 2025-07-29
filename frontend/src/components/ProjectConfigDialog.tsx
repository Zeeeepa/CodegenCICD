import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tabs,
  Tab,
  Box,
  Alert,
  IconButton,
} from '@mui/material';
import {
  Close as CloseIcon,
  Rule as RuleIcon,
  Terminal as TerminalIcon,
  Security as SecurityIcon,
  Description as DescriptionIcon,
} from '@mui/icons-material';
import { ProjectConfiguration, configurationsApi } from '../services/api';
import RepositoryRulesTab from './config-tabs/RepositoryRulesTab';
import SetupCommandsTab from './config-tabs/SetupCommandsTab';
import SecretsTab from './config-tabs/SecretsTab';
import PlanningStatementTab from './config-tabs/PlanningStatementTab';

interface ProjectConfigDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`config-tabpanel-${index}`}
      aria-labelledby={`config-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
};

const ProjectConfigDialog: React.FC<ProjectConfigDialogProps> = ({
  open,
  onClose,
  projectId,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [configuration, setConfiguration] = useState<ProjectConfiguration | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    if (open && projectId) {
      loadConfiguration();
    }
  }, [open, projectId]);

  const loadConfiguration = async () => {
    try {
      setLoading(true);
      const response = await configurationsApi.getByProject(projectId);
      setConfiguration(response.data);
    } catch (err: any) {
      if (err.response?.status === 404) {
        // Configuration doesn't exist yet, create empty one
        setConfiguration({
          id: 0,
          project_id: projectId,
          repository_rules: '',
          setup_commands: '',
          planning_statement: '',
          branch_name: 'main',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      } else {
        setError(err.response?.data?.detail || 'Failed to load configuration');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleConfigurationUpdate = async (updates: Partial<ProjectConfiguration>) => {
    if (!configuration) return;

    try {
      const response = await configurationsApi.update(projectId, updates);
      setConfiguration(response.data);
      setHasUnsavedChanges(false);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update configuration');
      throw err;
    }
  };

  const handleClose = () => {
    if (hasUnsavedChanges) {
      const confirmClose = window.confirm(
        'You have unsaved changes. Are you sure you want to close?'
      );
      if (!confirmClose) return;
    }
    
    setActiveTab(0);
    setConfiguration(null);
    setError(null);
    setHasUnsavedChanges(false);
    onClose();
  };

  const tabsConfig = [
    {
      label: 'Repository Rules',
      icon: <RuleIcon />,
      component: RepositoryRulesTab,
    },
    {
      label: 'Setup Commands',
      icon: <TerminalIcon />,
      component: SetupCommandsTab,
    },
    {
      label: 'Secrets',
      icon: <SecurityIcon />,
      component: SecretsTab,
    },
    {
      label: 'Planning Statement',
      icon: <DescriptionIcon />,
      component: PlanningStatementTab,
    },
  ];

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { height: '80vh', maxHeight: '800px' }
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          Project Configuration
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        {error && (
          <Alert severity="error" sx={{ m: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="fullWidth"
            sx={{ px: 2 }}
          >
            {tabsConfig.map((tab, index) => (
              <Tab
                key={index}
                icon={tab.icon}
                label={tab.label}
                iconPosition="start"
                sx={{ minHeight: 64 }}
              />
            ))}
          </Tabs>
        </Box>

        <Box sx={{ px: 2, height: 'calc(100% - 64px)', overflow: 'auto' }}>
          {tabsConfig.map((tab, index) => {
            const TabComponent = tab.component;
            return (
              <TabPanel key={index} value={activeTab} index={index}>
                {configuration && (
                  <TabComponent
                    projectId={projectId}
                    configuration={configuration}
                    onUpdate={handleConfigurationUpdate}
                    onUnsavedChanges={setHasUnsavedChanges}
                    loading={loading}
                  />
                )}
              </TabPanel>
            );
          })}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleClose}>
          Close
        </Button>
        {hasUnsavedChanges && (
          <Alert severity="warning" sx={{ flexGrow: 1, mr: 2 }}>
            You have unsaved changes
          </Alert>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ProjectConfigDialog;

