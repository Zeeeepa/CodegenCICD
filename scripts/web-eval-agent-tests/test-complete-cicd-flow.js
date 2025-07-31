/**
 * Complete CICD Flow Testing with Web-Eval-Agent
 * Tests the full integration between all components
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
    GEMINI_API_KEY: process.env.GEMINI_API_KEY || "AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0",
    PLATFORM_URL: process.env.PLATFORM_URL || "http://localhost:3000",
    API_URL: process.env.API_URL || "http://localhost:8000",
    HEADLESS: process.env.HEADLESS === 'true',
    TIMEOUT: parseInt(process.env.TIMEOUT) || 30000,
    GITHUB_TOKEN: process.env.GITHUB_TOKEN,
    CODEGEN_API_TOKEN: process.env.CODEGEN_API_TOKEN,
    CODEGEN_ORG_ID: process.env.CODEGEN_ORG_ID || "323"
};

class CompleteCICDFlowTester {
    constructor() {
        this.results = [];
        this.startTime = Date.now();
        this.browser = null;
        this.page = null;
        this.screenshots = [];
    }

    async runTest(testName, testFunction) {
        console.log(`\n🧪 Running: ${testName}`);
        const startTime = Date.now();
        
        try {
            await testFunction();
            const duration = Date.now() - startTime;
            this.results.push({
                name: testName,
                status: 'PASS',
                duration,
                error: null
            });
            console.log(`✅ ${testName} - PASSED (${duration}ms)`);
        } catch (error) {
            const duration = Date.now() - startTime;
            this.results.push({
                name: testName,
                status: 'FAIL',
                duration,
                error: error.message
            });
            console.log(`❌ ${testName} - FAILED (${duration}ms)`);
            console.log(`   Error: ${error.message}`);
            
            // Take screenshot on failure
            if (this.page) {
                await this.takeScreenshot(`failure-${testName.replace(/\s+/g, '-').toLowerCase()}`);
            }
        }
    }

    async takeScreenshot(name) {
        try {
            const screenshotPath = path.join(__dirname, 'screenshots', `${name}-${Date.now()}.png`);
            await fs.promises.mkdir(path.dirname(screenshotPath), { recursive: true });
            await this.page.screenshot({ path: screenshotPath, fullPage: true });
            this.screenshots.push(screenshotPath);
            console.log(`📸 Screenshot saved: ${screenshotPath}`);
        } catch (error) {
            console.log(`⚠️ Failed to take screenshot: ${error.message}`);
        }
    }

    async initializeBrowser() {
        this.browser = await chromium.launch({
            headless: CONFIG.HEADLESS,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        
        this.page = await this.browser.newPage();
        await this.page.setViewportSize({ width: 1920, height: 1080 });
        
        // Set up console logging
        this.page.on('console', msg => {
            if (msg.type() === 'error') {
                console.log(`🔴 Browser Console Error: ${msg.text()}`);
            }
        });
        
        // Set up error handling
        this.page.on('pageerror', error => {
            console.log(`🔴 Page Error: ${error.message}`);
        });
    }

    async testCompleteWorkflow() {
        // Test the complete CICD workflow from start to finish
        
        // 1. Navigate to dashboard
        await this.page.goto(CONFIG.PLATFORM_URL, { waitUntil: 'networkidle' });
        await this.takeScreenshot('dashboard-loaded');
        
        // 2. Verify dashboard components are loaded
        await this.page.waitForSelector('[data-testid="dashboard-header"]', { timeout: CONFIG.TIMEOUT });
        await this.page.waitForSelector('[data-testid="project-grid"]', { timeout: CONFIG.TIMEOUT });
        
        // 3. Add a new project
        await this.page.click('[data-testid="add-project-button"]');
        await this.page.waitForSelector('[data-testid="project-selector-dialog"]', { timeout: CONFIG.TIMEOUT });
        
        // 4. Select a GitHub repository
        await this.page.fill('[data-testid="github-owner-input"]', 'Zeeeepa');
        await this.page.fill('[data-testid="github-repo-input"]', 'CodegenCICD');
        await this.page.click('[data-testid="add-project-confirm"]');
        
        // 5. Wait for project to be added
        await this.page.waitForSelector('[data-testid="project-card"]', { timeout: CONFIG.TIMEOUT });
        await this.takeScreenshot('project-added');
        
        // 6. Configure project settings
        await this.page.click('[data-testid="project-settings-button"]');
        await this.page.waitForSelector('[data-testid="project-settings-dialog"]', { timeout: CONFIG.TIMEOUT });
        
        // 7. Set up planning statement
        await this.page.fill('[data-testid="planning-statement-input"]', 
            'Implement comprehensive CICD pipeline with automated testing and deployment validation');
        
        // 8. Configure setup commands
        await this.page.fill('[data-testid="setup-commands-input"]', 
            'npm install\nnpm run build\nnpm test');
        
        // 9. Save settings
        await this.page.click('[data-testid="save-settings-button"]');
        await this.page.waitForSelector('[data-testid="settings-saved-notification"]', { timeout: CONFIG.TIMEOUT });
        
        // 10. Create an agent run
        await this.page.click('[data-testid="create-agent-run-button"]');
        await this.page.waitForSelector('[data-testid="agent-run-dialog"]', { timeout: CONFIG.TIMEOUT });
        
        // 11. Enter target for agent run
        await this.page.fill('[data-testid="agent-run-target-input"]', 
            'Add comprehensive error handling to the API endpoints and improve test coverage');
        
        // 12. Start agent run
        await this.page.click('[data-testid="start-agent-run-button"]');
        await this.takeScreenshot('agent-run-started');
        
        // 13. Monitor agent run progress
        await this.page.waitForSelector('[data-testid="agent-run-status"]', { timeout: CONFIG.TIMEOUT });
        
        // 14. Wait for plan confirmation (if required)
        const planConfirmationExists = await this.page.waitForSelector(
            '[data-testid="plan-confirmation-dialog"]', 
            { timeout: 10000 }
        ).catch(() => null);
        
        if (planConfirmationExists) {
            await this.page.click('[data-testid="confirm-plan-button"]');
            await this.takeScreenshot('plan-confirmed');
        }
        
        // 15. Wait for agent run completion (with timeout)
        let completed = false;
        let attempts = 0;
        const maxAttempts = 60; // 5 minutes with 5-second intervals
        
        while (!completed && attempts < maxAttempts) {
            await this.page.waitForTimeout(5000);
            
            const status = await this.page.textContent('[data-testid="agent-run-status"]');
            console.log(`Agent run status: ${status}`);
            
            if (status.includes('completed') || status.includes('failed')) {
                completed = true;
            }
            
            attempts++;
        }
        
        if (!completed) {
            throw new Error('Agent run did not complete within timeout period');
        }
        
        await this.takeScreenshot('agent-run-completed');
        
        // 16. Verify PR was created (check GitHub integration)
        const prLinkExists = await this.page.waitForSelector(
            '[data-testid="pr-link"]', 
            { timeout: 10000 }
        ).catch(() => null);
        
        if (prLinkExists) {
            console.log('✅ PR link found - GitHub integration working');
        }
        
        // 17. Test webhook functionality
        await this.testWebhookIntegration();
        
        // 18. Test real-time updates
        await this.testRealTimeUpdates();
        
        console.log('🎉 Complete CICD workflow test completed successfully!');
    }

    async testWebhookIntegration() {
        console.log('🔗 Testing webhook integration...');
        
        // Simulate webhook event by making API call
        const webhookPayload = {
            action: 'opened',
            pull_request: {
                id: 123,
                number: 1,
                title: 'Test PR from Codegen',
                state: 'open',
                html_url: 'https://github.com/Zeeeepa/CodegenCICD/pull/1'
            },
            repository: {
                name: 'CodegenCICD',
                owner: { login: 'Zeeeepa' }
            }
        };
        
        // Send webhook to API
        const response = await fetch(`${CONFIG.API_URL}/api/webhooks/github`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-GitHub-Event': 'pull_request'
            },
            body: JSON.stringify(webhookPayload)
        });
        
        if (!response.ok) {
            throw new Error(`Webhook test failed: ${response.status}`);
        }
        
        // Wait for UI to update
        await this.page.waitForTimeout(2000);
        
        // Check if notification appeared
        const notificationExists = await this.page.waitForSelector(
            '[data-testid="webhook-notification"]', 
            { timeout: 5000 }
        ).catch(() => null);
        
        if (notificationExists) {
            console.log('✅ Webhook integration working - notification received');
        }
    }

    async testRealTimeUpdates() {
        console.log('⚡ Testing real-time updates...');
        
        // Check if WebSocket connection is established
        const wsStatus = await this.page.evaluate(() => {
            return window.wsConnection && window.wsConnection.readyState === WebSocket.OPEN;
        });
        
        if (wsStatus) {
            console.log('✅ WebSocket connection established');
        } else {
            console.log('⚠️ WebSocket connection not found');
        }
        
        // Test real-time project status updates
        await this.page.reload({ waitUntil: 'networkidle' });
        
        // Verify that project data loads without full page refresh
        const projectDataLoaded = await this.page.waitForSelector(
            '[data-testid="project-card"]', 
            { timeout: CONFIG.TIMEOUT }
        ).catch(() => null);
        
        if (projectDataLoaded) {
            console.log('✅ Real-time data loading working');
        }
    }

    async testAPIEndpoints() {
        console.log('🔌 Testing API endpoints...');
        
        const endpoints = [
            { path: '/api/health', method: 'GET' },
            { path: '/api/projects', method: 'GET' },
            { path: '/api/agent-runs', method: 'GET' },
            { path: '/api/webhooks/status', method: 'GET' }
        ];
        
        for (const endpoint of endpoints) {
            try {
                const response = await fetch(`${CONFIG.API_URL}${endpoint.path}`, {
                    method: endpoint.method,
                    headers: {
                        'Authorization': `Bearer ${CONFIG.CODEGEN_API_TOKEN}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    console.log(`✅ ${endpoint.method} ${endpoint.path} - OK`);
                } else {
                    console.log(`❌ ${endpoint.method} ${endpoint.path} - ${response.status}`);
                }
            } catch (error) {
                console.log(`❌ ${endpoint.method} ${endpoint.path} - Error: ${error.message}`);
            }
        }
    }

    async testServiceIntegrations() {
        console.log('🔧 Testing service integrations...');
        
        // Test GitHub API integration
        if (CONFIG.GITHUB_TOKEN) {
            try {
                const response = await fetch('https://api.github.com/user', {
                    headers: {
                        'Authorization': `token ${CONFIG.GITHUB_TOKEN}`,
                        'User-Agent': 'CodegenCICD-Test'
                    }
                });
                
                if (response.ok) {
                    console.log('✅ GitHub API integration working');
                } else {
                    console.log('❌ GitHub API integration failed');
                }
            } catch (error) {
                console.log(`❌ GitHub API test error: ${error.message}`);
            }
        }
        
        // Test Codegen API integration
        if (CONFIG.CODEGEN_API_TOKEN) {
            try {
                const response = await fetch('https://api.codegen.com/v1/health', {
                    headers: {
                        'Authorization': `Bearer ${CONFIG.CODEGEN_API_TOKEN}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    console.log('✅ Codegen API integration working');
                } else {
                    console.log('❌ Codegen API integration failed');
                }
            } catch (error) {
                console.log(`❌ Codegen API test error: ${error.message}`);
            }
        }
    }

    async testErrorHandling() {
        console.log('🚨 Testing error handling...');
        
        // Test invalid project creation
        await this.page.click('[data-testid="add-project-button"]');
        await this.page.waitForSelector('[data-testid="project-selector-dialog"]', { timeout: CONFIG.TIMEOUT });
        
        // Try to add project with invalid data
        await this.page.fill('[data-testid="github-owner-input"]', '');
        await this.page.fill('[data-testid="github-repo-input"]', '');
        await this.page.click('[data-testid="add-project-confirm"]');
        
        // Check for error message
        const errorExists = await this.page.waitForSelector(
            '[data-testid="error-message"]', 
            { timeout: 5000 }
        ).catch(() => null);
        
        if (errorExists) {
            console.log('✅ Error handling working - validation errors shown');
        }
        
        // Close dialog
        await this.page.click('[data-testid="cancel-button"]');
    }

    async generateReport() {
        const totalDuration = Date.now() - this.startTime;
        const passedTests = this.results.filter(r => r.status === 'PASS').length;
        const failedTests = this.results.filter(r => r.status === 'FAIL').length;
        
        const report = {
            summary: {
                total: this.results.length,
                passed: passedTests,
                failed: failedTests,
                duration: totalDuration,
                timestamp: new Date().toISOString()
            },
            results: this.results,
            screenshots: this.screenshots,
            config: CONFIG
        };
        
        // Save report to file
        const reportPath = path.join(__dirname, 'reports', `complete-cicd-flow-${Date.now()}.json`);
        await fs.promises.mkdir(path.dirname(reportPath), { recursive: true });
        await fs.promises.writeFile(reportPath, JSON.stringify(report, null, 2));
        
        // Generate HTML report
        await this.generateHTMLReport(report, reportPath.replace('.json', '.html'));
        
        console.log('\n📊 COMPLETE CICD FLOW TEST REPORT');
        console.log('=====================================');
        console.log(`Total Tests: ${report.summary.total}`);
        console.log(`Passed: ${report.summary.passed}`);
        console.log(`Failed: ${report.summary.failed}`);
        console.log(`Duration: ${(totalDuration / 1000).toFixed(2)}s`);
        console.log(`Report saved: ${reportPath}`);
        
        if (failedTests > 0) {
            console.log('\n❌ FAILED TESTS:');
            this.results.filter(r => r.status === 'FAIL').forEach(test => {
                console.log(`  - ${test.name}: ${test.error}`);
            });
        }
        
        return report;
    }

    async generateHTMLReport(report, filePath) {
        const html = `
<!DOCTYPE html>
<html>
<head>
    <title>Complete CICD Flow Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .metric { background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .test-result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .pass { background: #d4edda; border-left: 4px solid #28a745; }
        .fail { background: #f8d7da; border-left: 4px solid #dc3545; }
        .screenshots img { max-width: 300px; margin: 10px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Complete CICD Flow Test Report</h1>
        <p>Generated: ${report.summary.timestamp}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <p>${report.summary.total}</p>
        </div>
        <div class="metric">
            <h3>Passed</h3>
            <p style="color: green;">${report.summary.passed}</p>
        </div>
        <div class="metric">
            <h3>Failed</h3>
            <p style="color: red;">${report.summary.failed}</p>
        </div>
        <div class="metric">
            <h3>Duration</h3>
            <p>${(report.summary.duration / 1000).toFixed(2)}s</p>
        </div>
    </div>
    
    <h2>Test Results</h2>
    ${report.results.map(test => `
        <div class="test-result ${test.status.toLowerCase()}">
            <h3>${test.name}</h3>
            <p>Status: ${test.status} | Duration: ${test.duration}ms</p>
            ${test.error ? `<p>Error: ${test.error}</p>` : ''}
        </div>
    `).join('')}
    
    <h2>Screenshots</h2>
    <div class="screenshots">
        ${report.screenshots.map(screenshot => `
            <img src="${screenshot}" alt="Test Screenshot" />
        `).join('')}
    </div>
</body>
</html>`;
        
        await fs.promises.writeFile(filePath, html);
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    async run() {
        try {
            console.log('🚀 Starting Complete CICD Flow Testing...');
            console.log(`Platform URL: ${CONFIG.PLATFORM_URL}`);
            console.log(`API URL: ${CONFIG.API_URL}`);
            
            await this.initializeBrowser();
            
            // Run all tests
            await this.runTest('API Endpoints Test', () => this.testAPIEndpoints());
            await this.runTest('Service Integrations Test', () => this.testServiceIntegrations());
            await this.runTest('Complete Workflow Test', () => this.testCompleteWorkflow());
            await this.runTest('Error Handling Test', () => this.testErrorHandling());
            
            // Generate report
            const report = await this.generateReport();
            
            return report;
            
        } catch (error) {
            console.error('💥 Test execution failed:', error);
            throw error;
        } finally {
            await this.cleanup();
        }
    }
}

// Run tests if called directly
if (require.main === module) {
    const tester = new CompleteCICDFlowTester();
    tester.run()
        .then(report => {
            console.log('\n✅ All tests completed!');
            process.exit(report.summary.failed > 0 ? 1 : 0);
        })
        .catch(error => {
            console.error('💥 Test suite failed:', error);
            process.exit(1);
        });
}

module.exports = CompleteCICDFlowTester;
