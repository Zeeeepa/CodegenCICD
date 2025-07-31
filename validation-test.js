#!/usr/bin/env node

const { chromium } = require('playwright');

/**
 * CodegenCICD Web-Eval-Agent Validation Test
 * This test validates that the web-eval-agent infrastructure is working correctly
 */

class ValidationTester {
    constructor() {
        this.browser = null;
        this.page = null;
        this.results = {
            passed: 0,
            failed: 0,
            tests: []
        };
    }

    async initialize() {
        console.log('🚀 Initializing Web-Eval-Agent Validation...');
        
        try {
            this.browser = await chromium.launch({
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            });
            
            this.page = await this.browser.newPage();
            await this.page.setViewportSize({ width: 1280, height: 720 });
            
            console.log('✅ Browser initialized successfully');
            return true;
        } catch (error) {
            console.error('❌ Browser initialization failed:', error.message);
            return false;
        }
    }

    async runTest(name, testFn) {
        console.log(`\n🧪 Running: ${name}`);
        const startTime = Date.now();
        
        try {
            await testFn();
            const duration = Date.now() - startTime;
            console.log(`✅ ${name} - PASSED (${duration}ms)`);
            this.results.passed++;
            this.results.tests.push({ name, status: 'PASSED', duration });
        } catch (error) {
            const duration = Date.now() - startTime;
            console.log(`❌ ${name} - FAILED (${duration}ms)`);
            console.log(`   Error: ${error.message}`);
            this.results.failed++;
            this.results.tests.push({ name, status: 'FAILED', duration, error: error.message });
        }
    }

    async testBrowserNavigation() {
        // Test basic browser navigation
        await this.page.goto('https://httpbin.org/json');
        const content = await this.page.textContent('body');
        
        if (!content.includes('slideshow')) {
            throw new Error('Expected content not found');
        }
        
        console.log('   ✓ Navigation successful');
        console.log('   ✓ Content validation passed');
    }

    async testJavaScriptExecution() {
        // Test JavaScript execution
        await this.page.goto('data:text/html,<html><body><div id="test">Hello</div></body></html>');
        
        const result = await this.page.evaluate(() => {
            const div = document.getElementById('test');
            div.textContent = 'Modified by JS';
            return div.textContent;
        });
        
        if (result !== 'Modified by JS') {
            throw new Error('JavaScript execution failed');
        }
        
        console.log('   ✓ JavaScript execution successful');
    }

    async testElementInteraction() {
        // Test element interaction
        await this.page.goto('data:text/html,<html><body><button id="btn">Click me</button><div id="result"></div></body></html>');
        
        await this.page.evaluate(() => {
            document.getElementById('btn').onclick = () => {
                document.getElementById('result').textContent = 'Clicked!';
            };
        });
        
        await this.page.click('#btn');
        const result = await this.page.textContent('#result');
        
        if (result !== 'Clicked!') {
            throw new Error('Element interaction failed');
        }
        
        console.log('   ✓ Element interaction successful');
    }

    async testScreenshotCapture() {
        // Test screenshot capability
        await this.page.goto('data:text/html,<html><body><h1 style="color: blue;">Screenshot Test</h1></body></html>');
        
        const screenshot = await this.page.screenshot({ 
            path: '/tmp/validation-test.png',
            fullPage: true 
        });
        
        if (!screenshot || screenshot.length === 0) {
            throw new Error('Screenshot capture failed');
        }
        
        console.log('   ✓ Screenshot captured successfully');
    }

    async testFormHandling() {
        // Test form handling
        const html = `
            <html>
                <body>
                    <form id="testForm">
                        <input type="text" id="name" name="name" />
                        <input type="email" id="email" name="email" />
                        <button type="submit">Submit</button>
                    </form>
                    <div id="output"></div>
                    <script>
                        document.getElementById('testForm').onsubmit = (e) => {
                            e.preventDefault();
                            const name = document.getElementById('name').value;
                            const email = document.getElementById('email').value;
                            document.getElementById('output').textContent = name + ':' + email;
                        };
                    </script>
                </body>
            </html>
        `;
        
        await this.page.goto(`data:text/html,${encodeURIComponent(html)}`);
        
        await this.page.fill('#name', 'Test User');
        await this.page.fill('#email', 'test@example.com');
        await this.page.click('button[type="submit"]');
        
        const output = await this.page.textContent('#output');
        
        if (output !== 'Test User:test@example.com') {
            throw new Error('Form handling failed');
        }
        
        console.log('   ✓ Form handling successful');
    }

    async testWaitForElements() {
        // Test waiting for dynamic elements
        const html = `
            <html>
                <body>
                    <div id="container"></div>
                    <script>
                        setTimeout(() => {
                            const div = document.createElement('div');
                            div.id = 'dynamic';
                            div.textContent = 'Dynamic Content';
                            document.getElementById('container').appendChild(div);
                        }, 1000);
                    </script>
                </body>
            </html>
        `;
        
        await this.page.goto(`data:text/html,${encodeURIComponent(html)}`);
        
        // Wait for dynamic element
        await this.page.waitForSelector('#dynamic', { timeout: 5000 });
        const content = await this.page.textContent('#dynamic');
        
        if (content !== 'Dynamic Content') {
            throw new Error('Dynamic element waiting failed');
        }
        
        console.log('   ✓ Dynamic element waiting successful');
    }

    async testNetworkRequests() {
        // Test network request interception
        let requestCaptured = false;
        
        this.page.on('request', (request) => {
            if (request.url().includes('httpbin.org')) {
                requestCaptured = true;
            }
        });
        
        await this.page.goto('https://httpbin.org/get');
        
        if (!requestCaptured) {
            throw new Error('Network request interception failed');
        }
        
        console.log('   ✓ Network request interception successful');
    }

    async testEnvironmentVariables() {
        // Test environment variable access
        const requiredVars = [
            'GEMINI_API_KEY',
            'CODEGEN_API_TOKEN',
            'GITHUB_TOKEN',
            'CLOUDFLARE_API_KEY'
        ];
        
        const missingVars = [];
        
        for (const varName of requiredVars) {
            if (!process.env[varName]) {
                missingVars.push(varName);
            }
        }
        
        if (missingVars.length > 0) {
            throw new Error(`Missing environment variables: ${missingVars.join(', ')}`);
        }
        
        console.log('   ✓ All required environment variables present');
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
            console.log('✅ Browser closed successfully');
        }
    }

    async run() {
        console.log('🔧 CodegenCICD Web-Eval-Agent Infrastructure Validation');
        console.log('=' * 60);
        
        // Initialize browser
        const initialized = await this.initialize();
        if (!initialized) {
            console.log('\n❌ VALIDATION FAILED - Browser initialization failed');
            return false;
        }
        
        // Run all tests
        await this.runTest('Environment Variables Test', () => this.testEnvironmentVariables());
        await this.runTest('Browser Navigation Test', () => this.testBrowserNavigation());
        await this.runTest('JavaScript Execution Test', () => this.testJavaScriptExecution());
        await this.runTest('Element Interaction Test', () => this.testElementInteraction());
        await this.runTest('Screenshot Capture Test', () => this.testScreenshotCapture());
        await this.runTest('Form Handling Test', () => this.testFormHandling());
        await this.runTest('Dynamic Element Waiting Test', () => this.testWaitForElements());
        await this.runTest('Network Request Interception Test', () => this.testNetworkRequests());
        
        // Cleanup
        await this.cleanup();
        
        // Results summary
        console.log('\n📊 VALIDATION RESULTS');
        console.log('=' * 40);
        console.log(`✅ Tests Passed: ${this.results.passed}`);
        console.log(`❌ Tests Failed: ${this.results.failed}`);
        console.log(`📈 Success Rate: ${Math.round((this.results.passed / (this.results.passed + this.results.failed)) * 100)}%`);
        
        if (this.results.failed === 0) {
            console.log('\n🎉 ALL TESTS PASSED!');
            console.log('✅ Web-Eval-Agent infrastructure is fully operational');
            console.log('✅ Browser automation capabilities verified');
            console.log('✅ Environment configuration validated');
            console.log('✅ Ready for CICD flow testing');
            return true;
        } else {
            console.log('\n⚠️ SOME TESTS FAILED');
            console.log('❌ Please review failed tests above');
            return false;
        }
    }
}

// Run the validation if this script is executed directly
if (require.main === module) {
    const tester = new ValidationTester();
    tester.run()
        .then(success => {
            process.exit(success ? 0 : 1);
        })
        .catch(error => {
            console.error('💥 Validation failed with error:', error);
            process.exit(1);
        });
}

module.exports = ValidationTester;
