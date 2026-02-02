#!/bin/bash

# Partnership Ads UI Wrapper Script
# This script sets up the environment and runs the Partnership Ads UI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

cd "$SCRIPT_DIR"

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
echo "🚀 Starting Partnership Ads UI..."
echo "   Access the UI at: http://localhost:8501"
echo ""
streamlit run partnership_ads_ui.py "$@"
