#!/bin/bash

set -e

echo "Installing dependencies..."
pip3 install pyinstaller --break-system-packages -q 2>/dev/null || python3 -m venv venv && source venv/bin/activate && pip install pyinstaller -q

echo "Building HiVPN binary..."
if [ -d "venv" ]; then
    source venv/bin/activate
fi
python3 build.py

echo ""
echo "✓ Build complete!"
echo ""

echo "Installing to /usr/local/bin..."
sudo rm -f /usr/local/bin/hivpn
sudo cp dist/hivpn /usr/local/bin/hivpn
sudo chmod +x /usr/local/bin/hivpn

echo "✓ Installed! Run: hivpn"
echo ""
