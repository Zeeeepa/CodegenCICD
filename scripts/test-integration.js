#!/usr/bin/env node

const { spawn } = require('child_process');
const chalk = require('chalk');
const ora = require('ora');
const path = require('path');

console.log(chalk.blue.bold('🧪 Integration Test Suite'));
console.log(chalk.gray('Running comprehensive tests for all integrated components\n'));

class IntegrationTestRunner {
    constructor() {
        this.testResults = [];
        this.startTime = Date.now();
    }

    async runCommand(command, args = [], options = {}) {
        return new Promise((resolve, reject) => {
            const process = spawn(command, args, {
                stdio: 'pipe',
                shell: true,
                ...options
            });
            
            let stdout = '';
            let stderr = '';
            
            process.stdout?.on('data', (data) => {
                stdout += data.toString();
            });
            
            process.stderr?.on('data', (data) => {
                stderr += data.toString();
            });
            
            process.on('close', (code) => {
                resolve({
                    code,
                    stdout,
                    stderr,
                    success: code === 0
                });
            });
            
            process.on('error', (error) => {
                reject(error);
            });
        });
    }

    async logTest(name, testFn) {
        const spinner = ora(`Running: ${name}`).start();
        const testStart = Date.now();
        
        try {
            const result = await testFn();
            const duration = Date.now() - testStart;
            
            this.testResults.push({
                name,
                status: result.success ? 'passed' : 'failed',
                duration,
                result
            });
            
            if (result.success) {
                spinner.succeed(`${name} (${duration}ms)`);
            } else {
                spinner.fail(`${name} (${duration}ms): ${result.error || 'Test failed'}`);
            }
            
            return result;
        } catch (error) {
            const duration = Date.now() - testStart;
            
            this.testResults.push({
                name,
                status: 'failed',
                duration,
                error: error.message
            });
            
            spinner.fail(`${name} (${duration}ms): ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    async testPythonBackendTests() {
        return await this.logTest('Python Backend Tests', async () => {
            const result = await this.runCommand('python', ['-m', 'pytest', 'tests/', '-v', '--tb=short'], {
                cwd: path.join(process.cwd(), 'backend')
            });
            
            return {
                success: result.code === 0,
                stdout: result.stdout,
                stderr: result.stderr,
                exit_code: result.code
            };
        });
    }

    async testFrontendTests() {
        return await this.logTest('Frontend Tests', async () => {
            const frontendDir = path.join(process.cwd(), 'frontend');
            
            // Check if frontend directory exists
            const fs = require('fs');
            if (!fs.existsSync(frontendDir)) {
                return {
                    success: true,
                    skipped: true,
                    message: 'Frontend directory not found - skipping frontend tests'
                };
            }
            
            // Check if package.json exists
            const packageJsonPath = path.join(frontendDir, 'package.json');
            if (!fs.existsSync(packageJsonPath)) {
                return {
                    success: true,
                    skipped: true,
                    message: 'Frontend package.json not found - skipping frontend tests'
                };
            }
            
            const result = await this.runCommand('npm', ['test', '--', '--watchAll=false'], {
                cwd: frontendDir
            });
            
            return {
                success: result.code === 0,
                stdout: result.stdout,
                stderr: result.stderr,
                exit_code: result.code
            };
        });
    }

    async testServiceValidation() {
        return await this.logTest('Service Validation', async () => {
            const result = await this.runCommand('node', ['scripts/validate-services.js']);
            
            return {
                success: result.code === 0,
                stdout: result.stdout,
                stderr: result.stderr,
                exit_code: result.code
            };
        });
    }

    async testIntegrationValidation() {
        return await this.logTest('Integration Validation', async () => {
            const result = await this.runCommand('node', ['scripts/validate-integration.js']);
            
            return {
                success: result.code === 0,
                stdout: result.stdout,
                stderr: result.stderr,
                exit_code: result.code
            };
        });
    }

    async testWebEvalFlow() {
        return await this.logTest('Web-eval-agent CICD Flow', async () => {
            const result = await this.runCommand('node', ['scripts/test-web-eval-flow.js']);
            
            return {
                success: result.code === 0,
                stdout: result.stdout,
                stderr: result.stderr,
                exit_code: result.code
            };
        });
    }

    async testAPIEndpoints() {
        return await this.logTest('API Endpoints Test', async () => {
            const axios = require('axios');
            const BACKEND_URL = 'http://localhost:8000';
            
            try {
                // Test health endpoint
                const healthResponse = await axios.get(`${BACKEND_URL}/api/health`, { timeout: 5000 });
                if (healthResponse.status !== 200) {
                    throw new Error(`Health endpoint failed: ${healthResponse.status}`);
                }
                
                // Test integrated health endpoint
                const integratedHealthResponse = await axios.get(`${BACKEND_URL}/api/integrated/health`, { timeout: 10000 });
                if (integratedHealthResponse.status !== 200) {
                    throw new Error(`Integrated health endpoint failed: ${integratedHealthResponse.status}`);
                }
                
                // Test a simple service endpoint
                const grainchainResponse = await axios.get(`${BACKEND_URL}/api/integrated/grainchain/providers`, { timeout: 5000 });
                if (grainchainResponse.status !== 200) {
                    throw new Error(`Grainchain providers endpoint failed: ${grainchainResponse.status}`);
                }
                
                return {
                    success: true,
                    endpoints_tested: 3,
                    health_status: healthResponse.data,
                    integrated_health: integratedHealthResponse.data
                };
                
            } catch (error) {
                if (error.code === 'ECONNREFUSED') {
                    return {
                        success: false,
                        error: 'Backend server is not running. Start with: npm run backend:dev'
                    };
                }
                return {
                    success: false,
                    error: error.message
                };
            }
        });
    }

    async testEnvironmentConfiguration() {
        return await this.logTest('Environment Configuration', async () => {
            require('dotenv').config();
            
            const requiredVars = [
                'CODEGEN_ORG_ID',
                'CODEGEN_API_TOKEN',
                'GEMINI_API_KEY',
                'GITHUB_TOKEN'
            ];
            
            const missingVars = [];
            const placeholderVars = [];
            
            for (const varName of requiredVars) {
                if (!process.env[varName]) {
                    missingVars.push(varName);
                } else if (process.env[varName].includes('your-') || process.env[varName].includes('change-')) {
                    placeholderVars.push(varName);
                }
            }
            
            const success = missingVars.length === 0 && placeholderVars.length === 0;
            
            return {
                success,
                missing_vars: missingVars,
                placeholder_vars: placeholderVars,
                total_required: requiredVars.length,
                configured_vars: requiredVars.length - missingVars.length - placeholderVars.length
            };
        });
    }

    async testDependencyInstallation() {
        return await this.logTest('Dependency Installation Check', async () => {
            const checks = [];
            
            // Check Python dependencies
            try {
                const pythonResult = await this.runCommand('python', ['-c', 'import fastapi, uvicorn, pydantic, sqlalchemy']);
                checks.push({ name: 'Python Core Dependencies', success: pythonResult.success });
            } catch (error) {
                checks.push({ name: 'Python Core Dependencies', success: false, error: error.message });
            }
            
            // Check Node.js dependencies
            try {
                require('axios');
                require('chalk');
                require('inquirer');
                require('ora');
                checks.push({ name: 'Node.js Dependencies', success: true });
            } catch (error) {
                checks.push({ name: 'Node.js Dependencies', success: false, error: error.message });
            }
            
            // Check integrated libraries (optional)
            const integratedLibs = [
                { name: 'grainchain', command: 'python -c "import grainchain"' },
                { name: 'graph-sitter', command: 'python -c "import graph_sitter"' },
                { name: 'codegen-api-client', command: 'python -c "import codegen_api_client"' }
            ];
            
            for (const lib of integratedLibs) {
                try {
                    const result = await this.runCommand('python', ['-c', lib.command.split(' ').slice(1).join(' ')]);
                    checks.push({ name: lib.name, success: result.success, optional: true });
                } catch (error) {
                    checks.push({ name: lib.name, success: false, optional: true, error: error.message });
                }
            }
            
            // Check web-eval-agent
            try {
                const webEvalResult = await this.runCommand('uvx', ['--help']);
                checks.push({ name: 'uvx (for web-eval-agent)', success: webEvalResult.success });
            } catch (error) {
                checks.push({ name: 'uvx (for web-eval-agent)', success: false, error: error.message });
            }
            
            const requiredChecks = checks.filter(c => !c.optional);
            const optionalChecks = checks.filter(c => c.optional);
            const requiredSuccess = requiredChecks.filter(c => c.success).length;
            const optionalSuccess = optionalChecks.filter(c => c.success).length;
            
            return {
                success: requiredSuccess === requiredChecks.length,
                required_dependencies: {
                    total: requiredChecks.length,
                    successful: requiredSuccess,
                    checks: requiredChecks
                },
                optional_dependencies: {
                    total: optionalChecks.length,
                    successful: optionalSuccess,
                    checks: optionalChecks
                }
            };
        });
    }

    generateTestReport() {
        const totalDuration = Date.now() - this.startTime;
        const passedTests = this.testResults.filter(t => t.status === 'passed').length;
        const failedTests = this.testResults.filter(t => t.status === 'failed').length;
        const totalTests = this.testResults.length;
        
        console.log(chalk.blue.bold('\n📊 Integration Test Report'));
        console.log(chalk.gray('=' .repeat(60)));
        
        // Summary
        console.log(chalk.blue(`📈 Test Summary:`));
        console.log(chalk.gray(`   Total Tests: ${totalTests}`));
        console.log(chalk.green(`   Passed: ${passedTests}`));
        console.log(chalk.red(`   Failed: ${failedTests}`));
        console.log(chalk.blue(`   Success Rate: ${((passedTests / totalTests) * 100).toFixed(1)}%`));
        console.log(chalk.gray(`   Total Duration: ${(totalDuration / 1000).toFixed(1)}s`));
        
        console.log(chalk.blue(`\n📋 Test Details:`));
        
        // Individual test results
        for (const test of this.testResults) {
            const statusIcon = test.status === 'passed' ? '✅' : '❌';
            const statusColor = test.status === 'passed' ? chalk.green : chalk.red;
            
            console.log(`${statusIcon} ${test.name.padEnd(35)} ${statusColor(test.status.toUpperCase())} (${(test.duration / 1000).toFixed(1)}s)`);
            
            if (test.status === 'failed') {
                console.log(chalk.red(`   └─ Error: ${test.error}`));
            } else if (test.result && typeof test.result === 'object') {
                // Show relevant details for successful tests
                if (test.result.skipped) {
                    console.log(chalk.yellow(`   └─ Skipped: ${test.result.message}`));
                } else if (test.result.endpoints_tested) {
                    console.log(chalk.gray(`   └─ Endpoints tested: ${test.result.endpoints_tested}`));
                } else if (test.result.configured_vars !== undefined) {
                    console.log(chalk.gray(`   └─ Environment vars: ${test.result.configured_vars}/${test.result.total_required} configured`));
                } else if (test.result.required_dependencies) {
                    const req = test.result.required_dependencies;
                    const opt = test.result.optional_dependencies;
                    console.log(chalk.gray(`   └─ Dependencies: ${req.successful}/${req.total} required, ${opt.successful}/${opt.total} optional`));
                }
            }
        }
        
        console.log(chalk.gray('=' .repeat(60)));
        
        // Overall result
        if (failedTests === 0) {
            console.log(chalk.green.bold('🎉 All integration tests passed! System is ready for use.'));
        } else if (passedTests > failedTests) {
            console.log(chalk.yellow.bold('⚠️  Some tests failed but core functionality is working.'));
        } else {
            console.log(chalk.red.bold('❌ Critical issues detected. System needs fixes.'));
        }
        
        // Recommendations
        if (failedTests > 0) {
            console.log(chalk.yellow('\n💡 Troubleshooting Tips:'));
            
            const failedTestNames = this.testResults.filter(t => t.status === 'failed').map(t => t.name);
            
            if (failedTestNames.includes('API Endpoints Test')) {
                console.log(chalk.gray('• Start the backend server: npm run backend:dev'));
            }
            if (failedTestNames.includes('Environment Configuration')) {
                console.log(chalk.gray('• Configure environment variables: npm run setup:env'));
            }
            if (failedTestNames.includes('Dependency Installation Check')) {
                console.log(chalk.gray('• Install dependencies: npm run install:all'));
            }
            if (failedTestNames.includes('Python Backend Tests')) {
                console.log(chalk.gray('• Check Python dependencies and test files'));
            }
            if (failedTestNames.includes('Service Validation')) {
                console.log(chalk.gray('• Validate services individually: npm run validate:services'));
            }
        }
        
        return failedTests === 0;
    }

    async runAllTests() {
        console.log(chalk.blue('Starting comprehensive integration test suite...\n'));
        
        // Run tests in logical order
        await this.testEnvironmentConfiguration();
        await this.testDependencyInstallation();
        await this.testAPIEndpoints();
        await this.testPythonBackendTests();
        await this.testFrontendTests();
        await this.testServiceValidation();
        await this.testIntegrationValidation();
        await this.testWebEvalFlow();
        
        return this.generateTestReport();
    }
}

async function main() {
    try {
        const runner = new IntegrationTestRunner();
        const success = await runner.runAllTests();
        
        if (success) {
            console.log(chalk.green.bold('\n🎉 All integration tests completed successfully!'));
            console.log(chalk.blue('The integrated system is ready for production use.'));
            process.exit(0);
        } else {
            console.log(chalk.red.bold('\n❌ Some integration tests failed.'));
            console.log(chalk.yellow('Please review the test results and fix the issues.'));
            process.exit(1);
        }
        
    } catch (error) {
        console.error(chalk.red('Integration test suite failed:'), error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = IntegrationTestRunner;

