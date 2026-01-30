#!/bin/bash
# HydroQ-QC-Assistant Frontend Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$SCRIPT_DIR/apps/web"

echo "🌊 HydroQ-QC-Assistant Frontend"
echo "==============================="

if [ ! -d "$WEB_DIR/node_modules" ]; then
    echo "📦 Installing dependencies..."
    cd "$WEB_DIR"
    npm install
    cd "$SCRIPT_DIR"
fi

echo ""
echo "🚀 Starting Frontend server"
echo "🌐 URL: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$WEB_DIR"
npm run dev
