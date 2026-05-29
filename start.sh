#!/bin/bash
set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Start FastAPI backend
cd backend
echo "Starting backend..."
if [ ! -d "venv" ]; then
    python3 -m venv venv || true
fi
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start Vite React frontend
cd frontend
echo "Starting frontend..."
npm run dev -- --host &
FRONTEND_PID=$!

echo "================================"
echo "Servers running..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "================================"

# Wait for both background processes
wait $BACKEND_PID $FRONTEND_PID
