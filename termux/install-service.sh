#!/data/data/com.termux/files/usr/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="$PREFIX/var/service/telegram-auto-post-bot"
mkdir -p "$SERVICE_DIR/log"
cat > "$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
cd "$ROOT"
termux-wake-lock 2>/dev/null || true
exec python bot.py
EOF
chmod +x "$SERVICE_DIR/run"
cat > "$SERVICE_DIR/log/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
mkdir -p "$ROOT/logs"
exec svlogd "$ROOT/logs"
EOF
chmod +x "$SERVICE_DIR/log/run"
echo "Installed service: telegram-auto-post-bot"
echo "Start: sv up telegram-auto-post-bot"
echo "Stop:  sv down telegram-auto-post-bot"
echo "Log:   tail -f $ROOT/logs/current"
