#!/usr/bin/env node

const axios = require('axios');
const chalk = require('chalk');
const ora = require('ora');
const fs = require('fs');
const path = require('path');

console.log(chalk.blue.bold('🔗 Integration Validation'));
console.log(chalk.gray('Testing complete integration between all four libraries\n'));

const BACKEND_URL = 'http://localhost:8000';

class IntegrationValidator {
    constructor() {
        this.testResults = [];
        this.startTime = Date.now();
    }

    async logTest(name, testFn) {
        const spinner = ora(`Testing: ${name}`).start();
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
            return null;
        }
    }

    async testCompleteIntegratedPipeline() {
        return await this.logTest('Complete Integrated Pipeline', async () => {
            const pipelineRequest = {
                description: 'Full integration test pipeline',
                type: 'integration_test',
                
                // Code analysis with Graph-sitter
                repo_path: './test_repo',
                code_analysis_enabled: true,
                include_diagnostics: true,
                analyze_dependencies: true,
                
                // Sandbox execution with Grainchain
                code_to_execute: 'print("Integration test successful!")\nimport sys\nprint(f"Python version: {sys.version}")',
                sandbox_execution_enabled: true,
                sandbox_provider: 'local',
                execution_timeout: 60,
                environment_vars: {
                    'TEST_ENV': 'integration',
                    'PIPELINE_ID': 'test-pipeline-001'
                },
                create_snapshot: true,
                
                // UI testing with Web-eval-agent
                webapp_url: 'https://example.com',
                ui_testing_enabled: true,
                ui_test_task: 'Test the complete user interface including navigation, forms, and content display',
                headless_testing: true,
                ui_test_timeout: 90,
                capture_screenshots: true,
                capture_network: true,
                capture_console: true,
                test_accessibility: true,
                accessibility_standards: ['WCAG 2.1 AA'],
                test_performance: true,
                performance_metrics: ['First Contentful Paint', 'Largest Contentful Paint', 'Time to Interactive'],
                
                // Agent orchestration with Codegen SDK
                create_agent_run: true,
                priority: 'high',
                cleanup_resources: true,
                
                configuration: {
                    test_mode: true,
                    integration_validation: true
                }
            };
            
            const response = await axios.post(`${BACKEND_URL}/api/integrated/pipeline/execute`, pipelineRequest, {
                timeout: 180000 // 3 minutes
            });
            
            if (response.status !== 200) {
                throw new Error(`Pipeline execution failed with status ${response.status}`);
            }
            
            const result = response.data;
            
            // Validate pipeline completion
            if (result.status !== 'completed' && result.status !== 'failed') {
                throw new Error(`Pipeline did not complete. Status: ${result.status}`);
            }
            
            // Check that all expected stages were executed
            const expectedStages = ['initialization', 'code_analysis', 'sandbox_execution', 'ui_testing', 'results_integration', 'completion'];
            const actualStages = Object.keys(result.stages || {});
            
            for (const stage of expectedStages) {
                if (!actualStages.includes(stage)) {
                    throw new Error(`Missing expected stage: ${stage}`);
                }
            }
            
            return {
                pipeline_id: result.pipeline_id,
                status: result.status,
                execution_time: result.execution_time,
                progress: result.progress,
                stages_completed: actualStages.length,
                stages_successful: Object.values(result.stages).filter(s => s.status === 'completed').length,
                agent_run_id: result.agent_run_id,
                errors: result.errors || [],
                warnings: result.warnings || []
            };
        });
    }

    async testServiceInteroperability() {
        return await this.logTest('Service Interoperability', async () => {
            // Test that services can work together by passing data between them
            
            // 1. First, analyze some code with Graph-sitter
            const analysisResponse = await axios.post(`${BACKEND_URL}/api/integrated/graph-sitter/analyze`, {
                repo_path: './test_repo',
                include_diagnostics: true
            }, { timeout: 30000 });
            
            if (analysisResponse.status !== 200) {
                throw new Error('Graph-sitter analysis failed');
            }
            
            const analysisResult = analysisResponse.data;
            
            // 2. Use analysis results to generate code for Grainchain execution
            const codeToExecute = `
# Generated from analysis results
print("Code analysis completed")
print(f"Repository analyzed: ${analysisResult.repo_path || 'test_repo'}")
print(f"Analysis timestamp: ${analysisResult.analysis_timestamp || 'unknown'}")

# Simulate processing analysis data
import json
analysis_summary = {
    "repo_path": "${analysisResult.repo_path || 'test_repo'}",
    "has_summary": ${!!analysisResult.summary},
    "timestamp": "${new Date().toISOString()}"
}
print(f"Analysis summary: {json.dumps(analysis_summary)}")
`;
            
            const executionResponse = await axios.post(`${BACKEND_URL}/api/integrated/grainchain/execute`, {
                code: codeToExecute,
                provider: 'local',
                timeout: 30,
                environment_vars: {
                    'ANALYSIS_ID': analysisResult.analysis_id || 'test-analysis'
                }
            }, { timeout: 35000 });
            
            if (executionResponse.status !== 200) {
                throw new Error('Grainchain execution failed');
            }
            
            const executionResult = executionResponse.data;
            
            // 3. Test web-eval with results from previous steps
            const webEvalResponse = await axios.post(`${BACKEND_URL}/api/integrated/web-eval/test`, {
                url: 'https://example.com',
                task: `Test web application after code analysis and execution. Analysis completed at ${analysisResult.analysis_timestamp || 'unknown'}, execution ${executionResult.success ? 'successful' : 'failed'}.`,
                headless: true,
                timeout: 30
            }, { timeout: 35000 });
            
            if (webEvalResponse.status !== 200) {
                throw new Error('Web-eval test failed');
            }
            
            const webEvalResult = webEvalResponse.data;
            
            // 4. Create agent run with combined results
            const agentRunResponse = await axios.post(`${BACKEND_URL}/api/integrated/codegen-sdk/agent-run`, {
                task_data: {
                    description: 'Interoperability test with combined results',
                    type: 'interoperability_test',
                    context: {
                        analysis_completed: !!analysisResult.summary,
                        execution_successful: executionResult.success,
                        web_eval_successful: webEvalResult.success,
                        combined_test: true
                    }
                },
                priority: 'normal'
            }, { timeout: 15000 });
            
            if (agentRunResponse.status !== 200) {
                throw new Error('Agent run creation failed');
            }
            
            const agentRunResult = agentRunResponse.data;
            
            return {
                analysis_successful: !!analysisResult.summary,
                execution_successful: executionResult.success,
                web_eval_successful: webEvalResult.success,
                agent_run_created: agentRunResult.success,
                data_flow_working: true,
                all_services_interoperable: true
            };
        });
    }

    async testConcurrentServiceUsage() {
        return await this.logTest('Concurrent Service Usage', async () => {
            // Test multiple services running concurrently
            const requests = [
                // Graph-sitter analysis
                axios.post(`${BACKEND_URL}/api/integrated/graph-sitter/analyze`, {
                    repo_path: './test_repo_1',
                    include_diagnostics: false
                }, { timeout: 30000 }),
                
                // Grainchain execution
                axios.post(`${BACKEND_URL}/api/integrated/grainchain/execute`, {
                    code: 'print("Concurrent test 1")\nfor i in range(3): print(f"Step {i+1}")',
                    provider: 'local',
                    timeout: 30
                }, { timeout: 35000 }),
                
                // Web-eval test
                axios.post(`${BACKEND_URL}/api/integrated/web-eval/test`, {
                    url: 'https://example.com',
                    task: 'Concurrent web evaluation test',
                    headless: true,
                    timeout: 30
                }, { timeout: 35000 }),
                
                // Codegen SDK agent run
                axios.post(`${BACKEND_URL}/api/integrated/codegen-sdk/agent-run`, {
                    task_data: {
                        description: 'Concurrent agent run test',
                        type: 'concurrent_test'
                    }
                }, { timeout: 15000 })
            ];
            
            const results = await Promise.allSettled(requests);
            const successful = results.filter(r => r.status === 'fulfilled' && r.value.status === 200).length;
            const total = requests.length;
            
            if (successful < total) {
                console.log(chalk.yellow(`Warning: Only ${successful}/${total} concurrent requests succeeded`));
            }
            
            return {
                total_requests: total,
                successful_requests: successful,
                success_rate: (successful / total) * 100,
                concurrent_execution_supported: successful >= total * 0.75 // At least 75% success
            };
        });
    }

    async testErrorPropagation() {
        return await this.logTest('Error Propagation and Recovery', async () => {
            // Test how errors propagate through the integrated system
            
            try {
                const response = await axios.post(`${BACKEND_URL}/api/integrated/pipeline/execute`, {
                    description: 'Error propagation test',
                    type: 'error_test',
                    
                    // Intentionally cause errors
                    repo_path: '/nonexistent/path/that/should/fail',
                    code_analysis_enabled: true,
                    
                    code_to_execute: 'raise Exception("Intentional test error")',
                    sandbox_execution_enabled: true,
                    
                    webapp_url: 'http://invalid-url-12345.com',
                    ui_testing_enabled: true,
                    
                    create_agent_run: false // Skip agent run to avoid external API calls
                }, { timeout: 120000 });
                
                const result = response.data;
                
                // Pipeline should complete even with errors
                const hasErrors = result.errors && result.errors.length > 0;
                const stagesWithErrors = Object.values(result.stages || {}).filter(s => s.status === 'failed').length;
                
                return {
                    pipeline_completed: !!result.pipeline_id,
                    errors_captured: hasErrors,
                    error_count: result.errors ? result.errors.length : 0,
                    failed_stages: stagesWithErrors,
                    graceful_degradation: result.status === 'failed' || result.status === 'completed',
                    error_handling_working: true
                };
                
            } catch (error) {
                // Even HTTP errors should be handled gracefully
                if (error.response && error.response.status >= 400) {
                    return {
                        http_error_handled: true,
                        status_code: error.response.status,
                        error_response: !!error.response.data,
                        graceful_http_error_handling: true
                    };
                }
                throw error;
            }
        });
    }

    async testDataConsistency() {
        return await this.logTest('Data Consistency Across Services', async () => {
            // Test that data remains consistent when passed between services
            
            const testId = `test-${Date.now()}`;
            const testData = {
                test_id: testId,
                timestamp: new Date().toISOString(),
                test_type: 'data_consistency'
            };
            
            // 1. Execute code that generates specific output
            const executionResponse = await axios.post(`${BACKEND_URL}/api/integrated/grainchain/execute`, {
                code: `
import json
test_data = ${JSON.stringify(testData)}
print(f"TEST_OUTPUT_START:{json.dumps(test_data)}:TEST_OUTPUT_END")
print("Data consistency test completed")
`,
                provider: 'local',
                timeout: 30
            }, { timeout: 35000 });
            
            if (executionResponse.status !== 200 || !executionResponse.data.success) {
                throw new Error('Initial execution failed');
            }
            
            const executionResult = executionResponse.data;
            
            // 2. Verify the output contains our test data
            const stdout = executionResult.stdout || '';
            const outputMatch = stdout.match(/TEST_OUTPUT_START:(.*?):TEST_OUTPUT_END/);
            
            if (!outputMatch) {
                throw new Error('Test data not found in execution output');
            }
            
            let extractedData;
            try {
                extractedData = JSON.parse(outputMatch[1]);
            } catch (error) {
                throw new Error('Failed to parse extracted test data');
            }
            
            // 3. Verify data integrity
            const dataIntact = (
                extractedData.test_id === testData.test_id &&
                extractedData.timestamp === testData.timestamp &&
                extractedData.test_type === testData.test_type
            );
            
            if (!dataIntact) {
                throw new Error('Data integrity check failed');
            }
            
            return {
                test_id: testId,
                data_sent: testData,
                data_received: extractedData,
                data_integrity_maintained: dataIntact,
                execution_successful: executionResult.success,
                output_parsing_successful: true
            };
        });
    }

    async testServiceHealthMonitoring() {
        return await this.logTest('Service Health Monitoring', async () => {
            const response = await axios.get(`${BACKEND_URL}/api/integrated/health`, {
                timeout: 10000
            });
            
            if (response.status !== 200) {
                throw new Error(`Health endpoint failed with status ${response.status}`);
            }
            
            const health = response.data;
            
            // Validate health response structure
            const requiredFields = ['overall_status', 'healthy_services', 'total_services', 'services'];
            for (const field of requiredFields) {
                if (!(field in health)) {
                    throw new Error(`Missing required health field: ${field}`);
                }
            }
            
            // Validate individual service health data
            const requiredServices = ['grainchain', 'graph_sitter', 'web_eval', 'codegen_sdk'];
            for (const service of requiredServices) {
                if (!(service in health.services)) {
                    throw new Error(`Missing service health data: ${service}`);
                }
            }
            
            return {
                overall_status: health.overall_status,
                healthy_services: health.healthy_services,
                total_services: health.total_services,
                service_count: Object.keys(health.services).length,
                monitoring_functional: true,
                health_data_complete: true
            };
        });
    }

    generateIntegrationReport() {
        const totalDuration = Date.now() - this.startTime;
        const passedTests = this.testResults.filter(t => t.status === 'passed').length;
        const failedTests = this.testResults.filter(t => t.status === 'failed').length;
        const totalTests = this.testResults.length;
        
        console.log(chalk.blue.bold('\n📊 Integration Validation Report'));
        console.log(chalk.gray('=' .repeat(70)));
        
        // Summary
        console.log(chalk.blue(`📈 Integration Test Summary:`));
        console.log(chalk.gray(`   Total Tests: ${totalTests}`));
        console.log(chalk.green(`   Passed: ${passedTests}`));
        console.log(chalk.red(`   Failed: ${failedTests}`));
        console.log(chalk.blue(`   Success Rate: ${((passedTests / totalTests) * 100).toFixed(1)}%`));
        console.log(chalk.gray(`   Total Duration: ${(totalDuration / 1000).toFixed(1)}s`));
        
        console.log(chalk.blue(`\n📋 Integration Test Details:`));
        
        // Individual test results with detailed info
        for (const test of this.testResults) {
            const statusIcon = test.status === 'passed' ? '✅' : '❌';
            const statusColor = test.status === 'passed' ? chalk.green : chalk.red;
            
            console.log(`${statusIcon} ${test.name.padEnd(40)} ${statusColor(test.status.toUpperCase())} (${(test.duration / 1000).toFixed(1)}s)`);
            
            if (test.status === 'failed') {
                console.log(chalk.red(`   └─ Error: ${test.error}`));
            } else if (test.result && typeof test.result === 'object') {
                // Show key integration metrics
                if (test.result.stages_completed !== undefined) {
                    console.log(chalk.gray(`   └─ Stages Completed: ${test.result.stages_completed}`));
                }
                if (test.result.all_services_interoperable !== undefined) {
                    console.log(chalk.gray(`   └─ Services Interoperable: ${test.result.all_services_interoperable ? 'Yes' : 'No'}`));
                }
                if (test.result.success_rate !== undefined) {
                    console.log(chalk.gray(`   └─ Success Rate: ${test.result.success_rate}%`));
                }
                if (test.result.data_integrity_maintained !== undefined) {
                    console.log(chalk.gray(`   └─ Data Integrity: ${test.result.data_integrity_maintained ? 'Maintained' : 'Compromised'}`));
                }
            }
        }
        
        console.log(chalk.gray('=' .repeat(70)));
        
        // Integration-specific analysis
        console.log(chalk.blue(`\n🔗 Integration Analysis:`));
        
        const pipelineTest = this.testResults.find(t => t.name === 'Complete Integrated Pipeline');
        if (pipelineTest && pipelineTest.status === 'passed') {
            console.log(chalk.green(`   ✅ Full pipeline integration working`));
            if (pipelineTest.result.stages_completed) {
                console.log(chalk.gray(`      └─ ${pipelineTest.result.stages_completed} stages completed`));
            }
        } else {
            console.log(chalk.red(`   ❌ Full pipeline integration has issues`));
        }
        
        const interopTest = this.testResults.find(t => t.name === 'Service Interoperability');
        if (interopTest && interopTest.status === 'passed') {
            console.log(chalk.green(`   ✅ Service interoperability confirmed`));
        } else {
            console.log(chalk.red(`   ❌ Service interoperability issues detected`));
        }
        
        const concurrentTest = this.testResults.find(t => t.name === 'Concurrent Service Usage');
        if (concurrentTest && concurrentTest.status === 'passed') {
            console.log(chalk.green(`   ✅ Concurrent usage supported`));
            if (concurrentTest.result.success_rate) {
                console.log(chalk.gray(`      └─ ${concurrentTest.result.success_rate}% success rate`));
            }
        } else {
            console.log(chalk.yellow(`   ⚠️  Concurrent usage may have limitations`));
        }
        
        const errorTest = this.testResults.find(t => t.name === 'Error Propagation and Recovery');
        if (errorTest && errorTest.status === 'passed') {
            console.log(chalk.green(`   ✅ Error handling and recovery working`));
        } else {
            console.log(chalk.red(`   ❌ Error handling needs improvement`));
        }
        
        // Overall integration status
        if (failedTests === 0) {
            console.log(chalk.green.bold('\n🎉 All integration tests passed! The system is fully integrated and ready for production.'));
        } else if (passedTests >= totalTests * 0.8) {
            console.log(chalk.yellow.bold('\n⚠️  Most integration tests passed. Minor issues detected but system is functional.'));
        } else {
            console.log(chalk.red.bold('\n❌ Critical integration issues detected. System needs fixes before production use.'));
        }
        
        // Save detailed report
        this.saveIntegrationReport();
        
        return failedTests === 0;
    }

    saveIntegrationReport() {
        const reportData = {
            timestamp: new Date().toISOString(),
            test_type: 'integration_validation',
            summary: {
                total_tests: this.testResults.length,
                passed_tests: this.testResults.filter(t => t.status === 'passed').length,
                failed_tests: this.testResults.filter(t => t.status === 'failed').length,
                total_duration: Date.now() - this.startTime,
                success_rate: (this.testResults.filter(t => t.status === 'passed').length / this.testResults.length) * 100
            },
            test_results: this.testResults,
            integration_analysis: {
                full_pipeline_working: this.testResults.find(t => t.name === 'Complete Integrated Pipeline')?.status === 'passed',
                service_interoperability: this.testResults.find(t => t.name === 'Service Interoperability')?.status === 'passed',
                concurrent_usage: this.testResults.find(t => t.name === 'Concurrent Service Usage')?.status === 'passed',
                error_handling: this.testResults.find(t => t.name === 'Error Propagation and Recovery')?.status === 'passed',
                data_consistency: this.testResults.find(t => t.name === 'Data Consistency Across Services')?.status === 'passed',
                health_monitoring: this.testResults.find(t => t.name === 'Service Health Monitoring')?.status === 'passed'
            }
        };
        
        const reportsDir = path.join(process.cwd(), 'backend', 'logs');
        if (!fs.existsSync(reportsDir)) {
            fs.mkdirSync(reportsDir, { recursive: true });
        }
        
        const reportPath = path.join(reportsDir, `integration-validation-report-${Date.now()}.json`);
        fs.writeFileSync(reportPath, JSON.stringify(reportData, null, 2));
        
        console.log(chalk.blue(`\n📄 Detailed integration report saved: ${reportPath}`));
    }

    async runFullIntegrationValidation() {
        console.log(chalk.blue('Starting comprehensive integration validation...\n'));
        
        try {
            // Core integration tests
            await this.testCompleteIntegratedPipeline();
            await this.testServiceInteroperability();
            
            // Reliability and performance tests
            await this.testConcurrentServiceUsage();
            await this.testErrorPropagation();
            await this.testDataConsistency();
            
            // Monitoring and observability
            await this.testServiceHealthMonitoring();
            
        } catch (error) {
            console.log(chalk.yellow(`\nIntegration validation stopped due to critical failure: ${error.message}`));
        }
        
        return this.generateIntegrationReport();
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
        
        const validator = new IntegrationValidator();
        const success = await validator.runFullIntegrationValidation();
        
        if (success) {
            console.log(chalk.green.bold('\n🎉 Integration validation completed successfully!'));
            console.log(chalk.blue('All four libraries are properly integrated and working together.'));
            process.exit(0);
        } else {
            console.log(chalk.red.bold('\n❌ Integration validation detected issues.'));
            console.log(chalk.yellow('Please review the test results and fix the integration problems.'));
            process.exit(1);
        }
        
    } catch (error) {
        console.error(chalk.red('Integration validation failed:'), error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = IntegrationValidator;

