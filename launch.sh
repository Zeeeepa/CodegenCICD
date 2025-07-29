#!/bin/bash

# CodegenCICD Dashboard Launch Script
echo "🚀 CodegenCICD Dashboard Launch Script"
echo "======================================"

# Check if services are already running
BACKEND_PID=$(pgrep -f "python main.py")
FRONTEND_PID=$(pgrep -f "react-scripts start")

if [ ! -z "$BACKEND_PID" ] && [ ! -z "$FRONTEND_PID" ]; then
    echo "✅ Services are already running!"
    echo ""
    echo "🔗 Access URLs:"
    echo "   Frontend (React UI): http://localhost:3001"
    echo "   Backend API:         http://localhost:8000"
    echo "   API Health Check:    http://localhost:8000/health"
    echo "   API Documentation:   http://localhost:8000/docs"
    echo ""
    echo "📊 Service Status:"
    echo "   Backend PID:  $BACKEND_PID"
    echo "   Frontend PID: $FRONTEND_PID"
    echo ""
    echo "🛑 To stop services: ./stop.sh"
    exit 0
fi

echo "🔧 Setting up environment..."

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Environment file created"
fi

# Start backend
echo "🐍 Starting backend server..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Python virtual environment created"
fi

source venv/bin/activate
pip install -q fastapi uvicorn python-multipart websockets sqlalchemy asyncpg python-dotenv pydantic httpx aiohttp requests

nohup python main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend started successfully"
        break
    fi
    sleep 1
done

# Start frontend
echo "⚛️  Starting frontend server..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
    echo "✅ Node.js dependencies installed"
fi

PORT=3001 nohup npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:3001 > /dev/null 2>&1; then
        echo "✅ Frontend started successfully"
        break
    fi
    sleep 2
done

echo ""
echo "🎉 CodegenCICD Dashboard is now running!"
echo "======================================"
echo ""
echo "🔗 Access URLs:"
echo "   Frontend (React UI): http://localhost:3001"
echo "   Backend API:         http://localhost:8000"
echo "   API Health Check:    http://localhost:8000/health"
echo "   API Documentation:   http://localhost:8000/docs"
echo ""
echo "📊 Service Status:"
echo "   Backend PID:  $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "📝 Logs:"
echo "   Backend logs: tail -f backend.log"
echo "   Frontend logs: tail -f frontend.log"
echo ""
echo "🛑 To stop services: ./stop.sh"
echo ""
echo "🎯 Features Available:"
echo "   • Project Management Dashboard"
echo "   • GitHub Integration"
echo "   • AI Agent Runs with Codegen API"
echo "   • Real-time WebSocket Updates"
echo "   • 4-Tab Configuration System"
echo "   • Automated Validation Pipeline"
echo "   • Auto-merge Capabilities"
echo ""
echo "Happy coding! 🚀"

