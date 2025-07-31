# Complete CICD Flow Validation with Web-Eval-Agent

## Overview
This document provides comprehensive instructions for validating the entire CodegenCICD platform using web-eval-agent. The validation covers all UI interactions, backend integrations, and external service connections to ensure a fully functional CICD pipeline.

## Prerequisites Setup

### 1. Clone and Setup Web-Eval-Agent
```bash
# Clone the web-eval-agent repository
git clone https://github.com/Zeeeepa/web-eval-agent.git
cd web-eval-agent

# Install dependencies
npm install
# or
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0"
export PLATFORM_URL="http://localhost:3000"
export API_URL="http://localhost:8000"
export HEADLESS="false"  # Set to true for CI/CD environments
```

### 2. Platform Environment Setup
```bash
# Ensure all required environment variables are set
export CODEGEN_ORG_ID="323"
export CODEGEN_API_TOKEN="your_codegen_api_token_here"
export GITHUB_TOKEN="your_github_token_here"
export GEMINI_API_KEY="your_gemini_api_key_here"
export CLOUDFLARE_API_KEY="your_cloudflare_api_key_here"
export CLOUDFLARE_ACCOUNT_ID="2b2a1d3effa7f7fe4fe2a8c4e48681e3"
export CLOUDFLARE_WORKER_NAME="webhook-gateway"
export CLOUDFLARE_WORKER_URL="https://webhook-gateway.pixeliumperfecto.workers.dev"
```

### 3. Start Platform Services
```bash
# Start backend API server
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start frontend development server (in another terminal)
cd frontend
npm start
# or
npm run dev
```

## Comprehensive UI Interaction Test Scenarios

### Scenario 1: Complete Project Lifecycle
**Objective**: Test full project creation, configuration, and management workflow

**Web-Eval-Agent Instructions**:
```javascript
// Navigate to dashboard
await page.goto('http://localhost:3000');
await page.waitForLoadState('networkidle');

// Test 1: Dashboard Loading and Initial State
await page.waitForSelector('[data-testid="dashboard-header"]');
await page.waitForSelector('[data-testid="project-grid"]');
await page.screenshot({ path: 'test-results/01-dashboard-loaded.png' });

// Test 2: Add New Project - Valid Input
await page.click('[data-testid="add-project-button"]');
await page.waitForSelector('[data-testid="project-selector-dialog"]');
await page.fill('[data-testid="github-owner-input"]', 'Zeeeepa');
await page.fill('[data-testid="github-repo-input"]', 'CodegenCICD');
await page.click('[data-testid="add-project-confirm"]');
await page.waitForSelector('[data-testid="project-card"]');
await page.screenshot({ path: 'test-results/02-project-added.png' });

// Test 3: Project Configuration
await page.click('[data-testid="project-settings-button"]');
await page.waitForSelector('[data-testid="project-settings-dialog"]');

// Configure Planning Statement
await page.fill('[data-testid="planning-statement-input"]', 
  'Implement comprehensive CICD pipeline with automated testing, code quality checks, and deployment validation using grainchain snapshots and web-eval-agent testing');

// Configure Repository Rules
await page.fill('[data-testid="repository-rules-input"]', 
  'Always use TypeScript for new components. Maintain 90% test coverage. Follow Material-UI design patterns. Implement proper error handling.');

// Configure Setup Commands
await page.fill('[data-testid="setup-commands-input"]', 
  'npm install\nnpm run build\nnpm test\nnpm run lint\nnpm run type-check');

// Set Branch Name
await page.selectOption('[data-testid="branch-name-select"]', 'main');

// Enable Auto-merge and Auto-confirm
await page.check('[data-testid="auto-merge-checkbox"]');
await page.check('[data-testid="auto-confirm-plans-checkbox"]');

await page.click('[data-testid="save-settings-button"]');
await page.waitForSelector('[data-testid="settings-saved-notification"]');
await page.screenshot({ path: 'test-results/03-project-configured.png' });
```

### Scenario 2: Secrets Management Validation
**Objective**: Test secure environment variable management

**Web-Eval-Agent Instructions**:
```javascript
// Test 4: Secrets Management
await page.click('[data-testid="project-secrets-tab"]');
await page.waitForSelector('[data-testid="secrets-management-panel"]');

// Add multiple secrets
const secrets = [
  { key: 'DATABASE_URL', value: 'postgresql://user:pass@localhost:5432/testdb' },
  { key: 'REDIS_URL', value: 'redis://localhost:6379' },
  { key: 'JWT_SECRET', value: 'super-secret-jwt-key-for-testing' },
  { key: 'STRIPE_API_KEY', value: 'sk_test_123456789' }
];

for (const secret of secrets) {
  await page.click('[data-testid="add-secret-button"]');
  await page.fill('[data-testid="secret-key-input"]', secret.key);
  await page.fill('[data-testid="secret-value-input"]', secret.value);
  await page.click('[data-testid="save-secret-button"]');
  await page.waitForSelector(`[data-testid="secret-${secret.key}"]`);
}

await page.screenshot({ path: 'test-results/04-secrets-configured.png' });

// Test secret editing
await page.click('[data-testid="edit-secret-DATABASE_URL"]');
await page.fill('[data-testid="secret-value-input"]', 'postgresql://user:newpass@localhost:5432/testdb');
await page.click('[data-testid="save-secret-button"]');

// Test secret deletion
await page.click('[data-testid="delete-secret-STRIPE_API_KEY"]');
await page.click('[data-testid="confirm-delete-button"]');
await page.waitForSelector('[data-testid="secret-STRIPE_API_KEY"]', { state: 'detached' });
```

### Scenario 3: Agent Run Creation and Monitoring
**Objective**: Test complete agent run lifecycle with various input types

**Web-Eval-Agent Instructions**:
```javascript
// Test 5: Agent Run Creation - Simple Task
await page.click('[data-testid="create-agent-run-button"]');
await page.waitForSelector('[data-testid="agent-run-dialog"]');

await page.fill('[data-testid="agent-run-target-input"]', 
  'Add comprehensive error handling to all API endpoints and implement proper logging with correlation IDs');

await page.click('[data-testid="start-agent-run-button"]');
await page.waitForSelector('[data-testid="agent-run-status"]');
await page.screenshot({ path: 'test-results/05-agent-run-started.png' });

// Test 6: Agent Run Creation - Complex Task with File References
await page.click('[data-testid="create-agent-run-button"]');
await page.fill('[data-testid="agent-run-target-input"]', 
  'Refactor the CICDDashboard.tsx component to improve performance by implementing React.memo, useMemo for expensive calculations, and useCallback for event handlers. Also add comprehensive PropTypes validation.');

// Add metadata
await page.click('[data-testid="advanced-options-toggle"]');
await page.fill('[data-testid="metadata-input"]', JSON.stringify({
  priority: 'high',
  category: 'performance',
  files: ['frontend/src/components/CICDDashboard.tsx'],
  estimatedTime: '30 minutes'
}));

await page.click('[data-testid="start-agent-run-button"]');

// Test 7: Agent Run Creation - Database Migration Task
await page.click('[data-testid="create-agent-run-button"]');
await page.fill('[data-testid="agent-run-target-input"]', 
  'Create a new database migration to add indexing for frequently queried columns in the projects and agent_runs tables. Include proper rollback procedures.');

await page.fill('[data-testid="metadata-input"]', JSON.stringify({
  priority: 'medium',
  category: 'database',
  requiresReview: true,
  affectedTables: ['projects', 'agent_runs']
}));

await page.click('[data-testid="start-agent-run-button"]');
```

### Scenario 4: Plan Confirmation Workflow
**Objective**: Test plan review and confirmation process

**Web-Eval-Agent Instructions**:
```javascript
// Test 8: Plan Confirmation - Accept Plan
await page.waitForSelector('[data-testid="plan-confirmation-dialog"]', { timeout: 60000 });
await page.screenshot({ path: 'test-results/06-plan-received.png' });

// Review plan details
const planText = await page.textContent('[data-testid="plan-content"]');
console.log('Plan received:', planText);

// Accept the plan
await page.click('[data-testid="confirm-plan-button"]');
await page.waitForSelector('[data-testid="plan-confirmed-notification"]');
await page.screenshot({ path: 'test-results/07-plan-confirmed.png' });

// Test 9: Plan Confirmation - Reject and Modify
await page.waitForSelector('[data-testid="plan-confirmation-dialog"]', { timeout: 60000 });

// Reject the plan with feedback
await page.click('[data-testid="reject-plan-button"]');
await page.waitForSelector('[data-testid="plan-feedback-dialog"]');
await page.fill('[data-testid="feedback-input"]', 
  'Please also add unit tests for the new error handling functions and update the API documentation to reflect the new error response formats.');

await page.click('[data-testid="submit-feedback-button"]');
await page.waitForSelector('[data-testid="feedback-submitted-notification"]');
```

### Scenario 5: Real-time Updates and Notifications
**Objective**: Test WebSocket connections and live updates

**Web-Eval-Agent Instructions**:
```javascript
// Test 10: Real-time Status Updates
// Monitor agent run progress
let statusChecks = 0;
const maxStatusChecks = 120; // 10 minutes with 5-second intervals

while (statusChecks < maxStatusChecks) {
  await page.waitForTimeout(5000);
  
  const status = await page.textContent('[data-testid="agent-run-status"]');
  const progress = await page.textContent('[data-testid="agent-run-progress"]');
  
  console.log(`Status check ${statusChecks + 1}: ${status} - ${progress}`);
  
  if (status.includes('completed') || status.includes('failed')) {
    break;
  }
  
  statusChecks++;
}

await page.screenshot({ path: 'test-results/08-agent-run-completed.png' });

// Test 11: Webhook Notifications
// Simulate webhook events
const webhookPayloads = [
  {
    event: 'pull_request.opened',
    data: {
      action: 'opened',
      pull_request: { id: 123, number: 1, title: 'Test PR from Codegen' },
      repository: { name: 'CodegenCICD', owner: { login: 'Zeeeepa' } }
    }
  },
  {
    event: 'pull_request.synchronize',
    data: {
      action: 'synchronize',
      pull_request: { id: 123, number: 1, title: 'Test PR from Codegen' },
      repository: { name: 'CodegenCICD', owner: { login: 'Zeeeepa' } }
    }
  }
];

for (const webhook of webhookPayloads) {
  // Send webhook via API
  await page.evaluate(async (payload) => {
    await fetch('http://localhost:8000/api/webhooks/github', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-GitHub-Event': payload.event.split('.')[0]
      },
      body: JSON.stringify(payload.data)
    });
  }, webhook);
  
  // Wait for notification to appear
  await page.waitForSelector('[data-testid="webhook-notification"]', { timeout: 10000 });
  await page.screenshot({ path: `test-results/09-webhook-${webhook.event}.png` });
}
```

### Scenario 6: Error Handling and Edge Cases
**Objective**: Test system resilience and error handling

**Web-Eval-Agent Instructions**:
```javascript
// Test 12: Invalid Input Validation
await page.click('[data-testid="add-project-button"]');
await page.waitForSelector('[data-testid="project-selector-dialog"]');

// Test empty inputs
await page.click('[data-testid="add-project-confirm"]');
await page.waitForSelector('[data-testid="validation-error"]');
await page.screenshot({ path: 'test-results/10-validation-error.png' });

// Test invalid GitHub repository
await page.fill('[data-testid="github-owner-input"]', 'invalid-owner-12345');
await page.fill('[data-testid="github-repo-input"]', 'non-existent-repo-67890');
await page.click('[data-testid="add-project-confirm"]');
await page.waitForSelector('[data-testid="github-error"]');

// Test 13: Network Error Handling
// Simulate network failure
await page.route('**/api/**', route => route.abort());

await page.click('[data-testid="refresh-projects-button"]');
await page.waitForSelector('[data-testid="network-error-notification"]');
await page.screenshot({ path: 'test-results/11-network-error.png' });

// Restore network
await page.unroute('**/api/**');

// Test 14: Large Input Handling
await page.click('[data-testid="create-agent-run-button"]');
const largeInput = 'A'.repeat(10000); // 10KB input
await page.fill('[data-testid="agent-run-target-input"]', largeInput);
await page.click('[data-testid="start-agent-run-button"]');
// Should handle gracefully or show appropriate error
```

### Scenario 7: Performance and Load Testing
**Objective**: Test system performance under various loads

**Web-Eval-Agent Instructions**:
```javascript
// Test 15: Multiple Concurrent Agent Runs
const concurrentRuns = [];
for (let i = 0; i < 5; i++) {
  concurrentRuns.push(
    page.evaluate(async (index) => {
      const response = await fetch('http://localhost:8000/api/agent-runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: `Concurrent test run ${index + 1}: Create a simple utility function`,
          metadata: { test: true, index: index + 1 }
        })
      });
      return response.json();
    }, i)
  );
}

const results = await Promise.all(concurrentRuns);
console.log('Concurrent runs created:', results.length);

// Test 16: Rapid UI Interactions
for (let i = 0; i < 10; i++) {
  await page.click('[data-testid="refresh-projects-button"]');
  await page.waitForTimeout(100);
}

// Verify UI remains responsive
await page.waitForSelector('[data-testid="project-grid"]');
await page.screenshot({ path: 'test-results/12-rapid-interactions.png' });
```

## Advanced Testing Scenarios

### Scenario 8: Integration Testing
**Objective**: Test all external service integrations

**Web-Eval-Agent Instructions**:
```javascript
// Test 17: GitHub Integration
await page.evaluate(async () => {
  const response = await fetch('http://localhost:8000/api/github/repositories', {
    headers: { 'Authorization': 'Bearer ' + process.env.GITHUB_TOKEN }
  });
  return response.ok;
});

// Test 18: Codegen API Integration
await page.evaluate(async () => {
  const response = await fetch('http://localhost:8000/api/codegen/health', {
    headers: { 'Authorization': 'Bearer ' + process.env.CODEGEN_API_TOKEN }
  });
  return response.ok;
});

// Test 19: Grainchain Integration
await page.evaluate(async () => {
  const response = await fetch('http://localhost:8000/api/grainchain/snapshots');
  return response.ok;
});

// Test 20: Cloudflare Integration
await page.evaluate(async () => {
  const response = await fetch('http://localhost:8000/api/cloudflare/workers');
  return response.ok;
});
```

## Execution Instructions

### 1. Run Individual Test Scenarios
```bash
# Run specific test scenario
node scripts/web-eval-agent-tests/test-complete-cicd-flow.js --scenario="project-lifecycle"
node scripts/web-eval-agent-tests/test-complete-cicd-flow.js --scenario="secrets-management"
node scripts/web-eval-agent-tests/test-complete-cicd-flow.js --scenario="agent-runs"
```

### 2. Run Complete Test Suite
```bash
# Run all test scenarios
node scripts/web-eval-agent-tests/test-complete-cicd-flow.js --all

# Run with specific configuration
HEADLESS=false TIMEOUT=60000 node scripts/web-eval-agent-tests/test-complete-cicd-flow.js --all
```

### 3. Generate Comprehensive Report
```bash
# Generate detailed HTML report with screenshots
node scripts/web-eval-agent-tests/test-complete-cicd-flow.js --report --output="test-results/full-validation-report.html"
```

## Success Criteria

### ✅ All tests must pass:
1. **UI Responsiveness**: All interactions complete within 5 seconds
2. **Data Persistence**: All configurations and secrets are properly saved
3. **Real-time Updates**: WebSocket connections work and updates appear instantly
4. **Error Handling**: All error scenarios display appropriate messages
5. **Integration**: All external services respond correctly
6. **Performance**: System handles concurrent operations without degradation
7. **Security**: Secrets are encrypted and never exposed in logs or UI

### 📊 Performance Benchmarks:
- Page load time: < 3 seconds
- API response time: < 500ms
- Agent run creation: < 2 seconds
- Real-time update latency: < 1 second
- Memory usage: < 512MB for frontend
- CPU usage: < 50% during normal operations

### 🔒 Security Validations:
- All secrets encrypted at rest
- No sensitive data in browser console
- Proper authentication for all API calls
- CORS policies correctly configured
- Input validation prevents XSS/injection attacks

## Troubleshooting

### Common Issues:
1. **Timeout Errors**: Increase TIMEOUT environment variable
2. **Network Failures**: Check API server is running on port 8000
3. **Authentication Errors**: Verify all API keys are valid
4. **UI Element Not Found**: Check data-testid attributes exist in components
5. **WebSocket Issues**: Ensure WebSocket server is properly configured

### Debug Mode:
```bash
# Run with debug logging
DEBUG=true HEADLESS=false node scripts/web-eval-agent-tests/test-complete-cicd-flow.js --all
```

This comprehensive validation ensures that every aspect of the CodegenCICD platform is thoroughly tested and validated before deployment.
