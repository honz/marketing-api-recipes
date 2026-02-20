#!/bin/bash

# Partnership Ads UI - Double-click to run
# This script sets up the environment and runs the Partnership Ads UI

set -e

# Change to the script's directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

cd "$SCRIPT_DIR"

echo "========================================"
echo "  🚀 Partnership Ads Booster UI"
echo "========================================"
echo ""

# Check if virtual environment exists, if not create it
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install/upgrade dependencies
echo "📦 Installing dependencies..."
pip install --quiet --upgrade requests streamlit pandas

# Run the Streamlit app
echo ""
echo "🚀 Starting Partnership Ads UI..."
echo "   Access the UI at: http://localhost:8501"
echo ""
echo "   Press Ctrl+C to stop the server"
echo "========================================"
echo ""

streamlit run partnership_ads_ui.py

# Keep terminal open if there's an error
read -p "Press Enter to close..."
