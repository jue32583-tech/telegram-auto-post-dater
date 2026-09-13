#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")/.."
termux-wake-lock 2>/dev/null || true
exec python bot.py
