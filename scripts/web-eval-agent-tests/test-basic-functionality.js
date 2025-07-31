#!/usr/bin/env node

/**
 * Web-eval-agent Basic Functionality Test
 * Tests core web-eval-agent functionality with CodegenCICD platform
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
    GEMINI_API_KEY: process.env.GEMINI_API_KEY || "AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0",
    PLATFORM_URL: process.env.PLATFORM_URL || "http://localhost:3000",
    API_URL: process.env.API_URL || "http://localhost:8000",
    HEADLESS: process.env.HEADLESS === 'true',
    TIMEOUT: parseInt(process.env.TIMEOUT) || 30000
};

class WebEvalAgentTester {
    constructor() {
        this.results = [];
        this.startTime = Date.now();
    }

    async log(message, type = 'info') {
        const timestamp = new Date().toISOString();
        const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
        console.log(`${prefix} [${timestamp}] ${message}`);
    }

    async runTest(testName, testFunction) {
        this.log(`Starting test: ${testName}`);
        const testStart = Date.now();
        
        try {
            await testFunction();
            const duration = Date.now() - testStart;
            this.results.push({
                name: testName,
                status: 'PASS',
                duration: duration,
                timestamp: new Date().toISOString()
            });
            this.log(`Test passed: ${testName} (${duration}ms)`, 'success');
        } catch (error) {
            const duration = Date.now() - testStart;
            this.results.push({
                name: testName,
                status: 'FAIL',
                duration: duration,
                error: error.message,
                timestamp: new Date().toISOString()
            });
            this.log(`Test failed: ${testName} - ${error.message}`, 'error');
        }
    }

    async checkPrerequisites() {
        this.log('Checking prerequisites...');
        
        // Check if GEMINI_API_KEY is set
        if (!CONFIG.GEMINI_API_KEY) {
            throw new Error('GEMINI_API_KEY environment variable is not set');
        }
        
        // Check if web-eval-agent is available
        if (!fs.existsSync('./web-eval-agent') && !fs.existsSync('../web-eval-agent')) {
            throw new Error('web-eval-agent directory not found. Please clone it first.');
        }
        
        // Check if CodegenCICD platform is running
        try {
            const response = await fetch(CONFIG.PLATFORM_URL);
            if (!response.ok) {
                throw new Error(`Platform not accessible at ${CONFIG.PLATFORM_URL}`);
            }
        } catch (error) {
            throw new Error(`Platform not running at ${CONFIG.PLATFORM_URL}: ${error.message}`);
        }
        
        // Check if API is running
        try {
            const response = await fetch(`${CONFIG.API_URL}/api/health`);
            if (!response.ok) {
                throw new Error(`API not accessible at ${CONFIG.API_URL}`);
            }
        } catch (error) {
            throw new Error(`API not running at ${CONFIG.API_URL}: ${error.message}`);
        }
        
        this.log('All prerequisites met', 'success');
    }

    async testWebEvalAgentInstallation() {
        // Test if web-eval-agent can be imported and initialized
        const webEvalPath = fs.existsSync('./web-eval-agent') ? './web-eval-agent' : '../web-eval-agent';
        
        return new Promise((resolve, reject) => {
            const testScript = `
                const path = require('path');
                process.chdir('${webEvalPath}');
                
                try {
                    // Try to require the main module
                    const webEval = require('./src/index.js');
                    console.log('✅ Web-eval-agent module loaded successfully');
                    process.exit(0);
                } catch (error) {
                    console.error('❌ Failed to load web-eval-agent:', error.message);
                    process.exit(1);
                }
            `;
            
            const child = spawn('node', ['-e', testScript], {
                stdio: 'pipe',
                env: { ...process.env, GEMINI_API_KEY: CONFIG.GEMINI_API_KEY }
            });
            
            let output = '';
            child.stdout.on('data', (data) => {
                output += data.toString();
            });
            
            child.stderr.on('data', (data) => {
                output += data.toString();
            });
            
            child.on('close', (code) => {
                if (code === 0) {
                    this.log('Web-eval-agent installation verified');
                    resolve();
                } else {
                    reject(new Error(`Web-eval-agent test failed: ${output}`));
                }
            });
            
            setTimeout(() => {
                child.kill();
                reject(new Error('Web-eval-agent test timed out'));
            }, CONFIG.TIMEOUT);
        });
    }

    async testBasicBrowserAutomation() {
        const webEvalPath = fs.existsSync('./web-eval-agent') ? './web-eval-agent' : '../web-eval-agent';
        
        return new Promise((resolve, reject) => {
            const testScript = `
                const path = require('path');
                process.chdir('${webEvalPath}');
                
                async function testBrowser() {
                    try {
                        const { WebEvalAgent } = require('./src/index.js');
                        
                        const agent = new WebEvalAgent({
                            geminiApiKey: '${CONFIG.GEMINI_API_KEY}',
                            headless: ${CONFIG.HEADLESS},
                            timeout: ${CONFIG.TIMEOUT}
                        });
                        
                        console.log('🚀 Initializing browser...');
                        await agent.initialize();
                        
                        console.log('🌐 Navigating to platform...');
                        await agent.navigate('${CONFIG.PLATFORM_URL}');
                        
                        console.log('📸 Taking screenshot...');
                        await agent.screenshot('test-screenshot.png');
                        
                        console.log('🔍 Checking page title...');
                        const title = await agent.getTitle();
                        console.log('Page title:', title);
                        
                        console.log('🧹 Closing browser...');
                        await agent.close();
                        
                        console.log('✅ Basic browser automation test completed successfully');
                        process.exit(0);
                        
                    } catch (error) {
                        console.error('❌ Browser automation test failed:', error.message);
                        process.exit(1);
                    }
                }
                
                testBrowser();
            `;
            
            const child = spawn('node', ['-e', testScript], {
                stdio: 'pipe',
                env: { ...process.env, GEMINI_API_KEY: CONFIG.GEMINI_API_KEY }
            });
            
            let output = '';
            child.stdout.on('data', (data) => {
                const text = data.toString();
                output += text;
                console.log(text.trim());
            });
            
            child.stderr.on('data', (data) => {
                const text = data.toString();
                output += text;
                console.error(text.trim());
            });
            
            child.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`Browser automation test failed with code ${code}: ${output}`));
                }
            });
            
            setTimeout(() => {
                child.kill();
                reject(new Error('Browser automation test timed out'));
            }, CONFIG.TIMEOUT * 2);
        });
    }

    async testPlatformInteraction() {
        const webEvalPath = fs.existsSync('./web-eval-agent') ? './web-eval-agent' : '../web-eval-agent';
        
        return new Promise((resolve, reject) => {
            const testScript = `
                const path = require('path');
                process.chdir('${webEvalPath}');
                
                async function testInteraction() {
                    try {
                        const { WebEvalAgent } = require('./src/index.js');
                        
                        const agent = new WebEvalAgent({
                            geminiApiKey: '${CONFIG.GEMINI_API_KEY}',
                            headless: ${CONFIG.HEADLESS},
                            timeout: ${CONFIG.TIMEOUT}
                        });
                        
                        await agent.initialize();
                        await agent.navigate('${CONFIG.PLATFORM_URL}');
                        
                        // Test basic interactions
                        console.log('🔍 Looking for interactive elements...');
                        
                        // Try to find and interact with common elements
                        const elements = await agent.findElements('button, a, input');
                        console.log(\`Found \${elements.length} interactive elements\`);
                        
                        // Test clicking on the first button if available
                        const buttons = await agent.findElements('button');
                        if (buttons.length > 0) {
                            console.log('🖱️ Testing button interaction...');
                            await agent.click(buttons[0]);
                            console.log('✅ Button interaction successful');
                        }
                        
                        // Test form interaction if available
                        const inputs = await agent.findElements('input[type="text"], input[type="email"]');
                        if (inputs.length > 0) {
                            console.log('⌨️ Testing form interaction...');
                            await agent.fill(inputs[0], 'test@example.com');
                            console.log('✅ Form interaction successful');
                        }
                        
                        await agent.close();
                        console.log('✅ Platform interaction test completed successfully');
                        process.exit(0);
                        
                    } catch (error) {
                        console.error('❌ Platform interaction test failed:', error.message);
                        process.exit(1);
                    }
                }
                
                testInteraction();
            `;
            
            const child = spawn('node', ['-e', testScript], {
                stdio: 'pipe',
                env: { ...process.env, GEMINI_API_KEY: CONFIG.GEMINI_API_KEY }
            });
            
            let output = '';
            child.stdout.on('data', (data) => {
                const text = data.toString();
                output += text;
                console.log(text.trim());
            });
            
            child.stderr.on('data', (data) => {
                const text = data.toString();
                output += text;
                console.error(text.trim());
            });
            
            child.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`Platform interaction test failed with code ${code}: ${output}`));
                }
            });
            
            setTimeout(() => {
                child.kill();
                reject(new Error('Platform interaction test timed out'));
            }, CONFIG.TIMEOUT * 2);
        });
    }

    async testAPIValidation() {
        // Test API endpoints through web-eval-agent
        const endpoints = [
            '/api/health',
            '/api/integrated/services/status',
            '/api/integrated/grainchain/health',
            '/api/integrated/graph-sitter/health',
            '/api/integrated/web-eval/health',
            '/api/integrated/codegen-sdk/health'
        ];
        
        for (const endpoint of endpoints) {
            try {
                const response = await fetch(`${CONFIG.API_URL}${endpoint}`);
                if (!response.ok) {
                    throw new Error(`API endpoint ${endpoint} returned ${response.status}`);
                }
                this.log(`API endpoint ${endpoint} is healthy`);
            } catch (error) {
                throw new Error(`API endpoint ${endpoint} failed: ${error.message}`);
            }
        }
    }

    async generateReport() {
        const totalTests = this.results.length;
        const passedTests = this.results.filter(r => r.status === 'PASS').length;
        const failedTests = this.results.filter(r => r.status === 'FAIL').length;
        const successRate = ((passedTests / totalTests) * 100).toFixed(1);
        const totalDuration = Date.now() - this.startTime;
        
        const report = {
            summary: {
                total: totalTests,
                passed: passedTests,
                failed: failedTests,
                successRate: `${successRate}%`,
                totalDuration: `${totalDuration}ms`,
                timestamp: new Date().toISOString()
            },
            configuration: CONFIG,
            results: this.results
        };
        
        // Save report
        fs.writeFileSync('basic-functionality-test-report.json', JSON.stringify(report, null, 2));
        
        // Display summary
        console.log('\n📊 Basic Functionality Test Results:');
        console.log('=====================================');
        console.log(`Total Tests: ${totalTests}`);
        console.log(`✅ Passed: ${passedTests}`);
        console.log(`❌ Failed: ${failedTests}`);
        console.log(`📊 Success Rate: ${successRate}%`);
        console.log(`⏱️ Total Duration: ${totalDuration}ms`);
        
        if (failedTests > 0) {
            console.log('\n❌ Failed Tests:');
            this.results.filter(r => r.status === 'FAIL').forEach(test => {
                console.log(`  - ${test.name}: ${test.error}`);
            });
        }
        
        console.log(`\n📄 Detailed report saved to: basic-functionality-test-report.json`);
        
        return successRate === '100.0';
    }

    async run() {
        try {
            this.log('🚀 Starting Web-eval-agent Basic Functionality Tests...');
            
            await this.runTest('Prerequisites Check', () => this.checkPrerequisites());
            await this.runTest('Web-eval-agent Installation', () => this.testWebEvalAgentInstallation());
            await this.runTest('Basic Browser Automation', () => this.testBasicBrowserAutomation());
            await this.runTest('Platform Interaction', () => this.testPlatformInteraction());
            await this.runTest('API Validation', () => this.testAPIValidation());
            
            const allPassed = await this.generateReport();
            
            if (allPassed) {
                this.log('🎉 All basic functionality tests passed!', 'success');
                process.exit(0);
            } else {
                this.log('❌ Some tests failed. Check the report for details.', 'error');
                process.exit(1);
            }
            
        } catch (error) {
            this.log(`💥 Test suite failed: ${error.message}`, 'error');
            process.exit(1);
        }
    }
}

// Run the tests
if (require.main === module) {
    const tester = new WebEvalAgentTester();
    tester.run();
}

module.exports = WebEvalAgentTester;

