import os
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.getenv("8916785736:AAGLli4iSJMYNlW0WxctiRLpFh4lB_AzSZk")
OWNER_ID_TEXT = os.getenv("7827157553", "0")
REPLY_FILE = Path("reply.txt")


def load_reply() -> str:
    if REPLY_FILE.exists():
        return REPLY_FILE.read_text(encoding="utf-8")
    return ""


async def setreply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    try:
        owner_id = int(OWNER_ID_TEXT)
    except ValueError:
        owner_id = 0

    if user.id != owner_id:
        return

    new_reply = " ".join(context.args).strip()
    if not new_reply:
        await message.reply_text("Use: /setreply Your message")
        return

    REPLY_FILE.write_text(new_reply, encoding="utf-8")
    context.application.bot_data["reply"] = new_reply
    await message.reply_text("Auto-reply set successfully!")


async def auto_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    if not message:
        return

    reply = context.application.bot_data.get("reply", "")
    if reply:
        await message.reply_text(reply)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in Environment variables.")

    try:
        owner_id = int(OWNER_ID_TEXT)
    except ValueError as exc:
        raise RuntimeError("OWNER_ID must be a numeric Telegram user ID.") from exc

    if owner_id <= 0:
        raise RuntimeError("Set OWNER_ID to your numeric Telegram user ID.")

    app = Application.builder().token(TOKEN).build()
    app.bot_data["reply"] = load_reply()

    # The bot has exactly one command: /setreply
    app.add_handler(CommandHandler("setreply", setreply))
    app.add_handler(MessageHandler(filters.ALL, auto_reply))

    print("Telegram Auto Reply Bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
      
