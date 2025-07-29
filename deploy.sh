#!/bin/bash

# CodegenCICD Dashboard - Deployment Script
# This script installs all dependencies and sets up the environment

set -e  # Exit on any error

echo "🚀 CodegenCICD Dashboard - Deployment Setup"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root (not recommended)
if [[ $EUID -eq 0 ]]; then
   print_warning "Running as root is not recommended. Consider using a regular user account."
   read -p "Continue anyway? (y/N): " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       exit 1
   fi
fi

# Detect OS
print_info "Detecting operating system..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    print_status "Detected Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    print_status "Detected macOS"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    print_status "Detected Windows (Git Bash/Cygwin)"
else
    print_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

# Check for required system dependencies
print_info "Checking system dependencies..."

# Check for Python 3.8+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [[ $PYTHON_MAJOR -eq 3 ]] && [[ $PYTHON_MINOR -ge 8 ]]; then
        print_status "Python $PYTHON_VERSION found"
        PYTHON_CMD="python3"
    else
        print_error "Python 3.8+ required, found $PYTHON_VERSION"
        exit 1
    fi
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [[ $PYTHON_MAJOR -eq 3 ]] && [[ $PYTHON_MINOR -ge 8 ]]; then
        print_status "Python $PYTHON_VERSION found"
        PYTHON_CMD="python"
    else
        print_error "Python 3.8+ required, found $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3.8+ is required but not installed"
    print_info "Please install Python 3.8+ and try again"
    exit 1
fi

# Check for Node.js 16+
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | sed 's/v//')
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
    
    if [[ $NODE_MAJOR -ge 16 ]]; then
        print_status "Node.js $NODE_VERSION found"
    else
        print_error "Node.js 16+ required, found $NODE_VERSION"
        exit 1
    fi
else
    print_error "Node.js 16+ is required but not installed"
    print_info "Please install Node.js 16+ and try again"
    exit 1
fi

# Check for npm
if ! command -v npm &> /dev/null; then
    print_error "npm is required but not installed"
    exit 1
else
    print_status "npm $(npm --version) found"
fi

# Check for git
if ! command -v git &> /dev/null; then
    print_error "git is required but not installed"
    exit 1
else
    print_status "git $(git --version | cut -d' ' -f3) found"
fi

print_info "All system dependencies satisfied!"

# Setup Python virtual environment
print_info "Setting up Python virtual environment..."
cd backend

if [[ ! -d "venv" ]]; then
    print_info "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
if [[ "$OS" == "windows" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_info "Installing Python dependencies..."
if [[ -f "requirements.txt" ]]; then
    pip install -r requirements.txt
    print_status "Python dependencies installed"
else
    print_error "requirements.txt not found in backend directory"
    exit 1
fi

cd ..

# Setup Node.js dependencies
print_info "Setting up Node.js dependencies..."
cd frontend

if [[ -f "package.json" ]]; then
    print_info "Installing Node.js dependencies..."
    npm install
    print_status "Node.js dependencies installed"
else
    print_error "package.json not found in frontend directory"
    exit 1
fi

cd ..

# Create .env.example if it doesn't exist
print_info "Setting up environment configuration..."
if [[ ! -f ".env.example" ]]; then
    cat > .env.example << 'EOF'
# CodegenCICD Dashboard Environment Configuration
# Copy this file to .env and fill in your actual values

# Codegen API Configuration
CODEGEN_ORG_ID=your_org_id_here
CODEGEN_API_TOKEN=your_codegen_api_token_here

# GitHub Integration
GITHUB_TOKEN=your_github_token_here

# AI Services
GEMINI_API_KEY=your_gemini_api_key_here

# Cloudflare Configuration (for webhooks)
CLOUDFLARE_API_KEY=your_cloudflare_api_key_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=your_cloudflare_worker_url_here

# Service Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3001
BACKEND_HOST=localhost
FRONTEND_HOST=localhost

# External Service URLs (for integrations)
GRAINCHAIN_URL=http://localhost:8001
GRAPH_SITTER_URL=http://localhost:8002
WEB_EVAL_AGENT_URL=http://localhost:8003
EOF
    print_status "Created .env.example template"
else
    print_status ".env.example already exists"
fi

# Create logs directory
print_info "Creating logs directory..."
mkdir -p logs
print_status "Logs directory created"

# Set executable permissions on scripts
print_info "Setting script permissions..."
chmod +x deploy.sh 2>/dev/null || true
chmod +x start.sh 2>/dev/null || true

print_status "Deployment setup completed successfully!"

echo ""
echo "🎉 Installation Complete!"
echo "========================"
echo ""
print_info "Next steps:"
echo "1. Copy .env.example to .env and configure your API keys:"
echo "   cp .env.example .env"
echo "   nano .env  # or use your preferred editor"
echo ""
echo "2. Start the dashboard:"
echo "   ./start.sh"
echo ""
print_info "The dashboard will be available at:"
echo "   Frontend: http://localhost:3001"
echo "   Backend:  http://localhost:8000"
echo ""
print_status "Ready to launch your AI-powered CI/CD dashboard! 🚀"

