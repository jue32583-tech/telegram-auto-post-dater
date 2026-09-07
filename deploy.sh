#!/bin/bash
# ============================================
# Telegram Auto Post Bot - Deploy Script
# 24/7 Server မှာ Run ထားဖို့
# ============================================

echo "🤖 Telegram Auto Post Bot Deploy..."
echo "━━━━━━━━━━━━━━━━━━━━"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 မတပ်ဆင်ရသေးပါ!"
    echo "📦 Install: sudo apt install python3 python3-pip"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"

# Install dependencies
echo "📦 Dependencies install လုပ်နေ..."
pip3 install -r requirements.txt

echo "━━━━━━━━━━━━━━━━━━━━"

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "⚠️ .env file မရှိပါ!"
    echo "📝 .env file ကို ဖန်တီးပေးပါ:"
    echo ""
    echo "API_ID=3841104"
    echo "API_HASH=3c7752a29b4cc0ec9daf6e1782c0b4e2"
    echo "BOT_TOKEN=8249701481:AAGsVCusZe5Dn8MJkPwGqMyeFVsJtlij3Bo"
    echo ""
    exit 1
fi

# Create log directory
mkdir -p logs

# Run the bot in background (24/7)
echo "🚀 Bot Start လုပ်နေ..."
nohup python3 bot.py > logs/bot.log 2>&1 &

# Save PID
echo $! > bot.pid

echo ""
echo "✅ Bot Start ပြီးပါပြီ!"
echo "📋 PID: $(cat bot.pid)"
echo "📝 Log: logs/bot.log"
echo ""
echo "━━━ Useful Commands ━━━"
echo "View logs: tail -f logs/bot.log"
echo "Stop bot: kill \$(cat bot.pid)"
echo "Restart:  bash deploy.sh restart"
echo "Status:   cat bot.pid && ps -p \$(cat bot.pid)"
echo "━━━━━━━━━━━━━━━━━━━━"
