#!/usr/bin/env bash
#
# run_brand.sh — Launch the Brand CPAS Dashboard
#
# Usage:
#   cd cpas_demos
#   ./run_brand.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi

source venv/bin/activate
streamlit run brand_portal/brand_dashboard_ui.py --server.port 8502
