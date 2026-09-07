# Telegram Auto Post Bot

> Source Channel က post များကို auto-repost လုပ်ပေးသော Telegram Bot
>
> **Admin မဖြစ်ဘဲ Channel Link ပေးရုံဖြင့် post ဖတ်နိုင်ပါသည်!**
> **ဖုန်းပိတ်ထားလဲ Server မှာ 24/7 run ထားနိုင်ပါသည်!**

---

## 📋 Bot ၏ လုပ်ဆောင်ချက်များ

| Button | လုပ်ဆောင်ချက် |
|---|---|
| ⚙️ Channel Setup | Source Channel နှင့် Target Channel (A, B, C) ထည့်သွင်း |
| 🔄 Start Forwarding | Auto-forward စတင် |
| ⏹️ Stop Forwarding | Auto-forward ရပ်ဆိုင်း |
| 📊 Status | Bot Status ကြည့်ရှု |
| 🔧 Settings | Forward Mode ပြောင်း, Data Reset |
| ❓ Help | အကူအညီ |

---

## 📤 Channel Format

| Channel | ပုံစံ |
|---|---|
| **Channel A** | ပုံ + ဇာတ်ညွန် + Channel Link + Video Link (text) |
| **Channel B** | Video forward |
| **Channel C** | နောက်ထပ် post (ပုံ + ဇာတ်ညွန်) |

---

## 🚀 Quick Start

### Step 1: Clone and Install

```bash
git clone https://github.com/jue32583-tech/telegram-auto-post-bot.git
cd telegram-auto-post-bot
pip3 install -r requirements.txt
```

### Step 2: Setup .env

```bash
cp .env.example .env
```

`.env` file ကို edit:
```
API_ID=3841104
API_HASH=3c7752a29b4cc0ec9daf6e1782c0b4e2
BOT_TOKEN=8249701481:AAGsVCusZe5Dn8MJkPwGqMyeFVsJtlij3Bo
```

### Step 3: Run

**Local testing:**
```bash
python3 bot.py
```

**24/7 Server (ဖုန်းပိတ်ထားလဲ run):**
```bash
bash deploy.sh
```

**Restart:**
```bash
bash deploy_restart.sh
```

---

## 📱 Telegram မှာ အသုံးပြုပုံ

1. Bot ကို `/start` ပေးပို့ပါ
2. ⚙️ Channel Setup → Source Channel Link ထည့်ပါ
3. Channel A, B, C ထည့်ပါ (Admin ထည့်ရမည်)
4. 🔄 Start Forwarding နှိပ်ပါ

---

## ⚠️ အရေးကြီး

- **Source Channel:** Admin မလို - Link ပေးရုံဖြင့် post ဖတ်နိုင်
- **Target Channel (A, B, C):** Bot ကို Admin ထည့်ထားရမည်
- **30 စက္ကန့်တိုင်း** source channel ကို auto-check
- **ကြိုက်သလောက်** Source Channel Link ထည့်နိုင်
- **Server မှာ run ထားရင်** ဖုန်းပိတ်ထားလဲ auto-forward အလုပ်လုပ်

---

## 🖥️ Server မှာ 24/7 Run ထားဖို့

### Railway (Free)
1. https://railway.app မှာ account ဖွင့်
2. New Project → Deploy from GitHub
3. Environment Variables: API_ID, API_HASH, BOT_TOKEN
4. Deploy!

### VPS (DigitalOcean, AWS)
```bash
sudo apt update && sudo apt install python3 python3-pip -y
git clone https://github.com/jue32583-tech/telegram-auto-post-bot.git
cd telegram-auto-post-bot
pip3 install -r requirements.txt
bash deploy.sh
```

---

## 🔧 Commands

| Command | Description |
|---|---|
| `python3 bot.py` | Bot run (foreground) |
| `bash deploy.sh` | Bot run (background, 24/7) |
| `bash deploy_restart.sh` | Bot restart |
| `tail -f logs/bot.log` | Log ကြည့် |
| `kill $(cat bot.pid)` | Bot stop |

---

## 📝 License

MIT License - Free to use and modify
