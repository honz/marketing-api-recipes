#!/usr/bin/env bash
#
# install.sh — Set up the Merchant CPAS Platform
#
# Usage:
#   cd cpas_demos
#   ./install.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# -------------------------------------------------------
# 1. Check Python 3.8+
# -------------------------------------------------------
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        major=$("$candidate" -c 'import sys; print(sys.version_info.major)')
        minor=$("$candidate" -c 'import sys; print(sys.version_info.minor)')
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.8 or higher is required but was not found."
    echo ""
    echo "Install Python:"
    echo "  macOS:   brew install python3"
    echo "  Ubuntu:  sudo apt install python3"
    echo "  Windows: https://www.python.org/downloads/"
    exit 1
fi

echo "Using $PYTHON ($version)"

# -------------------------------------------------------
# 2. Create virtual environment
# -------------------------------------------------------
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv venv
else
    echo "Virtual environment already exists."
fi

# -------------------------------------------------------
# 3. Install dependencies
# -------------------------------------------------------
echo "Installing dependencies..."
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet streamlit pandas requests

# -------------------------------------------------------
# 4. Copy config template if needed
# -------------------------------------------------------
if [ ! -f "merchant_platform/config.py" ]; then
    cp merchant_platform/config.example.py merchant_platform/config.py
    echo "Created merchant_platform/config.py from template."
else
    echo "merchant_platform/config.py already exists, skipping."
fi

# -------------------------------------------------------
# Done
# -------------------------------------------------------
echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit merchant_platform/config.py with your ACCESS_TOKEN and MERCHANT_BUSINESS_ID"
echo "  2. Run:  ./run.sh"
