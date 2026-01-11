#!/bin/bash

# Run the AI Scheduling Assistant Demo
# This is a standalone demo that runs entirely in the browser - no backend required!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "=========================================="
echo "  AI Scheduling Assistant Demo"
echo "=========================================="
echo ""

# Check if node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Installing dependencies..."
    cd "$FRONTEND_DIR"
    npm install
    echo ""
fi

echo "Starting demo server..."
echo ""
echo "Open http://localhost:5173 in your browser"
echo ""
echo "Try these commands in the chat:"
echo "  - 'Book a meeting tomorrow at 2pm'"
echo "  - 'What's on my schedule today?'"
echo "  - 'Am I free on Friday at 3pm?'"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$FRONTEND_DIR"
npm run dev
