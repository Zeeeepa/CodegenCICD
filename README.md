# 🚀 CodegenCICD Dashboard

**AI-Powered CI/CD Flow Cycle Project Management System**

A comprehensive dashboard for managing AI-powered CI/CD workflows with real-time agent runs, validation pipelines, and automated deployment processes. Built with React, FastAPI, and integrated with Codegen Agent API, grainchain, and web-eval-agent.

![CodegenCICD Dashboard](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![React](https://img.shields.io/badge/React-18+-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

## 🎯 **Overview**

CodegenCICD Dashboard is a complete AI-powered CI/CD management system that automates the entire development workflow from code generation to deployment validation. It integrates multiple AI services and tools to provide a seamless, intelligent development experience.

### **Key Features**

✅ **AI-Powered Agent Runs** - Natural language code generation with Codegen API  
✅ **Real-time Validation Pipeline** - Automated testing with grainchain + web-eval-agent  
✅ **Project Configuration Management** - Repository rules, setup commands, secrets  
✅ **WebSocket Real-time Updates** - Live progress tracking and notifications  
✅ **Auto-merge Validated PRs** - Intelligent PR management and deployment  
✅ **Comprehensive Settings** - 4-tab configuration system for complete control  
✅ **Production-Ready Deployment** - Docker Compose with monitoring and scaling  

## 🏗️ **Architecture**

### **System Components**

```mermaid
graph TB
    A[React Frontend] --> B[FastAPI Backend]
    B --> C[PostgreSQL Database]
    B --> D[Redis Cache]
    B --> E[Celery Workers]
    
    F[Codegen API] --> B
    G[GitHub API] --> B
    H[Gemini API] --> B
    I[Cloudflare Workers] --> B
    
    J[grainchain] --> K[Validation Pipeline]
    L[web-eval-agent] --> K
    K --> B
    
    M[Docker Compose] --> N[Production Deployment]
```

### **Core Services**

| Service | Purpose | Technology |
|---------|---------|------------|
| **Frontend** | React dashboard with Material-UI | React 18, TypeScript, WebSocket |
| **Backend API** | FastAPI server with async support | FastAPI, SQLAlchemy, WebSocket |
| **Database** | PostgreSQL with encrypted secrets | PostgreSQL 15, Encryption |
| **Cache/Queue** | Redis for Celery and sessions | Redis 7, Celery |
| **Validation** | grainchain + web-eval-agent | Docker, Sandboxing |
| **AI Integration** | Codegen, Gemini APIs | HTTP clients, async |

## 🚀 **Quick Start**

### **Prerequisites**

- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.9+ (for local development)

### **1. Clone Repository**

```bash
git clone https://github.com/Zeeeepa/CodegenCICD.git
cd CodegenCICD
```

### **2. Environment Setup**

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys and configuration
nano .env
```

### **3. Deploy with Docker**

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f backend
```

### **4. Access Dashboard**

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Monitoring**: http://localhost:3001 (Grafana)

## 🎮 **Usage Guide**

### **1. Project Management**

#### **Create Project**
1. Click "Create Project" in dashboard
2. Enter project details:
   - Name and description
   - GitHub repository URL
   - Default branch
   - Webhook URL (auto-configured)

#### **Project Configuration**
Each project has a comprehensive settings dialog with 4 tabs:

**🔧 Repository Rules Tab**
- Define coding standards and guidelines
- Visual color indication when configured
- Integrated into all agent runs

**⚙️ Setup Commands Tab**
- Specify deployment commands
- Branch selection dropdown
- Real-time execution with logs
- Run/Save/Test functionality

**🔐 Secrets Tab**
- Encrypted environment variables
- Individual or bulk import modes
- Secure storage with Fernet encryption

**📋 Planning Statement Tab**
- Pre-prompt for agent runs
- Consistent context and guidelines
- Automatic integration with user requests

### **2. AI Agent Workflow**

#### **Starting an Agent Run**
1. Select project from dropdown header
2. Click "Agent Run" button on project card
3. Enter target/goal in dialog
4. Planning statement automatically prepended
5. Real-time progress tracking

#### **Response Types**
The agent returns one of three response types:

**📝 Regular Response**
- Shows agent output
- "Continue" button for additional input
- Resume endpoint integration

**📋 Plan Response**
- Displays proposed plan
- "Confirm" or "Modify" buttons
- Auto-confirm option available

**🔀 PR Response**
- Shows created PR link
- Triggers validation pipeline
- Real-time validation progress

### **3. Validation Pipeline**

The complete 6-step validation process:

#### **Step 1: Snapshot Creation**
- Creates sandbox environment
- Deploys grainchain + web-eval-agent
- Configures required environment variables

#### **Step 2: Code Clone**
- Clones PR branch to sandbox
- Validates repository access
- Prepares workspace

#### **Step 3: Deployment**
- Executes setup commands
- Applies environment variables
- Real-time deployment logs

#### **Step 4: Deployment Validation**
- Uses Gemini API for validation
- Analyzes deployment success
- Provides validation score

#### **Step 5: UI Testing**
- Runs comprehensive web-eval-agent tests
- Tests all flows and components
- Provides detailed test results

#### **Step 6: Auto-merge**
- Checks auto-merge settings
- Merges PR if validation passes
- Sends completion notifications

### **4. Error Handling & Retry Logic**

#### **Automatic Error Recovery**
- Failed steps trigger retry mechanism
- Error context sent to Codegen API
- Automatic PR updates with fixes
- Maximum 3 retries per step

#### **Error Context Integration**
- Deployment errors → Gemini analysis → Codegen fix
- UI test failures → web-eval-agent logs → Codegen fix
- Real-time error reporting via WebSocket

## 🔧 **Configuration**

### **Environment Variables**

#### **Required Configuration**
```bash
# Codegen API
CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=sk-your-token

# GitHub Integration
GITHUB_TOKEN=github_pat_your-token

# Gemini API (for validation)
GEMINI_API_KEY=AIzaSy-your-key

# Database
POSTGRES_PASSWORD=secure-password
DATABASE_URL=postgresql://postgres:password@localhost:5432/codegencd

# Security
SECRET_KEY=your-secret-key-min-32-chars
ENCRYPTION_KEY=base64-encoded-32-bytes
ENCRYPTION_SALT=your-encryption-salt
```

#### **Optional Configuration**
```bash
# Cloudflare (for webhooks)
CLOUDFLARE_API_KEY=your-api-key
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_WORKER_URL=https://your-worker.workers.dev

# Monitoring
GRAFANA_PASSWORD=admin

# Validation Pipeline
MAX_CONCURRENT_VALIDATIONS=5
VALIDATION_TIMEOUT=1800
MAX_VALIDATION_RETRIES=3
```

### **Project Settings**

Each project supports comprehensive configuration:

#### **Auto-confirm Plan Checkbox**
- Automatically confirms proposed plans
- Skips manual confirmation step
- Speeds up development workflow

#### **Auto-merge Validated PR Checkbox**
- Automatically merges PRs after successful validation
- Only merges if all validation steps pass
- Configurable per project

#### **Repository Rules**
- Custom coding standards
- Project-specific guidelines
- Visual indication on project card

#### **Setup Commands**
- Deployment command sequences
- Branch-specific configurations
- Real-time execution logs

#### **Secrets Management**
- Encrypted environment variables
- Individual or bulk import
- Secure Fernet encryption

## 🐳 **Deployment**

### **Development Deployment**

```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### **Production Deployment**

```bash
# Use production profile
docker-compose --profile production up -d

# Include monitoring
docker-compose --profile production --profile monitoring up -d

# SSL configuration
# Edit nginx/nginx.conf for SSL settings
# Place certificates in nginx/ssl/
```

### **Scaling**

```bash
# Scale backend workers
docker-compose up -d --scale celery_worker=4

# Scale validation pipeline
# Edit MAX_CONCURRENT_VALIDATIONS in .env
```

## 📊 **Monitoring**

### **Health Checks**

All services include comprehensive health checks:

- **Backend**: `/health` endpoint
- **Database**: PostgreSQL connection test
- **Redis**: Ping command
- **Frontend**: HTTP response check

### **Metrics & Logging**

#### **Prometheus Metrics**
- API request rates and latencies
- Validation pipeline success rates
- Database connection pool status
- WebSocket connection counts

#### **Grafana Dashboards**
- Real-time system metrics
- Validation pipeline analytics
- Error rate monitoring
- Performance tracking

### **Log Aggregation**

```bash
# View all logs
docker-compose logs -f

# Service-specific logs
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Follow validation logs
docker-compose logs -f backend | grep validation
```

## 🔒 **Security**

### **Data Protection**

#### **Encryption**
- Secrets encrypted with Fernet (AES 128)
- PBKDF2 key derivation
- Base64 encoding for storage

#### **Authentication**
- JWT-based API authentication
- API key support for service integration
- Environment-based configuration

#### **Network Security**
- Docker network isolation
- CORS configuration
- Rate limiting on API endpoints

### **Best Practices**

#### **Environment Variables**
- Never commit `.env` files
- Use strong, unique passwords
- Rotate API keys regularly

#### **Database Security**
- Encrypted connections
- Regular backups
- Access control

## 🧪 **Testing**

### **Running Tests**

```bash
# Backend tests
cd backend
python -m pytest tests/

# Frontend tests
cd frontend
npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### **End-to-End Testing with Web-Eval-Agent**

The system includes comprehensive E2E testing:

```bash
# Run complete flow test
python tests/test_complete_flow.py

# Test validation pipeline
python tests/test_validation_pipeline.py

# Test web-eval-agent integration
python tests/test_web_eval_integration.py
```

## 🤝 **Contributing**

### **Development Setup**

```bash
# Clone repository
git clone https://github.com/Zeeeepa/CodegenCICD.git
cd CodegenCICD

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
npm start

# Database setup
docker-compose up -d postgres redis
python backend/database.py  # Create tables
```

### **Code Style**

#### **Backend (Python)**
- Black code formatting
- isort import sorting
- flake8 linting
- Type hints required

#### **Frontend (TypeScript)**
- Prettier code formatting
- ESLint linting
- Strict TypeScript configuration
- Material-UI design system

### **Pull Request Process**

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Run linting and tests
5. Submit pull request
6. Code review process
7. Merge after approval

## 📚 **API Documentation**

### **REST API Endpoints**

#### **Projects**
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

#### **Configurations**
- `GET /api/configurations/{project_id}` - Get project configuration
- `PUT /api/configurations/{project_id}` - Update configuration
- `POST /api/configurations/{project_id}/secrets` - Create secret
- `DELETE /api/configurations/{project_id}/secrets/{id}` - Delete secret

#### **Agent Runs**
- `POST /api/agent-runs` - Start agent run
- `GET /api/agent-runs/{id}` - Get agent run status
- `POST /api/agent-runs/{id}/resume` - Resume agent run

#### **Validation**
- `POST /api/validation/start` - Start validation pipeline
- `GET /api/validation/{id}` - Get validation status
- `GET /api/validation/{id}/logs` - Get validation logs

### **WebSocket Events**

#### **Client → Server**
```javascript
// Subscribe to project updates
{
  "type": "subscribe_project",
  "project_id": "uuid"
}

// Heartbeat
{
  "type": "ping",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### **Server → Client**
```javascript
// Agent run update
{
  "type": "agent_run_update",
  "project_id": "uuid",
  "agent_run_id": "uuid",
  "status": "running",
  "data": {...}
}

// Validation update
{
  "type": "validation_update",
  "project_id": "uuid",
  "step_index": 2,
  "step": {...},
  "overall_status": "running"
}

// PR notification
{
  "type": "pr_notification",
  "project_id": "uuid",
  "pr_url": "https://github.com/user/repo/pull/123",
  "action": "created"
}
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Database Connection Errors**
```bash
# Check PostgreSQL status
docker-compose ps postgres

# View database logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

#### **WebSocket Connection Issues**
```bash
# Check backend logs
docker-compose logs backend | grep websocket

# Test WebSocket endpoint
wscat -c ws://localhost:8000/ws/test-client
```

#### **Validation Pipeline Failures**
```bash
# Check validation logs
docker-compose logs backend | grep validation

# Check grainchain integration
docker ps | grep grainchain

# Check web-eval-agent status
docker-compose logs celery_worker | grep web-eval
```

### **Performance Optimization**

#### **Database Optimization**
- Add indexes for frequently queried fields
- Use connection pooling
- Regular VACUUM and ANALYZE

#### **Redis Optimization**
- Configure memory limits
- Use appropriate data structures
- Monitor memory usage

#### **Frontend Optimization**
- Enable code splitting
- Optimize bundle size
- Use service workers for caching

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **Codegen API** - AI-powered code generation
- **grainchain** - Sandboxing and snapshotting
- **web-eval-agent** - UI testing and interaction
- **graph-sitter** - Code quality analysis
- **Material-UI** - React component library
- **FastAPI** - Modern Python web framework

## 📞 **Support**

- **Documentation**: [GitHub Wiki](https://github.com/Zeeeepa/CodegenCICD/wiki)
- **Issues**: [GitHub Issues](https://github.com/Zeeeepa/CodegenCICD/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Zeeeepa/CodegenCICD/discussions)

---

**Built with ❤️ by the CodegenCICD Team**
