# CodegenCICD Dashboard

A comprehensive AI-powered CI/CD dashboard that integrates multiple services for automated code generation, validation, and deployment workflows.

## 🚀 Overview

CodegenCICD Dashboard is a modern web application that streamlines the development workflow by integrating GitHub projects with AI-powered code generation, automated validation, and comprehensive testing. The system provides a unified interface for managing projects, running AI agents, and validating changes through a sophisticated pipeline.

## 🏗️ Architecture

### Core Components

1. **Frontend Dashboard** - React-based UI with Material-UI components
2. **Backend API** - FastAPI-based REST API with async support
3. **Database** - SQLAlchemy with PostgreSQL for persistent storage
4. **Webhook System** - Cloudflare Workers for GitHub webhook handling
5. **Validation Pipeline** - Multi-service validation with automated testing

### Service Integration Stack

#### 1. Codegen SDK - Agent Coordination & Code Generation
- **Purpose**: Core agentic prompt-based NLP requests for code generation
- **API**: https://docs.codegen.com/api-reference/agents/create-agent-run
- **Environment Variables**:
  ```bash
  CODEGEN_ORG_ID=your-org-id
  CODEGEN_API_TOKEN=your-api-token
  ```

#### 2. Graph-Sitter - Static Analysis & Code Quality
- **Purpose**: Static analysis and code quality metrics
- **Repository**: https://github.com/zeeeepa/graph-sitter
- **Features**: AST parsing, complexity analysis, security scanning

#### 3. Grainchain - Sandboxing & Snapshot Management
- **Purpose**: Sandboxing, snapshot creation, and PR validation deployments
- **Repository**: https://github.com/zeeeepa/grainchain
- **Features**: Container management, environment isolation, deployment testing

#### 4. Web-Eval-Agent - UI Testing & Browser Automation
- **Purpose**: UI testing and browser automation for validation
- **Repository**: https://github.com/zeeeepa/web-eval-agent
- **Environment Variables**:
  ```bash
  GEMINI_API_KEY=your-gemini-api-key
  ```

### External Services

#### 1. GitHub Integration
- **Purpose**: Repository management, webhook handling, PR operations
- **Environment Variables**:
  ```bash
  GITHUB_TOKEN=your-github-token
  ```

#### 2. Cloudflare Workers
- **Purpose**: Online accessibility and webhook gateway
- **Environment Variables**:
  ```bash
  CLOUDFLARE_API_KEY=your-cloudflare-api-key
  CLOUDFLARE_ACCOUNT_ID=your-account-id
  CLOUDFLARE_WORKER_NAME=webhook-gateway
  CLOUDFLARE_WORKER_URL=your-worker-url
  ```

## 🎯 Key Features

### Project Management
- **GitHub Project Selector**: Dropdown interface for selecting and pinning GitHub repositories
- **Project Cards**: Visual representation of pinned projects with status indicators
- **Persistent Storage**: All project configurations survive application restarts
- **Webhook Integration**: Automatic webhook setup for real-time PR notifications

### Agent Run System
- **Target Text Input**: Natural language interface for describing tasks
- **Planning Statements**: Configurable pre-prompts for consistent agent behavior
- **Response Types**: Support for regular, plan, and PR response types
- **Continue Functionality**: Ability to continue conversations with agents
- **Auto-Confirm Plans**: Optional automatic plan confirmation

### Project Configuration
- **Repository Rules**: Custom rules and guidelines for specific repositories
- **Setup Commands**: Configurable deployment and setup command sequences
- **Secrets Management**: Secure environment variable storage and management
- **Branch Selection**: Support for different branches in setup commands

### Validation Pipeline
1. **Snapshot Creation**: Grainchain-based environment snapshots
2. **Codebase Cloning**: Automatic PR branch cloning
3. **Deployment Testing**: Execution of setup commands with validation
4. **UI Testing**: Web-Eval-Agent comprehensive testing
5. **Error Recovery**: Automatic error detection and fix attempts
6. **Auto-Merge**: Optional automatic merging of validated PRs

### Real-time Features
- **WebSocket Notifications**: Live updates for agent runs and validations
- **Progress Tracking**: Real-time progress indicators for long-running operations
- **Status Indicators**: Visual feedback for all system components

## 🛠️ Installation & Setup

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.9+
- PostgreSQL database
- Docker (for service deployment)

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Core Application
NODE_ENV=development
BACKEND_HOST=localhost
FRONTEND_HOST=localhost

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/codegencd

# Codegen API
CODEGEN_ORG_ID=your-org-id
CODEGEN_API_TOKEN=your-api-token

# GitHub Integration
GITHUB_TOKEN=your-github-token

# Cloudflare Workers
CLOUDFLARE_API_KEY=your-cloudflare-api-key
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=your-worker-url

# AI Services
GEMINI_API_KEY=your-gemini-api-key

# Service URLs (when deployed)
GRAINCHAIN_URL=http://localhost:8001
GRAPH_SITTER_URL=http://localhost:8002
WEB_EVAL_AGENT_URL=http://localhost:8003
```

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm start
```

### Service Deployment

Deploy the required services using Docker:

```bash
# Deploy Grainchain
docker run -d --name grainchain -p 8001:8000 zeeeepa/grainchain

# Deploy Graph-Sitter
docker run -d --name graph-sitter -p 8002:8000 zeeeepa/graph-sitter

# Deploy Web-Eval-Agent
docker run -d --name web-eval-agent -p 8003:8000 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  zeeeepa/web-eval-agent
```

## 📖 Usage Guide

### 1. Project Setup

1. **Access Dashboard**: Navigate to `http://localhost:3000`
2. **Select Project**: Click "Select Project" in the header dropdown
3. **Choose Repository**: Select a GitHub repository from the list
4. **Automatic Configuration**: Webhook URL is automatically set to Cloudflare worker

### 2. Project Configuration

1. **Open Settings**: Click the gear icon on any project card
2. **Configure Tabs**:
   - **General**: Auto-confirm plans, auto-merge settings
   - **Planning Statement**: Default prompt text for all agent runs
   - **Repository Rules**: Custom rules for the specific repository
   - **Setup Commands**: Deployment and setup command sequences
   - **Secrets**: Environment variables and sensitive configuration

### 3. Running Agents

1. **Start Agent Run**: Click the "Run" button on a project card
2. **Enter Target**: Describe what you want the agent to accomplish
3. **Monitor Progress**: Watch real-time progress and logs
4. **Handle Responses**:
   - **Regular**: Use "Continue" to add more instructions
   - **Plan**: Choose "Confirm" or "Modify" the proposed plan
   - **PR**: View the created PR and trigger validation

### 4. Validation Flow

When a PR is created:

1. **Automatic Trigger**: Validation starts automatically
2. **Snapshot Creation**: Grainchain creates isolated environment
3. **Codebase Cloning**: PR branch is cloned to sandbox
4. **Deployment Testing**: Setup commands are executed
5. **UI Testing**: Web-Eval-Agent runs comprehensive tests
6. **Error Handling**: Automatic error detection and fix attempts
7. **Results**: Merge option or GitHub link provided

### 5. Webhook Notifications

- **Real-time Updates**: Receive notifications for PR events
- **Status Changes**: Visual indicators update automatically
- **Progress Tracking**: Monitor long-running operations

## 🔧 API Reference

### Project Management

```bash
# List GitHub repositories
GET /api/projects/github-repos

# Create/pin project
POST /api/projects
{
  "github_id": 123456,
  "name": "my-project",
  "full_name": "owner/repo",
  "github_owner": "owner",
  "github_repo": "repo",
  "github_url": "https://github.com/owner/repo"
}

# Update project settings
PUT /api/projects/{project_id}
{
  "auto_confirm_plans": true,
  "planning_statement": "Custom planning text",
  "repository_rules": "Follow coding standards"
}

# Delete/unpin project
DELETE /api/projects/{project_id}
```

### Agent Runs

```bash
# Start agent run
POST /api/projects/{project_id}/agent-runs
{
  "target_text": "Create a login form with validation"
}

# Continue agent run
POST /api/projects/{project_id}/agent-runs/{run_id}/continue
{
  "message": "Add password strength validation"
}

# Get agent run status
GET /api/projects/{project_id}/agent-runs/{run_id}
```

### Secrets Management

```bash
# List project secrets
GET /api/projects/{project_id}/secrets

# Create/update secret
POST /api/projects/{project_id}/secrets
{
  "key": "API_KEY",
  "value": "secret-value"
}

# Delete secret
DELETE /api/projects/{project_id}/secrets/{secret_id}
```

## 🧪 Testing

### Automated Testing with Web-Eval-Agent

The system automatically tests all new components using Web-Eval-Agent:

```bash
# Manual testing trigger
curl -X POST http://localhost:8003/api/test/comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://localhost:3000",
    "gemini_api_key": "your-gemini-api-key"
  }'
```

### Test Coverage

- **Homepage Functionality**: Load times, element presence, error checking
- **Navigation Testing**: Link functionality, routing, back button
- **Form Validation**: Input validation, submission handling
- **Responsive Design**: Mobile, tablet, desktop compatibility
- **Accessibility**: WCAG compliance, keyboard navigation
- **Performance**: Core Web Vitals, Lighthouse scores

## 🔒 Security

### Authentication & Authorization
- GitHub token-based authentication
- Webhook signature verification
- Environment variable encryption
- API rate limiting

### Data Protection
- Secrets are encrypted at rest
- Sensitive data is masked in logs
- HTTPS enforcement in production
- CORS configuration for API access

## 🚀 Deployment

### Production Environment

```bash
# Build frontend
cd frontend && npm run build

# Deploy backend
cd backend && gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Deploy services
docker-compose up -d
```

### Cloudflare Worker Deployment

The webhook gateway is automatically deployed to Cloudflare Workers:

```javascript
// Automatic deployment via API
POST /api/webhooks/cloudflare/deploy
```

## 📊 Monitoring & Observability

### Health Checks
- Service health monitoring
- Database connection status
- External service availability
- Real-time status indicators

### Logging
- Structured logging with context
- Error tracking and alerting
- Performance metrics
- Audit trails for all operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation for common solutions
- Review the API reference for integration details

## 🔄 Changelog

### v1.0.0
- Initial release with full dashboard functionality
- GitHub integration and webhook support
- Agent run system with multiple response types
- Comprehensive validation pipeline
- Real-time notifications and progress tracking
- Multi-service integration (Codegen, Graph-Sitter, Grainchain, Web-Eval-Agent)

---

**Built with ❤️ for developers who want AI-powered CI/CD workflows**
