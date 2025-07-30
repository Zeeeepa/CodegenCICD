#!/usr/bin/env node

const axios = require('axios');
const chalk = require('chalk');
const ora = require('ora');
const { spawn } = require('child_process');

console.log(chalk.blue.bold('🔍 Service Validation'));
console.log(chalk.gray('Validating all integrated services and dependencies\n'));

const BACKEND_URL = 'http://localhost:8000';
const FRONTEND_URL = 'http://localhost:3000';

class ServiceValidator {
    constructor() {
        this.results = {
            backend: { status: 'unknown', details: {} },
            frontend: { status: 'unknown', details: {} },
            grainchain: { status: 'unknown', details: {} },
            graphSitter: { status: 'unknown', details: {} },
            webEval: { status: 'unknown', details: {} },
            codegenSDK: { status: 'unknown', details: {} },
            integration: { status: 'unknown', details: {} }
        };
    }

    async validatePythonDependencies() {
        const spinner = ora('Checking Python dependencies...').start();
        
        try {
            const dependencies = [
                'fastapi',
                'uvicorn',
                'pydantic',
                'sqlalchemy',
                'redis',
                'httpx',
                'structlog'
            ];
            
            for (const dep of dependencies) {
                try {
                    await this.runCommand('python', ['-c', `import ${dep}`]);
                } catch (error) {
                    throw new Error(`Missing Python dependency: ${dep}`);
                }
            }
            
            spinner.succeed('Python dependencies validated');
            return true;
        } catch (error) {
            spinner.fail(`Python dependencies validation failed: ${error.message}`);
            return false;
        }
    }

    async validateNodeDependencies() {
        const spinner = ora('Checking Node.js dependencies...').start();
        
        try {
            const fs = require('fs');
            const path = require('path');
            
            // Check if node_modules exists
            const nodeModulesPath = path.join(process.cwd(), 'node_modules');
            if (!fs.existsSync(nodeModulesPath)) {
                throw new Error('node_modules not found. Run npm install first.');
            }
            
            // Check critical dependencies
            const criticalDeps = ['concurrently', 'axios', 'chalk', 'inquirer', 'ora'];
            for (const dep of criticalDeps) {
                try {
                    require(dep);
                } catch (error) {
                    throw new Error(`Missing Node.js dependency: ${dep}`);
                }
            }
            
            spinner.succeed('Node.js dependencies validated');
            return true;
        } catch (error) {
            spinner.fail(`Node.js dependencies validation failed: ${error.message}`);
            return false;
        }
    }

    async validateBackendService() {
        const spinner = ora('Validating backend service...').start();
        
        try {
            // Check if backend is running
            const healthResponse = await axios.get(`${BACKEND_URL}/api/health`, {
                timeout: 5000
            });
            
            if (healthResponse.status === 200) {
                this.results.backend.status = 'healthy';
                this.results.backend.details = healthResponse.data;
                spinner.succeed('Backend service is healthy');
                return true;
            } else {
                throw new Error(`Backend returned status ${healthResponse.status}`);
            }
        } catch (error) {
            this.results.backend.status = 'unhealthy';
            this.results.backend.details = { error: error.message };
            
            if (error.code === 'ECONNREFUSED') {
                spinner.fail('Backend service is not running. Start with: npm run backend:dev');
            } else {
                spinner.fail(`Backend validation failed: ${error.message}`);
            }
            return false;
        }
    }

    async validateIntegratedServices() {
        const spinner = ora('Validating integrated services...').start();
        
        try {
            const servicesResponse = await axios.get(`${BACKEND_URL}/api/integrated/health`, {
                timeout: 10000
            });
            
            if (servicesResponse.status === 200) {
                const healthData = servicesResponse.data;
                
                // Update individual service statuses
                this.results.grainchain.status = healthData.services?.grainchain?.grainchain_available ? 'available' : 'mock';
                this.results.grainchain.details = healthData.services?.grainchain || {};
                
                this.results.graphSitter.status = healthData.services?.graph_sitter?.status || 'unknown';
                this.results.graphSitter.details = healthData.services?.graph_sitter || {};
                
                this.results.webEval.status = healthData.services?.web_eval?.status || 'unknown';
                this.results.webEval.details = healthData.services?.web_eval || {};
                
                this.results.codegenSDK.status = healthData.services?.codegen_sdk?.status || 'unknown';
                this.results.codegenSDK.details = healthData.services?.codegen_sdk || {};
                
                this.results.integration.status = healthData.overall_status;
                this.results.integration.details = {
                    healthy_services: healthData.healthy_services,
                    total_services: healthData.total_services
                };
                
                spinner.succeed(`Integrated services validated (${healthData.healthy_services}/${healthData.total_services} healthy)`);
                return true;
            } else {
                throw new Error(`Services health check returned status ${servicesResponse.status}`);
            }
        } catch (error) {
            spinner.fail(`Integrated services validation failed: ${error.message}`);
            return false;
        }
    }

    async validateGrainchainService() {
        const spinner = ora('Testing Grainchain service...').start();
        
        try {
            const testCode = 'print("Hello from Grainchain!")';
            const response = await axios.post(`${BACKEND_URL}/api/integrated/grainchain/execute`, {
                code: testCode,
                provider: 'local',
                timeout: 30
            }, { timeout: 35000 });
            
            if (response.status === 200 && response.data.success) {
                spinner.succeed('Grainchain service test passed');
                return true;
            } else {
                throw new Error('Grainchain execution failed');
            }
        } catch (error) {
            spinner.fail(`Grainchain service test failed: ${error.message}`);
            return false;
        }
    }

    async validateGraphSitterService() {
        const spinner = ora('Testing Graph-sitter service...').start();
        
        try {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/graph-sitter/analyze`, {
                repo_path: './test_repo',
                include_diagnostics: true,
                use_cache: false
            }, { timeout: 30000 });
            
            if (response.status === 200) {
                spinner.succeed('Graph-sitter service test passed');
                return true;
            } else {
                throw new Error('Graph-sitter analysis failed');
            }
        } catch (error) {
            spinner.fail(`Graph-sitter service test failed: ${error.message}`);
            return false;
        }
    }

    async validateWebEvalService() {
        const spinner = ora('Testing Web-eval-agent service...').start();
        
        try {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/web-eval/test`, {
                url: 'http://example.com',
                task: 'Test basic page loading',
                headless: true,
                timeout: 30
            }, { timeout: 35000 });
            
            if (response.status === 200) {
                spinner.succeed('Web-eval-agent service test passed');
                return true;
            } else {
                throw new Error('Web-eval-agent test failed');
            }
        } catch (error) {
            spinner.fail(`Web-eval-agent service test failed: ${error.message}`);
            return false;
        }
    }

    async validateCodegenSDKService() {
        const spinner = ora('Testing Codegen SDK service...').start();
        
        try {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/codegen-sdk/agent-run`, {
                task_data: {
                    description: 'Test agent run',
                    type: 'validation_test'
                },
                priority: 'normal'
            }, { timeout: 15000 });
            
            if (response.status === 200) {
                spinner.succeed('Codegen SDK service test passed');
                return true;
            } else {
                throw new Error('Codegen SDK test failed');
            }
        } catch (error) {
            spinner.fail(`Codegen SDK service test failed: ${error.message}`);
            return false;
        }
    }

    async validateEnvironmentVariables() {
        const spinner = ora('Checking environment variables...').start();
        
        try {
            require('dotenv').config();
            
            const requiredVars = [
                'CODEGEN_ORG_ID',
                'CODEGEN_API_TOKEN',
                'GEMINI_API_KEY',
                'GITHUB_TOKEN'
            ];
            
            const missingVars = [];
            for (const varName of requiredVars) {
                if (!process.env[varName] || process.env[varName].includes('your-') || process.env[varName].includes('change-')) {
                    missingVars.push(varName);
                }
            }
            
            if (missingVars.length > 0) {
                throw new Error(`Missing or placeholder environment variables: ${missingVars.join(', ')}`);
            }
            
            spinner.succeed('Environment variables validated');
            return true;
        } catch (error) {
            spinner.fail(`Environment validation failed: ${error.message}`);
            return false;
        }
    }

    async runCommand(command, args = [], options = {}) {
        return new Promise((resolve, reject) => {
            const process = spawn(command, args, {
                stdio: 'pipe',
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
                if (code === 0) {
                    resolve({ stdout, stderr });
                } else {
                    reject(new Error(`Command failed with code ${code}: ${stderr}`));
                }
            });
            
            process.on('error', (error) => {
                reject(error);
            });
        });
    }

    printResults() {
        console.log(chalk.blue.bold('\n📊 Validation Results:'));
        console.log(chalk.gray('=' .repeat(50)));
        
        const services = [
            { name: 'Backend Service', key: 'backend' },
            { name: 'Grainchain', key: 'grainchain' },
            { name: 'Graph-sitter', key: 'graphSitter' },
            { name: 'Web-eval-agent', key: 'webEval' },
            { name: 'Codegen SDK', key: 'codegenSDK' },
            { name: 'Integration', key: 'integration' }
        ];
        
        for (const service of services) {
            const result = this.results[service.key];
            const status = result.status;
            
            let statusColor = chalk.gray;
            let statusIcon = '❓';
            
            switch (status) {
                case 'healthy':
                case 'available':
                    statusColor = chalk.green;
                    statusIcon = '✅';
                    break;
                case 'mock':
                    statusColor = chalk.yellow;
                    statusIcon = '🔶';
                    break;
                case 'unhealthy':
                case 'failed':
                    statusColor = chalk.red;
                    statusIcon = '❌';
                    break;
                case 'degraded':
                    statusColor = chalk.orange;
                    statusIcon = '⚠️';
                    break;
            }
            
            console.log(`${statusIcon} ${service.name.padEnd(20)} ${statusColor(status.toUpperCase())}`);
            
            // Show additional details for some services
            if (result.details && Object.keys(result.details).length > 0) {
                if (service.key === 'integration' && result.details.healthy_services !== undefined) {
                    console.log(chalk.gray(`   └─ ${result.details.healthy_services}/${result.details.total_services} services healthy`));
                }
                if (result.details.error) {
                    console.log(chalk.red(`   └─ Error: ${result.details.error}`));
                }
            }
        }
        
        console.log(chalk.gray('=' .repeat(50)));
        
        // Overall status
        const healthyCount = Object.values(this.results).filter(r => 
            r.status === 'healthy' || r.status === 'available'
        ).length;
        const totalCount = Object.keys(this.results).length;
        
        if (healthyCount === totalCount) {
            console.log(chalk.green.bold('🎉 All services are healthy!'));
        } else if (healthyCount > totalCount / 2) {
            console.log(chalk.yellow.bold('⚠️  Some services are degraded but system is functional'));
        } else {
            console.log(chalk.red.bold('❌ System has critical issues'));
        }
        
        console.log(chalk.blue(`\n📈 Overall Health: ${healthyCount}/${totalCount} services healthy`));
    }

    async runFullValidation() {
        console.log(chalk.blue('Starting comprehensive service validation...\n'));
        
        const validations = [
            { name: 'Environment Variables', fn: () => this.validateEnvironmentVariables() },
            { name: 'Node.js Dependencies', fn: () => this.validateNodeDependencies() },
            { name: 'Python Dependencies', fn: () => this.validatePythonDependencies() },
            { name: 'Backend Service', fn: () => this.validateBackendService() },
            { name: 'Integrated Services', fn: () => this.validateIntegratedServices() },
            { name: 'Grainchain Service', fn: () => this.validateGrainchainService() },
            { name: 'Graph-sitter Service', fn: () => this.validateGraphSitterService() },
            { name: 'Web-eval-agent Service', fn: () => this.validateWebEvalService() },
            { name: 'Codegen SDK Service', fn: () => this.validateCodegenSDKService() }
        ];
        
        const results = [];
        for (const validation of validations) {
            try {
                const result = await validation.fn();
                results.push({ name: validation.name, success: result });
            } catch (error) {
                results.push({ name: validation.name, success: false, error: error.message });
            }
        }
        
        this.printResults();
        
        const successCount = results.filter(r => r.success).length;
        console.log(chalk.blue(`\n📊 Validation Summary: ${successCount}/${results.length} checks passed`));
        
        if (successCount < results.length) {
            console.log(chalk.yellow('\n💡 Troubleshooting Tips:'));
            console.log(chalk.gray('• Ensure backend is running: npm run backend:dev'));
            console.log(chalk.gray('• Check environment variables in .env file'));
            console.log(chalk.gray('• Install missing dependencies: npm run install:all'));
            console.log(chalk.gray('• Check logs: npm run logs'));
        }
        
        return successCount === results.length;
    }
}

async function main() {
    try {
        const validator = new ServiceValidator();
        const success = await validator.runFullValidation();
        
        if (success) {
            console.log(chalk.green.bold('\n🎉 All validations passed! System is ready.'));
            process.exit(0);
        } else {
            console.log(chalk.red.bold('\n❌ Some validations failed. Please check the issues above.'));
            process.exit(1);
        }
    } catch (error) {
        console.error(chalk.red('Validation failed:'), error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = ServiceValidator;

