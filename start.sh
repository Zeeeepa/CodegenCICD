#!/bin/bash

# CodegenCICD Dashboard - Start Script
# This script validates environment variables and launches the services

set -e  # Exit on any error

echo "🚀 CodegenCICD Dashboard - Starting Services"
echo "============================================="

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

# Check if deployment was run
if [[ ! -d "backend/venv" ]] || [[ ! -d "frontend/node_modules" ]]; then
    print_error "Dependencies not installed. Please run ./deploy.sh first"
    exit 1
fi

# Load environment variables if .env exists
if [[ -f ".env" ]]; then
    print_info "Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
    print_status "Environment variables loaded"
else
    print_warning ".env file not found"
fi

# Required environment variables
REQUIRED_VARS=(
    "CODEGEN_ORG_ID"
    "CODEGEN_API_TOKEN"
    "GITHUB_TOKEN"
    "GEMINI_API_KEY"
    "CLOUDFLARE_API_KEY"
    "CLOUDFLARE_ACCOUNT_ID"
    "CLOUDFLARE_WORKER_URL"
)

# Optional environment variables with defaults
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3001}
BACKEND_HOST=${BACKEND_HOST:-localhost}
FRONTEND_HOST=${FRONTEND_HOST:-localhost}

# Function to prompt for missing environment variable
prompt_for_var() {
    local var_name=$1
    local var_description=$2
    local is_secret=${3:-false}
    
    echo ""
    print_info "Missing required variable: $var_name"
    echo "Description: $var_description"
    
    if [[ "$is_secret" == "true" ]]; then
        echo -n "Enter value (input will be hidden): "
        read -s var_value
        echo ""
    else
        echo -n "Enter value: "
        read var_value
    fi
    
    if [[ -z "$var_value" ]]; then
        print_error "Value cannot be empty"
        return 1
    fi
    
    # Export the variable
    export $var_name="$var_value"
    
    # Add to .env file
    if [[ -f ".env" ]]; then
        # Remove existing line if present
        sed -i.bak "/^$var_name=/d" .env 2>/dev/null || true
    fi
    echo "$var_name=$var_value" >> .env
    
    return 0
}

# Check and prompt for missing environment variables
print_info "Validating environment variables..."
missing_vars=()

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    print_warning "Some required environment variables are missing"
    echo ""
    
    for var in "${missing_vars[@]}"; do
        case $var in
            "CODEGEN_ORG_ID")
                prompt_for_var "$var" "Your Codegen organization ID (numeric)" false
                ;;
            "CODEGEN_API_TOKEN")
                prompt_for_var "$var" "Your Codegen API token (starts with sk-)" true
                ;;
            "GITHUB_TOKEN")
                prompt_for_var "$var" "Your GitHub personal access token" true
                ;;
            "GEMINI_API_KEY")
                prompt_for_var "$var" "Your Google Gemini API key" true
                ;;
            "CLOUDFLARE_API_KEY")
                prompt_for_var "$var" "Your Cloudflare API key" true
                ;;
            "CLOUDFLARE_ACCOUNT_ID")
                prompt_for_var "$var" "Your Cloudflare account ID" false
                ;;
            "CLOUDFLARE_WORKER_URL")
                prompt_for_var "$var" "Your Cloudflare Worker webhook URL" false
                ;;
        esac
    done
    
    print_status "All environment variables configured"
    
    # Reload environment variables
    export $(grep -v '^#' .env | xargs)
else
    print_status "All required environment variables are set"
fi

# Validate API tokens format (basic validation)
print_info "Validating API token formats..."

if [[ ! "$CODEGEN_API_TOKEN" =~ ^sk- ]]; then
    print_warning "CODEGEN_API_TOKEN should start with 'sk-'"
fi

if [[ ! "$GITHUB_TOKEN" =~ ^(ghp_|github_pat_) ]]; then
    print_warning "GITHUB_TOKEN should start with 'ghp_' or 'github_pat_'"
fi

if [[ ! "$GEMINI_API_KEY" =~ ^AIza ]]; then
    print_warning "GEMINI_API_KEY should start with 'AIza'"
fi

# Check for port conflicts
print_info "Checking for port conflicts..."

check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $port is already in use (needed for $service)"
        echo -n "Kill existing process and continue? (y/N): "
        read -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Killing process on port $port..."
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
            sleep 2
            print_status "Port $port freed"
        else
            print_error "Cannot start $service on port $port"
            exit 1
        fi
    else
        print_status "Port $port is available for $service"
    fi
}

check_port $BACKEND_PORT "backend"
check_port $FRONTEND_PORT "frontend"

# Create logs directory
mkdir -p logs

# Function to start backend
start_backend() {
    print_info "Starting backend server..."
    cd backend
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        if [[ -f "venv/Scripts/activate" ]]; then
            source venv/Scripts/activate
        else
            print_error "Virtual environment activation script not found at venv/Scripts/activate"
            print_error "Please run ./deploy.sh to set up the environment properly"
            exit 1
        fi
    else
        if [[ -f "venv/bin/activate" ]]; then
            source venv/bin/activate
        else
            print_error "Virtual environment activation script not found at venv/bin/activate"
            print_error "Please run ./deploy.sh to set up the environment properly"
            exit 1
        fi
    fi
    
    # Start backend server in background
    nohup python main.py > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../logs/backend.pid
    
    cd ..
    
    # Wait for backend to start
    print_info "Waiting for backend to start..."
    for i in {1..30}; do
        if curl -s http://$BACKEND_HOST:$BACKEND_PORT/health > /dev/null 2>&1; then
            print_status "Backend started successfully (PID: $BACKEND_PID)"
            return 0
        fi
        sleep 1
    done
    
    print_error "Backend failed to start within 30 seconds"
    print_info "Check logs: tail -f logs/backend.log"
    return 1
}

# Function to start frontend
start_frontend() {
    print_info "Starting frontend server..."
    cd frontend
    
    # Set environment variables for React
    export REACT_APP_BACKEND_URL="http://$BACKEND_HOST:$BACKEND_PORT"
    export PORT=$FRONTEND_PORT
    
    # Start frontend server in background
    nohup npm start > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../logs/frontend.pid
    
    cd ..
    
    # Wait for frontend to start
    print_info "Waiting for frontend to start..."
    for i in {1..60}; do
        if curl -s http://$FRONTEND_HOST:$FRONTEND_PORT > /dev/null 2>&1; then
            print_status "Frontend started successfully (PID: $FRONTEND_PID)"
            return 0
        fi
        sleep 1
    done
    
    print_error "Frontend failed to start within 60 seconds"
    print_info "Check logs: tail -f logs/frontend.log"
    return 1
}

# Function to cleanup on exit
cleanup() {
    print_info "Shutting down services..."
    
    if [[ -f "logs/backend.pid" ]]; then
        BACKEND_PID=$(cat logs/backend.pid)
        kill $BACKEND_PID 2>/dev/null || true
        rm -f logs/backend.pid
    fi
    
    if [[ -f "logs/frontend.pid" ]]; then
        FRONTEND_PID=$(cat logs/frontend.pid)
        kill $FRONTEND_PID 2>/dev/null || true
        rm -f logs/frontend.pid
    fi
    
    print_status "Services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start services
print_info "Starting CodegenCICD Dashboard services..."

if start_backend && start_frontend; then
    echo ""
    echo "🎉 CodegenCICD Dashboard is now running!"
    echo "========================================"
    echo ""
    print_info "Access URLs:"
    echo "   Frontend (React UI): http://$FRONTEND_HOST:$FRONTEND_PORT"
    echo "   Backend API:         http://$BACKEND_HOST:$BACKEND_PORT"
    echo "   API Health Check:    http://$BACKEND_HOST:$BACKEND_PORT/health"
    echo "   API Documentation:   http://$BACKEND_HOST:$BACKEND_PORT/docs"
    echo ""
    print_info "Service PIDs:"
    echo "   Backend:  $(cat logs/backend.pid 2>/dev/null || echo 'N/A')"
    echo "   Frontend: $(cat logs/frontend.pid 2>/dev/null || echo 'N/A')"
    echo ""
    print_info "Logs:"
    echo "   Backend:  tail -f logs/backend.log"
    echo "   Frontend: tail -f logs/frontend.log"
    echo "   Both:     tail -f logs/backend.log logs/frontend.log"
    echo ""
    print_info "To stop services: Press Ctrl+C or kill the PIDs above"
    echo ""
    print_status "Dashboard ready! Open http://$FRONTEND_HOST:$FRONTEND_PORT in your browser 🚀"
    
    # Keep script running
    while true; do
        sleep 1
        
        # Check if services are still running
        if ! kill -0 $(cat logs/backend.pid 2>/dev/null) 2>/dev/null; then
            print_error "Backend process died unexpectedly"
            break
        fi
        
        if ! kill -0 $(cat logs/frontend.pid 2>/dev/null) 2>/dev/null; then
            print_error "Frontend process died unexpectedly"
            break
        fi
    done
else
    print_error "Failed to start services"
    cleanup
    exit 1
fi
