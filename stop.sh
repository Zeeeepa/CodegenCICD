#!/bin/bash

# CodegenCICD Dashboard Stop Script
echo "🛑 Stopping CodegenCICD Dashboard Services"
echo "=========================================="

# Stop backend
BACKEND_PID=$(pgrep -f "python main.py")
if [ ! -z "$BACKEND_PID" ]; then
    kill $BACKEND_PID
    echo "✅ Backend stopped (PID: $BACKEND_PID)"
else
    echo "ℹ️  Backend was not running"
fi

# Stop frontend
FRONTEND_PID=$(pgrep -f "react-scripts start")
if [ ! -z "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID
    echo "✅ Frontend stopped (PID: $FRONTEND_PID)"
else
    echo "ℹ️  Frontend was not running"
fi

# Stop any remaining Node.js processes related to the project
NODE_PIDS=$(pgrep -f "CodegenCICD/frontend")
if [ ! -z "$NODE_PIDS" ]; then
    echo $NODE_PIDS | xargs kill
    echo "✅ Additional Node.js processes stopped"
fi

echo ""
echo "🎯 All services stopped successfully!"
echo "To restart: ./launch.sh"

