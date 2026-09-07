"""
Telegram Auto Post Bot v4.9 (Bot Token Login - Official API ID fallback)
=========================================================================
Button နှိပ်ရုံဖြင့် အသုံးပြုနိုင်သော Bot
Source Channel post များကို AI ဖြင့် caption ပြောင်းပြီး
Channel A/B/C မှာ Auto Format ဖြင့် တင်ပေးသော Bot
"""
import os
import json
import asyncio
import re
from datetime import datetime
from dotenv import load_dotenv

from telethon import TelegramClient, events, Button
 Admin Configuration
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6081621017"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "waiyanphyo99")

def load_encrypted_env():
    """Method 2: Load API keys from encrypted .env.encrypted file (optional)."""
    encrypted_file = ".env.encrypted"
    key_file = ".env.key"
    if os.path.exists(encrypted_file) and os.path.exists(key_file):
        try:
            from cryptography.fernet import Fernet
            with open(key_file, "rb") as f:
                key = f.read().strip()
            with open(encrypted_file, "rb") as f:
                encrypted = f.read()
            content = Fernet(key).decrypt(encrypted).decode("utf-8")
            for line in content.splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            print("🔐 Loaded keys from .env.encrypted")
            return True
        except Exception as e:
            print(f"⚠️ Encrypted env failed: {e}")
    return False

load_dotenv()
load_encrypted_env()

# ========================
# Configuration
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8249701481:AAGsVCusZe5Dn8MJkPwGqMyeFVsJtlij3Bo")
API_ID = int(os.getenv("API_ID", "2000000"))
API_HASH = os.getenv("API_HASH", "b18441a1ff607e10a989891a5462e627")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-89VAtJz2LmK0bYpQ4xRsTuVwXyZ6CdEfGhIjKlMnOpQrStUvWxYz")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SESSION_NAME = "auto_post_bot_session"
DATA_FILE = "bot_data.json"
CHANNEL_A_LINK = "https://t.me/+qQzDp0NEes85Zjg1"

SYSTEM_PROMPT = (
    "You are a social media caption writer. Rewrite the given caption in an engaging, "
    "attractive style that draws attention. Keep the same meaning but make it more "
    "exciting and clickable. Add appropriate emojis. Return ONLY the rewritten caption, "
    "no explanations."
)

def rewrite_with_openai(original_text: str) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("No OpenAI API key")
    import requests
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Rewrite this caption: {original_text}"}
        ],
        "max_tokens": 500
    }
    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=30)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    raise Exception(f"OpenAI error: {resp.status_code}")

def rewrite_with_gemini(original_text: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("No Gemini API key")
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    data = {
        "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nRewrite this caption: {original_text}"}]}],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.9}
    }
    resp = requests.post(url, json=data, timeout=30)
    if resp.status_code == 200:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise Exception(f"Gemini error: {resp.status_code}")

def rewrite_caption_ai(original_text: str) -> str:
    if not original_text: return ""
    if OPENAI_API_KEY:
        try:
            res = rewrite_with_openai(original_text)
            if res: return res.strip()
        except: pass
    if GEMINI_API_KEY:
        try:
            res = rewrite_with_gemini(original_text)
            if res: return res.strip()
        except: pass
    return original_text

# ========================
# Data Management
# ========================
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "channels": {"source": [], "channel_a": "", "channel_b": "", "channel_c": ""},
        "forwarding": {"enabled": False, "last_message_id": {}, "mode": "text_and_video"},
        "owner_id": None,
        "status": "inactive",
        "pending_action": None,
        "pending_chat_id": None
    }

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_channel_from_link(link: str) -> str:
    patterns = [r't\.me/(\+[\w-]+)', r't\.me/([\w-]+)', r'telegram\.me/([\w-]+)']
    for pattern in patterns:
        match = re.search(pattern, link)
        if match: return match.group(1)
    return link[1:] if link.startswith("@") else link

# ========================
# Keyboards & Formatting
# ========================
def get_main_keyboard():
    return [
        [Button.text("⚙️ Channel Setup"), Button.text("📊 Status")],
        [Button.text("🔄 Start Forwarding"), Button.text("⏹️ Stop Forwarding")],
        [Button.text("❓ Help"), Button.text("🔧 Settings")],
    ]

def get_setup_keyboard():
    return [
        [Button.inline("➕ Source Channel ထည့်ရန်", b"set_source")],
        [Button.inline("➕ Channel A ထည့်ရန်", b"set_channel_a")],
        [Button.inline("➕ Channel B ထည့်ရန်", b"set_channel_b")],
        [Button.inline("➕ Channel C ထည့်ရန်", b"set_channel_c")],
        [Button.inline("📋 View Channels", b"view_channels")],
        [Button.inline("↩️ Back", b"back_main")],
    ]

def get_forward_mode_keyboard():
    return [
        [Button.inline("📝 Text + Video", b"mode_text_video")],
        [Button.inline("🔄 Full Forward", b"mode_forward")],
        [Button.inline("📄 Text Only", b"mode_text")],
        [Button.inline("↩️ Back", b"back_main")],
    ]

def get_settings_keyboard():
    return [
        [Button.inline("🔁 Forward Mode ပြောင်းရန်", b"change_mode")],
        [Button.inline("🗑️ Reset All Data", b"reset_data")],
        [Button.inline("↩️ Back", b"back_main")],
    ]

def format_channel_a_caption(source_channel: str, original_text: str = "", media_type: str = "") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ai_text = rewrite_caption_ai(original_text)
    caption = f"{ai_text}\n\n" if ai_text else ""
    caption += "━━━━━━━━━━━━━━━━━━━━\n"
    caption += f"📎 Source: {source_channel}\n"
    caption += f"📅 {now}\n"
    caption += "━━━━━━━━━━━━━━━━━━━━\n"
    if media_type: caption += f"🏷️ {media_type}\n"
    caption += f"🔗 Join: {CHANNEL_A_LINK}\n"
    caption += f"📺 Channel: {source_channel}"
    return caption

# ========================
# Create Client
# ========================
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ========================
# Bot Handlers
# ========================
@client.on(events.NewMessage(pattern=r"^/start"))
async def start_handler(event):
    data = load_data()
    data["owner_id"] = event.chat_id
    save_data(data)
    await event.respond(
        "🤖 <b>Telegram Auto Post Bot</b>\n\n"
        "👋 ကြိုဆိုပါတယ့်! Button နှိပ်ပြီး အသုံးပြုပါ\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ Channel Setup - Channel များ ထည့်\n"
        "🔄 Start Forwarding - Auto forward စတင်\n"
        "⏹️ Stop Forwarding - Auto forward ရပ်\n"
        "📊 Status - Bot Status ကြည့်\n"
        "🔧 Settings - Mode ပြောင်း\n"
        "❓ Help - အကူအညီ\n"
        "━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        buttons=get_main_keyboard()
    )

@client.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
async def handle_button_press(event):
    data = load_data()
    text = event.raw_text

    # Handle Link Inputs for Channel Setup
    pending = data.get("pending_action")
    if pending and event.chat_id == data.get("pending_chat_id"):
        link = extract_channel_from_link(text.strip())
        if pending == "set_source":
            if link not in data["channels"]["source"]:
                data["channels"]["source"].append(link)
        elif pending == "set_channel_a": data["channels"]["channel_a"] = link
        elif pending == "set_channel_b": data["channels"]["channel_b"] = link
        elif pending == "set_channel_c": data["channels"]["channel_c"] = link
        
        data["pending_action"] = None
        save_data(data)
        await event.respond(f"✅ အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ: {link}", buttons=get_setup_keyboard())
        return

    if text == "⚙️ Channel Setup":
        current = ""
        if data["channels"]["source"]: current += f"Source: {', '.join(data['channels']['source'])}\n"
        if data["channels"]["channel_a"]: current += f"Channel A: {data['channels']['channel_a']}\n"
        if data["channels"]["channel_b"]: current += f"Channel B: {data['channels']['channel_b']}\n"
        if data["channels"]["channel_c"]: current += f"Channel C: {data['channels']['channel_c']}\n"
        if not current: current = "Channel များ မထည့်ရသေးပါ"
        await event.respond(f"⚙️ <b>Channel Setup</b>\n\n{current}\n\nButton နှိပ်ပါ:", parse_mode="HTML", buttons=get_setup_keyboard())

    elif text == "🔄 Start Forwarding":
        if not data["channels"]["source"] or not all([data["channels"]["channel_a"], data["channels"]["channel_b"], data["channels"]["channel_c"]]):
            await event.respond("⚠️ Channel အားလုံး အပြည့်အစုံ ထည့်ပေးပါ! (⚙️ Channel Setup)")
            return
        data["forwarding"]["enabled"] = True
        data["status"] = "active"
        save_data(data)
        await event.respond("✅ <b>Forwarding စတင်ပါပြီ!</b>\nStatus: <b>ACTIVE</b>", parse_mode="HTML", buttons=get_main_keyboard())

    elif text == "⏹️ Stop Forwarding":
        data["forwarding"]["enabled"] = False
        data["status"] = "inactive"
        save_data(data)
        await event.respond("⏹️ <b>Forwarding ရပ်ဆိုင်းပါပြီ</b>", parse_mode="HTML", buttons=get_main_keyboard())

    elif text == "📊 Status":
        status_text = "🟢 ACTIVE" if data["forwarding"]["enabled"] else "🔴 INACTIVE"
        await event.respond(
            f"📊 <b>Bot Status</b>\n\n"
            f"Forwarding: {status_text}\n"
            f"Mode: {data['forwarding']['mode']}\n\n"
            f"Source: {', '.join(data['channels']['source']) if data['channels']['source'] else 'မထည့်ရသေး'}\n"
            f"Channel A: {data['channels']['channel_a'] or 'မထည့်ရသေး'}\n"
            f"Channel B: {data['channels']['channel_b'] or 'မထည့်ရသေး'}\n"
            f"Channel C: {data['channels']['channel_c'] or 'မထည့်ရသေး'}",
            parse_mode="HTML", buttons=get_main_keyboard()
        )

    elif text == "❓ Help":
        await event.respond("❓ <b>Bot အသုံးပြုပုံ</b>\n\nChannel များထည့်သွင်းပြီး Start နှိပ်ရုံပါပဲ။ \n⚠️ Bot ကို Channel များတွင် Admin/Member ထည့်ထားဖို့ လိုအပ်ပါတယ်။", parse_mode="HTML")

    elif text == "🔧 Settings":
        await event.respond("🔧 <b>Settings</b>\n\nMode နှင့် Data Management:", parse_mode="HTML", buttons=get_settings_keyboard())


@client.on(events.CallbackQuery)
async def handle_callback(event):
    data = load_data()
    await event.answer()
    action = event.data.decode()

    if action == "back_main":
        await event.edit("🤖 <b>Telegram Auto Post Bot</b>\n\nButton နှိပ်ပြီး အသုံးပြုပါ:", parse_mode="HTML", buttons=get_main_keyboard())
    elif action in ["set_source", "set_channel_a", "set_channel_b", "set_channel_c"]:
        await event.edit("➕ <b>Channel Link သို့မဟုတ် Username ပေးပို့ပါ</b>\n\nဥပမာ: https://t.me/channelname", parse_mode="HTML", buttons=[Button.inline("↩️ Back", b"back_main")])
        data["pending_action"] = action
        data["pending_chat_id"] = event.chat_id
        save_data(data)
    elif action == "view_channels":
        await event.edit("📋 Current Channels များကို 📊 Status တွင် ကြည့်နိုင်ပါသည်။", buttons=get_setup_keyboard())
    elif action == "change_mode":
        await event.edit(f"📝 <b>Forward Mode ရွေးပါ</b>\nCurrent: {data['forwarding']['mode']}", parse_mode="HTML", buttons=get_forward_mode_keyboard())
    elif action in ["mode_text_video", "mode_forward", "mode_text"]:
        mode_map = {"mode_text_video": "text_and_video", "mode_forward": "full_forward", "mode_text": "text_only"}
        data["forwarding"]["mode"] = mode_map[action]
        save_data(data)
        await event.edit(f"✅ Mode ပြောင်းလဲပြီးပါပြီ: {mode_map[action]}", buttons=get_main_keyboard())
    elif action == "reset_data":
        await event.edit("🗑️ <b>Data အားလုံး ဖျက်မည်လား?</b>\n⚠️ ပြန်လည်ရယူ၍ မရနိုင်ပါ!", parse_mode="HTML", buttons=[[Button.inline("✅ Yes", b"confirm_reset")], [Button.inline("❌ No", b"back_main")]])
    elif action == "confirm_reset":
        default = {"channels": {"source": [], "channel_a": "", "channel_b": "", "channel_c": ""}, "forwarding": {"enabled": False, "last_message_id": {}, "mode": "text_and_video"}, "owner_id": None, "status": "inactive"}
        save_data(default)
        await event.edit("✅ Data အားလုံး Reset လုပ်ပြီးပါပြီ။", buttons=get_main_keyboard())


# ========================
# Source Channel Listener (Auto Forward)
# ========================
@client.on(events.NewMessage)
async def source_channel_listener(event):
    data = load_data()
    if not data["forwarding"]["enabled"] or event.is_private:
        return

    chat = await event.get_chat()
    if not chat: return
    
    chat_username = getattr(chat, 'username', None)
    chat_id = str(chat.id)
    clean_id = chat_id.replace('-100', '')
    
    source_list = [str(s).replace('@', '') for s in data["channels"]["source"]]
    
    # Check if the incoming message is from our source channel
    if (chat_username and chat_username in source_list) or chat_id in source_list or clean_id in source_list:
        text = event.text or ""
        channel_a = data["channels"]["channel_a"]
        channel_b = data["channels"]["channel_b"]
        channel_c = data["channels"]["channel_c"]
        
        mode = data["forwarding"]["mode"]
        caption = format_channel_a_caption(f"@{chat_username}" if chat_username else chat_id, text, "Media")
        
        try:
            # Channel A: AI Caption + Photo/Video
            if channel_a and (text or event.media):
                await client.send_message(channel_a, caption, file=event.media)
            
            # Channel B: Video Only
            if channel_b and event.media:
                await client.send_message(channel_b, file=event.media)
                
            # Channel C: Full Forward
            if channel_c:
                await client.forward_messages(channel_c, event.message)
                
        except Exception as e:
            print(f"⚠️ Forwarding error: {e}")

# ========================
# Main Execution
# ========================
if __name__ == "__main__":
    print("🤖 Bot starting...")
    client.start(bot_token=BOT_TOKEN)
    print("✅ Bot is running successfully!")
    client.run_until_disconnected()
