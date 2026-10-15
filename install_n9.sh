#!/bin/sh
# ==============================================================================
# MeeFin - Nokia N9 (MeeGo 1.2 Harmattan) Installer
# ==============================================================================

set -e
echo "=== Installing MeeFin for Nokia N9 ==="

if [ "$(id -u)" != "0" ]; then
    echo "ERROR: Please run this script as root (use 'devel-su', password: rootme)"
    exit 1
fi

APP_DIR="/opt/meefin"
ICON_DIR="/usr/share/icons/hicolor/80x80/apps"
DESK_DIR="/usr/share/applications"
USER_DOCS="/home/user/MyDocs"

mkdir -p "$APP_DIR" "$ICON_DIR" "$DESK_DIR" "$USER_DOCS"

SCRIPT_DIR="$(dirname "$0")"

# Install client files
if [ -f "$SCRIPT_DIR/meefin.py" ]; then
    cp "$SCRIPT_DIR/meefin.py" "$APP_DIR/meefin.py"
    cp "$SCRIPT_DIR/meefin.py" "$USER_DOCS/n9_market_tracker.py"
elif [ -f "$USER_DOCS/n9_market_tracker.py" ]; then
    cp "$USER_DOCS/n9_market_tracker.py" "$APP_DIR/meefin.py"
fi

if [ -f "$SCRIPT_DIR/meefin.png" ]; then
    cp "$SCRIPT_DIR/meefin.png" "$ICON_DIR/meefin.png"
fi

if [ -f "$SCRIPT_DIR/meefin.desktop" ]; then
    cp "$SCRIPT_DIR/meefin.desktop" "$DESK_DIR/meefin.desktop"
fi

# Set proper permissions
chmod 755 "$APP_DIR/meefin.py" "$USER_DOCS/n9_market_tracker.py" 2>/dev/null || true
chmod 644 "$ICON_DIR/meefin.png" "$DESK_DIR/meefin.desktop" 2>/dev/null || true
chown -R user:users "$APP_DIR" "$USER_DOCS/n9_market_tracker.py" 2>/dev/null || true

echo "--------------------------------------------------------"
echo "  MeeFin successfully installed to /opt/meefin/!"
echo "  Launch it directly from the Nokia N9 Application Grid."
echo "--------------------------------------------------------"
