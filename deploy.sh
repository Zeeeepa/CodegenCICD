#!/bin/bash

# CodegenCICD Dashboard Deployment Script
# This script deploys the complete system and runs end-to-end tests

set -e

echo "🚀 Starting CodegenCICD Dashboard Deployment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys and configuration"
    echo "   Required: CODEGEN_API_TOKEN, GITHUB_TOKEN, GEMINI_API_KEY"
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p nginx/ssl
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources
mkdir -p logs

# Build and start services
echo "🐳 Building and starting Docker services..."
docker-compose down -v 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
services=("postgres" "redis" "backend" "frontend")
for service in "${services[@]}"; do
    if docker-compose ps $service | grep -q "Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service failed to start"
        docker-compose logs $service
        exit 1
    fi
done

# Initialize database
echo "🗄️  Initializing database..."
docker-compose exec -T backend python -c "
from backend.database import create_tables
create_tables()
print('Database tables created successfully')
"

# Create sample project for testing
echo "📋 Creating sample project..."
docker-compose exec -T backend python -c "
from backend.database import SessionLocal
from backend.models.project import Project
from backend.models.configuration import ProjectConfiguration

db = SessionLocal()

# Check if sample project already exists
existing = db.query(Project).filter(Project.name == 'CodegenCICD-Test').first()
if not existing:
    project = Project(
        name='CodegenCICD-Test',
        description='Sample project for testing the complete CI/CD flow',
        github_repository='https://github.com/Zeeeepa/CodegenCICD.git',
        default_branch='main',
        webhook_url='https://webhook-gateway.pixeliumperfecto.workers.dev/webhook',
        auto_confirm_plan=True,
        auto_merge_validated_pr=False
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create configuration
    config = ProjectConfiguration(
        project_id=project.id,
        repository_rules='Use TypeScript for all frontend code. Follow React best practices.',
        setup_commands='echo \"Setting up test environment...\"\necho \"Installation complete\"',
        planning_statement='Project Context: <Project=\"CodegenCICD-Test\">\n\nYou are working on the CodegenCICD Dashboard test project. Follow best practices and create comprehensive test files.'
    )
    db.add(config)
    db.commit()
    
    print(f'Sample project created with ID: {project.id}')
else:
    print('Sample project already exists')

db.close()
"

echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Access Points:"
echo "   Dashboard:  http://localhost:3000"
echo "   API Docs:   http://localhost:8000/docs"
echo "   Monitoring: http://localhost:3001 (admin/admin)"
echo ""
echo "🧪 To run end-to-end tests:"
echo "   python tests/test_complete_flow.py"
echo ""
echo "📝 Next steps:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Select 'CodegenCICD-Test' project from dropdown"
echo "   3. Click 'Agent Run' and enter: 'Create test.py in root of the project which would test all features and functions of the project'"
echo "   4. Watch the complete CI/CD flow in action!"
