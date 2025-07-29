# 🚀 CodegenCICD Dashboard - Launch Instructions

## 🎯 **Quick Start Guide**

The CodegenCICD Dashboard is a native Python + React application that provides AI-powered CI/CD management without any containerization dependencies.

## 📋 **Prerequisites**

Before launching, ensure you have:
- **Python 3.8+** installed
- **Node.js 16+** installed  
- **Git** installed
- **Required API keys** (see configuration section)

## 🚀 **Launch Process**

### **Step 1: Install Dependencies**
```bash
./deploy.sh
```

This will:
- ✅ Check system requirements
- ✅ Create Python virtual environment
- ✅ Install all Python dependencies
- ✅ Install all Node.js dependencies
- ✅ Set up configuration templates

### **Step 2: Configure Environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required Configuration:**
- `CODEGEN_ORG_ID` - Your Codegen organization ID
- `CODEGEN_API_TOKEN` - Your Codegen API token
- `GITHUB_TOKEN` - GitHub personal access token
- `GEMINI_API_KEY` - Google Gemini API key
- `CLOUDFLARE_API_KEY` - Cloudflare API key
- `CLOUDFLARE_ACCOUNT_ID` - Cloudflare account ID
- `CLOUDFLARE_WORKER_URL` - Webhook gateway URL

### **Step 3: Start Services**
```bash
./start.sh
```

This will:
- ✅ Validate all environment variables
- ✅ Prompt for any missing values
- ✅ Check port availability
- ✅ Start backend FastAPI server
- ✅ Start frontend React development server
- ✅ Provide access URLs and monitoring info

## 🌐 **Access URLs**

Once launched, access the dashboard at:

- **🎨 Frontend Dashboard**: http://localhost:3001
- **🔧 Backend API**: http://localhost:8000
- **📚 API Documentation**: http://localhost:8000/docs
- **❤️ Health Check**: http://localhost:8000/health

## 🎯 **Dashboard Features**

### **1. Project Management**
- Select GitHub repositories from dropdown
- View project cards with real-time status
- Configure project-specific settings

### **2. AI Agent Runs**
- Click "Agent Run" button on any project card
- Enter natural language goals/requirements
- Monitor real-time progress via WebSocket
- Handle different response types (regular/plan/PR)

### **3. Configuration System (4 Tabs)**

#### **Repository Rules Tab**
Define custom AI agent behavior:
```
Follow TypeScript best practices
Include comprehensive error handling
Write unit tests for all functions
Use Material-UI components
```

#### **Setup Commands Tab**
Configure deployment commands:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python main.py &

cd ../frontend
npm install
npm start
```

#### **Secrets Management Tab**
Store environment variables securely:
- Add individual key-value pairs
- Bulk paste from text file
- Encrypted storage

#### **Planning Statements Tab**
Configure AI agent personality:
```
You are a senior full-stack developer.
Focus on clean, maintainable code.
Always include proper error handling.
Use modern React patterns and hooks.
```

### **4. Validation Pipeline**

The 7-step automated validation process:

1. **📸 Snapshot Creation** - Grainchain creates isolated environment
2. **📥 PR Clone** - Downloads and prepares PR codebase
3. **🚀 Deployment** - Runs configured setup commands
4. **✅ Validation** - Gemini AI validates deployment success
5. **🧪 UI Testing** - Web-eval-agent tests all user flows
6. **🔄 Error Handling** - Automatic retry with error context
7. **🎯 Auto-merge** - Merge validated PRs (if enabled)

## 📊 **Monitoring & Logs**

### **Service Status**
```bash
# Check if services are running
ps aux | grep -E "(python.*main.py|npm.*start)"

# Check port usage
lsof -i :8000,3001
```

### **Log Files**
```bash
# View backend logs
tail -f logs/backend.log

# View frontend logs  
tail -f logs/frontend.log

# View both logs simultaneously
tail -f logs/backend.log logs/frontend.log
```

### **Service PIDs**
Service process IDs are stored in:
- `logs/backend.pid`
- `logs/frontend.pid`

## 🛑 **Stopping Services**

The `start.sh` script runs in the foreground and handles graceful shutdown:

- **Ctrl+C** - Gracefully stops both services
- **Kill PIDs** - Manually stop services using stored PIDs

```bash
# Manual stop using PIDs
kill $(cat logs/backend.pid)
kill $(cat logs/frontend.pid)
```

## 🔧 **Troubleshooting**

### **Port Conflicts**
If ports 8000 or 3001 are in use:
```bash
# Find and kill processes using the ports
lsof -ti:8000,3001 | xargs kill -9
```

### **Environment Variable Issues**
The `start.sh` script will prompt for missing variables, but you can also:
```bash
# Validate your .env file
grep -v '^#' .env | grep '='
```

### **Python Virtual Environment Issues**
```bash
# Recreate virtual environment
rm -rf backend/venv
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **Node.js Dependencies Issues**
```bash
# Clear and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

## 🔄 **Development Mode**

For development, you can run services separately:

### **Backend Only**
```bash
cd backend
source venv/bin/activate
python main.py
```

### **Frontend Only**
```bash
cd frontend
npm start
```

## 🌟 **Key Integrations**

The dashboard integrates with these external services:

- **[Codegen API](https://docs.codegen.com/api-reference)** - AI agent coordination
- **[Grainchain](https://github.com/Zeeeepa/grainchain)** - Sandboxing and snapshots
- **[Graph-sitter](https://github.com/Zeeeepa/graph-sitter)** - Code quality analysis
- **[Web-eval-agent](https://github.com/Zeeeepa/web-eval-agent)** - UI testing
- **GitHub API** - Repository management
- **Gemini AI** - Intelligent validation
- **Cloudflare Workers** - Webhook gateway

## 🎉 **Success!**

Once launched successfully, you'll see:

```
🎉 CodegenCICD Dashboard is now running!
========================================

🔗 Access URLs:
   Frontend (React UI): http://localhost:3001
   Backend API:         http://localhost:8000
   API Health Check:    http://localhost:8000/health
   API Documentation:   http://localhost:8000/docs

📊 Service Status:
   Backend PID:  12345
   Frontend PID: 12346

📝 Logs:
   Backend logs: tail -f logs/backend.log
   Frontend logs: tail -f logs/frontend.log

🚀 Dashboard ready! Open http://localhost:3001 in your browser
```

**Your AI-powered CI/CD dashboard is now ready for use!** 🎯

Navigate to http://localhost:3001 to start managing your projects with AI assistance.

