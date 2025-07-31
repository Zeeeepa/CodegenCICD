# 🚀 CodegenCICD Platform Deployment Guide

## 📋 Prerequisites

### System Requirements
- **Node.js**: v18.0.0 or higher
- **Python**: 3.9 or higher
- **npm**: v8.0.0 or higher
- **Git**: Latest version

### Required API Keys
```bash
# Environment Variables Required
GEMINI_API_KEY=your_gemini_api_key_here
CODEGEN_API_TOKEN=your_codegen_api_token_here
GITHUB_TOKEN=your_github_token_here
CLOUDFLARE_API_KEY=your_cloudflare_api_key_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
CLOUDFLARE_WORKER_URL=your_cloudflare_worker_url_here
```

## 🔧 Quick Start Deployment

### Step 1: Clone and Setup
```bash
# Clone the repository
git clone https://github.com/Zeeeepa/CodegenCICD.git
cd CodegenCICD

# Make deployment script executable
chmod +x deploy.sh
chmod +x start.sh
```

### Step 2: Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
nano .env
```

### Step 3: One-Command Deployment
```bash
# Deploy everything (backend + frontend + services)
./deploy.sh
```

## 🎯 Manual Step-by-Step Deployment

### Backend Deployment

#### 1. Setup Python Environment
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment
```bash
# Create backend .env file
cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key_here
CODEGEN_API_TOKEN=your_codegen_api_token_here
GITHUB_TOKEN=your_github_token_here
CLOUDFLARE_API_KEY=your_cloudflare_api_key_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
CLOUDFLARE_WORKER_URL=your_cloudflare_worker_url_here
DATABASE_URL=sqlite:///./codegencd.db
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
EOF
```

#### 3. Start Backend Server
```bash
# Development mode
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend Deployment

#### 1. Setup Node.js Environment
```bash
# Navigate to frontend directory (in new terminal)
cd frontend

# Install dependencies
npm install
```

#### 2. Configure Frontend Environment
```bash
# Create frontend .env file
cat > .env << EOF
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENVIRONMENT=development
EOF
```

#### 3. Start Frontend Server
```bash
# Development mode
npm start

# Production build
npm run build
npm install -g serve
serve -s build -l 3000
```

## 🌐 Production Deployment Options

### Option 1: Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: PM2 Process Manager
```bash
# Install PM2 globally
npm install -g pm2

# Start backend with PM2
cd backend
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name "codegencd-backend"

# Start frontend with PM2
cd ../frontend
npm run build
pm2 serve build 3000 --name "codegencd-frontend" --spa

# Save PM2 configuration
pm2 save
pm2 startup
```

### Option 3: Nginx + Systemd
```bash
# Create systemd service for backend
sudo tee /etc/systemd/system/codegencd-backend.service > /dev/null << EOF
[Unit]
Description=CodegenCICD Backend
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/path/to/CodegenCICD/backend
Environment=PATH=/path/to/CodegenCICD/backend/venv/bin
ExecStart=/path/to/CodegenCICD/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable codegencd-backend
sudo systemctl start codegencd-backend

# Configure Nginx
sudo tee /etc/nginx/sites-available/codegencd > /dev/null << EOF
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/CodegenCICD/frontend/build;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/codegencd /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔍 Verification & Testing

### Health Check Endpoints
```bash
# Backend health check
curl http://localhost:8000/health

# API endpoints test
curl http://localhost:8000/api/projects
curl http://localhost:8000/api/agent-runs
curl http://localhost:8000/api/webhooks/status
```

### Frontend Access
```bash
# Open in browser
open http://localhost:3000

# Or test with curl
curl http://localhost:3000
```

### Web-Eval-Agent Integration Test
```bash
# Run comprehensive validation
cd ../web-eval-agent
GEMINI_API_KEY=your_key_here node validation-test.js

# Run full CICD cycle test
GEMINI_API_KEY=your_key_here node full-cicd-cycle-test.js
```

## 🛠️ Troubleshooting

### Common Issues

#### Backend Issues
```bash
# Check backend logs
tail -f backend/logs/app.log

# Test database connection
cd backend
python -c "from database import engine; print('Database OK')"

# Check API endpoints
curl -v http://localhost:8000/docs
```

#### Frontend Issues
```bash
# Check frontend build
cd frontend
npm run build

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check proxy configuration
cat package.json | grep proxy
```

#### Environment Issues
```bash
# Verify environment variables
printenv | grep -E "(GEMINI|CODEGEN|GITHUB|CLOUDFLARE)"

# Test API keys
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

### Performance Optimization

#### Backend Optimization
```bash
# Use production ASGI server
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Enable caching
pip install redis
# Configure Redis in backend/config.py
```

#### Frontend Optimization
```bash
# Optimize build
npm run build
npm install -g serve
serve -s build -l 3000

# Enable compression
# Configure in nginx.conf or use CDN
```

## 📊 Monitoring & Logging

### Application Monitoring
```bash
# Install monitoring tools
pip install prometheus-client
npm install @prometheus/client

# Setup log aggregation
tail -f backend/logs/*.log
tail -f frontend/logs/*.log
```

### Health Monitoring
```bash
# Create health check script
cat > health-check.sh << 'EOF'
#!/bin/bash
echo "Checking CodegenCICD Platform Health..."

# Backend health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend: Healthy"
else
    echo "❌ Backend: Unhealthy"
fi

# Frontend health
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend: Healthy"
else
    echo "❌ Frontend: Unhealthy"
fi

# Database health
if python3 -c "from backend.database import engine; engine.connect()" 2>/dev/null; then
    echo "✅ Database: Healthy"
else
    echo "❌ Database: Unhealthy"
fi
EOF

chmod +x health-check.sh
./health-check.sh
```

## 🚀 Quick Commands Summary

```bash
# Complete deployment
./deploy.sh

# Start services manually
./start.sh

# Backend only
cd backend && uvicorn main:app --reload

# Frontend only
cd frontend && npm start

# Run tests
python -m pytest tests/
npm test

# Health check
curl http://localhost:8000/health
curl http://localhost:3000

# Web-eval-agent validation
cd ../web-eval-agent && node validation-test.js
```

## 🎯 Next Steps

1. **Access the platform**: http://localhost:3000
2. **API documentation**: http://localhost:8000/docs
3. **Run web-eval-agent tests**: Follow WEB-EVAL-AGENT-CICD-INSTRUCTIONS.md
4. **Configure webhooks**: Set up Cloudflare Worker URLs
5. **Test complete CICD flow**: Create agent runs and validate pipeline

Your CodegenCICD platform is now ready for production use! 🎉
