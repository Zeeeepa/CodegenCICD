# 🌐 Web-eval-agent Complete CICD Flow Validation Instructions

## 🎯 Overview

This document provides comprehensive instructions for validating ALL features and functions of the CodegenCICD platform using web-eval-agent. Every UI interaction, API endpoint, and system component MUST be validated through automated testing.

## 🚀 Quick Setup

### 1. Clone and Setup Web-eval-agent
```bash
# Clone web-eval-agent repository
git clone https://github.com/Zeeeepa/web-eval-agent.git
cd web-eval-agent

# Set Gemini API key
export GEMINI_API_KEY="AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0"

# Install dependencies
npm install
```

### 2. Setup CodegenCICD Platform
```bash
# In a separate terminal, setup the main platform
cd ../CodegenCICD
npm install
npm run setup
npm run dev
```

## 🧪 Complete CICD Flow Test Suite

### Phase 1: Environment Validation
```bash
# Test 1: Verify all services are running
npm run test:services-health

# Test 2: Validate API endpoints
npm run test:api-endpoints

# Test 3: Check database connectivity
npm run test:database-connection
```

### Phase 2: Web-eval-agent Integration Testing

#### 2.1 Basic Functionality Tests
```bash
# Navigate to web-eval-agent directory
cd web-eval-agent

# Test basic web-eval-agent functionality
node test-basic-functionality.js
```

#### 2.2 CodegenCICD Platform UI Testing
```bash
# Test all UI components and interactions
node test-codegen-ui-complete.js
```

#### 2.3 API Integration Testing
```bash
# Test all API endpoints through UI
node test-api-integration.js
```

## 📋 Comprehensive Test Scenarios

### Scenario 1: Complete User Journey Testing

#### 1.1 Authentication Flow
- [ ] Login page validation
- [ ] Registration process
- [ ] Password reset functionality
- [ ] Session management
- [ ] Logout process

#### 1.2 Dashboard Navigation
- [ ] Main dashboard loading
- [ ] Navigation menu functionality
- [ ] Sidebar interactions
- [ ] Header components
- [ ] Footer elements

#### 1.3 Project Management
- [ ] Create new project
- [ ] Edit project settings
- [ ] Delete project
- [ ] Project list view
- [ ] Project search functionality

### Scenario 2: Service Integration Testing

#### 2.1 Grainchain Service Testing
- [ ] Sandbox provider selection
- [ ] Code execution interface
- [ ] Result display
- [ ] Error handling
- [ ] Performance monitoring

#### 2.2 Graph-sitter Service Testing
- [ ] Code analysis interface
- [ ] Language selection
- [ ] Analysis results display
- [ ] Quality metrics visualization
- [ ] Export functionality

#### 2.3 Web-eval-agent Service Testing
- [ ] UI testing configuration
- [ ] Test scenario creation
- [ ] Accessibility testing
- [ ] Performance auditing
- [ ] Report generation

#### 2.4 Codegen SDK Service Testing
- [ ] Agent configuration
- [ ] Task creation
- [ ] Execution monitoring
- [ ] Result processing
- [ ] Integration with other services

### Scenario 3: Pipeline Execution Testing

#### 3.1 Complete Pipeline Flow
- [ ] Pipeline configuration
- [ ] Stage-by-stage execution
- [ ] Progress monitoring
- [ ] Error handling
- [ ] Result aggregation

#### 3.2 Individual Stage Testing
- [ ] Initialization stage
- [ ] Code analysis stage
- [ ] Sandbox execution stage
- [ ] UI testing stage
- [ ] Results integration stage
- [ ] Completion stage

## 🔧 Test Implementation Scripts

### Script 1: Basic Functionality Test
```javascript
// test-basic-functionality.js
const { WebEvalAgent } = require('./src/web-eval-agent');

async function testBasicFunctionality() {
    console.log('🧪 Testing Web-eval-agent Basic Functionality...');
    
    const agent = new WebEvalAgent({
        geminiApiKey: process.env.GEMINI_API_KEY,
        headless: false // Set to true for CI/CD
    });
    
    try {
        // Test 1: Initialize browser
        await agent.initialize();
        console.log('✅ Browser initialization successful');
        
        // Test 2: Navigate to CodegenCICD platform
        await agent.navigate('http://localhost:3000');
        console.log('✅ Navigation to platform successful');
        
        // Test 3: Take screenshot
        const screenshot = await agent.screenshot();
        console.log('✅ Screenshot capture successful');
        
        // Test 4: Basic interaction
        await agent.click('button[data-testid="get-started"]');
        console.log('✅ Basic interaction successful');
        
        await agent.close();
        console.log('🎉 Basic functionality tests completed successfully!');
        
    } catch (error) {
        console.error('❌ Basic functionality test failed:', error);
        await agent.close();
        process.exit(1);
    }
}

testBasicFunctionality();
```

### Script 2: Complete UI Testing
```javascript
// test-codegen-ui-complete.js
const { WebEvalAgent } = require('./src/web-eval-agent');

async function testCompleteUI() {
    console.log('🌐 Testing Complete CodegenCICD UI...');
    
    const agent = new WebEvalAgent({
        geminiApiKey: process.env.GEMINI_API_KEY,
        headless: false,
        viewport: { width: 1920, height: 1080 }
    });
    
    const testResults = [];
    
    try {
        await agent.initialize();
        await agent.navigate('http://localhost:3000');
        
        // Test Suite 1: Authentication
        console.log('🔐 Testing Authentication Flow...');
        await testAuthenticationFlow(agent, testResults);
        
        // Test Suite 2: Dashboard
        console.log('📊 Testing Dashboard Components...');
        await testDashboardComponents(agent, testResults);
        
        // Test Suite 3: Service Integration
        console.log('🔗 Testing Service Integration...');
        await testServiceIntegration(agent, testResults);
        
        // Test Suite 4: Pipeline Execution
        console.log('⚙️ Testing Pipeline Execution...');
        await testPipelineExecution(agent, testResults);
        
        // Test Suite 5: Settings and Configuration
        console.log('⚙️ Testing Settings and Configuration...');
        await testSettingsConfiguration(agent, testResults);
        
        // Generate comprehensive report
        generateTestReport(testResults);
        
        await agent.close();
        console.log('🎉 Complete UI testing finished!');
        
    } catch (error) {
        console.error('❌ UI testing failed:', error);
        await agent.close();
        process.exit(1);
    }
}

async function testAuthenticationFlow(agent, results) {
    const tests = [
        {
            name: 'Login Page Load',
            action: async () => {
                await agent.navigate('http://localhost:3000/login');
                return await agent.waitForSelector('form[data-testid="login-form"]');
            }
        },
        {
            name: 'Login Form Validation',
            action: async () => {
                await agent.fill('input[name="email"]', 'test@example.com');
                await agent.fill('input[name="password"]', 'password123');
                await agent.click('button[type="submit"]');
                return await agent.waitForSelector('.dashboard');
            }
        },
        {
            name: 'Session Management',
            action: async () => {
                await agent.reload();
                return await agent.waitForSelector('.dashboard');
            }
        },
        {
            name: 'Logout Process',
            action: async () => {
                await agent.click('button[data-testid="logout"]');
                return await agent.waitForSelector('form[data-testid="login-form"]');
            }
        }
    ];
    
    for (const test of tests) {
        try {
            await test.action();
            results.push({ category: 'Authentication', test: test.name, status: 'PASS' });
            console.log(`  ✅ ${test.name}`);
        } catch (error) {
            results.push({ category: 'Authentication', test: test.name, status: 'FAIL', error: error.message });
            console.log(`  ❌ ${test.name}: ${error.message}`);
        }
    }
}

async function testDashboardComponents(agent, results) {
    const tests = [
        {
            name: 'Dashboard Header',
            action: async () => {
                return await agent.waitForSelector('header[data-testid="dashboard-header"]');
            }
        },
        {
            name: 'Navigation Menu',
            action: async () => {
                await agent.click('button[data-testid="nav-toggle"]');
                return await agent.waitForSelector('nav[data-testid="main-navigation"]');
            }
        },
        {
            name: 'Project Selector',
            action: async () => {
                await agent.click('select[data-testid="project-selector"]');
                return await agent.waitForSelector('option[value="test-project"]');
            }
        },
        {
            name: 'Service Status Cards',
            action: async () => {
                return await agent.waitForSelector('.service-status-card');
            }
        },
        {
            name: 'Recent Activity Feed',
            action: async () => {
                return await agent.waitForSelector('.activity-feed');
            }
        }
    ];
    
    for (const test of tests) {
        try {
            await test.action();
            results.push({ category: 'Dashboard', test: test.name, status: 'PASS' });
            console.log(`  ✅ ${test.name}`);
        } catch (error) {
            results.push({ category: 'Dashboard', test: test.name, status: 'FAIL', error: error.message });
            console.log(`  ❌ ${test.name}: ${error.message}`);
        }
    }
}

async function testServiceIntegration(agent, results) {
    const services = ['grainchain', 'graph-sitter', 'web-eval', 'codegen-sdk'];
    
    for (const service of services) {
        const tests = [
            {
                name: `${service} Service Page Load`,
                action: async () => {
                    await agent.navigate(`http://localhost:3000/services/${service}`);
                    return await agent.waitForSelector(`[data-testid="${service}-service"]`);
                }
            },
            {
                name: `${service} Configuration Form`,
                action: async () => {
                    await agent.click(`button[data-testid="${service}-configure"]`);
                    return await agent.waitForSelector(`form[data-testid="${service}-config-form"]`);
                }
            },
            {
                name: `${service} Test Execution`,
                action: async () => {
                    await agent.click(`button[data-testid="${service}-test"]`);
                    return await agent.waitForSelector(`[data-testid="${service}-test-results"]`);
                }
            }
        ];
        
        for (const test of tests) {
            try {
                await test.action();
                results.push({ category: 'Service Integration', test: test.name, status: 'PASS' });
                console.log(`  ✅ ${test.name}`);
            } catch (error) {
                results.push({ category: 'Service Integration', test: test.name, status: 'FAIL', error: error.message });
                console.log(`  ❌ ${test.name}: ${error.message}`);
            }
        }
    }
}

async function testPipelineExecution(agent, results) {
    const tests = [
        {
            name: 'Pipeline Configuration',
            action: async () => {
                await agent.navigate('http://localhost:3000/pipeline');
                await agent.click('button[data-testid="new-pipeline"]');
                return await agent.waitForSelector('form[data-testid="pipeline-config"]');
            }
        },
        {
            name: 'Pipeline Stage Configuration',
            action: async () => {
                await agent.fill('input[name="pipeline-name"]', 'Test Pipeline');
                await agent.check('input[name="enable-code-analysis"]');
                await agent.check('input[name="enable-ui-testing"]');
                return await agent.click('button[data-testid="save-pipeline"]');
            }
        },
        {
            name: 'Pipeline Execution',
            action: async () => {
                await agent.click('button[data-testid="execute-pipeline"]');
                return await agent.waitForSelector('[data-testid="pipeline-progress"]');
            }
        },
        {
            name: 'Pipeline Results',
            action: async () => {
                await agent.waitForSelector('[data-testid="pipeline-completed"]', { timeout: 60000 });
                return await agent.waitForSelector('[data-testid="pipeline-results"]');
            }
        }
    ];
    
    for (const test of tests) {
        try {
            await test.action();
            results.push({ category: 'Pipeline Execution', test: test.name, status: 'PASS' });
            console.log(`  ✅ ${test.name}`);
        } catch (error) {
            results.push({ category: 'Pipeline Execution', test: test.name, status: 'FAIL', error: error.message });
            console.log(`  ❌ ${test.name}: ${error.message}`);
        }
    }
}

async function testSettingsConfiguration(agent, results) {
    const tests = [
        {
            name: 'Settings Page Access',
            action: async () => {
                await agent.navigate('http://localhost:3000/settings');
                return await agent.waitForSelector('[data-testid="settings-page"]');
            }
        },
        {
            name: 'API Key Configuration',
            action: async () => {
                await agent.fill('input[name="gemini-api-key"]', 'test-api-key');
                await agent.fill('input[name="github-token"]', 'test-github-token');
                return await agent.click('button[data-testid="save-api-keys"]');
            }
        },
        {
            name: 'Service Settings',
            action: async () => {
                await agent.click('tab[data-testid="service-settings"]');
                await agent.select('select[name="default-sandbox"]', 'local');
                return await agent.click('button[data-testid="save-service-settings"]');
            }
        },
        {
            name: 'User Preferences',
            action: async () => {
                await agent.click('tab[data-testid="user-preferences"]');
                await agent.check('input[name="dark-mode"]');
                return await agent.click('button[data-testid="save-preferences"]');
            }
        }
    ];
    
    for (const test of tests) {
        try {
            await test.action();
            results.push({ category: 'Settings', test: test.name, status: 'PASS' });
            console.log(`  ✅ ${test.name}`);
        } catch (error) {
            results.push({ category: 'Settings', test: test.name, status: 'FAIL', error: error.message });
            console.log(`  ❌ ${test.name}: ${error.message}`);
        }
    }
}

function generateTestReport(results) {
    console.log('\n📊 Test Results Summary:');
    console.log('========================');
    
    const categories = [...new Set(results.map(r => r.category))];
    
    categories.forEach(category => {
        const categoryResults = results.filter(r => r.category === category);
        const passed = categoryResults.filter(r => r.status === 'PASS').length;
        const failed = categoryResults.filter(r => r.status === 'FAIL').length;
        
        console.log(`\n${category}:`);
        console.log(`  ✅ Passed: ${passed}`);
        console.log(`  ❌ Failed: ${failed}`);
        console.log(`  📊 Success Rate: ${((passed / categoryResults.length) * 100).toFixed(1)}%`);
        
        // Show failed tests
        const failedTests = categoryResults.filter(r => r.status === 'FAIL');
        if (failedTests.length > 0) {
            console.log('  Failed Tests:');
            failedTests.forEach(test => {
                console.log(`    - ${test.test}: ${test.error}`);
            });
        }
    });
    
    const totalPassed = results.filter(r => r.status === 'PASS').length;
    const totalFailed = results.filter(r => r.status === 'FAIL').length;
    const overallSuccessRate = ((totalPassed / results.length) * 100).toFixed(1);
    
    console.log('\n🎯 Overall Results:');
    console.log(`  Total Tests: ${results.length}`);
    console.log(`  ✅ Passed: ${totalPassed}`);
    console.log(`  ❌ Failed: ${totalFailed}`);
    console.log(`  📊 Overall Success Rate: ${overallSuccessRate}%`);
    
    // Save detailed report
    const reportData = {
        timestamp: new Date().toISOString(),
        summary: {
            total: results.length,
            passed: totalPassed,
            failed: totalFailed,
            successRate: overallSuccessRate
        },
        categories: categories.map(cat => {
            const catResults = results.filter(r => r.category === cat);
            return {
                name: cat,
                total: catResults.length,
                passed: catResults.filter(r => r.status === 'PASS').length,
                failed: catResults.filter(r => r.status === 'FAIL').length,
                tests: catResults
            };
        }),
        detailedResults: results
    };
    
    require('fs').writeFileSync('test-report.json', JSON.stringify(reportData, null, 2));
    console.log('\n📄 Detailed report saved to: test-report.json');
}

testCompleteUI();
```

### Script 3: API Integration Testing
```javascript
// test-api-integration.js
const { WebEvalAgent } = require('./src/web-eval-agent');

async function testAPIIntegration() {
    console.log('🔗 Testing API Integration through UI...');
    
    const agent = new WebEvalAgent({
        geminiApiKey: process.env.GEMINI_API_KEY,
        headless: false
    });
    
    try {
        await agent.initialize();
        await agent.navigate('http://localhost:3000');
        
        // Test all API endpoints through UI interactions
        await testGrainchainAPI(agent);
        await testGraphSitterAPI(agent);
        await testWebEvalAPI(agent);
        await testCodegenSDKAPI(agent);
        await testIntegratedPipelineAPI(agent);
        
        await agent.close();
        console.log('🎉 API integration testing completed!');
        
    } catch (error) {
        console.error('❌ API integration testing failed:', error);
        await agent.close();
        process.exit(1);
    }
}

async function testGrainchainAPI(agent) {
    console.log('🏗️ Testing Grainchain API...');
    
    // Navigate to Grainchain service
    await agent.navigate('http://localhost:3000/services/grainchain');
    
    // Test sandbox execution
    await agent.fill('textarea[name="code"]', 'print("Hello from Grainchain!")');
    await agent.select('select[name="provider"]', 'local');
    await agent.click('button[data-testid="execute-code"]');
    
    // Wait for results
    await agent.waitForSelector('[data-testid="execution-results"]');
    console.log('  ✅ Grainchain execution test passed');
    
    // Test different providers
    const providers = ['e2b', 'daytona', 'morph'];
    for (const provider of providers) {
        try {
            await agent.select('select[name="provider"]', provider);
            await agent.click('button[data-testid="test-connection"]');
            await agent.waitForSelector(`[data-testid="${provider}-status"]`);
            console.log(`  ✅ ${provider} provider test passed`);
        } catch (error) {
            console.log(`  ⚠️ ${provider} provider test skipped: ${error.message}`);
        }
    }
}

async function testGraphSitterAPI(agent) {
    console.log('🧠 Testing Graph-sitter API...');
    
    await agent.navigate('http://localhost:3000/services/graph-sitter');
    
    // Test code analysis
    await agent.fill('textarea[name="source-code"]', `
        function calculateSum(a, b) {
            return a + b;
        }
        
        const result = calculateSum(5, 3);
        console.log(result);
    `);
    
    await agent.select('select[name="language"]', 'javascript');
    await agent.click('button[data-testid="analyze-code"]');
    
    await agent.waitForSelector('[data-testid="analysis-results"]');
    console.log('  ✅ Code analysis test passed');
    
    // Test quality metrics
    await agent.click('tab[data-testid="quality-metrics"]');
    await agent.waitForSelector('[data-testid="quality-score"]');
    console.log('  ✅ Quality metrics test passed');
}

async function testWebEvalAPI(agent) {
    console.log('🌐 Testing Web-eval API...');
    
    await agent.navigate('http://localhost:3000/services/web-eval');
    
    // Test UI testing configuration
    await agent.fill('input[name="target-url"]', 'http://localhost:3000');
    await agent.check('input[name="test-accessibility"]');
    await agent.check('input[name="test-performance"]');
    await agent.click('button[data-testid="start-ui-test"]');
    
    await agent.waitForSelector('[data-testid="ui-test-results"]');
    console.log('  ✅ UI testing test passed');
    
    // Test accessibility validation
    await agent.click('tab[data-testid="accessibility-results"]');
    await agent.waitForSelector('[data-testid="accessibility-score"]');
    console.log('  ✅ Accessibility validation test passed');
}

async function testCodegenSDKAPI(agent) {
    console.log('🤖 Testing Codegen SDK API...');
    
    await agent.navigate('http://localhost:3000/services/codegen-sdk');
    
    // Test agent configuration
    await agent.fill('input[name="agent-name"]', 'Test Agent');
    await agent.fill('textarea[name="agent-description"]', 'Test agent for validation');
    await agent.click('button[data-testid="create-agent"]');
    
    await agent.waitForSelector('[data-testid="agent-created"]');
    console.log('  ✅ Agent creation test passed');
    
    // Test task execution
    await agent.fill('textarea[name="task-description"]', 'Analyze the provided code');
    await agent.click('button[data-testid="execute-task"]');
    
    await agent.waitForSelector('[data-testid="task-results"]');
    console.log('  ✅ Task execution test passed');
}

async function testIntegratedPipelineAPI(agent) {
    console.log('⚙️ Testing Integrated Pipeline API...');
    
    await agent.navigate('http://localhost:3000/pipeline');
    
    // Create and execute complete pipeline
    await agent.click('button[data-testid="new-pipeline"]');
    await agent.fill('input[name="pipeline-name"]', 'Complete Test Pipeline');
    
    // Enable all services
    await agent.check('input[name="enable-grainchain"]');
    await agent.check('input[name="enable-graph-sitter"]');
    await agent.check('input[name="enable-web-eval"]');
    await agent.check('input[name="enable-codegen-sdk"]');
    
    await agent.click('button[data-testid="save-pipeline"]');
    await agent.click('button[data-testid="execute-pipeline"]');
    
    // Monitor pipeline execution
    await agent.waitForSelector('[data-testid="pipeline-stage-1"]');
    console.log('  ✅ Pipeline stage 1 (Initialization) passed');
    
    await agent.waitForSelector('[data-testid="pipeline-stage-2"]');
    console.log('  ✅ Pipeline stage 2 (Code Analysis) passed');
    
    await agent.waitForSelector('[data-testid="pipeline-stage-3"]');
    console.log('  ✅ Pipeline stage 3 (Sandbox Execution) passed');
    
    await agent.waitForSelector('[data-testid="pipeline-stage-4"]');
    console.log('  ✅ Pipeline stage 4 (UI Testing) passed');
    
    await agent.waitForSelector('[data-testid="pipeline-stage-5"]');
    console.log('  ✅ Pipeline stage 5 (Results Integration) passed');
    
    await agent.waitForSelector('[data-testid="pipeline-completed"]');
    console.log('  ✅ Pipeline completion test passed');
}

testAPIIntegration();
```

## 🎯 Execution Instructions

### Step 1: Environment Setup
```bash
# Terminal 1: Setup CodegenCICD
cd CodegenCICD
npm install
npm run setup
npm run dev

# Terminal 2: Setup Web-eval-agent
git clone https://github.com/Zeeeepa/web-eval-agent.git
cd web-eval-agent
export GEMINI_API_KEY="AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0"
npm install
```

### Step 2: Run Complete Test Suite
```bash
# In web-eval-agent directory
node test-basic-functionality.js
node test-codegen-ui-complete.js
node test-api-integration.js
```

### Step 3: Validate Results
```bash
# Check test reports
cat test-report.json

# Verify all services are healthy
curl http://localhost:8000/api/health

# Check frontend accessibility
curl http://localhost:3000
```

## 📊 Expected Results

### Success Criteria
- ✅ All UI components load and function correctly
- ✅ All API endpoints respond within acceptable time limits
- ✅ All service integrations work seamlessly
- ✅ Complete pipeline executes without errors
- ✅ Accessibility standards are met (WCAG 2.1 AA)
- ✅ Performance metrics are within acceptable ranges
- ✅ Error handling works correctly
- ✅ User interactions are smooth and responsive

### Performance Benchmarks
- Page load time: < 3 seconds
- API response time: < 2 seconds
- Pipeline execution: < 60 seconds
- UI interaction response: < 500ms
- Accessibility score: > 90%
- Performance score: > 80%

## 🚨 Troubleshooting

### Common Issues
1. **Service not responding**: Check if all services are running with `npm run health`
2. **API key errors**: Verify GEMINI_API_KEY is set correctly
3. **Browser automation fails**: Ensure Chrome/Chromium is installed
4. **Timeout errors**: Increase timeout values in test scripts
5. **Network issues**: Check firewall and proxy settings

### Debug Commands
```bash
# Check service status
npm run validate:services

# Test individual components
npm run test:grainchain
npm run test:graph-sitter
npm run test:web-eval
npm run test:codegen-sdk

# View detailed logs
npm run logs:backend
npm run logs:frontend
```

## 🎉 Completion Checklist

- [ ] All test scripts execute successfully
- [ ] Test report shows 100% success rate
- [ ] All UI interactions validated
- [ ] All API endpoints tested
- [ ] Complete pipeline execution verified
- [ ] Performance benchmarks met
- [ ] Accessibility standards achieved
- [ ] Error handling validated
- [ ] Documentation updated
- [ ] Results documented and shared

**🎯 Goal Achieved: Complete CICD flow validation with web-eval-agent ensuring all features and functions are properly tested and validated!**

