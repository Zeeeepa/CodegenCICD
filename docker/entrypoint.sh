#!/bin/bash
set -e

# CodegenCICD Production Entrypoint Script
echo "🚀 Starting CodegenCICD application..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
python3 -c "
import time
import psycopg2
import os
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL', 'postgresql://codegencd:codegencd@postgres:5432/codegencd')
parsed = urlparse(db_url)

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]  # Remove leading slash
        )
        conn.close()
        print('✅ Database connection successful')
        break
    except psycopg2.OperationalError as e:
        retry_count += 1
        print(f'❌ Database connection failed (attempt {retry_count}/{max_retries}): {e}')
        if retry_count >= max_retries:
            print('💥 Failed to connect to database after maximum retries')
            exit(1)
        time.sleep(2)
"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis connection..."
python3 -c "
import time
import redis
import os
from urllib.parse import urlparse

redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
parsed = urlparse(redis_url)

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        r = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0
        )
        r.ping()
        print('✅ Redis connection successful')
        break
    except redis.ConnectionError as e:
        retry_count += 1
        print(f'❌ Redis connection failed (attempt {retry_count}/{max_retries}): {e}')
        if retry_count >= max_retries:
            print('💥 Failed to connect to Redis after maximum retries')
            exit(1)
        time.sleep(2)
"

# Run database migrations
echo "🔄 Running database migrations..."
cd /app
python3 -c "
import asyncio
from backend.database import init_db

async def run_migrations():
    try:
        await init_db()
        print('✅ Database migrations completed')
    except Exception as e:
        print(f'❌ Database migration failed: {e}')
        exit(1)

asyncio.run(run_migrations())
"

# Validate environment variables
echo "🔍 Validating environment configuration..."
python3 -c "
import os
import sys

required_vars = [
    'CODEGEN_API_TOKEN',
    'CODEGEN_ORG_ID',
    'GITHUB_TOKEN',
    'GEMINI_API_KEY'
]

missing_vars = []
for var in required_vars:
    if not os.environ.get(var):
        missing_vars.append(var)

if missing_vars:
    print(f'❌ Missing required environment variables: {missing_vars}')
    print('Please set these variables before starting the application')
    sys.exit(1)
else:
    print('✅ All required environment variables are set')
"

# Create necessary directories
echo "📁 Creating application directories..."
mkdir -p /app/logs /app/data /app/tmp
chmod 755 /app/logs /app/data /app/tmp

# Set up logging configuration
echo "📝 Configuring logging..."
export PYTHONPATH=/app:$PYTHONPATH

# Validate external service connections
echo "🔗 Validating external service connections..."
python3 -c "
import asyncio
import os
import sys
sys.path.append('/app')

from backend.services.codegen_api_client import CodegenAPIClient

async def validate_services():
    try:
        # Test Codegen API connection
        async with CodegenAPIClient() as client:
            is_valid = await client.validate_connection()
            if is_valid:
                print('✅ Codegen API connection validated')
            else:
                print('⚠️  Codegen API connection failed - continuing anyway')
    except Exception as e:
        print(f'⚠️  Codegen API validation error: {e} - continuing anyway')

asyncio.run(validate_services())
"

# Start application based on command
echo "🎯 Starting application with command: $@"

# Handle different startup modes
case "$1" in
    "gunicorn")
        echo "🌐 Starting web server with Gunicorn..."
        exec gunicorn --config /app/docker/gunicorn.conf.py backend.main:app
        ;;
    "celery-worker")
        echo "👷 Starting Celery worker..."
        exec celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=4
        ;;
    "celery-beat")
        echo "⏰ Starting Celery beat scheduler..."
        exec celery -A backend.tasks.celery_app beat --loglevel=info --schedule=/app/data/celerybeat-schedule
        ;;
    "migrate")
        echo "🔄 Running migrations only..."
        echo "✅ Migrations completed - exiting"
        exit 0
        ;;
    "shell")
        echo "🐚 Starting interactive shell..."
        exec /bin/bash
        ;;
    *)
        echo "🚀 Executing custom command: $@"
        exec "$@"
        ;;
esac

