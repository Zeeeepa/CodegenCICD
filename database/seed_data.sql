-- ============================================================================
-- Seed Data for CodegenCICD Dashboard
-- ============================================================================
-- Sample data for development and testing purposes
-- ============================================================================

-- Create schema migrations table if it doesn't exist
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sample projects
INSERT OR IGNORE INTO projects (
    name, 
    github_repo_url, 
    github_repo_name, 
    github_owner, 
    description, 
    default_branch,
    is_active,
    auto_merge_enabled,
    auto_confirm_plans
) VALUES 
(
    'CodegenCICD',
    'https://github.com/Zeeeepa/CodegenCICD',
    'CodegenCICD',
    'Zeeeepa',
    'AI-Powered CICD Dashboard with comprehensive testing and validation',
    'main',
    1,
    0,
    0
),
(
    'Web-Eval-Agent',
    'https://github.com/Zeeeepa/web-eval-agent',
    'web-eval-agent',
    'Zeeeepa',
    'Browser automation and UI testing framework',
    'main',
    1,
    1,
    1
),
(
    'Grainchain',
    'https://github.com/Zeeeepa/grainchain',
    'grainchain',
    'Zeeeepa',
    'Sandboxing and snapshot creation for code validation',
    'main',
    1,
    0,
    0
),
(
    'Graph-Sitter',
    'https://github.com/Zeeeepa/graph-sitter',
    'graph-sitter',
    'Zeeeepa',
    'Static analysis and code quality metrics',
    'main',
    1,
    1,
    0
);

-- Sample project settings
INSERT OR IGNORE INTO project_settings (
    project_id,
    planning_statement,
    repository_rules,
    setup_commands,
    target_branch,
    deployment_config,
    notification_config
) VALUES 
(
    1,
    'Build a comprehensive CICD dashboard with full web-eval-agent integration, automated testing, and robust error handling. Focus on user experience and real-time feedback.',
    'Follow Python best practices, use type hints, comprehensive error handling, and maintain >90% test coverage. All commits must be signed and pass security scans.',
    'pip install -r requirements.txt\ncd frontend && npm install && npm run build\ncd .. && python -m pytest tests/',
    'main',
    '{"environment": "production", "auto_deploy": false, "require_tests": true}',
    '{"slack_webhook": null, "email_notifications": true, "pr_notifications": true}'
),
(
    2,
    'Enhance web-eval-agent with comprehensive browser automation capabilities and Gemini API integration for intelligent testing.',
    'Maintain compatibility with existing test suites, ensure cross-browser support, and implement proper error handling for all automation scenarios.',
    'pip install -r requirements.txt\nplaywright install\npython -m pytest tests/ --browser=chromium',
    'main',
    '{"environment": "testing", "auto_deploy": true, "require_tests": true}',
    '{"slack_webhook": null, "email_notifications": false, "pr_notifications": true}'
),
(
    3,
    'Improve grainchain snapshot creation and management with better resource cleanup and validation reporting.',
    'Ensure proper resource cleanup, implement comprehensive logging, and maintain backward compatibility with existing snapshot formats.',
    'pip install -r requirements.txt\ndocker build -t grainchain .\npython -m pytest tests/',
    'main',
    '{"environment": "development", "auto_deploy": false, "require_tests": true}',
    '{"slack_webhook": null, "email_notifications": true, "pr_notifications": false}'
),
(
    4,
    'Enhance graph-sitter with additional language support and improved code quality metrics.',
    'Maintain performance standards, ensure accurate parsing for all supported languages, and provide comprehensive documentation.',
    'cargo build --release\ncargo test\npython setup.py install',
    'main',
    '{"environment": "production", "auto_deploy": true, "require_tests": true}',
    '{"slack_webhook": null, "email_notifications": true, "pr_notifications": true}'
);

-- Sample project secrets (encrypted values are placeholders)
INSERT OR IGNORE INTO project_secrets (
    project_id,
    key_name,
    encrypted_value,
    description,
    is_active
) VALUES 
(
    1,
    'CODEGEN_API_TOKEN',
    'encrypted_sk_ce027fa7_3c8d_4beb_8c86_ed8ae982ac99',
    'API token for Codegen service integration',
    1
),
(
    1,
    'GITHUB_TOKEN',
    'encrypted_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',
    'GitHub personal access token for repository operations',
    1
),
(
    1,
    'CLOUDFLARE_API_KEY',
    'encrypted_eae82cf159577a8838cc83612104c09c5a0d6',
    'Cloudflare API key for webhook gateway',
    1
),
(
    2,
    'GEMINI_API_KEY',
    'encrypted_AIzaSyBXmhlHudrD4zXiv_5fjxi1gGG_GkdtaZ0',
    'Google Gemini API key for AI testing capabilities',
    1
),
(
    2,
    'PLAYWRIGHT_BROWSERS_PATH',
    'encrypted_opt_playwright_browsers',
    'Path to Playwright browser installations',
    1
),
(
    3,
    'DOCKER_REGISTRY_TOKEN',
    'encrypted_docker_registry_token_placeholder',
    'Docker registry authentication token',
    1
),
(
    4,
    'RUST_BACKTRACE',
    'encrypted_1',
    'Enable Rust backtrace for debugging',
    1
);

-- Sample agent runs
INSERT OR IGNORE INTO agent_runs (
    project_id,
    codegen_run_id,
    prompt,
    planning_statement,
    status,
    result,
    metadata,
    web_url,
    github_pr_url,
    github_pr_number
) VALUES 
(
    1,
    63369,
    'Implement comprehensive UI dashboard with GitHub project management, real-time notifications, and agent run orchestration.',
    'Build a comprehensive CICD dashboard with full web-eval-agent integration, automated testing, and robust error handling.',
    'completed',
    'Successfully implemented dashboard with project cards, settings dialogs, and real-time GitHub integration.',
    '{"source": "api", "priority": "high", "features": ["ui", "github", "notifications"]}',
    'https://codegen.com/agent/trace/63369',
    'https://github.com/Zeeeepa/CodegenCICD/pull/23',
    23
),
(
    2,
    63370,
    'Add comprehensive browser automation tests with Gemini API integration for intelligent test validation.',
    'Enhance web-eval-agent with comprehensive browser automation capabilities and Gemini API integration.',
    'running',
    null,
    '{"source": "webhook", "priority": "medium", "features": ["automation", "gemini", "testing"]}',
    'https://codegen.com/agent/trace/63370',
    null,
    null
),
(
    1,
    63371,
    'Fix API test validation and implement proper response handling with comprehensive error management.',
    'Build a comprehensive CICD dashboard with full web-eval-agent integration, automated testing, and robust error handling.',
    'pending',
    null,
    '{"source": "manual", "priority": "high", "features": ["api", "validation", "errors"]}',
    'https://codegen.com/agent/trace/63371',
    null,
    null
);

-- Sample pipeline states
INSERT OR IGNORE INTO pipeline_states (
    agent_run_id,
    state,
    previous_state,
    data,
    retry_count
) VALUES 
(
    1,
    'completed',
    'validation_complete',
    '{"pr_merged": true, "tests_passed": true, "validation_score": 95}',
    0
),
(
    2,
    'testing',
    'deployment_running',
    '{"snapshot_id": "snap_abc123", "tests_running": 5, "tests_completed": 2}',
    0
),
(
    3,
    'created',
    null,
    '{"initial_setup": true, "webhook_configured": false}',
    0
);

-- Sample webhooks
INSERT OR IGNORE INTO webhooks (
    project_id,
    webhook_type,
    webhook_url,
    secret_token,
    events,
    is_active
) VALUES 
(
    1,
    'github_pr',
    'https://webhook-gateway.pixeliumperfecto.workers.dev/github/pr',
    'webhook_secret_placeholder',
    '["pull_request", "pull_request_review"]',
    1
),
(
    2,
    'github_push',
    'https://webhook-gateway.pixeliumperfecto.workers.dev/github/push',
    'webhook_secret_placeholder',
    '["push", "release"]',
    1
),
(
    3,
    'cloudflare',
    'https://webhook-gateway.pixeliumperfecto.workers.dev/cloudflare',
    'cloudflare_secret_placeholder',
    '["deployment", "error"]',
    1
);

-- Sample test results
INSERT OR IGNORE INTO test_results (
    agent_run_id,
    test_type,
    test_name,
    status,
    result_data,
    duration_seconds,
    screenshot_path,
    log_path
) VALUES 
(
    1,
    'web-eval-agent',
    'Dashboard UI Functionality Test',
    'passed',
    '{"components_tested": 8, "interactions_verified": 15, "performance_score": 92}',
    45.2,
    '/test_results/screenshots/dashboard_test_20250729.png',
    '/test_results/logs/dashboard_test_20250729.log'
),
(
    1,
    'api',
    'GitHub Integration API Test',
    'passed',
    '{"endpoints_tested": 12, "response_times": [120, 89, 156, 203], "success_rate": 100}',
    12.8,
    null,
    '/test_results/logs/api_test_20250729.log'
),
(
    2,
    'playwright',
    'Browser Automation Test Suite',
    'running',
    '{"tests_total": 25, "tests_completed": 18, "tests_passed": 16, "tests_failed": 2}',
    null,
    '/test_results/screenshots/automation_test_20250729.png',
    '/test_results/logs/automation_test_20250729.log'
);

-- Sample grainchain snapshots
INSERT OR IGNORE INTO grainchain_snapshots (
    agent_run_id,
    snapshot_id,
    status,
    config,
    validation_results
) VALUES 
(
    1,
    'snap_codegen_cicd_20250729_001',
    'completed',
    '{"base_image": "ubuntu:22.04", "tools": ["graph-sitter", "web-eval-agent"], "env_vars": ["CODEGEN_API_TOKEN", "GITHUB_TOKEN"]}',
    '{"deployment_success": true, "tests_passed": 8, "performance_score": 95, "security_scan": "passed"}'
),
(
    2,
    'snap_web_eval_agent_20250729_001',
    'running',
    '{"base_image": "playwright:latest", "tools": ["gemini-api", "browser-automation"], "env_vars": ["GEMINI_API_KEY", "PLAYWRIGHT_BROWSERS_PATH"]}',
    null
);

-- Sample system logs
INSERT OR IGNORE INTO system_logs (
    level,
    message,
    component,
    context,
    correlation_id
) VALUES 
(
    'INFO',
    'Database schema initialized successfully',
    'database',
    '{"migration_version": "001", "tables_created": 9, "indexes_created": 20}',
    'init_001'
),
(
    'INFO',
    'Project created successfully',
    'project_service',
    '{"project_id": 1, "project_name": "CodegenCICD", "github_repo": "Zeeeepa/CodegenCICD"}',
    'proj_001'
),
(
    'INFO',
    'Agent run started',
    'agent_service',
    '{"agent_run_id": 1, "project_id": 1, "codegen_run_id": 63369}',
    'agent_001'
),
(
    'WARNING',
    'Rate limit approaching for GitHub API',
    'github_client',
    '{"remaining_requests": 150, "reset_time": "2025-07-29T11:00:00Z", "limit": 5000}',
    'github_001'
),
(
    'ERROR',
    'Webhook delivery failed',
    'webhook_handler',
    '{"webhook_id": 1, "project_id": 1, "error": "Connection timeout", "retry_count": 2}',
    'webhook_001'
);

-- Update statistics
ANALYZE;

