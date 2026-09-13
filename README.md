# Telegram Auto Post Bot

A Telegram bot for **authorized** auto-posting. It has two safe modes:

1. **Approved-source mode:** the bot reads posts only from channels where the bot/account has access and that an admin explicitly added with `/addchannel`.
2. **User-submission mode:** an admin sends a photo/video to the bot, and the bot posts it to the configured target channel.

The bot does not bypass channel permissions, scrape inaccessible channels, remove other people's logos, or hide source/copyright information.

## Admins

The code allows exactly these three admin IDs:

| Username | Telegram ID |
|---|---:|
| `@waiyanphyo99` | `6081621017` |
| `@waiyan7861` | `6940887457` |
| `@Bingopop1991` | `6432487408` |

Non-admin users receive `❌ Admin များသာ သုံးနိုင်ပါတယ်။` for admin commands.

## Environment

Copy `.env.example` to `.env` and fill in real values. Never commit `.env` or tokens.

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_new_bot_token
TARGET_CHANNEL=@your_own_target_channel
SESSION_NAME=auto_post_bot_session
DATA_FILE=bot_data.json
```

`TARGET_CHANNEL` must be a channel owned by you or one where the bot has permission to post. You can also set it inside Telegram with `/settarget`.

If a token was exposed in a screenshot or chat, revoke it in BotFather and create a new token before running the bot.

## Burmese commands and buttons

- `/start` — `🤖 Bot အလုပ်လုပ်နေပါပြီ` and the main buttons
- `/rules` — rules
- `/help` — general help and admin command help
- `/status` — enabled state, channel counts, and post counters
- `/channels` — approved source and target list
- `/addchannel` — add an authorized source channel
- `/removechannel` — remove a source channel
- `/settarget` — set your target channel
- `/post` — send media to the bot for reposting
- `/on` and `/off` — enable/disable approved-source auto-posting
- `/stats` — statistics

The same actions are available from Burmese buttons after `/start`.

## Channel setup

1. Add the bot as an administrator in your own target channel.
2. If using approved-source mode, add the bot/account to each source channel as required by Telegram and ensure you have permission to repost the content.
3. Send `/settarget` and send the target channel username or link.
4. Send `/addchannel` and send an authorized source channel username or link.
5. Send `/on`.
6. For user-submission mode, send `/post`, then send a photo/video with its caption.

The bot adds a source attribution line when reposting an approved source post. Logo removal and source hiding are intentionally not implemented.

## Termux: foreground test

```bash
pkg update -y
pkg install python git clang rust openssl -y
git clone https://github.com/jue32583-tech/telegram-auto-post-dater.git
cd telegram-auto-post-dater
pip install -r requirements.txt
cp .env.example .env
nano .env
python bot.py
```

## Termux: 24/7 background service

For a restartable service, install `termux-services`:

```bash
pkg install termux-services -y
source $PREFIX/etc/profile.d/start-services.sh
cd ~/telegram-auto-post-dater
chmod +x termux/run-bot.sh termux/install-service.sh
./termux/install-service.sh
sv up telegram-auto-post-bot
sv status telegram-auto-post-bot
tail -f logs/current
```

Stop or restart it with:

```bash
sv down telegram-auto-post-bot
sv up telegram-auto-post-bot
```

Keep Android from stopping Termux:

- Android Settings → Apps → Termux → Battery → **Unrestricted**.
- Do not swipe Termux away from recent apps.
- Install Termux:Boot if the bot must start after a phone reboot; create `~/.termux/boot/start-bot` containing `sv up telegram-auto-post-bot` and run `chmod +x ~/.termux/boot/start-bot`.
- `termux-wake-lock` is called by the service and may increase battery use.

A phone-based service can still stop when the phone loses power, data, or Android terminates the app. For reliable unattended 24/7 operation, use an always-on server.

## Security

Do not paste `BOT_TOKEN`, `API_HASH`, login codes, or two-step verification passwords into chat. The bot never asks users for Telegram login codes or phone verification codes.
