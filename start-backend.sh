#!/bin/bash
# HydroQ-QC-Assistant Backend Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$SCRIPT_DIR/apps/api"

echo "🌊 HydroQ-QC-Assistant Backend"
echo "=============================="

# Check if venv exists
if [ ! -d "$API_DIR/venv" ]; then
    echo "❌ Virtual environment not found. Run setup first:"
    echo "   cd apps/api && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate venv
source "$API_DIR/venv/bin/activate"

# Check for .env file
if [ ! -f "$API_DIR/.env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp "$SCRIPT_DIR/.env.example" "$API_DIR/.env"
    echo "📝 Created .env file. Please update JWT_SECRET_KEY for production!"
fi

# Ensure data directories exist
mkdir -p "$SCRIPT_DIR/data/uploads"
mkdir -p "$SCRIPT_DIR/data/outputs"
mkdir -p "$SCRIPT_DIR/data/samples"

echo ""
echo "🚀 Starting API server on http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "🏥 Health:   http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$API_DIR"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
