# 🚀 CodegenCICD Dashboard - Launch Instructions

## Quick Start

The CodegenCICD Dashboard is now **RUNNING** and ready to use!

### 🔗 Access URLs

- **Frontend (React UI)**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs

### 📊 Current Status

Both services are currently running:
- ✅ Backend: FastAPI server on port 8000
- ✅ Frontend: React development server on port 3001

## 🎯 Available Features

### 1. **Project Management Dashboard**
- View and manage GitHub projects
- Real-time project cards with status indicators
- Auto-merge and auto-confirm capabilities

### 2. **AI Agent Runs**
- Natural language to code generation via Codegen API
- Target text input with planning statements
- Real-time progress tracking
- Support for regular, plan, and PR response types

### 3. **4-Tab Configuration System**
- **Repository Rules**: Custom rules for the AI agent
- **Setup Commands**: Deployment and build commands
- **Secrets Management**: Encrypted environment variables
- **Planning Statements**: AI agent behavior configuration

### 4. **Validation Pipeline**
- 7-step automated validation process
- Integration with grainchain (sandboxing)
- Integration with graph-sitter (code analysis)
- Integration with web-eval-agent (UI testing)
- Gemini API for intelligent validation

### 5. **Real-time Updates**
- WebSocket connections for live progress
- Instant notifications for PR creation
- Live validation status updates

## 🛠️ Management Commands

### Start Services
```bash
./launch.sh
```

### Check Status
```bash
./status.sh
```

### Stop Services
```bash
./stop.sh
```

### View Logs
```bash
# Backend logs
tail -f backend.log

# Frontend logs
tail -f frontend.log

# Both logs
tail -f backend.log frontend.log
```

## 🔧 Configuration

### Environment Variables
The system uses the following key environment variables (already configured):

```bash
# Codegen API
CODEGEN_ORG_ID=your_org_id_here
CODEGEN_API_TOKEN=your_codegen_api_token_here

# GitHub Integration
GITHUB_TOKEN=your_github_token_here

# AI Services
GEMINI_API_KEY=your_gemini_api_key_here

# Cloudflare (Webhooks)
CLOUDFLARE_API_KEY=your_cloudflare_api_key_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
CLOUDFLARE_WORKER_URL=your_cloudflare_worker_url_here
```

## 🎮 How to Use

### 1. **Access the Dashboard**
Open http://localhost:3001 in your browser to see the main dashboard.

### 2. **Select a Project**
Use the project dropdown to select from available GitHub repositories.

### 3. **Run an AI Agent**
1. Click the "Agent Run" button on a project card
2. Enter your target text/goal
3. Click confirm to start the agent run
4. Watch real-time progress updates

### 4. **Configure Projects**
Click the settings gear icon on any project card to access:
- Repository rules
- Setup commands
- Secrets management
- Planning statements

### 5. **Validation Flow**
When a PR is created, the system automatically:
1. Creates a sandbox snapshot
2. Clones the PR codebase
3. Runs deployment commands
4. Validates deployment success
5. Runs UI testing with web-eval-agent
6. Provides feedback or auto-merges

## 🏗️ Architecture

### Backend (FastAPI)
- **Location**: `backend/`
- **Port**: 8000
- **Features**: REST API, WebSocket support, external service integrations

### Frontend (React + TypeScript)
- **Location**: `frontend/`
- **Port**: 3001
- **Features**: Material-UI dashboard, real-time updates, project management

### External Integrations
- **Codegen API**: AI agent coordination
- **GitHub API**: Repository management
- **Grainchain**: Sandboxing and snapshots
- **Graph-sitter**: Code quality analysis
- **Web-eval-agent**: UI testing and validation
- **Gemini API**: Intelligent validation

## 🔍 Troubleshooting

### Services Not Starting
```bash
# Check if ports are in use
lsof -i :8000
lsof -i :3001

# Kill existing processes if needed
./stop.sh
./launch.sh
```

### API Not Responding
```bash
# Check backend health
curl http://localhost:8000/health

# Check backend logs
tail -f backend.log
```

### Frontend Not Loading
```bash
# Check frontend accessibility
curl http://localhost:3001

# Check frontend logs
tail -f frontend.log
```

## 📝 Development

### Backend Development
```bash
cd backend
source venv/bin/activate
python main.py
```

### Frontend Development
```bash
cd frontend
PORT=3001 npm start
```

### Adding New Features
1. Backend: Add endpoints in `backend/main.py`
2. Frontend: Add components in `frontend/src/components/`
3. API integration: Update `frontend/src/services/api.ts`

## 🎉 Success!

Your CodegenCICD Dashboard is now fully operational with:
- ✅ Complete UI dashboard
- ✅ AI agent integration
- ✅ Real-time updates
- ✅ Validation pipeline
- ✅ External service integrations
- ✅ Auto-merge capabilities

**Ready to transform your development workflow with AI-powered CI/CD!** 🚀
