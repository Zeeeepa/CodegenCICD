-- ============================================================================
-- CodegenCICD Dashboard Database Schema
-- ============================================================================
-- Complete SQLite schema for CICD dashboard functionality including projects,
-- settings, secrets, pipeline states, agent runs, and webhook configurations
-- ============================================================================

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- ============================================================================
-- PROJECTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    github_repo_url TEXT NOT NULL,
    github_repo_name TEXT NOT NULL,
    github_owner TEXT NOT NULL,
    description TEXT,
    default_branch TEXT DEFAULT 'main',
    webhook_url TEXT,
    webhook_secret TEXT,
    is_active BOOLEAN DEFAULT 1,
    auto_merge_enabled BOOLEAN DEFAULT 0,
    auto_confirm_plans BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PROJECT SETTINGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS project_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    planning_statement TEXT,
    repository_rules TEXT,
    setup_commands TEXT,
    target_branch TEXT DEFAULT 'main',
    deployment_config JSON,
    notification_config JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ============================================================================
-- PROJECT SECRETS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS project_secrets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    key_name TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, key_name)
);

-- ============================================================================
-- AGENT RUNS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    codegen_run_id INTEGER,
    prompt TEXT NOT NULL,
    planning_statement TEXT,
    status TEXT DEFAULT 'pending',
    result TEXT,
    error_message TEXT,
    metadata JSON,
    web_url TEXT,
    github_pr_url TEXT,
    github_pr_number INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ============================================================================
-- PIPELINE STATES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS pipeline_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id INTEGER NOT NULL,
    state TEXT NOT NULL,
    previous_state TEXT,
    data JSON,
    error_context TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE CASCADE
);

-- ============================================================================
-- WEBHOOKS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    webhook_type TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    secret_token TEXT,
    events JSON,
    is_active BOOLEAN DEFAULT 1,
    last_triggered_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ============================================================================
-- TEST RESULTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id INTEGER NOT NULL,
    test_type TEXT NOT NULL,
    test_name TEXT NOT NULL,
    status TEXT NOT NULL,
    result_data JSON,
    error_message TEXT,
    duration_seconds REAL,
    screenshot_path TEXT,
    log_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE CASCADE
);

-- ============================================================================
-- GRAINCHAIN SNAPSHOTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS grainchain_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id INTEGER NOT NULL,
    snapshot_id TEXT NOT NULL,
    status TEXT DEFAULT 'creating',
    config JSON,
    validation_results JSON,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    destroyed_at DATETIME,
    FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE CASCADE
);

-- ============================================================================
-- SYSTEM LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    component TEXT,
    context JSON,
    correlation_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Projects indexes
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_projects_github_repo ON projects(github_repo_name, github_owner);
CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active);

-- Project settings indexes
CREATE INDEX IF NOT EXISTS idx_project_settings_project_id ON project_settings(project_id);

-- Project secrets indexes
CREATE INDEX IF NOT EXISTS idx_project_secrets_project_id ON project_secrets(project_id);
CREATE INDEX IF NOT EXISTS idx_project_secrets_key ON project_secrets(project_id, key_name);

-- Agent runs indexes
CREATE INDEX IF NOT EXISTS idx_agent_runs_project_id ON agent_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_codegen_id ON agent_runs(codegen_run_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at);

-- Pipeline states indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_states_agent_run_id ON pipeline_states(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_states_state ON pipeline_states(state);
CREATE INDEX IF NOT EXISTS idx_pipeline_states_created_at ON pipeline_states(created_at);

-- Webhooks indexes
CREATE INDEX IF NOT EXISTS idx_webhooks_project_id ON webhooks(project_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_type ON webhooks(webhook_type);
CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhooks(is_active);

-- Test results indexes
CREATE INDEX IF NOT EXISTS idx_test_results_agent_run_id ON test_results(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_type ON test_results(test_type);
CREATE INDEX IF NOT EXISTS idx_test_results_status ON test_results(status);

-- Grainchain snapshots indexes
CREATE INDEX IF NOT EXISTS idx_grainchain_snapshots_agent_run_id ON grainchain_snapshots(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_grainchain_snapshots_snapshot_id ON grainchain_snapshots(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_grainchain_snapshots_status ON grainchain_snapshots(status);

-- System logs indexes
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component);
CREATE INDEX IF NOT EXISTS idx_system_logs_correlation_id ON system_logs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);

-- ============================================================================
-- TRIGGERS FOR AUDIT FIELDS
-- ============================================================================

-- Update timestamps on projects
CREATE TRIGGER IF NOT EXISTS update_projects_timestamp 
    AFTER UPDATE ON projects
    FOR EACH ROW
    BEGIN
        UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamps on project_settings
CREATE TRIGGER IF NOT EXISTS update_project_settings_timestamp 
    AFTER UPDATE ON project_settings
    FOR EACH ROW
    BEGIN
        UPDATE project_settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamps on project_secrets
CREATE TRIGGER IF NOT EXISTS update_project_secrets_timestamp 
    AFTER UPDATE ON project_secrets
    FOR EACH ROW
    BEGIN
        UPDATE project_secrets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamps on agent_runs
CREATE TRIGGER IF NOT EXISTS update_agent_runs_timestamp 
    AFTER UPDATE ON agent_runs
    FOR EACH ROW
    BEGIN
        UPDATE agent_runs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamps on pipeline_states
CREATE TRIGGER IF NOT EXISTS update_pipeline_states_timestamp 
    AFTER UPDATE ON pipeline_states
    FOR EACH ROW
    BEGIN
        UPDATE pipeline_states SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamps on webhooks
CREATE TRIGGER IF NOT EXISTS update_webhooks_timestamp 
    AFTER UPDATE ON webhooks
    FOR EACH ROW
    BEGIN
        UPDATE webhooks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamps on grainchain_snapshots
CREATE TRIGGER IF NOT EXISTS update_grainchain_snapshots_timestamp 
    AFTER UPDATE ON grainchain_snapshots
    FOR EACH ROW
    BEGIN
        UPDATE grainchain_snapshots SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active projects with latest agent run
CREATE VIEW IF NOT EXISTS active_projects_with_latest_run AS
SELECT 
    p.*,
    ar.id as latest_run_id,
    ar.status as latest_run_status,
    ar.created_at as latest_run_created_at,
    ar.github_pr_url as latest_pr_url
FROM projects p
LEFT JOIN agent_runs ar ON p.id = ar.project_id
LEFT JOIN agent_runs ar2 ON p.id = ar2.project_id AND ar.created_at < ar2.created_at
WHERE p.is_active = 1 AND ar2.id IS NULL;

-- Project summary with counts
CREATE VIEW IF NOT EXISTS project_summary AS
SELECT 
    p.id,
    p.name,
    p.github_repo_name,
    p.is_active,
    p.auto_merge_enabled,
    COUNT(ar.id) as total_runs,
    COUNT(CASE WHEN ar.status = 'completed' THEN 1 END) as completed_runs,
    COUNT(CASE WHEN ar.status = 'failed' THEN 1 END) as failed_runs,
    COUNT(CASE WHEN ar.status = 'running' THEN 1 END) as running_runs,
    MAX(ar.created_at) as last_run_at
FROM projects p
LEFT JOIN agent_runs ar ON p.id = ar.project_id
GROUP BY p.id, p.name, p.github_repo_name, p.is_active, p.auto_merge_enabled;

