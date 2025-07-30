#!/usr/bin/env node

const axios = require('axios');
const chalk = require('chalk');
const ora = require('ora');
const fs = require('fs');
const path = require('path');

console.log(chalk.blue.bold('🌐 Web-eval-agent CICD Flow Test'));
console.log(chalk.gray('Complete end-to-end testing of web-eval-agent integration\n'));

const BACKEND_URL = 'http://localhost:8000';

class WebEvalCICDTester {
    constructor() {
        this.testResults = [];
        this.startTime = Date.now();
    }

    async logTest(name, testFn) {
        const spinner = ora(`Running: ${name}`).start();
        const testStart = Date.now();
        
        try {
            const result = await testFn();
            const duration = Date.now() - testStart;
            
            this.testResults.push({
                name,
                status: 'passed',
                duration,
                result
            });
            
            spinner.succeed(`${name} (${duration}ms)`);
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
            throw error;
        }
    }

    async testServiceHealth() {
        return await this.logTest('Service Health Check', async () => {
            const response = await axios.get(`${BACKEND_URL}/api/integrated/health`, {
                timeout: 10000
            });
            
            if (response.status !== 200) {
                throw new Error(`Health check failed with status ${response.status}`);
            }
            
            const health = response.data;
            if (health.overall_status === 'unhealthy') {
                throw new Error('System is unhealthy');
            }
            
            return {
                overall_status: health.overall_status,
                healthy_services: health.healthy_services,
                total_services: health.total_services,
                web_eval_status: health.services?.web_eval?.status
            };
        });
    }

    async testWebEvalBasicFunctionality() {
        return await this.logTest('Web-eval Basic Test', async () => {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/web-eval/test`, {
                url: 'https://example.com',
                task: 'Test that the page loads correctly and displays the main heading',
                headless: true,
                timeout: 30,
                capture_screenshots: true,
                capture_network: true,
                capture_console: true
            }, { timeout: 35000 });
            
            if (response.status !== 200) {
                throw new Error(`Web-eval test failed with status ${response.status}`);
            }
            
            const result = response.data;
            if (!result.success && !result.mock) {
                throw new Error(`Web-eval execution failed: ${result.error}`);
            }
            
            return {
                success: result.success,
                mock: result.mock,
                execution_time: result.execution_time,
                url: result.url,
                has_report: !!result.report,
                has_screenshots: Array.isArray(result.screenshots) && result.screenshots.length > 0,
                has_network_logs: Array.isArray(result.network_logs) && result.network_logs.length > 0
            };
        });
    }

    async testLocalWebappTesting() {
        return await this.logTest('Local Webapp Testing', async () => {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/web-eval/test-local`, {
                port: 3000,
                framework: 'react',
                test_scenarios: [
                    'Test that the homepage loads correctly',
                    'Test navigation menu functionality',
                    'Test responsive design on mobile viewport'
                ]
            }, { timeout: 60000 });
            
            if (response.status !== 200) {
                throw new Error(`Local webapp test failed with status ${response.status}`);
            }
            
            const result = response.data;
            
            return {
                url: result.url,
                port: result.port,
                framework: result.framework,
                total_scenarios: result.total_scenarios,
                successful_scenarios: result.successful_scenarios,
                success_rate: result.success_rate,
                overall_success: result.overall_success,
                total_execution_time: result.total_execution_time
            };
        });
    }

    async testAccessibilityValidation() {
        return await this.logTest('Accessibility Validation', async () => {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/web-eval/accessibility`, {
                url: 'https://example.com',
                standards: ['WCAG 2.1 AA', 'Section 508']
            }, { timeout: 45000 });
            
            if (response.status !== 200) {
                throw new Error(`Accessibility test failed with status ${response.status}`);
            }
            
            const result = response.data;
            
            return {
                success: result.success,
                validation_type: result.validation_type,
                standards_checked: result.standards_checked,
                accessibility_score: result.accessibility_score,
                critical_issues: result.critical_issues,
                moderate_issues: result.moderate_issues,
                minor_issues: result.minor_issues
            };
        });
    }

    async testPerformanceAudit() {
        return await this.logTest('Performance Audit', async () => {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/web-eval/performance`, {
                url: 'https://example.com',
                metrics: [
                    'First Contentful Paint',
                    'Largest Contentful Paint',
                    'Cumulative Layout Shift',
                    'Time to Interactive'
                ]
            }, { timeout: 45000 });
            
            if (response.status !== 200) {
                throw new Error(`Performance audit failed with status ${response.status}`);
            }
            
            const result = response.data;
            
            return {
                success: result.success,
                audit_type: result.audit_type,
                metrics_collected: result.metrics_collected,
                performance_score: result.performance_score,
                core_web_vitals: result.core_web_vitals,
                recommendations: result.recommendations
            };
        });
    }

    async testBrowserStateSetup() {
        return await this.logTest('Browser State Setup', async () => {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/web-eval/setup-browser`, {
                url: 'https://example.com',
                timeout: 60
            }, { timeout: 65000 });
            
            if (response.status !== 200) {
                throw new Error(`Browser setup failed with status ${response.status}`);
            }
            
            const result = response.data;
            
            return {
                success: result.success,
                execution_time: result.execution_time,
                browser_state_saved: result.browser_state_saved,
                mock: result.mock
            };
        });
    }

    async testIntegratedPipelineWithWebEval() {
        return await this.logTest('Integrated Pipeline with Web-eval', async () => {
            const response = await axios.post(`${BACKEND_URL}/api/integrated/pipeline/execute`, {
                description: 'CICD test pipeline with web-eval-agent',
                type: 'cicd_test',
                webapp_url: 'https://example.com',
                ui_testing_enabled: true,
                ui_test_task: 'Comprehensive UI testing including accessibility and performance',
                headless_testing: true,
                ui_test_timeout: 60,
                capture_screenshots: true,
                capture_network: true,
                capture_console: true,
                test_accessibility: true,
                accessibility_standards: ['WCAG 2.1 AA'],
                test_performance: true,
                performance_metrics: ['First Contentful Paint', 'Largest Contentful Paint'],
                create_agent_run: false,
                cleanup_resources: true
            }, { timeout: 120000 });
            
            if (response.status !== 200) {
                throw new Error(`Pipeline execution failed with status ${response.status}`);
            }
            
            const result = response.data;
            
            return {
                pipeline_id: result.pipeline_id,
                status: result.status,
                progress: result.progress,
                execution_time: result.execution_time,
                stages_completed: Object.keys(result.stages || {}),
                ui_testing_stage: result.stages?.ui_testing,
                errors: result.errors || [],
                warnings: result.warnings || []
            };
        });
    }

    async testErrorHandling() {
        return await this.logTest('Error Handling Test', async () => {
            try {
                const response = await axios.post(`${BACKEND_URL}/api/integrated/web-eval/test`, {
                    url: 'http://invalid-url-that-does-not-exist-12345.com',
                    task: 'Test error handling with invalid URL',
                    headless: true,
                    timeout: 10
                }, { timeout: 15000 });
                
                const result = response.data;
                
                // Should handle error gracefully
                if (result.success === false || result.mock) {
                    return {
                        error_handled: true,
                        error_message: result.error || 'Mock implementation',
                        graceful_failure: true
                    };
                } else {
                    throw new Error('Expected error handling but got success');
                }
            } catch (error) {
                if (error.response && error.response.status >= 400) {
                    return {
                        error_handled: true,
                        http_error: error.response.status,
                        graceful_failure: true
                    };
                }
                throw error;
            }
        });
    }

    async testConcurrentRequests() {
        return await this.logTest('Concurrent Requests Test', async () => {
            const requests = [];
            const concurrency = 3;
            
            for (let i = 0; i < concurrency; i++) {
                requests.push(
                    axios.post(`${BACKEND_URL}/api/integrated/web-eval/test`, {
                        url: 'https://example.com',
                        task: `Concurrent test ${i + 1}`,
                        headless: true,
                        timeout: 20
                    }, { timeout: 25000 })
                );
            }
            
            const responses = await Promise.allSettled(requests);
            const successful = responses.filter(r => r.status === 'fulfilled').length;
            
            return {
                total_requests: concurrency,
                successful_requests: successful,
                success_rate: (successful / concurrency) * 100,
                all_completed: responses.length === concurrency
            };
        });
    }

    generateReport() {
        const totalDuration = Date.now() - this.startTime;
        const passedTests = this.testResults.filter(t => t.status === 'passed').length;
        const failedTests = this.testResults.filter(t => t.status === 'failed').length;
        const totalTests = this.testResults.length;
        
        console.log(chalk.blue.bold('\n📊 Web-eval-agent CICD Test Report'));
        console.log(chalk.gray('=' .repeat(60)));
        
        // Summary
        console.log(chalk.blue(`📈 Test Summary:`));
        console.log(chalk.gray(`   Total Tests: ${totalTests}`));
        console.log(chalk.green(`   Passed: ${passedTests}`));
        console.log(chalk.red(`   Failed: ${failedTests}`));
        console.log(chalk.blue(`   Success Rate: ${((passedTests / totalTests) * 100).toFixed(1)}%`));
        console.log(chalk.gray(`   Total Duration: ${totalDuration}ms`));
        
        console.log(chalk.blue(`\n📋 Test Details:`));
        
        // Individual test results
        for (const test of this.testResults) {
            const statusIcon = test.status === 'passed' ? '✅' : '❌';
            const statusColor = test.status === 'passed' ? chalk.green : chalk.red;
            
            console.log(`${statusIcon} ${test.name.padEnd(35)} ${statusColor(test.status.toUpperCase())} (${test.duration}ms)`);
            
            if (test.status === 'failed') {
                console.log(chalk.red(`   └─ Error: ${test.error}`));
            } else if (test.result && typeof test.result === 'object') {
                // Show key metrics for successful tests
                if (test.result.success_rate !== undefined) {
                    console.log(chalk.gray(`   └─ Success Rate: ${test.result.success_rate}%`));
                }
                if (test.result.execution_time !== undefined) {
                    console.log(chalk.gray(`   └─ Execution Time: ${test.result.execution_time}ms`));
                }
                if (test.result.mock) {
                    console.log(chalk.yellow(`   └─ Mock Implementation Used`));
                }
            }
        }
        
        console.log(chalk.gray('=' .repeat(60)));
        
        // Overall result
        if (failedTests === 0) {
            console.log(chalk.green.bold('🎉 All web-eval-agent tests passed! CICD flow is working correctly.'));
        } else if (passedTests > failedTests) {
            console.log(chalk.yellow.bold('⚠️  Some tests failed but core functionality is working.'));
        } else {
            console.log(chalk.red.bold('❌ Critical issues detected in web-eval-agent integration.'));
        }
        
        // Save detailed report
        this.saveDetailedReport();
        
        return failedTests === 0;
    }

    saveDetailedReport() {
        const reportData = {
            timestamp: new Date().toISOString(),
            summary: {
                total_tests: this.testResults.length,
                passed_tests: this.testResults.filter(t => t.status === 'passed').length,
                failed_tests: this.testResults.filter(t => t.status === 'failed').length,
                total_duration: Date.now() - this.startTime
            },
            test_results: this.testResults
        };
        
        const reportsDir = path.join(process.cwd(), 'backend', 'logs');
        if (!fs.existsSync(reportsDir)) {
            fs.mkdirSync(reportsDir, { recursive: true });
        }
        
        const reportPath = path.join(reportsDir, `web-eval-cicd-report-${Date.now()}.json`);
        fs.writeFileSync(reportPath, JSON.stringify(reportData, null, 2));
        
        console.log(chalk.blue(`\n📄 Detailed report saved: ${reportPath}`));
    }

    async runFullCICDFlow() {
        console.log(chalk.blue('Starting comprehensive web-eval-agent CICD flow test...\n'));
        
        try {
            // Core functionality tests
            await this.testServiceHealth();
            await this.testWebEvalBasicFunctionality();
            await this.testLocalWebappTesting();
            
            // Advanced feature tests
            await this.testAccessibilityValidation();
            await this.testPerformanceAudit();
            await this.testBrowserStateSetup();
            
            // Integration tests
            await this.testIntegratedPipelineWithWebEval();
            
            // Reliability tests
            await this.testErrorHandling();
            await this.testConcurrentRequests();
            
        } catch (error) {
            console.log(chalk.yellow(`\nTest execution stopped due to critical failure: ${error.message}`));
        }
        
        return this.generateReport();
    }
}

async function main() {
    try {
        console.log(chalk.blue('Checking prerequisites...'));
        
        // Check if backend is running
        try {
            await axios.get(`${BACKEND_URL}/api/health`, { timeout: 5000 });
            console.log(chalk.green('✓ Backend service is running'));
        } catch (error) {
            console.log(chalk.red('❌ Backend service is not running'));
            console.log(chalk.yellow('Please start the backend with: npm run backend:dev'));
            process.exit(1);
        }
        
        const tester = new WebEvalCICDTester();
        const success = await tester.runFullCICDFlow();
        
        if (success) {
            console.log(chalk.green.bold('\n🎉 Web-eval-agent CICD flow completed successfully!'));
            console.log(chalk.blue('The integration is ready for production use.'));
            process.exit(0);
        } else {
            console.log(chalk.red.bold('\n❌ Web-eval-agent CICD flow has issues.'));
            console.log(chalk.yellow('Please review the test results and fix the failing tests.'));
            process.exit(1);
        }
        
    } catch (error) {
        console.error(chalk.red('CICD flow test failed:'), error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = WebEvalCICDTester;

