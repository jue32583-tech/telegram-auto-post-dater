"""Telegram Auto Post Bot with approved-channel and user-submission modes."""
import asyncio
import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telethon import Button, TelegramClient, events

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_NAME = os.getenv("SESSION_NAME", "auto_post_bot_session")
DATA_FILE = Path(os.getenv("DATA_FILE", "bot_data.json"))
DEFAULT_TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "")
TARGET_CHANNELS_ENV = os.getenv("TARGET_CHANNELS", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
AUTO_HASHTAGS = os.getenv("AUTO_HASHTAGS", "#Movie #MyanmarSubtitle")

# Only these three Telegram accounts can use admin controls.
ADMIN_IDS = {
    6081621017,  # @waiyanphyo99
    6940887457,  # @waiyan7861
    6432487408,  # @Bingopop1991
}
ADMIN_NAMES = {
    6081621017: "@waiyanphyo99",
    6940887457: "@waiyan7861",
    6432487408: "@Bingopop1991",
}

WELCOME = """🎉 ကြိုဆိုပါတယ်!

🤖 Telegram Auto Post Bot အလုပ်လုပ်နေပါပြီ။
အောက်က ခလုတ်များ သို့မဟုတ် /rules /help /status ကို အသုံးပြုနိုင်ပါတယ်။

⚠️ ခွင့်ပြုချက်ရှိသော ကိုယ်ပိုင်/စီမံခန့်ခွဲခွင့်ရှိသော channel များနှင့် bot ထံ တိုက်ရိုက်ပို့သော media များကိုသာ ပြန်တင်ပေးနိုင်ပါတယ်။"""
RULES = """📋 စည်းကမ်းချက်များ

1. Admin ၃ ယောက်သာ စီမံခန့်ခွဲနိုင်ပါတယ်။
2. Source channel သည် ကိုယ်ပိုင် သို့မဟုတ် ခွင့်ပြုချက်ရှိသော channel ဖြစ်ရပါမယ်။
3. သူများ channel post များကို ခွင့်ပြုချက်မရှိဘဲ ကူးယူခြင်း၊ logo ဖယ်ရှားခြင်း၊ source ဖျောက်ခြင်း မလုပ်ပါ။
4. Bot ထံ ပို့သော media ကို target channel သို့ ပြန်တင်နိုင်ပါတယ်။
5. မူရင်း source link/copyright ကို မဖျောက်ပါနှင့်။"""
HELP = """📚 အသုံးပြုနည်း

/start — ကြိုဆိုစာနှင့် ခလုတ်များ
/rules — စည်းကမ်းချက်များ
/help — အကူအညီ
/status — အခြေအနေ
/channels — channel စာရင်း
/addchannel — ခွင့်ပြုထားသော source channel ထည့်ရန်
/removechannel — source channel ဖယ်ရှားရန်
/post — bot ထံ media ပို့ပြီး target channel သို့ ပြန်တင်ရန်
/stats — post အရေအတွက်နှင့် admin စာရင်း
/warn — reply လုပ်ထားသော user ကို Warning 1/2/3 မှတ်ရန်

Admin commands များကို admin ၃ ယောက်သာ အသုံးပြုနိုင်ပါတယ်။"""

_data_lock = threading.Lock()


def default_data():
    targets = [normalize_channel(item) for item in TARGET_CHANNELS_ENV.split(",") if item.strip()]
    if not targets and DEFAULT_TARGET_CHANNEL:
        targets = [normalize_channel(DEFAULT_TARGET_CHANNEL)]
    return {
        "approved_sources": [],
        "target_channels": targets,
        "enabled": True,
        "pending": {},
        "stats": {"source_posts": 0, "submitted_posts": 0, "failed_posts": 0},
        "warnings": {},
    }


def load_data():
    data = default_data()
    if DATA_FILE.exists():
        try:
            saved = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for key, value in saved.items():
                if isinstance(value, dict) and isinstance(data.get(key), dict):
                    data[key].update(value)
                else:
                    data[key] = value
            if not data["target_channels"] and saved.get("target_channel"):
                data["target_channels"] = [normalize_channel(saved["target_channel"])]
        except (OSError, ValueError) as exc:
            print(f"Data load warning: {exc}")
    return data


def save_data(data):
    with _data_lock:
        temporary = DATA_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(DATA_FILE)


def is_admin(event):
    return event.sender_id in ADMIN_IDS


def admin_only_message():
    return "❌ Admin များသာ သုံးနိုင်ပါတယ်။"


def normalize_channel(value):
    value = value.strip()
    match = re.search(r"(?:https?://)?t\.me/([A-Za-z0-9_+\-]+)", value)
    if match:
        value = match.group(1)
    return value.lstrip("@").strip()


def rewrite_caption(caption):
    """Rewrite an authorized caption with Gemini when configured; otherwise keep it."""
    caption = (caption or "").strip()
    if not caption or not GEMINI_API_KEY:
        return caption
    try:
        import requests
        prompt = (
            "Rewrite this movie caption in Burmese. Keep the meaning and all real links. "
            "Do not invent facts, remove attribution, or remove URLs. Return only the caption.\n\n"
            + caption
        )
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=8,
        )
        if response.ok:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"Gemini caption rewrite skipped: HTTP {response.status_code}")
    except Exception as exc:
        print(f"Gemini caption rewrite skipped: {exc}")
    return caption


async def rewrite_caption_async(caption):
    """Run blocking Gemini HTTP work away from Telethon's event loop."""
    if not caption or not GEMINI_API_KEY:
        return (caption or "").strip()
    return await asyncio.to_thread(rewrite_caption, caption)


async def build_caption(text, source_name=None):
    caption = await rewrite_caption_async(text)
    if AUTO_HASHTAGS:
        caption = f"{caption}\n\n{AUTO_HASHTAGS}" if caption else AUTO_HASHTAGS
    if source_name:
        caption += f"\n\n📎 Source: @{source_name}" if source_name else ""
    return caption


def channel_matches(chat, configured):
    username = (getattr(chat, "username", None) or "").lower()
    chat_id = str(getattr(chat, "id", ""))
    clean_id = chat_id.replace("-100", "")
    configured = str(configured).lower().lstrip("@")
    return configured in {username, chat_id, clean_id}


def main_keyboard():
    return [
        [Button.inline("📊 အခြေအနေ", b"status"), Button.inline("📡 Channel စာရင်း", b"channels")],
        [Button.inline("➕ Source ထည့်", b"add_source"), Button.inline("➖ Source ဖယ်", b"remove_source")],
        [Button.inline("🎯 Target ထည့်", b"set_target")],
        [Button.inline("🎬 Media တင်", b"submit_media"), Button.inline("⏯️ Auto Post", b"toggle_auto")],
        [Button.inline("📚 အကူအညီ", b"help"), Button.inline("📋 စည်းကမ်း", b"rules")],
    ]


def status_text(data):
    return (
        "✅ <b>Bot အခြေအနေ</b>\n\n"
        f"Auto Post: {'🟢 ဖွင့်ထား' if data['enabled'] else '🔴 ပိတ်ထား'}\n"
        f"Source channels: {len(data['approved_sources'])}\n"
        f"Targets: {', '.join(data['target_channels']) or 'မသတ်မှတ်ရသေး'}\n"
        f"Source posts: {data['stats']['source_posts']}\n"
        f"Submitted posts: {data['stats']['submitted_posts']}\n"
        f"Failed posts: {data['stats']['failed_posts']}\n"
        f"Warnings: {len(data['warnings'])}"
    )


# Python 3.14 no longer creates a default event loop automatically. Telethon
# 1.x expects one while constructing TelegramClient, so create it explicitly.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


@client.on(events.NewMessage(pattern=r"^/(start|rules|help|status|channels|stats)$"))
async def public_commands(event):
    command = event.pattern_match.group(1)
    print(f"Received /{command} from user_id={event.sender_id}", flush=True)
    if command == "start":
        await event.respond(WELCOME, buttons=main_keyboard())
    elif command == "rules":
        await event.respond(RULES, buttons=main_keyboard())
    elif command == "help":
        await event.respond(HELP, buttons=main_keyboard())
    elif command in {"status", "channels", "stats"}:
        if not is_admin(event):
            await event.respond(admin_only_message())
            return
        data = load_data()
        if command == "channels":
            sources = "\n".join(f"• {item}" for item in data["approved_sources"]) or "မရှိသေးပါ"
            await event.respond(f"📡 <b>ခွင့်ပြုထားသော Source channels</b>\n\n{sources}\n\nTargets: {', '.join(data['target_channels']) or 'မရှိသေးပါ'}", parse_mode="HTML", buttons=main_keyboard())
        else:
            await event.respond(status_text(data), parse_mode="HTML", buttons=main_keyboard())


@client.on(events.NewMessage(pattern=r"^/(addchannel|removechannel|settarget|post|warn|on|off)$"))
async def admin_commands(event):
    if not is_admin(event):
        await event.respond(admin_only_message())
        return
    command = event.pattern_match.group(1)
    data = load_data()
    if command == "addchannel":
        data["pending"][str(event.sender_id)] = "add_source"
        save_data(data)
        await event.respond("➕ ခွင့်ပြုချက်ရှိသော source channel link/username ကို ပို့ပါ။")
    elif command == "removechannel":
        data["pending"][str(event.sender_id)] = "remove_source"
        save_data(data)
        await event.respond("➖ ဖယ်ရှားမည့် source channel link/username ကို ပို့ပါ။")
    elif command == "settarget":
        data["pending"][str(event.sender_id)] = "set_target"
        save_data(data)
        await event.respond("🎯 ကိုယ်ပိုင် target channel link/username ကို ပို့ပါ။ Bot ကို အဲဒီ channel မှာ admin ထည့်ထားရပါမယ်။")
    elif command == "post":
        data["pending"][str(event.sender_id)] = "submit_media"
        save_data(data)
        await event.respond("🎬 Photo/video နှင့် caption ကို ဒီ chat ထဲပို့ပါ။ Bot က သတ်မှတ်ထားသော target channel သို့ တင်ပါမယ်။")
    elif command == "warn":
        replied = await event.get_reply_message()
        if not replied or not replied.sender_id:
            await event.respond("⚠️ Warning ပေးရန် user message ကို reply လုပ်ပြီး /warn ပို့ပါ။")
            return
        user_id = str(replied.sender_id)
        count = int(data["warnings"].get(user_id, 0)) + 1
        data["warnings"][user_id] = min(count, 3)
        save_data(data)
        if count == 1:
            message = "⚠️ Warning 1/3 — စည်းကမ်းချက်များကို လိုက်နာပါ။"
        elif count == 2:
            message = "⚠️ Warning 2/3 — နောက်ဆုံးသတိပေးချက် ဖြစ်ပါတယ်။"
        else:
            message = "⚠️ Warning 3/3 — သတိပေးချက် အများဆုံးရောက်ပါပြီ။ Admin က group စည်းကမ်းအတိုင်း ဆက်လက်ဆောင်ရွက်ပါမယ်။"
        await event.respond(message)
    elif command == "on":
        data["enabled"] = True
        save_data(data)
        await event.respond("✅ Auto Post ဖွင့်ပြီးပါပြီ။", buttons=main_keyboard())
    elif command == "off":
        data["enabled"] = False
        save_data(data)
        await event.respond("⏹️ Auto Post ပိတ်ပြီးပါပြီ။", buttons=main_keyboard())


@client.on(events.NewMessage(func=lambda event: event.is_private and not (event.raw_text or "").startswith("/")))
async def button_and_input_handler(event):
    if not is_admin(event):
        return
    data = load_data()
    text = (event.raw_text or "").strip()
    user_key = str(event.sender_id)
    pending = data["pending"].get(user_key)

    if text == "📊 အခြေအနေ":
        await event.respond(status_text(data), parse_mode="HTML", buttons=main_keyboard())
    elif text == "📡 Channel စာရင်း":
        await event.respond("📡 " + "\n".join(data["approved_sources"]) if data["approved_sources"] else "📡 Channel မရှိသေးပါ", buttons=main_keyboard())
    elif text == "➕ Source ထည့်":
        data["pending"][user_key] = "add_source"
        save_data(data)
        await event.respond("➕ ခွင့်ပြုချက်ရှိသော source channel link/username ကို ပို့ပါ။")
    elif text == "➖ Source ဖယ်":
        data["pending"][user_key] = "remove_source"
        save_data(data)
        await event.respond("➖ ဖယ်ရှားမည့် source channel link/username ကို ပို့ပါ။")
    elif text == "🎬 Media တင်":
        data["pending"][user_key] = "submit_media"
        save_data(data)
        await event.respond("🎬 Photo/video နှင့် caption ကို ပို့ပါ။")
    elif text == "⏯️ Auto Post":
        data["enabled"] = not data["enabled"]
        save_data(data)
        await event.respond("✅ Auto Post ဖွင့်ပြီးပါပြီ။" if data["enabled"] else "⏹️ Auto Post ပိတ်ပြီးပါပြီ။", buttons=main_keyboard())
    elif text == "📚 အကူအညီ":
        await event.respond(HELP, buttons=main_keyboard())
    elif text == "📋 စည်းကမ်း":
        await event.respond(RULES, buttons=main_keyboard())
    elif text == "🎯 Target ထည့်":
        data["pending"][user_key] = "set_target"
        save_data(data)
        await event.respond("🎯 ကိုယ်ပိုင် target channel link/username ကို ပို့ပါ။")
    elif pending in {"add_source", "remove_source", "set_target"}:
        channel = normalize_channel(text)
        if pending == "set_target" and channel:
            if channel and channel not in data["target_channels"]:
                data["target_channels"].append(channel)
            reply = f"✅ Target channel သတ်မှတ်ပြီးပါပြီ: {channel}"
        elif pending == "add_source" and channel and channel not in data["approved_sources"]:
            data["approved_sources"].append(channel)
            reply = f"✅ Source channel ထည့်ပြီးပါပြီ: {channel}"
        elif pending == "remove_source" and channel in data["approved_sources"]:
            data["approved_sources"].remove(channel)
            reply = f"✅ Source channel ဖယ်ပြီးပါပြီ: {channel}"
        else:
            reply = "❌ Channel မတွေ့ပါ သို့မဟုတ် link မမှန်ပါ။"
        data["pending"].pop(user_key, None)
        save_data(data)
        await event.respond(reply, buttons=main_keyboard())


@client.on(events.CallbackQuery)
async def inline_button_handler(event):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("Admin များသာ သုံးနိုင်ပါတယ်။", alert=True)
        return

    action = event.data.decode("utf-8")
    data = load_data()
    user_key = str(event.sender_id)
    await event.answer()

    if action == "status":
        await event.edit(status_text(data), parse_mode="HTML", buttons=main_keyboard())
    elif action == "channels":
        sources = "\n".join(f"• {item}" for item in data["approved_sources"]) or "မရှိသေးပါ"
        await event.edit(
            f"📡 <b>ခွင့်ပြုထားသော Source channels</b>\n\n{sources}\n\n"
            f"Targets: {', '.join(data['target_channels']) or 'မရှိသေးပါ'}",
            parse_mode="HTML", buttons=main_keyboard(),
        )
    elif action in {"add_source", "remove_source", "set_target"}:
        data["pending"][user_key] = action
        save_data(data)
        prompts = {
            "add_source": "➕ ခွင့်ပြုချက်ရှိသော source channel link/username ကို ပို့ပါ။",
            "remove_source": "➖ ဖယ်ရှားမည့် source channel link/username ကို ပို့ပါ။",
            "set_target": "🎯 ကိုယ်ပိုင် target channel link/username ကို ပို့ပါ။",
        }
        await event.edit(prompts[action], buttons=main_keyboard())
    elif action == "submit_media":
        data["pending"][user_key] = "submit_media"
        save_data(data)
        await event.edit("🎬 Photo/video နှင့် caption ကို ဒီ chat ထဲပို့ပါ။", buttons=main_keyboard())
    elif action == "toggle_auto":
        data["enabled"] = not data["enabled"]
        save_data(data)
        await event.edit("✅ Auto Post ဖွင့်ပြီးပါပြီ။" if data["enabled"] else "⏹️ Auto Post ပိတ်ပြီးပါပြီ။", buttons=main_keyboard())
    elif action == "help":
        await event.edit(HELP, buttons=main_keyboard())
    elif action == "rules":
        await event.edit(RULES, buttons=main_keyboard())


@client.on(events.NewMessage)
async def media_submission_handler(event):
    if not event.is_private or not is_admin(event) or not event.media:
        return
    data = load_data()
    if data["pending"].get(str(event.sender_id)) != "submit_media":
        return
    targets = data["target_channels"]
    if not targets:
        await event.respond("❌ Target channel မသတ်မှတ်ရသေးပါ။ Code ထဲမှာ TARGET_CHANNEL ထည့်ပါ။")
        return
    try:
        caption = await build_caption(event.text or "")
        await asyncio.gather(*(
            client.send_file(target, event.media, caption=caption)
            for target in targets
        ))
        data["stats"]["submitted_posts"] += 1
        await event.respond("✅ Media တင်ပြီးပါပြီ။")
    except Exception as exc:
        data["stats"]["failed_posts"] += 1
        await event.respond(f"❌ Media တင်မအောင်မြင်ပါ: {exc}")
    finally:
        data["pending"].pop(str(event.sender_id), None)
        save_data(data)


@client.on(events.NewMessage)
async def approved_source_listener(event):
    data = load_data()
    if not data["enabled"] or event.is_private or not (event.media or event.text):
        return
    chat = await event.get_chat()
    if not any(channel_matches(chat, source) for source in data["approved_sources"]):
        return
    if not data["target_channels"]:
        return
    try:
        source_name = getattr(chat, "username", None) or str(chat.id)
        caption = await build_caption(event.text or "", source_name if getattr(chat, "username", None) else None)
        if event.media:
            await asyncio.gather(*(
                client.send_file(target, event.media, caption=caption)
                for target in data["target_channels"]
            ))
        else:
            await asyncio.gather(*(
                client.send_message(target, caption)
                for target in data["target_channels"]
            ))
        data["stats"]["source_posts"] += 1
    except Exception as exc:
        data["stats"]["failed_posts"] += 1
        print(f"Approved source post failed: {exc}")
    save_data(data)


if __name__ == "__main__":
    if not BOT_TOKEN or not API_ID or not API_HASH:
        raise SystemExit("Set API_ID, API_HASH and BOT_TOKEN in .env")
    print("Telegram Auto Post Bot is running")
    print("Admins:", ", ".join(ADMIN_NAMES.values()))
    client.start(bot_token=BOT_TOKEN)
    me = client.loop.run_until_complete(client.get_me())
    print(f"Connected as @{getattr(me, 'username', None) or me.id}", flush=True)
    client.run_until_disconnected()
