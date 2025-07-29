# CodegenCICD - AI-Powered GitHub Project Management Dashboard

A comprehensive UI dashboard for managing GitHub projects with AI-powered automation, featuring real-time validation, webhook integration, and automated PR management.

## 🚀 **Overview**

CodegenCICD provides a complete solution for AI-driven software development automation. It integrates multiple cutting-edge technologies to create a seamless workflow from project selection to validated PR deployment.

## 🏗️ **Architecture**

### **Core Components**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │   PostgreSQL    │
│   Dashboard     │◄──►│   Backend       │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub API    │    │   Codegen API   │    │   Cloudflare    │
│   Integration   │    │   Agent Runs    │    │   Webhooks      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Technology Stack**

#### **1. Codegen SDK** - Agent Coordination & Code Generation
- **Purpose**: Core AI-powered code generation and agent coordination
- **API**: https://docs.codegen.com/api-reference/agents/create-agent-run
- **Environment Variables**: `CODEGEN_ORG_ID`, `CODEGEN_API_TOKEN`

#### **2. Graph-Sitter** - Static Analysis & Code Quality
- **Repository**: [zeeeepa/graph-sitter](https://github.com/zeeeepa/graph-sitter)
- **Purpose**: Code quality metrics and static analysis
- **Integration**: Pre-deployed for validation workflows

#### **3. Grainchain** - Sandboxing & Snapshot Creation
- **Repository**: [zeeeepa/grainchain](https://github.com/zeeeepa/grainchain)
- **Purpose**: Secure sandbox environments and PR validation deployments
- **Features**: Snapshot creation, isolated execution, deployment validation

#### **4. Web-Eval-Agent** - UI Testing & Browser Automation
- **Repository**: [zeeeepa/web-eval-agent](https://github.com/zeeeepa/web-eval-agent)
- **Purpose**: Automated UI testing and browser-based validation
- **Environment Variables**: `GEMINI_API_KEY`

### **Services**

#### **1. GitHub Client** - Repository Management
- **Purpose**: Retrieve project lists, manage branches, set webhook URLs
- **Features**: Live event notifications when PRs are created on pinned projects
- **Environment Variables**: `GITHUB_TOKEN`

#### **2. Cloudflare Worker** - Webhook Gateway
- **Purpose**: Online accessibility and webhook processing
- **Features**: Real-time PR notifications, secure webhook handling
- **Environment Variables**: `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_WORKER_URL`

## 🎯 **Features**

### **GitHub Project Management**
- **Project Selector**: Dropdown listing all user repositories
- **Project Cards**: Visual dashboard with webhook status, agent run buttons, and settings
- **Real-time Updates**: Live status updates and PR notifications
- **Webhook Integration**: Automatic setup of GitHub webhooks for PR events

### **AI Agent Runs**
- **Target Input**: Natural language goal specification
- **Planning Statements**: Customizable pre-prompts for agent context
- **Auto-confirm Plans**: Optional automatic plan confirmation
- **Progress Tracking**: Real-time monitoring of agent execution
- **PR Integration**: Automatic PR creation and tracking

### **Project Configuration**
- **Repository Rules**: Custom rules for agent behavior
- **Setup Commands**: Sandbox environment preparation scripts
- **Secrets Management**: Encrypted storage of environment variables
- **Branch Selection**: Configurable target branches for operations

### **Validation Flow**
- **Automated Testing**: Web-eval-agent integration for UI validation
- **Deployment Validation**: Grainchain-powered sandbox testing
- **Error Recovery**: Automatic retry loops with context preservation
- **Auto-merge**: Validated PR automatic merging

## 🚀 **Usage**

### **1. Project Setup**

1. **Add GitHub Project**:
   - Click "Add Project" in the dashboard header
   - Select from your GitHub repositories
   - Project card appears with webhook automatically configured

2. **Configure Project Settings**:
   - Click the settings gear icon on any project card
   - Configure across four tabs:
     - **Planning**: Set custom planning statements for agent context
     - **Repository Rules**: Define specific rules for the agent to follow
     - **Setup Commands**: Specify sandbox environment setup commands
     - **Secrets**: Add encrypted environment variables

### **2. Running AI Agents**

1. **Start Agent Run**:
   - Click "Agent Run" button on project card
   - Enter your target/goal in natural language
   - Optionally enable "Auto Confirm Proposed Plans"
   - Click "Start Agent Run"

2. **Monitor Progress**:
   - Real-time progress updates on project card
   - View detailed logs and responses
   - PR notifications appear when code is generated

### **3. Validation & Deployment**

1. **Automatic Validation**:
   - When PR is created, validation flow triggers automatically
   - Grainchain creates sandbox snapshot
   - Repository is cloned and deployment commands executed
   - Web-eval-agent tests all UI components and flows

2. **Error Handling**:
   - Failed validations send error context back to agent
   - Automatic retry loops until success or maximum attempts
   - All error contexts preserved for debugging

3. **Auto-merge**:
   - Enable "Auto-merge validated PR" checkbox on project cards
   - Successfully validated PRs merge automatically
   - Manual review option always available

## 🔧 **Configuration**

### **Environment Variables**

Create a `.env` file with the following variables:

```bash
# Codegen API
CODEGEN_ORG_ID=your-org-id
CODEGEN_API_TOKEN=your-api-token

# GitHub Integration
GITHUB_TOKEN=your-github-token

# Cloudflare Webhooks
CLOUDFLARE_API_KEY=your-cloudflare-api-key
CLOUDFLARE_ACCOUNT_ID=your-cloudflare-account-id
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=https://your-worker.your-domain.workers.dev

# Web-Eval-Agent
GEMINI_API_KEY=your-gemini-api-key

# Database
DATABASE_URL=postgresql://user:password@localhost/codegencd

# Security
SECRETS_ENCRYPTION_KEY=your-encryption-key-here
```

### **Development Mode**

The application runs in development mode by default with:
- Verbose logging enabled
- Debug information displayed
- Hot reloading for frontend changes
- Comprehensive error reporting

## 📋 **Workflow Example**

### **Complete Development Cycle**

1. **Project Selection**:
   ```
   User selects "my-web-app" from GitHub dropdown
   → Webhook automatically configured
   → Project card appears on dashboard
   ```

2. **Configuration**:
   ```
   User opens project settings
   → Sets planning statement: "You are a React expert..."
   → Adds repository rules: "Always write TypeScript"
   → Configures setup commands: "npm install && npm run build"
   → Adds secrets: API keys and database URLs
   ```

3. **Agent Run**:
   ```
   User clicks "Agent Run"
   → Enters target: "Add user authentication with JWT"
   → Agent analyzes request with project context
   → Creates implementation plan
   → Generates code and creates PR
   ```

4. **Validation Flow**:
   ```
   PR created → Webhook notification received
   → Grainchain creates sandbox snapshot
   → Repository cloned and setup commands executed
   → Deployment validated with health checks
   → Web-eval-agent tests all UI flows
   → If successful: Auto-merge (if enabled)
   → If failed: Error context sent back to agent
   ```

5. **Completion**:
   ```
   Validated PR merged to main branch
   → Project statistics updated
   → Success rate calculated
   → Ready for next agent run
   ```

## 🔒 **Security**

### **Data Protection**
- **Encrypted Secrets**: All environment variables encrypted with Fernet
- **Webhook Verification**: GitHub webhook signatures validated
- **Secure API Communication**: All API calls use HTTPS with proper authentication
- **Sandboxed Execution**: All code execution happens in isolated environments

### **Access Control**
- **GitHub Integration**: Uses personal access tokens with minimal required permissions
- **API Rate Limiting**: Built-in rate limiting to prevent abuse
- **Environment Isolation**: Development and production environments completely separated

## 🧪 **Testing**

### **Automated Testing with Web-Eval-Agent**

All components are tested using web-eval-agent with Gemini API:

```bash
# Run comprehensive UI tests
python -m web_eval_agent test --config tests/ui_test_config.json

# Test specific workflows
python -m web_eval_agent test --workflow "project_creation"
python -m web_eval_agent test --workflow "agent_run_execution"
python -m web_eval_agent test --workflow "validation_flow"
```

### **Test Coverage**
- **UI Components**: All React components tested for functionality
- **API Endpoints**: Complete backend API test coverage
- **Integration Tests**: End-to-end workflow validation
- **Security Tests**: Authentication and authorization validation

## 📚 **API Reference**

### **Projects API**
- `GET /api/projects/github-repositories` - List GitHub repositories
- `GET /api/projects/dashboard` - Get dashboard projects
- `POST /api/projects/add` - Add project to dashboard
- `DELETE /api/projects/{id}` - Remove project
- `GET /api/projects/{id}/settings` - Get project settings
- `PUT /api/projects/{id}/settings` - Update project settings

### **Agent Runs API**
- `POST /api/agent-runs/` - Create new agent run
- `GET /api/agent-runs/{id}` - Get agent run details
- `POST /api/agent-runs/{id}/continue` - Continue agent run
- `POST /api/agent-runs/{id}/confirm-plan` - Confirm agent plan
- `POST /api/agent-runs/{id}/cancel` - Cancel agent run

## 🚀 **Deployment**

### **Development**
```bash
# Backend
cd backend
pip install -r requirements.txt
python api.py

# Frontend
cd frontend
npm install
npm run dev
```

### **Production**
```bash
# Build frontend
cd frontend
npm run build

# Deploy backend
cd backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api:app
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests with web-eval-agent
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 **Support**

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation for common solutions
- Review the test suite for usage examples

---

**Built with ❤️ for AI-powered development automation**

