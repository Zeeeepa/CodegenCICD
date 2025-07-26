#!/bin/bash

# CodegenCICD Setup Script
# Automated setup for development and production environments

set -e

echo "🚀 CodegenCICD Setup Script"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_deps=()
    
    if ! command_exists docker; then
        missing_deps+=("docker")
    fi
    
    if ! command_exists docker-compose; then
        missing_deps+=("docker-compose")
    fi
    
    if ! command_exists git; then
        missing_deps+=("git")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and run this script again."
        exit 1
    fi
    
    log_success "All prerequisites are installed"
}

# Setup environment file
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success "Created .env file from .env.example"
        else
            log_info "Creating default .env file..."
            cat > .env << EOF
# Database Configuration
POSTGRES_PASSWORD=codegencd_secure_password

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Codegen API Configuration
CODEGEN_ORG_ID=your_org_id
CODEGEN_API_TOKEN=sk-your-codegen-api-token

# GitHub Integration
GITHUB_TOKEN=github_pat_your_github_token

# AI Services
GEMINI_API_KEY=your_gemini_api_key

# Cloudflare Configuration
CLOUDFLARE_API_KEY=your_cloudflare_api_key
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_WORKER_NAME=your-worker-name
CLOUDFLARE_WORKER_URL=https://your-worker.workers.dev
EOF
            log_success "Created default .env file"
        fi
    else
        log_warning ".env file already exists, skipping creation"
    fi
    
    log_warning "Please review and update the .env file with your actual API keys and configuration"
}

# Build and start services
start_services() {
    log_info "Building and starting services..."
    
    # Build images
    log_info "Building Docker images..."
    docker-compose build
    
    # Start services
    log_info "Starting services..."
    docker-compose up -d
    
    log_success "Services started successfully"
}

# Wait for services to be ready
wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "Backend service is ready"
            break
        fi
        
        log_info "Waiting for backend service... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "Backend service failed to start within expected time"
        log_info "Check service logs with: docker-compose logs backend"
        exit 1
    fi
    
    # Check frontend
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log_success "Frontend service is ready"
    else
        log_warning "Frontend service may not be ready yet"
    fi
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    docker-compose exec -T backend alembic upgrade head
    
    if [ $? -eq 0 ]; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        exit 1
    fi
}

# Run integration tests
run_tests() {
    log_info "Running integration tests..."
    
    if [ -f scripts/test_integration.py ]; then
        python3 scripts/test_integration.py
        
        if [ $? -eq 0 ]; then
            log_success "Integration tests passed"
        else
            log_warning "Some integration tests failed"
        fi
    else
        log_warning "Integration test script not found, skipping tests"
    fi
}

# Display service information
show_service_info() {
    log_success "Setup completed successfully!"
    echo ""
    echo "🌐 Service URLs:"
    echo "   Frontend Dashboard: http://localhost:3000"
    echo "   Backend API:        http://localhost:8000"
    echo "   API Documentation:  http://localhost:8000/docs"
    echo "   Database:           localhost:5432"
    echo "   Redis:              localhost:6379"
    echo ""
    echo "📋 Useful Commands:"
    echo "   View logs:          docker-compose logs -f"
    echo "   Stop services:      docker-compose down"
    echo "   Restart services:   docker-compose restart"
    echo "   Run tests:          python3 scripts/test_integration.py"
    echo ""
    echo "🔧 Configuration:"
    echo "   Environment file:   .env"
    echo "   Update API keys in .env file for full functionality"
    echo ""
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker-compose down
    log_success "Services stopped"
}

# Main setup function
main() {
    local mode=${1:-"full"}
    
    case $mode in
        "check")
            check_prerequisites
            ;;
        "env")
            setup_environment
            ;;
        "build")
            start_services
            ;;
        "test")
            run_tests
            ;;
        "clean")
            cleanup
            ;;
        "full"|*)
            check_prerequisites
            setup_environment
            start_services
            wait_for_services
            run_migrations
            run_tests
            show_service_info
            ;;
    esac
}

# Handle script interruption
trap cleanup INT TERM

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        echo "CodegenCICD Setup Script"
        echo ""
        echo "Usage: $0 [mode]"
        echo ""
        echo "Modes:"
        echo "  full     Complete setup (default)"
        echo "  check    Check prerequisites only"
        echo "  env      Setup environment file only"
        echo "  build    Build and start services only"
        echo "  test     Run integration tests only"
        echo "  clean    Stop and cleanup services"
        echo ""
        exit 0
        ;;
    *)
        main "$1"
        ;;
esac
