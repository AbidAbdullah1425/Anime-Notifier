import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import OWNER_ID

logger = logging.getLogger(__name__)

# Temporary storage for source command
source_data = {}

@Bot.on_message(filters.command("source") & filters.private & filters.user(OWNER_ID))
async def source_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Source name is missing. Usage: /source [source name]")
        return

    source_name = " ".join(message.command[1:])
    
    # Initialize user data
    source_data[user_id] = {
        "source_name": source_name,
        "in_progress": True
    }

    # Get channels where bot is admin
    channels = []
    async for dialog in client.get_dialogs():
        if dialog.chat.type == "channel":
            try:
                member = await client.get_chat_member(dialog.chat.id, "me")
                if member.can_post_messages:
                    channels.append({
                        "title": dialog.chat.title,
                        "id": dialog.chat.id
                    })
            except Exception:
                continue

    if not channels:
        await message.reply("No channels found where bot can post!")
        source_data.pop(user_id)
        return

    # Create channel selection keyboard
    keyboard = []
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(
                f"{channel['title']}",
                callback_data=f"source_post_{channel['id']}"
            )
        ])

    # Show preview and channel selection
    await message.reply(
        f"✨ Source: {source_name} ✨\n"
        "━━━━━━━━━━━━━━━\n\n"
        "Select a channel to post:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@Bot.on_callback_query(filters.regex("^source_post_") & filters.user(OWNER_ID))
async def post_source_to_channel(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        if user_id not in source_data:
            await callback_query.answer("Session expired. Please start over.", show_alert=True)
            return

        channel_id = int(callback_query.data.replace("source_post_", ""))
        
        # Show channel ID
        await callback_query.message.edit_text(f"{channel_id}")

        # Post to channel
        await client.send_message(
            chat_id=channel_id,
            text=(
                f"✨ Source: {source_data[user_id]['source_name']} ✨\n"
                "━━━━━━━━━━━━━━━"
            )
        )

        # Clean up
        source_data.pop(user_id)
        await callback_query.message.reply("✅ Posted successfully!")

    except Exception as e:
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)