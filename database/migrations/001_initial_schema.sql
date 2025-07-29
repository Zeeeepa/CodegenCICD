-- ============================================================================
-- Migration 001: Initial Schema
-- ============================================================================
-- Creates the complete database schema for CodegenCICD Dashboard
-- Version: 1.0.0
-- Date: 2025-07-29
-- ============================================================================

-- Migration UP
-- ============================================================================

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Create all tables from schema.sql
-- (This migration applies the complete schema)

-- Projects table
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

-- Project settings table
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

-- Project secrets table
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

-- Agent runs table
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

-- Pipeline states table
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

-- Webhooks table
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

-- Test results table
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

-- Grainchain snapshots table
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

-- System logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    component TEXT,
    context JSON,
    correlation_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create all indexes
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_projects_github_repo ON projects(github_repo_name, github_owner);
CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active);
CREATE INDEX IF NOT EXISTS idx_project_settings_project_id ON project_settings(project_id);
CREATE INDEX IF NOT EXISTS idx_project_secrets_project_id ON project_secrets(project_id);
CREATE INDEX IF NOT EXISTS idx_project_secrets_key ON project_secrets(project_id, key_name);
CREATE INDEX IF NOT EXISTS idx_agent_runs_project_id ON agent_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_codegen_id ON agent_runs(codegen_run_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_states_agent_run_id ON pipeline_states(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_states_state ON pipeline_states(state);
CREATE INDEX IF NOT EXISTS idx_pipeline_states_created_at ON pipeline_states(created_at);
CREATE INDEX IF NOT EXISTS idx_webhooks_project_id ON webhooks(project_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_type ON webhooks(webhook_type);
CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhooks(is_active);
CREATE INDEX IF NOT EXISTS idx_test_results_agent_run_id ON test_results(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_type ON test_results(test_type);
CREATE INDEX IF NOT EXISTS idx_test_results_status ON test_results(status);
CREATE INDEX IF NOT EXISTS idx_grainchain_snapshots_agent_run_id ON grainchain_snapshots(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_grainchain_snapshots_snapshot_id ON grainchain_snapshots(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_grainchain_snapshots_status ON grainchain_snapshots(status);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component);
CREATE INDEX IF NOT EXISTS idx_system_logs_correlation_id ON system_logs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);

-- Create all triggers
CREATE TRIGGER IF NOT EXISTS update_projects_timestamp 
    AFTER UPDATE ON projects
    FOR EACH ROW
    BEGIN
        UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_project_settings_timestamp 
    AFTER UPDATE ON project_settings
    FOR EACH ROW
    BEGIN
        UPDATE project_settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_project_secrets_timestamp 
    AFTER UPDATE ON project_secrets
    FOR EACH ROW
    BEGIN
        UPDATE project_secrets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_agent_runs_timestamp 
    AFTER UPDATE ON agent_runs
    FOR EACH ROW
    BEGIN
        UPDATE agent_runs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_pipeline_states_timestamp 
    AFTER UPDATE ON pipeline_states
    FOR EACH ROW
    BEGIN
        UPDATE pipeline_states SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_webhooks_timestamp 
    AFTER UPDATE ON webhooks
    FOR EACH ROW
    BEGIN
        UPDATE webhooks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_grainchain_snapshots_timestamp 
    AFTER UPDATE ON grainchain_snapshots
    FOR EACH ROW
    BEGIN
        UPDATE grainchain_snapshots SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Create views
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

-- Record migration
INSERT INTO schema_migrations (version, applied_at) VALUES ('001', CURRENT_TIMESTAMP);

-- ============================================================================
-- Migration DOWN (Rollback)
-- ============================================================================
-- To rollback this migration, run the following:
/*
DROP VIEW IF EXISTS project_summary;
DROP VIEW IF EXISTS active_projects_with_latest_run;
DROP TRIGGER IF EXISTS update_grainchain_snapshots_timestamp;
DROP TRIGGER IF EXISTS update_webhooks_timestamp;
DROP TRIGGER IF EXISTS update_pipeline_states_timestamp;
DROP TRIGGER IF EXISTS update_agent_runs_timestamp;
DROP TRIGGER IF EXISTS update_project_secrets_timestamp;
DROP TRIGGER IF EXISTS update_project_settings_timestamp;
DROP TRIGGER IF EXISTS update_projects_timestamp;
DROP TABLE IF EXISTS system_logs;
DROP TABLE IF EXISTS grainchain_snapshots;
DROP TABLE IF EXISTS test_results;
DROP TABLE IF EXISTS webhooks;
DROP TABLE IF EXISTS pipeline_states;
DROP TABLE IF EXISTS agent_runs;
DROP TABLE IF EXISTS project_secrets;
DROP TABLE IF EXISTS project_settings;
DROP TABLE IF EXISTS projects;
DELETE FROM schema_migrations WHERE version = '001';
*/

