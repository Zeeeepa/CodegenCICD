#!/bin/bash

# CodegenCICD Dashboard Status Check
echo "📊 CodegenCICD Dashboard Status"
echo "==============================="

# Check backend
echo "🐍 Backend Service:"
BACKEND_PID=$(pgrep -f "python main.py")
if [ ! -z "$BACKEND_PID" ]; then
    echo "   Status: ✅ Running (PID: $BACKEND_PID)"
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   Health: ✅ Healthy"
        echo "   URL:    http://localhost:8000"
    else
        echo "   Health: ❌ Not responding"
    fi
else
    echo "   Status: ❌ Not running"
fi

echo ""

# Check frontend
echo "⚛️  Frontend Service:"
FRONTEND_PID=$(pgrep -f "react-scripts start")
if [ ! -z "$FRONTEND_PID" ]; then
    echo "   Status: ✅ Running (PID: $FRONTEND_PID)"
    if curl -s http://localhost:3001 > /dev/null 2>&1; then
        echo "   Health: ✅ Accessible"
        echo "   URL:    http://localhost:3001"
    else
        echo "   Health: ❌ Not responding"
    fi
else
    echo "   Status: ❌ Not running"
fi

echo ""

# Quick API test
echo "🔧 API Test:"
if curl -s http://localhost:8000/api/projects > /dev/null 2>&1; then
    PROJECT_COUNT=$(curl -s http://localhost:8000/api/projects | jq '.projects | length' 2>/dev/null || echo "N/A")
    echo "   Projects API: ✅ Working ($PROJECT_COUNT projects)"
else
    echo "   Projects API: ❌ Not working"
fi

if curl -s http://localhost:8000/api/github-repos > /dev/null 2>&1; then
    REPO_COUNT=$(curl -s http://localhost:8000/api/github-repos | jq '.repositories | length' 2>/dev/null || echo "N/A")
    echo "   GitHub API:   ✅ Working ($REPO_COUNT repositories)"
else
    echo "   GitHub API:   ❌ Not working"
fi

echo ""
echo "🎯 Quick Actions:"
echo "   Start services: ./launch.sh"
echo "   Stop services:  ./stop.sh"
echo "   View logs:      tail -f backend.log frontend.log"

