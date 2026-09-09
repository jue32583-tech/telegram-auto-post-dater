"""
Telegram Auto Post Bot
Telegram inline buttons and a web dashboard control the same forwarding state.
"""
import asyncio
import hmac
import json
import os
import re
import threading
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template_string
from telethon import Button, TelegramClient, events

load_dotenv()

# ========================
# Configuration
# ========================
ADMIN_ID = int(os.getenv("ADMIN_ID", "6081621017"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "waiyanphyo99").lstrip("@").lower()
ADMIN_WEB_TOKEN = os.getenv("ADMIN_WEB_TOKEN", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "auto_post_bot_session")
DATA_FILE = os.getenv("DATA_FILE", "bot_data.json")
PORT = int(os.getenv("PORT", "10000"))
CHANNEL_A_LINK = os.getenv("CHANNEL_A_LINK", "")

SYSTEM_PROMPT = (
    "You are a social media caption writer. Rewrite the given caption in an engaging, "
    "attractive style while keeping the same meaning. Add suitable emojis. "
    "Return only the rewritten caption."
)


def load_encrypted_env():
    """Optionally load locally encrypted environment values."""
    encrypted_file, key_file = ".env.encrypted", ".env.key"
    if not (os.path.exists(encrypted_file) and os.path.exists(key_file)):
        return
    try:
        from cryptography.fernet import Fernet
        key = open(key_file, "rb").read().strip()
        encrypted = open(encrypted_file, "rb").read()
        for line in Fernet(key).decrypt(encrypted).decode().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key_name, _, value = line.partition("=")
                os.environ.setdefault(key_name.strip(), value.strip())
    except Exception as exc:
        print(f"Encrypted environment values were not loaded: {exc}")


load_encrypted_env()
BOT_TOKEN = os.getenv("BOT_TOKEN", BOT_TOKEN)
API_ID = int(os.getenv("API_ID", str(API_ID)))
API_HASH = os.getenv("API_HASH", API_HASH)


def default_data():
    return {
        "channels": {"source": [], "channel_a": "", "channel_b": "", "channel_c": ""},
        "forwarding": {"enabled": False, "last_message_id": {}, "mode": "text_and_video"},
        "owner_id": ADMIN_ID,
        "status": "inactive",
        "pending_action": None,
        "pending_chat_id": None,
    }


def load_data():
    data = default_data()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as handle:
                saved = json.load(handle)
            for key, value in saved.items():
                if isinstance(value, dict) and isinstance(data.get(key), dict):
                    data[key].update(value)
                else:
                    data[key] = value
        except (OSError, ValueError) as exc:
            print(f"Could not load {DATA_FILE}: {exc}")
    return data


_data_lock = threading.Lock()


def save_data(data):
    with _data_lock:
        temporary = f"{DATA_FILE}.tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, DATA_FILE)


def extract_channel_from_link(link):
    patterns = [r"t\.me/(\+[\w-]+)", r"t\.me/([\w-]+)", r"telegram\.me/([\w-]+)"]
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    return link[1:] if link.startswith("@") else link


def is_admin_event(event):
    return event.sender_id == ADMIN_ID


def rewrite_caption_ai(original_text):
    if not original_text:
        return ""
    # AI rewriting is optional. Forwarding continues unchanged when no provider is configured.
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return original_text
    try:
        import requests
        response = requests.post(
            os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1") + "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": original_text},
            ], "max_tokens": 500}, timeout=30,
        )
        if response.ok:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"Caption rewrite skipped: {exc}")
    return original_text


# ========================
# Telegram UI
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


def get_mode_keyboard():
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


def format_status(data):
    channels = data["channels"]
    return (
        "📊 <b>Bot Status</b>\n\n"
        f"Forwarding: {'🟢 ACTIVE' if data['forwarding']['enabled'] else '🔴 INACTIVE'}\n"
        f"Mode: {data['forwarding']['mode']}\n\n"
        f"Source: {', '.join(channels['source']) or 'မထည့်ရသေး'}\n"
        f"Channel A: {channels['channel_a'] or 'မထည့်ရသေး'}\n"
        f"Channel B: {channels['channel_b'] or 'မထည့်ရသေး'}\n"
        f"Channel C: {channels['channel_c'] or 'မထည့်ရသေး'}"
    )


def format_channel_a_caption(source_channel, original_text="", media_type=""):
    caption = rewrite_caption_ai(original_text)
    if caption:
        caption += "\n\n"
    caption += "━━━━━━━━━━━━━━━━━━━━\n"
    caption += f"📎 Source: {source_channel}\n📅 {datetime.now():%Y-%m-%d %H:%M}\n"
    if media_type:
        caption += f"🏷️ {media_type}\n"
    if CHANNEL_A_LINK:
        caption += f"🔗 Join: {CHANNEL_A_LINK}\n"
    return caption + f"📺 Channel: {source_channel}"


client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


@client.on(events.NewMessage(pattern=r"^/start$"))
async def start_handler(event):
    if not is_admin_event(event):
        await event.respond("⛔ ဒီ bot ကို admin သာ အသုံးပြုနိုင်ပါသည်။")
        return
    data = load_data()
    data["owner_id"] = ADMIN_ID
    save_data(data)
    await event.respond(
        "🤖 <b>Telegram Auto Post Bot</b>\n\nButton နှိပ်ပြီး အသုံးပြုပါ။\n"
        "Web panel နှင့် Telegram bot နှစ်ခုစလုံးမှ ထိန်းချုပ်နိုင်ပါသည်။",
        parse_mode="HTML", buttons=get_main_keyboard(),
    )


@client.on(events.NewMessage(func=lambda event: event.is_private and not event.text.startswith("/")))
async def handle_button_press(event):
    if not is_admin_event(event):
        return
    data, text = load_data(), event.raw_text
    pending = data.get("pending_action")
    if pending and event.chat_id == data.get("pending_chat_id"):
        link = extract_channel_from_link(text.strip())
        if pending == "set_source" and link not in data["channels"]["source"]:
            data["channels"]["source"].append(link)
        elif pending.startswith("set_channel_"):
            data["channels"][pending[4:]] = link
        data["pending_action"] = data["pending_chat_id"] = None
        save_data(data)
        await event.respond(f"✅ ထည့်သွင်းပြီးပါပြီ: {link}", buttons=get_setup_keyboard())
        return

    if text == "⚙️ Channel Setup":
        await event.respond("⚙️ <b>Channel Setup</b>\n\nChannel ထည့်ရန် အောက်က button ကိုနှိပ်ပါ။", parse_mode="HTML", buttons=get_setup_keyboard())
    elif text == "🔄 Start Forwarding":
        if not data["channels"]["source"] or not all(data["channels"][key] for key in ("channel_a", "channel_b", "channel_c")):
            await event.respond("⚠️ Source နှင့် Channel A/B/C အားလုံး ထည့်ပေးပါ။")
            return
        data["forwarding"].update(enabled=True)
        data["status"] = "active"
        save_data(data)
        await event.respond("✅ Forwarding စတင်ပါပြီ။", buttons=get_main_keyboard())
    elif text == "⏹️ Stop Forwarding":
        data["forwarding"].update(enabled=False)
        data["status"] = "inactive"
        save_data(data)
        await event.respond("⏹️ Forwarding ရပ်ဆိုင်းပါပြီ။", buttons=get_main_keyboard())
    elif text == "📊 Status":
        await event.respond(format_status(data), parse_mode="HTML", buttons=get_main_keyboard())
    elif text == "🔧 Settings":
        await event.respond("🔧 <b>Settings</b>", parse_mode="HTML", buttons=get_settings_keyboard())
    elif text == "❓ Help":
        await event.respond("❓ Channel များထည့်ပြီး Start Forwarding နှိပ်ပါ။ Bot ကို target channels တွင် admin ထည့်ထားရပါမည်။")


@client.on(events.CallbackQuery)
async def handle_callback(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("Admin only", alert=True)
        return
    data = load_data()
    await event.answer()
    action = event.data.decode()
    if action == "back_main":
        await event.edit("🤖 <b>Telegram Auto Post Bot</b>\n\nButton နှိပ်ပြီး အသုံးပြုပါ။", parse_mode="HTML", buttons=get_main_keyboard())
    elif action in {"set_source", "set_channel_a", "set_channel_b", "set_channel_c"}:
        data["pending_action"], data["pending_chat_id"] = action, event.chat_id
        save_data(data)
        await event.edit("➕ <b>Channel Link သို့မဟုတ် Username ပေးပို့ပါ</b>\nဥပမာ: https://t.me/channelname", parse_mode="HTML", buttons=[[Button.inline("↩️ Back", b"back_main")]])
    elif action == "view_channels":
        await event.edit(format_status(data), parse_mode="HTML", buttons=get_setup_keyboard())
    elif action == "change_mode":
        await event.edit(f"📝 <b>Forward Mode</b>\nCurrent: {data['forwarding']['mode']}", parse_mode="HTML", buttons=get_mode_keyboard())
    elif action in {"mode_text_video", "mode_forward", "mode_text"}:
        data["forwarding"]["mode"] = {"mode_text_video": "text_and_video", "mode_forward": "full_forward", "mode_text": "text_only"}[action]
        save_data(data)
        await event.edit("✅ Mode ပြောင်းလဲပြီးပါပြီ။", buttons=get_main_keyboard())
    elif action == "reset_data":
        await event.edit("🗑️ Data အားလုံး ဖျက်မည်လား?", buttons=[[Button.inline("✅ Yes", b"confirm_reset")], [Button.inline("❌ No", b"back_main")]])
    elif action == "confirm_reset":
        save_data(default_data())
        await event.edit("✅ Data Reset ပြီးပါပြီ။", buttons=get_main_keyboard())


@client.on(events.NewMessage)
async def source_channel_listener(event):
    data = load_data()
    if not data["forwarding"]["enabled"] or event.is_private or not event.media and not event.text:
        return
    chat = await event.get_chat()
    username = getattr(chat, "username", None)
    chat_id, clean_id = str(chat.id), str(chat.id).replace("-100", "")
    sources = [str(item).lstrip("@") for item in data["channels"]["source"]]
    if not ((username and username in sources) or chat_id in sources or clean_id in sources):
        return
    source_name = f"@{username}" if username else chat_id
    text, mode = event.text or "", data["forwarding"]["mode"]
    try:
        if mode != "full_forward" and data["channels"]["channel_a"]:
            caption = format_channel_a_caption(source_name, text, "Media")
            await client.send_message(data["channels"]["channel_a"], caption, file=None if mode == "text_only" else event.media)
        if mode != "text_only" and data["channels"]["channel_b"] and event.media:
            await client.send_message(data["channels"]["channel_b"], file=event.media)
        if data["channels"]["channel_c"]:
            await client.forward_messages(data["channels"]["channel_c"], event.message)
    except Exception as exc:
        print(f"Forwarding error: {exc}")


# ========================
# Web dashboard
# ========================
app = Flask(__name__)
DASHBOARD_HTML = """<!doctype html><html lang='my'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Telegram Auto Post Bot</title><style>body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;background:#f5f7fb;color:#182230}.card{background:white;padding:1.25rem;margin:1rem 0;border-radius:14px;box-shadow:0 2px 10px #0001}input{width:100%;box-sizing:border-box;padding:.7rem;margin:.3rem 0 1rem;border:1px solid #ccd3df;border-radius:8px}button{padding:.7rem 1rem;margin:.25rem;border:0;border-radius:8px;background:#2463eb;color:white;cursor:pointer}button.danger{background:#dc3545}#status{white-space:pre-wrap;background:#eef3ff;padding:1rem;border-radius:8px}</style></head><body><h1>Telegram Auto Post Bot</h1><div class='card'><label>Admin Web Token</label><input id='token' type='password' placeholder='ADMIN_WEB_TOKEN'><button onclick='loadState()'>Status ပြရန်</button><div id='status'>Token ထည့်ပြီး Status ပြပါ။</div></div><div class='card'><h2>Channel Setup</h2><label>Source channels (comma separated)</label><input id='source'><label>Channel A</label><input id='channel_a'><label>Channel B</label><input id='channel_b'><label>Channel C</label><input id='channel_c'><button onclick='saveChannels()'>Channels သိမ်းရန်</button></div><div class='card'><h2>Controls</h2><button onclick="action('start')">🔄 Start Forwarding</button><button class='danger' onclick="action('stop')">⏹️ Stop Forwarding</button><button onclick="action('mode_text_video')">Text + Video</button><button onclick="action('mode_forward')">Full Forward</button><button onclick="action('mode_text')">Text Only</button></div><script>const $=id=>document.getElementById(id);const headers=()=>({'Content-Type':'application/json','X-Admin-Token':$('token').value});async function api(url,opts={}){const r=await fetch(url,{...opts,headers:{...headers(),...(opts.headers||{})}});const j=await r.json();if(!r.ok)throw Error(j.error||'Request failed');return j}async function loadState(){try{const j=await api('/api/state');$('status').textContent=JSON.stringify(j,null,2);$('source').value=j.channels.source.join(', ');$('channel_a').value=j.channels.channel_a;$('channel_b').value=j.channels.channel_b;$('channel_c').value=j.channels.channel_c}catch(e){$('status').textContent='❌ '+e.message}}async function action(name){try{await api('/api/action',{method:'POST',body:JSON.stringify({action:name})});await loadState()}catch(e){$('status').textContent='❌ '+e.message}}async function saveChannels(){try{await api('/api/channels',{method:'POST',body:JSON.stringify({source:$('source').value.split(',').map(x=>x.trim()).filter(Boolean),channel_a:$('channel_a').value.trim(),channel_b:$('channel_b').value.trim(),channel_c:$('channel_c').value.trim()})});await loadState()}catch(e){$('status').textContent='❌ '+e.message}}</script></body></html>"""


def web_admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        supplied = request.headers.get("X-Admin-Token", "") or request.args.get("token", "")
        if not ADMIN_WEB_TOKEN or not hmac.compare_digest(supplied, ADMIN_WEB_TOKEN):
            return jsonify(error="Unauthorized. Set ADMIN_WEB_TOKEN and send it in the web panel."), 401
        return function(*args, **kwargs)
    return wrapper


@app.get("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.get("/health")
def health():
    return jsonify(ok=True, service="telegram-auto-post-bot")


@app.get("/api/state")
@web_admin_required
def api_state():
    return jsonify(load_data())


@app.post("/api/channels")
@web_admin_required
def api_channels():
    payload = request.get_json(silent=True) or {}
    data = load_data()
    channels = data["channels"]
    channels["source"] = [extract_channel_from_link(str(item)) for item in payload.get("source", []) if str(item).strip()]
    for key in ("channel_a", "channel_b", "channel_c"):
        channels[key] = extract_channel_from_link(str(payload.get(key, "")).strip()) if payload.get(key) else ""
    save_data(data)
    return jsonify(ok=True, channels=channels)


@app.post("/api/action")
@web_admin_required
def api_action():
    action = (request.get_json(silent=True) or {}).get("action")
    data = load_data()
    if action == "start":
        data["forwarding"]["enabled"], data["status"] = True, "active"
    elif action == "stop":
        data["forwarding"]["enabled"], data["status"] = False, "inactive"
    elif action in {"mode_text_video", "mode_forward", "mode_text"}:
        data["forwarding"]["mode"] = {"mode_text_video": "text_and_video", "mode_forward": "full_forward", "mode_text": "text_only"}[action]
    else:
        return jsonify(error="Unknown action"), 400
    save_data(data)
    return jsonify(ok=True, state=data)


def run_web():
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    if not BOT_TOKEN or not API_ID or not API_HASH:
        raise SystemExit("BOT_TOKEN, API_ID and API_HASH must be configured as environment variables")
    threading.Thread(target=run_web, daemon=True, name="web-dashboard").start()
    print(f"Web dashboard listening on port {PORT}")
    print(f"Telegram admin:@{ADMIN_USERNAME} ({ADMIN_ID})")
    client.start(bot_token=BOT_TOKEN)
    print("Telegram bot is running")
    client.run_until_disconnected()
