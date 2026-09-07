#!/bin/bash
# Bot Restart Script
echo "🔄 Bot Restart..."

# Stop existing bot
if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    kill $PID 2>/dev/null
    echo "✅ Old bot stopped (PID: $PID)"
    rm -f bot.pid
fi

# Start new bot
nohup python3 bot.py > logs/bot.log 2>&1 &
echo $! > bot.pid

echo "✅ Bot Restart ပြီးပါပြီ! (PID: $(cat bot.pid))"
echo "📝 Log: tail -f logs/bot.log"
