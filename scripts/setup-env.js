#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const inquirer = require('inquirer');
const chalk = require('chalk');
const ora = require('ora');

console.log(chalk.blue.bold('🚀 CodegenCICD Environment Setup'));
console.log(chalk.gray('Setting up environment configuration for integrated libraries\n'));

const ENV_TEMPLATE = `# CodegenCICD Integrated Environment Configuration
# Generated on ${new Date().toISOString()}

# ===========================================
# CORE APPLICATION SETTINGS
# ===========================================
ENVIRONMENT=development
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=true
LOG_LEVEL=info

# ===========================================
# DATABASE CONFIGURATION
# ===========================================
DATABASE_URL=sqlite:///./codegenapp.db
# For PostgreSQL: postgresql://username:password@localhost:5432/codegendb
REDIS_URL=redis://localhost:6379/0

# ===========================================
# CODEGEN API INTEGRATION (REQUIRED)
# ===========================================
CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99
CODEGEN_API_HOST=https://api.codegen.com

# ===========================================
# EXTERNAL API KEYS (REQUIRED FOR FULL FUNCTIONALITY)
# ===========================================
# Google Gemini API for Web-eval-agent
GEMINI_API_KEY=AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0

# GitHub API for Graph-sitter integration
GITHUB_TOKEN=your-github-token-here

# ===========================================
# CLOUDFLARE CONFIGURATION (OPTIONAL)
# ===========================================
CLOUDFLARE_API_KEY=eae82cf159577a8838cc83612104c09c5a0d6
CLOUDFLARE_ACCOUNT_ID=2b2a1d3effa7f7fe4fe2a8c4e48681e3
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=https://webhook-gateway.pixeliumperfecto.workers.dev

# ===========================================
# SANDBOX PROVIDERS (OPTIONAL)
# ===========================================
# Default provider for Grainchain
GRAINCHAIN_DEFAULT_PROVIDER=local

# E2B Sandbox API (optional)
E2B_API_KEY=your-e2b-api-key-here

# Daytona API (optional)
DAYTONA_API_KEY=your-daytona-api-key-here

# Morph API (optional)
MORPH_API_KEY=your-morph-api-key-here

# ===========================================
# SECURITY SETTINGS
# ===========================================
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS settings
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20

# ===========================================
# MONITORING AND OBSERVABILITY (OPTIONAL)
# ===========================================
PROMETHEUS_ENABLED=true
METRICS_ENABLED=true
STRUCTURED_LOGGING=true

# ===========================================
# DEVELOPMENT SETTINGS
# ===========================================
# Frontend development server
FRONTEND_PORT=3000
FRONTEND_HOST=localhost

# Backend development server
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0

# Hot reload settings
RELOAD_ON_CHANGE=true
WATCH_FILES=true
`;

async function setupEnvironment() {
    const spinner = ora('Setting up environment...').start();
    
    try {
        // Check if .env already exists
        const envPath = path.join(process.cwd(), '.env');
        const envExists = fs.existsSync(envPath);
        
        if (envExists) {
            spinner.stop();
            const { overwrite } = await inquirer.prompt([
                {
                    type: 'confirm',
                    name: 'overwrite',
                    message: '.env file already exists. Overwrite?',
                    default: false
                }
            ]);
            
            if (!overwrite) {
                console.log(chalk.yellow('Environment setup skipped.'));
                return;
            }
            spinner.start('Overwriting environment file...');
        }
        
        // Write environment file
        fs.writeFileSync(envPath, ENV_TEMPLATE);
        spinner.succeed('Environment file created successfully!');
        
        // Create logs directory
        const logsDir = path.join(process.cwd(), 'backend', 'logs');
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
            console.log(chalk.green('✓ Created logs directory'));
        }
        
        // Create data directory
        const dataDir = path.join(process.cwd(), 'backend', 'data');
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
            console.log(chalk.green('✓ Created data directory'));
        }
        
        console.log(chalk.blue('\n📝 Environment Configuration:'));
        console.log(chalk.gray('• .env file created with default configuration'));
        console.log(chalk.gray('• Update API keys in .env for full functionality'));
        console.log(chalk.gray('• Logs directory: backend/logs/'));
        console.log(chalk.gray('• Data directory: backend/data/'));
        
        console.log(chalk.yellow('\n⚠️  Important:'));
        console.log(chalk.gray('• Update CODEGEN_API_TOKEN with your actual token'));
        console.log(chalk.gray('• Update GEMINI_API_KEY for web-eval-agent functionality'));
        console.log(chalk.gray('• Update GITHUB_TOKEN for graph-sitter integration'));
        console.log(chalk.gray('• Change SECRET_KEY and JWT_SECRET_KEY for production'));
        
    } catch (error) {
        spinner.fail('Environment setup failed');
        console.error(chalk.red('Error:'), error.message);
        process.exit(1);
    }
}

// Interactive setup for API keys
async function interactiveSetup() {
    console.log(chalk.blue('\n🔧 Interactive API Key Setup'));
    console.log(chalk.gray('Configure your API keys for full functionality\n'));
    
    const questions = [
        {
            type: 'input',
            name: 'codegenToken',
            message: 'Codegen API Token (required):',
            default: 'sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99',
            validate: input => input.length > 0 || 'Codegen API token is required'
        },
        {
            type: 'input',
            name: 'geminiKey',
            message: 'Google Gemini API Key (for web-eval-agent):',
            default: 'AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0'
        },
        {
            type: 'input',
            name: 'githubToken',
            message: 'GitHub Token (for graph-sitter):',
            default: 'your-github-token-here'
        },
        {
            type: 'confirm',
            name: 'setupOptional',
            message: 'Configure optional sandbox providers (E2B, Daytona, Morph)?',
            default: false
        }
    ];
    
    const answers = await inquirer.prompt(questions);
    
    // Update .env file with provided values
    const envPath = path.join(process.cwd(), '.env');
    let envContent = fs.readFileSync(envPath, 'utf8');
    
    envContent = envContent.replace(/CODEGEN_API_TOKEN=.*/, `CODEGEN_API_TOKEN=${answers.codegenToken}`);
    envContent = envContent.replace(/GEMINI_API_KEY=.*/, `GEMINI_API_KEY=${answers.geminiKey}`);
    envContent = envContent.replace(/GITHUB_TOKEN=.*/, `GITHUB_TOKEN=${answers.githubToken}`);
    
    if (answers.setupOptional) {
        const optionalQuestions = [
            {
                type: 'input',
                name: 'e2bKey',
                message: 'E2B API Key (optional):'
            },
            {
                type: 'input',
                name: 'daytonaKey',
                message: 'Daytona API Key (optional):'
            },
            {
                type: 'input',
                name: 'morphKey',
                message: 'Morph API Key (optional):'
            }
        ];
        
        const optionalAnswers = await inquirer.prompt(optionalQuestions);
        
        if (optionalAnswers.e2bKey) {
            envContent = envContent.replace(/E2B_API_KEY=.*/, `E2B_API_KEY=${optionalAnswers.e2bKey}`);
        }
        if (optionalAnswers.daytonaKey) {
            envContent = envContent.replace(/DAYTONA_API_KEY=.*/, `DAYTONA_API_KEY=${optionalAnswers.daytonaKey}`);
        }
        if (optionalAnswers.morphKey) {
            envContent = envContent.replace(/MORPH_API_KEY=.*/, `MORPH_API_KEY=${optionalAnswers.morphKey}`);
        }
    }
    
    fs.writeFileSync(envPath, envContent);
    console.log(chalk.green('\n✓ API keys configured successfully!'));
}

async function main() {
    try {
        await setupEnvironment();
        
        const { interactive } = await inquirer.prompt([
            {
                type: 'confirm',
                name: 'interactive',
                message: 'Would you like to configure API keys interactively?',
                default: true
            }
        ]);
        
        if (interactive) {
            await interactiveSetup();
        }
        
        console.log(chalk.green.bold('\n🎉 Environment setup complete!'));
        console.log(chalk.blue('Next steps:'));
        console.log(chalk.gray('1. npm run install:all  # Install all dependencies'));
        console.log(chalk.gray('2. npm run dev          # Start development servers'));
        console.log(chalk.gray('3. npm run test         # Run tests'));
        console.log(chalk.gray('4. npm run validate     # Validate integration'));
        
    } catch (error) {
        console.error(chalk.red('Setup failed:'), error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { setupEnvironment, interactiveSetup };
