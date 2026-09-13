#!/bin/bash
set -e

command -v python3 >/dev/null || { echo "Python3 is required"; exit 1; }
pip3 install -r requirements.txt
if [ ! -f ".env" ] && [ -z "${BOT_TOKEN:-}" ]; then
  echo "Set BOT_TOKEN, API_ID, API_HASH and TARGET_CHANNEL in .env or the environment."
  exit 1
fi
mkdir -p logs
nohup python3 bot.py > logs/bot.log 2>&1 &
echo $! > bot.pid
echo "Bot started. PID: $(cat bot.pid)"
