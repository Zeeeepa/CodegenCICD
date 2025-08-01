#!/bin/bash

# 🚀 CodegenCICD Platform Quick Start Script
# This script will set up and start the entire platform

set -e

echo "🚀 Starting CodegenCICD Platform Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js v18+ from https://nodejs.org/"
        exit 1
    fi
    
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        print_error "Node.js version must be 18 or higher. Current version: $(node --version)"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.9+ from https://python.org/"
        exit 1
    fi
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm."
        exit 1
    fi
    
    print_success "All prerequisites are satisfied!"
}

# Setup environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_warning "Created .env file from template. Please edit it with your API keys."
        else
            cat > .env << EOF
# CodegenCICD Platform Environment Variables
GEMINI_API_KEY=your_gemini_api_key_here
CODEGEN_API_TOKEN=your_codegen_api_token_here
GITHUB_TOKEN=your_github_token_here
CLOUDFLARE_API_KEY=your_cloudflare_api_key_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
CLOUDFLARE_WORKER_URL=your_cloudflare_worker_url_here
DATABASE_URL=sqlite:///./codegencd.db
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENVIRONMENT=development
EOF
            print_warning "Created .env file with placeholders. Please edit it with your actual API keys."
        fi
        
        print_warning "Please edit the .env file with your actual API keys before continuing."
        read -p "Press Enter after you've updated the .env file with your API keys..."
    fi
    
    print_success "Environment configuration ready!"
}

# Setup backend
setup_backend() {
    print_status "Setting up backend..."
    
    cd backend
    
    # Check if virtual environment exists and is valid
    if [ -d "venv" ]; then
        # Check if activation script exists
        if [ -f "venv/bin/activate" ]; then
            print_status "Virtual environment already exists and is valid"
        else
            print_warning "Virtual environment exists but is corrupted, recreating..."
            rm -rf venv
            print_status "Creating Python virtual environment..."
            python3 -m venv venv
            if [ $? -ne 0 ]; then
                print_error "Failed to create virtual environment. Please install python3-venv:"
                print_error "sudo apt install python3-venv"
                exit 1
            fi
            
            # Wait a moment for filesystem to sync
            sleep 1
            
            # Verify the virtual environment was created successfully
            if [ ! -f "venv/bin/activate" ]; then
                print_error "Virtual environment was created but activation script is missing!"
                print_error "This might be a filesystem sync issue. Please try running the script again."
                exit 1
            fi
            print_status "Virtual environment recreated successfully"
        fi
    else
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment. Please install python3-venv:"
            print_error "sudo apt install python3-venv"
            exit 1
        fi
        
        # Wait a moment for filesystem to sync
        sleep 1
        
        # Verify the virtual environment was created successfully
        if [ ! -f "venv/bin/activate" ]; then
            print_error "Virtual environment was created but activation script is missing!"
            print_error "This might be a filesystem sync issue. Please try running the script again."
            exit 1
        fi
        print_status "Virtual environment created successfully"
    fi
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_status "Virtual environment activated successfully"
    else
        print_error "Virtual environment activation script not found!"
        print_error "Directory contents:"
        ls -la venv/ 2>/dev/null || echo "venv directory does not exist"
        exit 1
    fi
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        print_error "Failed to install Python dependencies"
        exit 1
    fi
    
    # Copy environment file
    if [ -f "../.env" ]; then
        cp ../.env .env
    fi
    
    cd ..
    print_success "Backend setup complete!"
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    cd frontend
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        print_error "Failed to install Node.js dependencies"
        exit 1
    fi
    
    # Install Tailwind CSS properly (no more CDN warnings!)
    print_status "Setting up Tailwind CSS..."
    if [ ! -f "tailwind.config.js" ]; then
        npx tailwindcss init -p
    fi
    
    # Copy environment file
    if [ -f "../.env" ]; then
        cp ../.env .env
    fi
    
    cd ..
    print_success "Frontend setup complete!"
}

# Start backend server
start_backend() {
    print_status "Starting backend server..."
    
    cd backend
    source venv/bin/activate
    
    # Set PYTHONPATH to include project root for backend imports
    export PYTHONPATH="$(pwd)/..:$PYTHONPATH"
    
    # Start backend in background
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    
    cd ..
    
    # Wait for backend to start
    print_status "Waiting for backend to start..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Backend server started successfully on http://localhost:8000"
            return 0
        fi
        sleep 1
    done
    
    print_error "Backend failed to start. Check backend.log for details."
    return 1
}

# Start frontend server
start_frontend() {
    print_status "Starting frontend server..."
    
    cd frontend
    
    # Start frontend in background
    nohup npm start > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    
    cd ..
    
    # Wait for frontend to start
    print_status "Waiting for frontend to start..."
    for i in {1..60}; do
        if curl -f http://localhost:3000 > /dev/null 2>&1; then
            print_success "Frontend server started successfully on http://localhost:3000"
            return 0
        fi
        sleep 1
    done
    
    print_error "Frontend failed to start. Check frontend.log for details."
    return 1
}

# Health check
health_check() {
    print_status "Performing health check..."
    
    # Check backend
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "✅ Backend: Healthy (http://localhost:8000)"
    else
        print_error "❌ Backend: Unhealthy"
        return 1
    fi
    
    # Check frontend
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        print_success "✅ Frontend: Healthy (http://localhost:3000)"
    else
        print_error "❌ Frontend: Unhealthy"
        return 1
    fi
    
    print_success "All services are healthy!"
}

# Stop services
stop_services() {
    print_status "Stopping services..."
    
    if [ -f backend.pid ]; then
        BACKEND_PID=$(cat backend.pid)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID
            print_success "Backend stopped"
        fi
        rm -f backend.pid
    fi
    
    if [ -f frontend.pid ]; then
        FRONTEND_PID=$(cat frontend.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID
            print_success "Frontend stopped"
        fi
        rm -f frontend.pid
    fi
    
    # Kill any remaining processes
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "react-scripts start" 2>/dev/null || true
}

# Show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start the platform (default)"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  status    - Check service status"
    echo "  logs      - Show service logs"
    echo "  help      - Show this help message"
}

# Show logs
show_logs() {
    echo "=== Backend Logs ==="
    if [ -f backend.log ]; then
        tail -n 20 backend.log
    else
        echo "No backend logs found"
    fi
    
    echo ""
    echo "=== Frontend Logs ==="
    if [ -f frontend.log ]; then
        tail -n 20 frontend.log
    else
        echo "No frontend logs found"
    fi
}

# Check status
check_status() {
    print_status "Checking service status..."
    
    # Check if processes are running
    if [ -f backend.pid ] && kill -0 $(cat backend.pid) 2>/dev/null; then
        print_success "✅ Backend: Running (PID: $(cat backend.pid))"
    else
        print_error "❌ Backend: Not running"
    fi
    
    if [ -f frontend.pid ] && kill -0 $(cat frontend.pid) 2>/dev/null; then
        print_success "✅ Frontend: Running (PID: $(cat frontend.pid))"
    else
        print_error "❌ Frontend: Not running"
    fi
    
    # Check HTTP endpoints
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "✅ Backend HTTP: Responding"
    else
        print_error "❌ Backend HTTP: Not responding"
    fi
    
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        print_success "✅ Frontend HTTP: Responding"
    else
        print_error "❌ Frontend HTTP: Not responding"
    fi
}

# Main execution
main() {
    case "${1:-start}" in
        "start")
            echo "🚀 CodegenCICD Platform - Quick Start"
            echo "====================================="
            
            check_prerequisites
            setup_environment
            setup_backend
            setup_frontend
            
            # Stop any existing services
            stop_services
            
            start_backend
            if [ $? -ne 0 ]; then
                print_error "Failed to start backend. Exiting."
                exit 1
            fi
            
            start_frontend
            if [ $? -ne 0 ]; then
                print_error "Failed to start frontend. Exiting."
                exit 1
            fi
            
            health_check
            
            # Test Codegen API integration
            print_status "Testing Codegen API integration..."
            if python3 tests/test_codegen_api.py; then
                print_success "✅ Codegen API integration validated"
            else
                print_warning "⚠️  Codegen API test failed - check your API credentials"
            fi
            
            echo ""
            echo "🎉 CodegenCICD Platform is now running!"
            echo "====================================="
            echo "📊 Frontend Dashboard: http://localhost:3000"
            echo "🔧 Backend API: http://localhost:8000"
            echo "📚 API Documentation: http://localhost:8000/docs"
            echo ""
            echo "📝 Logs:"
            echo "   Backend: tail -f backend.log"
            echo "   Frontend: tail -f frontend.log"
            echo ""
            echo "🛑 To stop: ./quick-start.sh stop"
            echo ""
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 2
            $0 start
            ;;
        "status")
            check_status
            ;;
        "logs")
            show_logs
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C
trap 'echo ""; print_warning "Interrupted. Stopping services..."; stop_services; exit 1' INT

# Run main function
main "$@"
