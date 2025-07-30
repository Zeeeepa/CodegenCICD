# 🚀 CodegenCICD Installation Guide

## 📋 Quick Start (npm-based deployment)

### Prerequisites

- **Node.js 18+** and **npm 9+**
- **Python 3.11+** with **pip**
- **Git**
- **uv** (Python package manager)

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/CodegenCICD.git
cd CodegenCICD

# Install all dependencies and set up environment
npm install
npm run setup
```

### 2. Start Development

```bash
# Start both backend and frontend
npm run dev
```

That's it! The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs

## 🔧 Detailed Installation

### Step 1: System Prerequisites

#### Install Node.js and npm
```bash
# Using Node Version Manager (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Or download from https://nodejs.org/
```

#### Install Python 3.11+
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip

# macOS with Homebrew
brew install python@3.11

# Windows: Download from https://python.org/
```

#### Install uv (Python package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv
```

### Step 2: Clone Repository

```bash
git clone https://github.com/Zeeeepa/CodegenCICD.git
cd CodegenCICD
```

### Step 3: Install Dependencies

#### Option A: Automatic Installation (Recommended)
```bash
npm install
npm run install:all
```

#### Option B: Manual Installation
```bash
# Install Node.js dependencies
npm install

# Install Python backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install integrated libraries
npm run install:integrated

# Install frontend dependencies (if exists)
cd frontend && npm install && cd .. || echo "Frontend not found"
```

### Step 4: Environment Configuration

#### Automatic Setup
```bash
npm run setup:env
```

#### Manual Setup
Create `.env` file in the project root:

```bash
# Copy template
cp .env.example .env

# Edit with your configuration
nano .env
```

Required environment variables:
```bash
# Core API Keys (Required)
CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=your-codegen-api-token
GEMINI_API_KEY=your-gemini-api-key
GITHUB_TOKEN=your-github-token

# Optional Sandbox Providers
E2B_API_KEY=your-e2b-api-key
DAYTONA_API_KEY=your-daytona-api-key
MORPH_API_KEY=your-morph-api-key

# Database (SQLite by default)
DATABASE_URL=sqlite:///./codegenapp.db

# Security
SECRET_KEY=your-super-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
```

### Step 5: Database Setup

```bash
npm run setup:db
```

Or manually:
```bash
cd backend
python -m alembic upgrade head
cd ..
```

### Step 6: Validation

```bash
# Validate all services
npm run validate

# Test integration
npm run test

# Test web-eval-agent CICD flow
npm run test:web-eval
```

## 🏃‍♂️ Running the Application

### Development Mode
```bash
# Start both backend and frontend
npm run dev

# Or start individually
npm run backend:dev  # Backend only
npm run frontend:dev # Frontend only
```

### Production Mode
```bash
# Build and start
npm run frontend:build
npm start
```

## 🧪 Testing and Validation

### Complete CICD Flow Test
```bash
# Run the complete CICD flow with web-eval-agent
npm run cicd:full
```

This will:
1. ✅ Set up environment and dependencies
2. ✅ Validate all service integrations
3. ✅ Run comprehensive tests
4. ✅ Execute web-eval-agent CICD flow
5. ✅ Generate detailed reports

### Individual Tests
```bash
# Validate services
npm run validate:services

# Test integration
npm run validate:integration

# Test web-eval-agent specifically
npm run test:web-eval

# Run backend tests
npm run test:backend

# Run frontend tests
npm run test:frontend
```

## 📊 Service Status and Health

### Check Application Health
```bash
npm run health
```

### View Logs
```bash
npm run logs
```

### Service Validation
```bash
# Check all integrated services
curl http://localhost:8000/api/integrated/health

# Individual service status
curl http://localhost:8000/api/integrated/grainchain/providers
curl http://localhost:8000/api/integrated/graph-sitter/status
curl http://localhost:8000/api/integrated/web-eval/status
curl http://localhost:8000/api/integrated/codegen-sdk/status
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Backend Won't Start
```bash
# Check Python dependencies
cd backend && python -c "import fastapi, uvicorn, pydantic"

# Reinstall dependencies
pip install -r requirements.txt

# Check environment variables
cat .env
```

#### 2. Integrated Libraries Not Working
```bash
# Reinstall integrated libraries
npm run install:integrated

# Check individual library installation
python -c "import grainchain" || echo "Grainchain not installed"
python -c "import graph_sitter" || echo "Graph-sitter not installed"
uvx --help || echo "uvx not installed"
```

#### 3. Web-eval-agent Issues
```bash
# Install Playwright browsers
npx playwright install --with-deps

# Test web-eval-agent
uvx --from git+https://github.com/Zeeeepa/web-eval-agent.git webEvalAgent --help
```

#### 4. Environment Variable Issues
```bash
# Reconfigure environment
npm run setup:env

# Validate environment
node -e "require('dotenv').config(); console.log('CODEGEN_API_TOKEN:', !!process.env.CODEGEN_API_TOKEN)"
```

#### 5. Database Issues
```bash
# Reset database
rm backend/codegenapp.db
npm run setup:db

# Check database connection
cd backend && python -c "from database import engine; print('Database OK')"
```

### Getting Help

If you encounter issues:

1. **Check the logs**: `npm run logs`
2. **Validate services**: `npm run validate`
3. **Run diagnostics**: `npm run test:integration`
4. **Check environment**: Ensure all required API keys are set
5. **Restart services**: `npm run dev`

## 🔄 Development Workflow

### Making Changes

1. **Backend changes**: Edit files in `backend/`, server auto-reloads
2. **Frontend changes**: Edit files in `frontend/`, hot reload enabled
3. **Service integration**: Modify `backend/services/` and test with `npm run validate`

### Testing Changes

```bash
# Quick validation
npm run validate:services

# Full integration test
npm run test:integration

# Web-eval-agent flow test
npm run test:web-eval
```

### Adding New Features

1. **Update service classes** in `backend/services/`
2. **Add API endpoints** in `backend/routers/`
3. **Update tests** in `tests/`
4. **Validate integration** with `npm run validate`

## 📦 Production Deployment

### Build for Production
```bash
# Build frontend
npm run frontend:build

# Start production server
npm start
```

### Environment Variables for Production
```bash
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-production-jwt-key
DATABASE_URL=postgresql://user:pass@localhost:5432/codegendb
ALLOWED_ORIGINS=https://yourdomain.com
```

### Process Management
```bash
# Using PM2
npm install -g pm2
pm2 start npm --name "codegenapp" -- start

# Using systemd
sudo systemctl enable codegenapp
sudo systemctl start codegenapp
```

## 🔒 Security Considerations

### API Keys
- Store API keys securely in `.env`
- Never commit `.env` to version control
- Use different keys for development and production
- Rotate keys regularly

### Network Security
- Use HTTPS in production
- Configure CORS properly
- Implement rate limiting
- Use secure headers

### Database Security
- Use strong database passwords
- Enable SSL for database connections
- Regular backups
- Limit database access

## 📈 Performance Optimization

### Backend Performance
- Use connection pooling for databases
- Enable Redis caching
- Configure proper logging levels
- Monitor resource usage

### Frontend Performance
- Build and minify assets
- Enable gzip compression
- Use CDN for static assets
- Implement lazy loading

### Service Performance
- Cache analysis results (Graph-sitter)
- Reuse sandbox environments (Grainchain)
- Optimize browser sessions (Web-eval-agent)
- Batch API calls (Codegen SDK)

## 🎯 Next Steps

After successful installation:

1. **Explore the API**: Visit http://localhost:8000/api/docs
2. **Run the CICD flow**: `npm run test:web-eval`
3. **Test integrations**: `npm run validate:integration`
4. **Build your first pipeline**: Use the integrated API endpoints
5. **Monitor performance**: Check logs and health endpoints

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/api/docs
- **Integration Guide**: [LIBRARY-INTEGRATION-ANALYSIS.md](LIBRARY-INTEGRATION-ANALYSIS.md)
- **Deployment Guide**: [DEPLOYMENT-GUIDE-INTEGRATED.md](DEPLOYMENT-GUIDE-INTEGRATED.md)
- **Troubleshooting**: Check logs in `backend/logs/`

---

**🎉 Congratulations! Your integrated CodegenCICD system is now ready for use.**

