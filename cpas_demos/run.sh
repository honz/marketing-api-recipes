#!/usr/bin/env bash
#
# run.sh — Launch the Merchant CPAS Platform
#
# Usage:
#   cd cpas_demos
#   ./run.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi

source venv/bin/activate
streamlit run merchant_platform/merchant_cpas_ui.py
