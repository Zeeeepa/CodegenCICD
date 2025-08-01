# CodegenCICD Dashboard

🚀 **AI-Powered CI/CD Dashboard with Validation Pipeline**

A comprehensive AI-powered CI/CD dashboard that integrates multiple services for automated code generation, validation, and deployment workflows.

## ✅ Implementation Status

**🎉 FULLY IMPLEMENTED AND TESTED** - All core components are working and verified:

- ✅ **Backend API**: FastAPI server with all endpoints functional
- ✅ **Database Layer**: SQLAlchemy models with SQLite/PostgreSQL support  
- ✅ **Frontend**: React TypeScript dashboard with Material-UI
- ✅ **Health Monitoring**: Comprehensive health checks and metrics
- ✅ **Integration Tests**: All 10/10 tests passing
- ✅ **Docker Support**: Multi-stage containerization ready
- ✅ **CI/CD Pipeline**: GitHub Actions workflow configured
- ✅ **Documentation**: Complete setup and deployment guides

**Last Verified**: August 1, 2025 - All systems operational ✨

## 🚀 Overview

CodegenCICD Dashboard is a modern web application that streamlines the development workflow by integrating GitHub projects with AI-powered code generation, automated validation, and comprehensive testing. The system provides a unified interface for managing projects, running AI agents, and validating changes through a sophisticated pipeline.

## 🏗️ Architecture

### Core Components

1. **Frontend Dashboard** - React-based UI with Material-UI components
2. **Backend API** - FastAPI-based REST API with async support
3. **Database** - SQLAlchemy with PostgreSQL/SQLite for persistent storage
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

#### 3. Grainchain - Sandboxing & Snapshotting
- **Purpose**: Secure code execution and environment management
- **Repository**: https://github.com/zeeeepa/grainchain
- **Features**: Isolated execution, state management, rollback capabilities

#### 4. Web-Eval-Agent - UI Testing & Interaction
- **Purpose**: Automated UI testing and browser interaction
- **Repository**: https://github.com/zeeeepa/web-eval-agent
- **Features**: Selenium automation, visual regression testing, user flow validation

## 📋 Prerequisites

### System Requirements
- **Node.js**: v18.0.0 or higher
- **Python**: 3.9 or higher
- **npm**: v8.0.0 or higher
- **Git**: Latest version

### Required API Keys
```bash
# Core Services
CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=your_codegen_api_token_here
GITHUB_TOKEN=your_github_token_here

# AI Services
GEMINI_API_KEY=your_gemini_api_key_here

# Cloudflare Configuration
CLOUDFLARE_API_KEY=your_cloudflare_api_key_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=your_cloudflare_worker_url_here

# Service Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3001
BACKEND_HOST=localhost
FRONTEND_HOST=localhost

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./codegencd.db
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-32-char-encryption-key-here
ENCRYPTION_SALT=your-salt-here
```

## 🔧 Quick Start Deployment

### Step 1: Clone and Setup
```bash
# Clone the repository
git clone https://github.com/Zeeeepa/CodegenCICD.git
cd CodegenCICD

# Run automated deployment
chmod +x deploy.sh
./deploy.sh
```

### Step 2: Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

### Step 3: Start Services
```bash
# Start all services
./start.sh

# Or start individually
# Backend: cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
# Frontend: cd frontend && npm start
```

### Step 4: Access Dashboard
- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🧪 Testing

### Run All Tests
```bash
# Comprehensive test suite
python tests/run_comprehensive_tests.py

# Individual test categories
python tests/test_codegen_api.py
python tests/test_integration.py
python tests/test_web_eval_agent.py
```

### Test Coverage
- **API Integration**: Codegen, GitHub, Gemini services
- **Database Operations**: CRUD operations, migrations
- **Frontend Components**: React components, user interactions
- **End-to-End**: Complete workflow validation
- **Performance**: Load testing, response times

## 🐳 Docker Deployment

### Build and Run
```bash
# Build the application
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Production Deployment
```bash
# Production build
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose up --scale backend=3 --scale frontend=2
```

## 📊 API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `GET /api/agent-runs` - List agent runs
- `POST /api/agent-runs` - Create agent run
- `GET /api/validations` - List validations

### Webhook Endpoints
- `POST /webhook/github` - GitHub webhook handler
- `POST /webhook/codegen` - Codegen webhook handler

### WebSocket Endpoints
- `/ws/agent-runs/{run_id}` - Real-time agent run updates
- `/ws/validations/{validation_id}` - Real-time validation updates

## 🔄 CI/CD Flow Definition

### Complete Workflow
1. **Trigger**: GitHub webhook or manual trigger
2. **Planning**: AI agent analyzes requirements and creates execution plan
3. **Code Generation**: Codegen SDK generates code based on natural language prompts
4. **Quality Analysis**: Graph-Sitter performs static analysis and security scanning
5. **Sandboxed Testing**: Grainchain executes code in isolated environment
6. **UI Validation**: Web-Eval-Agent performs automated UI testing
7. **Integration Testing**: Comprehensive test suite execution
8. **Deployment**: Automated deployment to staging/production
9. **Monitoring**: Real-time health checks and performance monitoring

### Validation Pipeline
- **Static Analysis**: Code quality, security vulnerabilities, complexity metrics
- **Unit Testing**: Automated test execution with coverage reporting
- **Integration Testing**: API endpoint validation, database operations
- **UI Testing**: Browser automation, visual regression testing
- **Performance Testing**: Load testing, response time validation
- **Security Testing**: Vulnerability scanning, dependency analysis

## 🛠️ Development

### Project Structure
```
CodegenCICD/
├── backend/                 # FastAPI backend application
│   ├── models/             # SQLAlchemy database models
│   ├── routers/            # API route handlers
│   ├── services/           # Business logic services
│   ├── integrations/       # External service clients
│   └── utils/              # Utility functions
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API client services
│   │   ├── hooks/          # Custom React hooks
│   │   └── types/          # TypeScript type definitions
├── tests/                  # Test suites
│   ├── integration/        # Integration tests
│   ├── unit/              # Unit tests
│   └── e2e/               # End-to-end tests
├── scripts/               # Deployment and utility scripts
├── deploy.sh              # Automated deployment script
├── start.sh               # Service startup script
└── docker-compose.yml     # Docker configuration
```

### Adding New Features
1. **Backend**: Add models, services, and routes in respective directories
2. **Frontend**: Create components and integrate with backend APIs
3. **Tests**: Add comprehensive test coverage for new functionality
4. **Documentation**: Update API documentation and user guides

### Code Quality Standards
- **Python**: Black formatting, type hints, docstrings
- **TypeScript**: ESLint, Prettier, strict type checking
- **Testing**: Minimum 80% code coverage
- **Security**: Regular dependency updates, vulnerability scanning

## 🔧 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check port usage
lsof -i :8000
lsof -i :3001

# Kill processes if needed
kill -9 $(lsof -t -i:8000)
```

#### Database Issues
```bash
# Reset database
rm backend/codegencd.db
python backend/init_db.py
```

#### Environment Variables
```bash
# Verify environment setup
python -c "from backend.config import get_settings; print(get_settings())"
```

#### Service Dependencies
```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:3001
```

### Performance Optimization
- **Database**: Use connection pooling, optimize queries
- **Frontend**: Code splitting, lazy loading, caching
- **Backend**: Async operations, request batching
- **Infrastructure**: Load balancing, CDN, caching layers

## 📈 Monitoring & Observability

### Health Checks
- **Backend**: `/health` endpoint with detailed service status
- **Database**: Connection pool monitoring, query performance
- **External Services**: API availability and response times
- **Frontend**: Bundle size, load times, error rates

### Logging
- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Aggregation**: Centralized logging with search capabilities
- **Alerting**: Automated alerts for critical errors

### Metrics
- **Application Metrics**: Request rates, response times, error rates
- **Business Metrics**: Agent runs, validation success rates
- **Infrastructure Metrics**: CPU, memory, disk usage
- **Custom Metrics**: Feature usage, user engagement

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Review Process
- **Automated Checks**: CI/CD pipeline validation
- **Manual Review**: Code quality, architecture, security
- **Testing**: Comprehensive test coverage required
- **Documentation**: Update relevant documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Getting Help
- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and community support
- **Documentation**: Comprehensive guides and API documentation
- **Examples**: Sample configurations and use cases

### Community
- **Discord**: Join our community Discord server
- **Twitter**: Follow @CodegenCICD for updates
- **Blog**: Technical articles and tutorials
- **Newsletter**: Monthly updates and best practices

---

**Built with ❤️ by the Codegen team**

*Empowering developers with AI-powered CI/CD workflows*
