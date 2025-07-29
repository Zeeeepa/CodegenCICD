# CodegenCICD Dashboard

## 🚀 AI-Powered CI/CD Management System

A comprehensive dashboard for managing AI-driven continuous integration and deployment workflows using the Codegen Agent API. This system provides an intuitive interface for project management, environment configuration, and automated validation flows.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)

## 🎯 Overview

CodegenCICD Dashboard is a modern web application that bridges the gap between AI-powered code generation and traditional CI/CD pipelines. It leverages multiple specialized tools to provide a complete development workflow automation solution.

### Core Components

1. **Dashboard Interface** - React-based UI for project management
2. **Project Pinning System** - GitHub repository integration with persistent storage
3. **Environment Management** - Real-time configuration editing
4. **Service Validation** - API connectivity testing and monitoring
5. **Agent Integration** - Codegen API for AI-powered development tasks

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CodegenCICD Dashboard                    │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React + TypeScript + Material-UI)               │
│  ├── Project Cards (Pinned GitHub Repositories)            │
│  ├── Environment Variable Editor                           │
│  ├── Service Status Monitoring                             │
│  └── Agent Run Interface                                   │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python)                                │
│  ├── Service Validation APIs                               │
│  ├── Environment Management                                │
│  ├── GitHub Integration                                     │
│  └── Codegen Agent Coordination                            │
├─────────────────────────────────────────────────────────────┤
│  External Integrations                                      │
│  ├── Codegen SDK (AI Agent Coordination)                   │
│  ├── Graph-Sitter (Static Analysis & Code Quality)        │
│  ├── Grainchain (Sandboxing & Snapshot Creation)          │
│  └── Web-Eval-Agent (UI Testing & Browser Automation)     │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

### 🎨 User Interface
- **Modern Dashboard**: Clean, responsive Material-UI design
- **Dark Theme**: Professional dark theme with intuitive navigation
- **Project Pinning**: Pin GitHub repositories as project cards
- **Real-time Updates**: Live status monitoring and notifications

### 🔧 Project Management
- **GitHub Integration**: Seamless repository browsing and selection
- **Project Cards**: Visual representation of pinned repositories
- **Persistent Storage**: Settings maintained across sessions
- **Repository Details**: Stars, forks, language, and description display

### ⚙️ Environment Configuration
- **Inline Editing**: Click-to-edit environment variables
- **API Integration**: Real-time updates via backend API
- **Validation**: Input validation and error handling
- **Categorized Variables**: Organized by service (Codegen, GitHub, Gemini, Cloudflare)

### 🔍 Service Validation
- **API Connectivity**: Test connections to external services
- **Real-time Monitoring**: Automatic health checks and status updates
- **Response Time Tracking**: Performance monitoring for all services
- **Error Reporting**: Detailed error messages and troubleshooting

### 🤖 AI Agent Integration
- **Codegen API**: Direct integration with Codegen Agent API
- **Natural Language Processing**: Send prompts and receive AI-generated responses
- **Project Context**: Automatic project context inclusion in requests
- **Response Handling**: Support for regular, plan, and PR response types

## 🚀 Installation

### Prerequisites
- **Node.js** (v16 or higher)
- **Python** (v3.8 or higher)
- **Git**

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/Zeeeepa/CodegenCICD.git
cd CodegenCICD

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Set up environment variables (see Environment Variables section)
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Frontend Setup
```bash
# Install Node.js dependencies
cd frontend
npm install

# Build the application
npm run build
```

### Running the Application
```bash
# Start the backend server
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Start the frontend development server (in a new terminal)
cd frontend
npm start
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📖 Usage

### 1. Project Setup
1. **Pin Repositories**: Use the dropdown selector to pin GitHub repositories to your dashboard
2. **Configure Environment**: Edit environment variables through the Environment tab
3. **Validate Services**: Check API connectivity in the Validation tab

### 2. Project Management
- **View Project Cards**: Pinned repositories appear as cards with repository information
- **Unpin Projects**: Remove projects using the unpin button on each card
- **Repository Details**: View stars, forks, language, and description

### 3. Environment Configuration
- **Edit Variables**: Click the edit icon next to any environment variable
- **Save Changes**: Use save/cancel buttons to confirm or discard changes
- **Real-time Updates**: Changes are immediately reflected in the system

### 4. Service Monitoring
- **API Status**: Monitor connectivity to Codegen, GitHub, Gemini, and Cloudflare APIs
- **Response Times**: Track API performance and response times
- **Error Handling**: View detailed error messages for failed connections

## 🔌 API Reference

### Service Validation Endpoints

#### GET `/api/validation/environment`
Retrieve all environment variables organized by category.

**Response:**
```json
{
  "environment_variables": {
    "codegen": {
      "CODEGEN_ORG_ID": "323",
      "CODEGEN_API_TOKEN": "sk-..."
    },
    "github": {
      "GITHUB_TOKEN": "github_pat_..."
    }
  },
  "timestamp": 1753768644.4178705,
  "total_variables": 12
}
```

#### PUT `/api/validation/environment/{variable_name}`
Update a specific environment variable.

**Request Body:**
```json
{
  "value": "new_value"
}
```

#### GET `/api/validation/codegen`
Validate Codegen API connectivity and authentication.

#### GET `/api/validation/github-repositories`
Fetch GitHub repositories from the authenticated user's account.

#### GET `/health`
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "codegencd-api"
}
```

## 📁 Project Structure

```
CodegenCICD/
├── backend/                    # FastAPI backend application
│   ├── main.py                # Application entry point
│   ├── routers/               # API route handlers
│   │   └── service_validation.py
│   └── requirements.txt       # Python dependencies
├── frontend/                  # React frontend application
│   ├── public/               # Static assets
│   ├── src/                  # Source code
│   │   ├── components/       # React components
│   │   │   ├── Dashboard.tsx # Main dashboard component
│   │   │   ├── EnvironmentVariables.tsx
│   │   │   ├── ServiceValidator.tsx
│   │   │   └── config-tabs/  # Configuration tab components
│   │   ├── hooks/           # Custom React hooks
│   │   └── types/           # TypeScript type definitions
│   ├── package.json         # Node.js dependencies
│   └── tsconfig.json        # TypeScript configuration
├── README.md                # This file
└── .env.example            # Environment variables template
```

## 🔐 Environment Variables

### Required Variables

#### Codegen API Configuration
```bash
CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=sk-[REDACTED]
```

#### GitHub Integration
```bash
GITHUB_TOKEN=github_pat_[REDACTED]
```

#### Gemini API (for AI validation)
```bash
GEMINI_API_KEY=AIzaSy[REDACTED]
```

#### Cloudflare Configuration
```bash
CLOUDFLARE_API_KEY=[REDACTED]
CLOUDFLARE_ACCOUNT_ID=[REDACTED]
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=https://webhook-gateway.pixeliumperfecto.workers.dev
```

#### Service Configuration
```bash
BACKEND_PORT=8000
FRONTEND_PORT=3001
BACKEND_HOST=localhost
FRONTEND_HOST=localhost
```

## 🛠️ External Project Dependencies

### [Graph-Sitter](https://github.com/Zeeeepa/graph-sitter)
**Purpose**: Static analysis & code quality metrics
- **Function**: Analyzes code structure and quality
- **Integration**: Used for code validation in PR workflows
- **Features**: AST parsing, complexity analysis, code metrics

### [Grainchain](https://github.com/Zeeeepa/grainchain)
**Purpose**: Sandboxing + snapshot creation + PR validation deployments
- **Function**: Creates isolated environments for testing
- **Integration**: Handles deployment validation and testing
- **Features**: Container management, snapshot creation, environment isolation

### [Web-Eval-Agent](https://github.com/Zeeeepa/web-eval-agent)
**Purpose**: UI testing & browser automation
- **Function**: Automated testing of web interfaces
- **Integration**: Validates UI functionality after deployments
- **Features**: Browser automation, UI testing, flow validation

### [Codegen SDK](https://docs.codegen.com/api-reference)
**Purpose**: Agent coordination & code generation
- **Function**: Core AI-powered development assistance
- **Integration**: Natural language to code generation
- **Features**: Agent runs, plan generation, PR creation

## 🔄 Workflow Integration

### Validation Flow Process
1. **Project Selection**: User pins GitHub repository to dashboard
2. **Agent Run**: User initiates AI agent with target text/goal
3. **Code Generation**: Codegen API processes request and generates code
4. **PR Creation**: System creates pull request with generated changes
5. **Validation Pipeline**:
   - **Snapshot Creation**: Grainchain creates isolated environment
   - **Code Analysis**: Graph-Sitter analyzes code quality
   - **Deployment**: Automated deployment to test environment
   - **UI Testing**: Web-Eval-Agent validates functionality
6. **Feedback Loop**: Results fed back to agent for improvements
7. **Auto-merge**: Optional automatic merging of validated PRs

## 🚀 Future Enhancements

### Planned Features
- **Agent Run Interface**: Text dialog for AI agent interactions
- **Planning Statement Configuration**: Customizable pre-prompts
- **Auto-confirm Plans**: Checkbox for automatic plan confirmation
- **Repository Rules**: Custom rules per repository
- **Setup Commands**: Configurable sandbox setup commands
- **Secrets Management**: Secure environment variable storage
- **Webhook Integration**: Real-time PR notifications
- **Deployment Monitoring**: Live deployment status tracking

### Advanced Capabilities
- **Multi-agent Coordination**: Orchestrate multiple AI agents
- **Custom Validation Rules**: User-defined validation criteria
- **Integration Templates**: Pre-configured workflow templates
- **Performance Analytics**: Detailed metrics and reporting
- **Team Collaboration**: Multi-user project management

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines
- Follow TypeScript best practices for frontend code
- Use Python type hints and docstrings for backend code
- Write tests for new functionality
- Update documentation for API changes
- Follow the existing code style and conventions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Codegen Team** for the powerful AI agent API
- **Material-UI** for the excellent React component library
- **FastAPI** for the high-performance Python web framework
- **React** for the robust frontend framework

---

**Built with ❤️ by the CodegenCICD Team**

For support or questions, please open an issue on GitHub or contact the development team.
