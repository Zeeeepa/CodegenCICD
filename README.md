# CodegenCICD Dashboard

🚀 **AI-Powered CI/CD Flow Cycle Project Management System**

A comprehensive dashboard for managing AI-driven development workflows using the Codegen API, featuring real-time project management, automated validation pipelines, and intelligent code analysis.

## 🌟 Features

### Core Functionality
- **Project Management**: Create and manage multiple development projects
- **AI Agent Runs**: Execute Codegen agents with custom prompts and planning statements
- **Real-time Updates**: WebSocket-powered live updates for all operations
- **Validation Pipeline**: Automated code quality, security, and integration testing
- **GitHub Integration**: Webhook-driven PR monitoring and automated workflows

### Advanced Capabilities
- **4-Tab Configuration System**: Repository rules, setup commands, secrets, and planning statements
- **Sandbox Testing**: Isolated environment testing using Grainchain
- **Web UI Evaluation**: Automated UI testing with web-eval-agent
- **Code Quality Analysis**: Graph-sitter powered code analysis
- **Security Scanning**: Integrated security vulnerability detection

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │   PostgreSQL    │
│   (Port 3000)   │◄──►│   (Port 8000)   │◄──►│   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────►│      Redis      │◄─────────────┘
                        │   (Port 6379)   │
                        └─────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │   External Services     │
                    │  • Codegen API          │
                    │  • GitHub API           │
                    │  • Cloudflare Workers   │
                    │  • Grainchain Sandbox   │
                    │  • Web-Eval-Agent       │
                    └─────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Zeeeepa/CodegenCICD.git
   cd CodegenCICD
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Update `.env` with your actual API keys:
   ```env
   # Codegen API
   CODEGEN_ORG_ID=your_org_id
   CODEGEN_API_TOKEN=sk-your-codegen-api-token
   
   # GitHub Integration
   GITHUB_TOKEN=github_pat_your_github_token
   
   # AI Services
   GEMINI_API_KEY=your_gemini_api_key
   
   # Cloudflare
   CLOUDFLARE_API_KEY=your_cloudflare_api_key
   CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
   CLOUDFLARE_WORKER_NAME=your-worker-name
   CLOUDFLARE_WORKER_URL=https://your-worker.workers.dev
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the dashboard**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📋 API Endpoints

### Projects
- `GET /api/v1/projects` - List all projects
- `POST /api/v1/projects` - Create a new project
- `GET /api/v1/projects/{id}` - Get project details
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project
- `GET /api/v1/projects/{id}/configuration` - Get project configuration
- `PUT /api/v1/projects/{id}/configuration` - Update project configuration

### Agent Runs
- `GET /api/v1/agent-runs` - List agent runs
- `POST /api/v1/agent-runs` - Create new agent run
- `GET /api/v1/agent-runs/{id}` - Get agent run details
- `POST /api/v1/agent-runs/{id}/continue` - Continue agent run

### Webhooks
- `POST /api/v1/webhooks/github` - GitHub webhook endpoint
- `GET /api/v1/webhooks/events` - List webhook events
- `GET /api/v1/webhooks/events/{id}` - Get webhook event details

### WebSocket
- `WS /ws/{client_id}` - Real-time updates connection

## 🔧 Configuration

### Project Configuration Tabs

#### 1. Repository Rules
Define custom rules and guidelines specific to your repository:
```
- Use TypeScript for all new code
- Follow existing code style conventions
- Add proper error handling
- Include unit tests for new features
```

#### 2. Setup Commands
Commands to execute when setting up the sandbox environment:
```bash
cd backend
python -m pip install -r requirements.txt
python manage.py migrate
cd ../frontend
npm install
npm run build
```

#### 3. Secrets Management
Environment variables and API keys (encrypted storage):
```
CODEGEN_ORG_ID=your_org_id
CODEGEN_TOKEN=sk-your-codegen-token
GITHUB_TOKEN=github_pat_your_token
GEMINI_API_KEY=your_gemini_key
```

#### 4. Planning Statement
Context automatically prepended to all agent runs:
```
You are working on a React/FastAPI project. Always follow these guidelines:
- Use TypeScript for frontend components
- Follow REST API conventions
- Implement proper error handling
- Add comprehensive logging
```

## 🔄 Validation Pipeline

The system includes a comprehensive validation pipeline that runs automatically on PR events:

1. **Code Quality Check** - Graph-sitter analysis for code quality metrics
2. **Security Scan** - Semgrep-based security vulnerability detection
3. **Setup Commands Test** - Validation of project setup in sandbox environment
4. **Web UI Evaluation** - Automated UI testing using web-eval-agent
5. **Integration Test** - Comprehensive integration testing

## 🛠️ Development

### Local Development Setup

1. **Backend Development**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Frontend Development**
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Database Setup**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up postgres redis -d
   
   # Run migrations
   cd backend
   alembic upgrade head
   ```

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 🔌 Integrations

### Codegen API
- Official SDK integration with fallback HTTP client
- Real-time task status monitoring
- Automatic response type detection (PR/Plan/Regular)

### GitHub Integration
- Webhook-based PR monitoring
- Automatic repository verification
- Branch and commit tracking

### Cloudflare Workers
- Webhook gateway for GitHub events
- Scalable event processing
- Global edge distribution

### Grainchain Sandbox
- Isolated code execution environment
- Secure testing and validation
- Snapshot and rollback capabilities

### Web-Eval-Agent
- Automated UI testing
- Responsive design validation
- User experience evaluation

## 📊 Monitoring

### WebSocket Events
- `agent_run_status` - Agent run status updates
- `agent_run_completed` - Agent run completion
- `agent_run_failed` - Agent run failures
- `pr_webhook` - GitHub PR events
- `validation_started` - Validation pipeline start
- `validation_step_completed` - Individual step completion
- `validation_completed` - Full validation completion

### Health Checks
- `/health` - Application health status
- `/ws/stats` - WebSocket connection statistics (debug mode)

## 🚀 Deployment

### Production Deployment

1. **Environment Configuration**
   ```bash
   # Update production environment variables
   export ENVIRONMENT=production
   export DEBUG=false
   export DATABASE_URL=postgresql://...
   ```

2. **Docker Compose Production**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **SSL/TLS Setup**
   ```bash
   # Configure reverse proxy (nginx/traefik)
   # Set up SSL certificates
   # Update CORS origins
   ```

### Scaling
- Horizontal scaling with multiple backend instances
- Redis-based session management
- PostgreSQL read replicas for high availability
- Cloudflare CDN for frontend assets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [API Docs](http://localhost:8000/docs)
- **Issues**: [GitHub Issues](https://github.com/Zeeeepa/CodegenCICD/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Zeeeepa/CodegenCICD/discussions)

## 🙏 Acknowledgments

- [Codegen](https://codegen.com) - AI-powered development platform
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - Frontend library
- [Material-UI](https://mui.com/) - React component library
- [Grainchain](https://github.com/Zeeeepa/grainchain) - Sandbox environment
- [Graph-sitter](https://github.com/Zeeeepa/graph-sitter) - Code quality analysis
- [Web-eval-agent](https://github.com/Zeeeepa/web-eval-agent) - UI testing framework

---

**Built with ❤️ by the Zeeeepa team**
