#!/usr/bin/env bash
# ==============================================================================
# MeeFin TLS Bridge Proxy Starter (Termux / Linux / macOS)
# ==============================================================================

PORT="${1:-8083}"

if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
fi

pkill -f "n9_tls_proxy.py" 2>/dev/null || true

echo "Starting MeeFin TLS Proxy on port $PORT..."
python3 n9_tls_proxy.py --port "$PORT"
