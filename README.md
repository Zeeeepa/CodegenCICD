# CodegenCICD Dashboard

🚀 **AI-Powered CI/CD Flow Cycle Project Management System**

A comprehensive dashboard for managing AI-powered CI/CD workflows with Codegen Agent API integration. This system allows users to input requirements, start agent runs, view real-time feedback, and track progress until requirements are fulfilled.

![CodegenCICD Dashboard](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![React](https://img.shields.io/badge/React-18.2.0-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-4.9.5-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)
![Material-UI](https://img.shields.io/badge/Material--UI-5.14.20-purple)

## 🎯 **Core Features**

### **Complete CI/CD Flow Cycle**
- **Requirements Input** → **Agent Execution** → **Real-time Feedback** → **Iterative Fulfillment**
- Interactive project management with GitHub integration
- Real-time WebSocket updates for live progress tracking
- Comprehensive validation pipeline with auto-merge capabilities

### **Project Management**
- 📊 **Project Cards**: Interactive cards with status indicators and Agent Run buttons
- ⚙️ **Settings Dialogs**: Repository rules, setup commands, and secrets management
- 🔄 **Auto-merge**: Automatic merging of validated pull requests
- ✅ **Auto-confirm**: Automatic confirmation of proposed plans

### **Agent Run Management**
- 🤖 **Agent Run Dialog**: Complete interface for starting and monitoring agent runs
- 📈 **Progress Tracker**: Real-time execution monitoring with detailed logs
- 🔄 **Response Handler**: Handles different response types (regular, plan, PR)
- 💬 **Continue Functionality**: Iterative refinement and additional requirements

## 🏗️ Architecture Overview

The CodegenCICD Dashboard is built with a modern, scalable architecture:

### Core Components

- **Backend**: FastAPI with async/await support
- **Frontend**: React with Material-UI components
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache/Queue**: Redis for real-time updates and background tasks
- **WebSocket**: Real-time communication for live updates
- **Validation Stack**: Integration with grainchain, graph-sitter, and web-eval-agent

### External Integrations

- **Codegen API**: AI-powered code generation and agent runs
- **GitHub API**: Repository management, PR creation, and webhooks
- **Cloudflare Workers**: Webhook gateway for GitHub events
- **Gemini API**: AI validation and error analysis

## 🎯 Key Features

### 📊 Project Dashboard
- **Project Cards**: Visual representation of GitHub repositories
- **Real-time Status**: Live updates on agent runs and validation progress
- **Project Selection**: Dropdown to switch between different repositories

### 🤖 Agent Run System
- **Target Input**: Natural language goals for AI agents
- **Planning Statements**: Customizable prompts for agent context
- **Auto-confirm Plans**: Optional automatic plan approval
- **Progress Tracking**: Real-time monitoring of agent execution

### 🔄 Validation Pipeline
1. **Snapshot Creation**: Using grainchain for sandboxed environments
2. **Code Cloning**: Automatic PR codebase retrieval
3. **Deployment**: Configurable setup commands execution
4. **Validation**: Gemini API-powered deployment verification
5. **Testing**: web-eval-agent for comprehensive UI/UX testing
6. **Auto-merge**: Validated PRs can be automatically merged

### ⚙️ Advanced Configuration
- **Repository Rules**: Custom rules for agent behavior
- **Setup Commands**: Configurable deployment scripts
- **Secrets Management**: Encrypted environment variables
- **Branch Selection**: Target specific branches for operations

### 🔗 GitHub Integration
- **Webhook Support**: Real-time PR notifications
- **Auto-merge**: Validated PRs can be merged automatically
- **Branch Management**: Support for multiple branches
- **PR Tracking**: Visual indicators for created PRs

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Environment Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd CodegenCICD
```

2. **Create environment file**:
```bash
cp .env.example .env
```

3. **Configure environment variables** (see Configuration section below)

4. **Start with Docker Compose**:
```bash
docker-compose up -d
```

5. **Access the application**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🔧 Configuration

### Required Environment Variables

```bash
# Codegen API Configuration
CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=your_codegen_api_token_here

# GitHub Integration
GITHUB_TOKEN=your_github_token_here

# AI Services
GEMINI_API_KEY=your_gemini_api_key_here

# Cloudflare Integration
CLOUDFLARE_API_KEY=your_cloudflare_api_key_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=https://webhook-gateway.pixeliumperfecto.workers.dev

# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/codegencd
REDIS_URL=redis://localhost:6379

# Security
SECRET_ENCRYPTION_KEY=<generate-with-fernet>
```

## 📖 Usage Guide

### 1. Project Setup

1. **Add a Project**:
   - Click "Add Project" in the dashboard
   - Enter GitHub repository details
   - Configure initial settings

2. **Configure Project Settings**:
   - **Repository Rules**: Custom instructions for the AI agent
   - **Setup Commands**: Deployment and build scripts
   - **Secrets**: Environment variables for the project
   - **Planning Statement**: Default prompt context

### 2. Running Agent Tasks

1. **Start an Agent Run**:
   - Click "Agent Run" on a project card
   - Enter your target/goal in natural language
   - Click "Confirm" to start the process

2. **Monitor Progress**:
   - Real-time updates appear on the project card
   - WebSocket connection provides live status updates
   - View detailed logs in the agent run details

### 3. Validation Flow

When a PR is created by an agent:

1. **Automatic Validation Trigger**:
   - System creates a snapshot environment
   - Clones the PR codebase
   - Runs configured setup commands

2. **Deployment Validation**:
   - Gemini API validates deployment success
   - Errors trigger automatic fixes via agent continuation

3. **UI/UX Testing**:
   - web-eval-agent tests all application flows
   - Comprehensive component and functionality validation

4. **Auto-merge** (if enabled):
   - Successfully validated PRs are automatically merged
   - Notification sent to user with completion status

## 🛠️ Development

### Local Development Setup

1. **Backend Development**:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. **Frontend Development**:
```bash
cd frontend
npm install
npm start
```

3. **Database Setup**:
```bash
# Start PostgreSQL and Redis
docker-compose up postgres redis -d

# Run database migrations
cd backend
alembic upgrade head
```

### Project Structure

```
CodegenCICD/
├── backend/                 # FastAPI backend
│   ├── main.py             # Application entry point
│   ├── database.py         # Database configuration
│   ├── models/             # SQLAlchemy models
│   ├── routers/            # API route handlers
│   ├── services/           # Business logic services
│   ├── websocket/          # WebSocket management
│   └── integrations/       # External API clients
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API clients
│   │   └── hooks/          # Custom React hooks
│   └── public/
├── docker-compose.yml      # Docker services configuration
└── README.md              # This file
```

## 🔌 API Endpoints

### Projects
- `GET /api/v1/projects` - List all projects
- `POST /api/v1/projects` - Create a new project
- `GET /api/v1/projects/{id}` - Get project details
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Agent Runs
- `GET /api/v1/agent-runs` - List agent runs
- `POST /api/v1/agent-runs` - Create new agent run
- `GET /api/v1/agent-runs/{id}` - Get agent run details

### Configuration
- `GET /api/v1/configurations/secrets` - List project secrets
- `POST /api/v1/configurations/secrets` - Create new secret
- `DELETE /api/v1/configurations/secrets/{id}` - Delete secret

### Webhooks
- `POST /api/v1/webhooks/github` - GitHub webhook handler

## 🔒 Security Features

- **Encrypted Secrets**: All environment variables are encrypted using Fernet
- **Webhook Verification**: GitHub webhook signatures are validated
- **Database Security**: Parameterized queries prevent SQL injection
- **CORS Configuration**: Proper cross-origin resource sharing setup

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📊 Monitoring

- **Health Checks**: `/health` endpoint for service monitoring
- **Real-time Updates**: WebSocket connections for live status
- **Logging**: Structured logging with different levels
- **Error Tracking**: Comprehensive error handling and reporting

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
- Check the API documentation at `/docs`
- Review the logs for debugging information

---

**Built with ❤️ using Codegen AI and modern web technologies**
