-- =============================================================================
-- CodegenCICD Dashboard - Database Initialization Script
-- Creates initial database schema and default data
-- =============================================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- =============================================================================
-- USERS AND AUTHENTICATION
-- =============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    avatar_url VARCHAR(500),
    github_username VARCHAR(100),
    preferences JSONB DEFAULT '{}'::jsonb
);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- =============================================================================
-- PROJECTS AND REPOSITORIES
-- =============================================================================

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    repository_url VARCHAR(500),
    github_repo_id BIGINT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Project members table
CREATE TABLE IF NOT EXISTS project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- =============================================================================
-- CI/CD PIPELINES
-- =============================================================================

-- Pipeline definitions
CREATE TABLE IF NOT EXISTS pipelines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Pipeline runs
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    run_number INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, running, success, failure, cancelled
    trigger_type VARCHAR(50) NOT NULL, -- manual, webhook, schedule, api
    trigger_data JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    logs TEXT,
    artifacts JSONB DEFAULT '[]'::jsonb,
    environment VARCHAR(50) DEFAULT 'development',
    commit_sha VARCHAR(40),
    branch VARCHAR(255),
    pr_number INTEGER,
    triggered_by UUID REFERENCES users(id)
);

-- Pipeline steps
CREATE TABLE IF NOT EXISTS pipeline_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    step_name VARCHAR(255) NOT NULL,
    step_type VARCHAR(100) NOT NULL, -- build, test, deploy, validate, etc.
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    logs TEXT,
    output JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    step_order INTEGER NOT NULL
);

-- =============================================================================
-- VALIDATION AND TESTING
-- =============================================================================

-- Validation runs (grainchain, web-eval, graph-sitter)
CREATE TABLE IF NOT EXISTS validation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    validation_type VARCHAR(50) NOT NULL, -- grainchain, web_eval, graph_sitter
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    config JSONB DEFAULT '{}'::jsonb,
    results JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    error_message TEXT
);

-- Test results
CREATE TABLE IF NOT EXISTS test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    validation_run_id UUID NOT NULL REFERENCES validation_runs(id) ON DELETE CASCADE,
    test_suite VARCHAR(255) NOT NULL,
    test_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- passed, failed, skipped, error
    duration_seconds DECIMAL(10,3),
    error_message TEXT,
    output TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- =============================================================================
-- DEPLOYMENTS
-- =============================================================================

-- Deployments table
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    environment VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    deployment_url VARCHAR(500),
    version VARCHAR(100),
    config JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    deployed_by UUID REFERENCES users(id),
    rollback_deployment_id UUID REFERENCES deployments(id)
);

-- =============================================================================
-- INTEGRATIONS
-- =============================================================================

-- Integration configurations
CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    integration_type VARCHAR(50) NOT NULL, -- github, slack, discord, email
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Webhook events
CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id UUID REFERENCES integrations(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- MONITORING AND METRICS
-- =============================================================================

-- System metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,6) NOT NULL,
    labels JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_github_username ON users(github_username);

-- API Keys indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;

-- Projects indexes
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_github_repo_id ON projects(github_repo_id);
CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active) WHERE is_active = true;

-- Pipeline runs indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_id ON pipeline_runs(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_commit_sha ON pipeline_runs(commit_sha);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_branch ON pipeline_runs(branch);

-- Pipeline steps indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_run_id ON pipeline_steps(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_status ON pipeline_steps(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_order ON pipeline_steps(pipeline_run_id, step_order);

-- Validation runs indexes
CREATE INDEX IF NOT EXISTS idx_validation_runs_pipeline_run_id ON validation_runs(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_validation_runs_type ON validation_runs(validation_type);
CREATE INDEX IF NOT EXISTS idx_validation_runs_status ON validation_runs(status);

-- Deployments indexes
CREATE INDEX IF NOT EXISTS idx_deployments_pipeline_run_id ON deployments(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_deployments_environment ON deployments(environment);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);

-- System metrics indexes
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_timestamp ON system_metrics(metric_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);

-- Audit logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- =============================================================================
-- TRIGGERS FOR UPDATED_AT
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pipelines_updated_at BEFORE UPDATE ON pipelines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_integrations_updated_at BEFORE UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- DEFAULT DATA
-- =============================================================================

-- Insert default admin user (password: admin123 - change in production!)
INSERT INTO users (email, username, full_name, hashed_password, is_superuser) 
VALUES (
    'admin@codegencd.local',
    'admin',
    'System Administrator',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJW.LKS5.',
    true
) ON CONFLICT (email) DO NOTHING;

-- Insert sample project
INSERT INTO projects (name, description, owner_id)
SELECT 
    'Sample Project',
    'A sample project for testing CodegenCICD functionality',
    id
FROM users 
WHERE email = 'admin@codegencd.local'
ON CONFLICT DO NOTHING;

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Pipeline runs with project information
CREATE OR REPLACE VIEW pipeline_runs_with_project AS
SELECT 
    pr.*,
    p.name as pipeline_name,
    proj.name as project_name,
    proj.repository_url,
    u.username as triggered_by_username
FROM pipeline_runs pr
JOIN pipelines p ON pr.pipeline_id = p.id
JOIN projects proj ON p.project_id = proj.id
LEFT JOIN users u ON pr.triggered_by = u.id;

-- Recent deployments view
CREATE OR REPLACE VIEW recent_deployments AS
SELECT 
    d.*,
    pr.run_number,
    pr.commit_sha,
    pr.branch,
    p.name as pipeline_name,
    proj.name as project_name,
    u.username as deployed_by_username
FROM deployments d
JOIN pipeline_runs pr ON d.pipeline_run_id = pr.id
JOIN pipelines p ON pr.pipeline_id = p.id
JOIN projects proj ON p.project_id = proj.id
LEFT JOIN users u ON d.deployed_by = u.id
ORDER BY d.started_at DESC;

-- =============================================================================
-- COMPLETION MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'CodegenCICD database initialization completed successfully!';
    RAISE NOTICE 'Default admin user created: admin@codegencd.local (password: admin123)';
    RAISE NOTICE 'Please change the default password in production!';
END $$;

