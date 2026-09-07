"""
Channel Test Script - Bot က Channel ထဲ message ပို့လို့ရလား စမ်းသပ့်ရန်
Run: python3 test_channel.py @channel_name
"""

import asyncio
from telethon import TelegramClient

# Configuration (same as bot.py)
API_ID = 2000000
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_TOKEN = "8249701481:AAGsVCusZe5Dn8MJkPwGqMyeFVsJtlij3Bo"
SESSION_NAME = "auto_post_bot_session"


async def main():
    # Get target channel from command line
    import sys
    if len(sys.argv) < 2:
        print("⚠️ Channel name ထည့်ရန် လိုအပ်ပါ")
        print("   ဥပမာ: python3 test_channel.py @my_channel")
        print("   သို့မဟုတ်: python3 test_channel.py https://t.me/my_channel")
        return

    target = sys.argv[1]
    # Clean up target
    if target.startswith("https://t.me/"):
        target = "@" + target.split("/")[-1]
    if not target.startswith("@"):
        target = "@" + target

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    print(f"✅ Logged in as: {me.first_name} (@{me.username})")

    print(f"\n📨 Sending test message to {target}...")
    try:
        await client.send_message(target, "🧪 Bot စမ်းသပ်မှု အောင်မြင်!\nBot က Channel ထဲ message ပို့လို့ရပါတယ်။")
        print(f"✅ SUCCESS! {target} ထဲ message ပို့အောင်မြင်ပါတယ်!")
        print("   Channel ထဲသွားကြည့်ပါ")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print("\n📋 ဖြေရှင်းနည်းများ:")
        print("   1. Bot ကို Channel ထဲ Admin အဖြစ် ထည့်ပါ")
        print("   2. Channel link မှားနေလား စစ်ပါ")
        print("   3. Channel က private ဆိုရင် Bot ကို invite link နဲ့ join ခိုင်းပါ")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
