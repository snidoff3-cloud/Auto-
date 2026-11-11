import json
import os
from pathlib import Path

from telegram import MessageEntity, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID_TEXT = os.getenv("OWNER_ID", "0")
REPLY_FILE = Path("reply.json")


def load_saved_reply():
    if not REPLY_FILE.exists():
        return "", []

    try:
        data = json.loads(REPLY_FILE.read_text(encoding="utf-8"))
        return data.get("text", ""), data.get("entities", [])
    except (json.JSONDecodeError, OSError):
        return "", []


async def setreply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if not message or not user or not message.text:
        return

    try:
        owner_id = int(OWNER_ID_TEXT)
    except ValueError:
        owner_id = 0

    if user.id != owner_id:
        return

    command_entity = next(
        (
            entity
            for entity in (message.entities or [])
            if entity.type == MessageEntity.BOT_COMMAND and entity.offset == 0
        ),
        None,
    )

    command_end = command_entity.length if command_entity else len("/setreply")
    body_start = command_end

    # Remove only one separator; preserve all remaining spaces and newlines.
    if body_start < len(message.text) and message.text[body_start] in (" ", "\n"):
        body_start += 1

    reply_text = message.text[body_start:]
    if not reply_text.strip():
        await message.reply_text("Use: /setreply Your message")
        return

    # Telegram entity offsets are measured in UTF-16 code units.
    prefix_units = len(message.text[:body_start].encode("utf-16-le")) // 2

    saved_entities = []
    for entity in message.entities or []:
        if entity.type == MessageEntity.BOT_COMMAND:
            continue

        entity_start = entity.offset
        entity_end = entity.offset + entity.length
        clipped_start = max(entity_start, prefix_units)

        if entity_end <= prefix_units or clipped_start >= entity_end:
            continue

        entity_data = entity.to_dict()
        entity_data["offset"] = clipped_start - prefix_units
        entity_data["length"] = entity_end - clipped_start
        saved_entities.append(entity_data)

    REPLY_FILE.write_text(
        json.dumps(
            {"text": reply_text, "entities": saved_entities},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    context.application.bot_data["reply_text"] = reply_text
    context.application.bot_data["reply_entities"] = saved_entities
    await message.reply_text("Auto-reply saved with line breaks and formatting!")


async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    reply_text = context.application.bot_data.get("reply_text", "")
    saved_entities = context.application.bot_data.get("reply_entities", [])

    if not reply_text:
        return

    entities = [
        MessageEntity.de_json(entity_data, context.bot)
        for entity_data in saved_entities
    ]
    await message.reply_text(reply_text, entities=entities)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    try:
        owner_id = int(OWNER_ID_TEXT)
    except ValueError as exc:
        raise RuntimeError("OWNER_ID must be a numeric Telegram user ID.") from exc

    if owner_id <= 0:
        raise RuntimeError("Set OWNER_ID to your numeric Telegram user ID.")

    app = Application.builder().token(TOKEN).build()

    saved_text, saved_entities = load_saved_reply()
    app.bot_data["reply_text"] = saved_text
    app.bot_data["reply_entities"] = saved_entities

    # Exactly one command: /setreply
    app.add_handler(CommandHandler("setreply", setreply))
    app.add_handler(MessageHandler(filters.ALL, auto_reply))

    print("Telegram Auto Reply Bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
