#!/bin/bash
set -e

# CodegenCICD Production Deployment Script
echo "🚀 Starting CodegenCICD deployment..."

# Configuration
ENVIRONMENT=${ENVIRONMENT:-production}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}
BACKUP_DIR=${BACKUP_DIR:-./backups}
LOG_FILE=${LOG_FILE:-./logs/deploy.log}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Check if required environment variables are set
    required_vars=(
        "CODEGEN_API_TOKEN"
        "CODEGEN_ORG_ID"
        "GITHUB_TOKEN"
        "GEMINI_API_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Required environment variable $var is not set"
        fi
    done
    
    success "Prerequisites check passed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    directories=(
        "./logs"
        "./data"
        "./backups"
        "./docker/postgres"
        "./docker/grafana/provisioning/dashboards"
        "./docker/grafana/provisioning/datasources"
        "./docker/nginx/ssl"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log "Created directory: $dir"
    done
    
    success "Directories created"
}

# Backup existing data
backup_data() {
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log "Creating backup of existing data..."
        
        backup_timestamp=$(date +%Y%m%d_%H%M%S)
        backup_path="$BACKUP_DIR/backup_$backup_timestamp"
        
        mkdir -p "$backup_path"
        
        # Backup database if it exists
        if docker-compose ps postgres | grep -q "Up"; then
            log "Backing up PostgreSQL database..."
            docker-compose exec -T postgres pg_dump -U codegencd codegencd > "$backup_path/database.sql"
            success "Database backup created: $backup_path/database.sql"
        fi
        
        # Backup application data
        if [[ -d "./data" ]]; then
            log "Backing up application data..."
            cp -r ./data "$backup_path/"
            success "Application data backup created"
        fi
        
        # Backup logs
        if [[ -d "./logs" ]]; then
            log "Backing up logs..."
            cp -r ./logs "$backup_path/"
            success "Logs backup created"
        fi
        
        success "Backup completed: $backup_path"
    else
        log "Skipping backup for non-production environment"
    fi
}

# Pull latest images
pull_images() {
    log "Pulling latest Docker images..."
    
    docker-compose -f "$COMPOSE_FILE" pull
    
    success "Images pulled successfully"
}

# Build application images
build_images() {
    log "Building application images..."
    
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    success "Images built successfully"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Start database first
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    timeout=60
    counter=0
    
    while ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U codegencd -d codegencd; do
        sleep 2
        counter=$((counter + 2))
        if [[ $counter -ge $timeout ]]; then
            error "Database failed to start within $timeout seconds"
        fi
    done
    
    # Run migrations
    docker-compose -f "$COMPOSE_FILE" run --rm app python -c "
import asyncio
from backend.database import init_db

async def run_migrations():
    await init_db()
    print('✅ Database migrations completed')

asyncio.run(run_migrations())
"
    
    success "Database migrations completed"
}

# Start services
start_services() {
    log "Starting all services..."
    
    # Start core services first
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    
    # Wait a bit for core services to stabilize
    sleep 5
    
    # Start application services
    docker-compose -f "$COMPOSE_FILE" up -d app worker scheduler
    
    # Wait for application to be ready
    log "Waiting for application to be ready..."
    timeout=120
    counter=0
    
    while ! curl -f http://localhost:8000/health &> /dev/null; do
        sleep 5
        counter=$((counter + 5))
        if [[ $counter -ge $timeout ]]; then
            error "Application failed to start within $timeout seconds"
        fi
        log "Waiting for application... ($counter/$timeout seconds)"
    done
    
    # Start monitoring services
    docker-compose -f "$COMPOSE_FILE" up -d prometheus grafana
    
    # Start reverse proxy
    docker-compose -f "$COMPOSE_FILE" up -d nginx
    
    success "All services started successfully"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Check service health
    services=("postgres" "redis" "app" "worker" "scheduler" "nginx")
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            success "✅ $service is running"
        else
            error "❌ $service is not running"
        fi
    done
    
    # Check application health endpoint
    if curl -f http://localhost:8000/health &> /dev/null; then
        success "✅ Application health check passed"
    else
        error "❌ Application health check failed"
    fi
    
    # Check if frontend is accessible
    if curl -f http://localhost/ &> /dev/null; then
        success "✅ Frontend is accessible"
    else
        warning "⚠️ Frontend may not be accessible"
    fi
    
    # Check metrics endpoint
    if curl -f http://localhost:8002/metrics &> /dev/null; then
        success "✅ Metrics endpoint is accessible"
    else
        warning "⚠️ Metrics endpoint may not be accessible"
    fi
    
    success "Deployment verification completed"
}

# Show deployment summary
show_summary() {
    log "Deployment Summary:"
    echo ""
    echo "🌐 Application URL: http://localhost"
    echo "📊 Grafana Dashboard: http://localhost:3000 (admin/admin)"
    echo "📈 Prometheus: http://localhost:9090"
    echo "🔍 Health Check: http://localhost:8000/health"
    echo "📊 Metrics: http://localhost:8002/metrics"
    echo ""
    echo "📁 Logs: ./logs/"
    echo "💾 Data: ./data/"
    echo "🔄 Backups: ./backups/"
    echo ""
    echo "🐳 Docker Compose Commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop services: docker-compose down"
    echo "  Restart services: docker-compose restart"
    echo "  View status: docker-compose ps"
    echo ""
    success "🎉 CodegenCICD deployment completed successfully!"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    # Add any cleanup tasks here
}

# Signal handlers
trap cleanup EXIT
trap 'error "Deployment interrupted"' INT TERM

# Main deployment flow
main() {
    log "Starting CodegenCICD deployment process..."
    
    check_prerequisites
    create_directories
    backup_data
    pull_images
    build_images
    run_migrations
    start_services
    verify_deployment
    show_summary
    
    success "🚀 Deployment completed successfully!"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "backup")
        backup_data
        ;;
    "migrate")
        run_migrations
        ;;
    "verify")
        verify_deployment
        ;;
    "stop")
        log "Stopping all services..."
        docker-compose -f "$COMPOSE_FILE" down
        success "All services stopped"
        ;;
    "restart")
        log "Restarting all services..."
        docker-compose -f "$COMPOSE_FILE" restart
        success "All services restarted"
        ;;
    "logs")
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
    "status")
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
    "clean")
        log "Cleaning up Docker resources..."
        docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
        docker system prune -f
        success "Cleanup completed"
        ;;
    *)
        echo "Usage: $0 {deploy|backup|migrate|verify|stop|restart|logs|status|clean}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  backup  - Create backup of data"
        echo "  migrate - Run database migrations"
        echo "  verify  - Verify deployment health"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - Show service logs"
        echo "  status  - Show service status"
        echo "  clean   - Clean up Docker resources"
        exit 1
        ;;
esac

