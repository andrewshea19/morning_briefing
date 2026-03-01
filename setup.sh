#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Morning Briefing Setup ==="

# 1. Create venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# 2. Install dependencies
echo "Installing dependencies..."
./venv/bin/pip install -q -r requirements.txt

# 3. Create .env from template if needed
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from template. Please edit it with your credentials:"
    echo "  $PWD/.env"
    echo ""
    echo "You need:"
    echo "  - Anthropic API key (https://console.anthropic.com/)"
    echo "  - Gmail app-specific passwords for both accounts"
    echo "    (https://myaccount.google.com/apppasswords)"
    echo ""
else
    echo ".env already exists."
fi

# 4. Create logs directory
mkdir -p logs

# 5. Install launchd plist
PLIST_NAME="com.andrewshea.morning-briefing"
PLIST_SRC="$PWD/${PLIST_NAME}.plist"
PLIST_DST="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

if [ -f "$PLIST_SRC" ]; then
    # Unload old version if exists
    launchctl bootout "gui/$(id -u)/${PLIST_NAME}" 2>/dev/null || true

    cp "$PLIST_SRC" "$PLIST_DST"
    launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
    echo "launchd job installed and loaded."
    echo "  Next run: 6:00 AM daily"
    echo "  Manual test: launchctl kickstart gui/$(id -u)/${PLIST_NAME}"
else
    echo "Warning: launchd plist not found at $PLIST_SRC"
fi

echo ""
echo "=== Setup Complete ==="
echo "Test with: ./venv/bin/python3 briefing.py"
