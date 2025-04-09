import requests
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import OWNER_ID

logger = logging.getLogger(__name__)

# Temporary storage for user input with states
user_data = {}

# States for the anime command flow
class State:
    IDLE = 0
    WAITING_FOR_BUTTONS = 1
    WAITING_FOR_CHANNEL = 2

def fetch_anime_details(anime_name):
    query = """query ($search: String) {
        Media(search: $search, type: ANIME) {
            id
            title {
                romaji
                english
                native
            }
            coverImage {
                extraLarge
            }
            season
            episodes
            description
        }
    }"""
    variables = {"search": anime_name}
    response = requests.post("https://graphql.anilist.co", json={"query": query, "variables": variables})
    data = response.json()

    if "errors" in data:
        logger.error("Anime not found. Name provided: %s", anime_name)
        return None

    anime_data = data["data"]["Media"]
    titles = anime_data["title"]
    anime_id = anime_data["id"]

    anime_title = titles.get("english") or titles.get("romaji") or titles.get("native")
    anime_cover_url = f"https://img.anili.st/media/{anime_id}"

    season = anime_data.get("season", "N/A").capitalize()
    episodes = anime_data.get("episodes", "N/A")
    description = anime_data.get("description", "No description available")

    return {
        "anime_title": anime_title,
        "anime_cover_url": anime_cover_url,
        "season": season,
        "episodes": episodes,
        "description": description
    }

@Bot.on_message(filters.command("anime") & filters.private & filters.user(OWNER_ID))
async def anime_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Anime name is missing. Usage: /anime [anime name]")
        return

    anime_name = " ".join(message.command[1:])
    anime_details = fetch_anime_details(anime_name)

    if anime_details is None:
        await message.reply("Anime not found. Please check the name and try again.")
        return

    # Initialize user state and data
    user_data[user_id] = {
        **anime_details,
        "state": State.WAITING_FOR_BUTTONS
    }

    # Ask for button details
    await message.reply(
        "Please send the button details in these formats:\n\n"
        "1. One button per line (vertical):\n"
        "Button1 - https://example1.com\n"
        "Button2 - https://example2.com\n\n"
        "2. Side by side buttons (horizontal):\n"
        "Button1 - https://example1.com | Button2 - https://example2.com\n\n"
        "You can mix both formats as needed."
    )

@Bot.on_message(filters.text & filters.private & filters.user(OWNER_ID))
async def process_input(client, message: Message):
    user_id = message.from_user.id
    
    # Check if user has an active anime command session
    if user_id not in user_data or user_data[user_id].get("state") != State.WAITING_FOR_BUTTONS:
        return
    
    try:
        buttons = []
        
        # Process button details
        for line in message.text.strip().split('\n'):
            if not line.strip():
                continue
            
            if '|' in line:
                horizontal_buttons = []
                for part in line.split('|'):
                    if ' - ' not in part:
                        raise ValueError(f"Invalid button format in: {part}")
                    
                    button_text, button_url = [x.strip() for x in part.split(' - ', 1)]
                    if not (button_url.startswith("http://") or button_url.startswith("https://")):
                        raise ValueError(f"Invalid URL format: {button_url}")
                    
                    horizontal_buttons.append(InlineKeyboardButton(button_text, url=button_url))
                
                buttons.append(horizontal_buttons)
            else:
                if ' - ' not in line:
                    raise ValueError(f"Invalid button format in line: {line}")
                
                button_text, button_url = [x.strip() for x in line.split(' - ', 1)]
                if not (button_url.startswith("http://") or button_url.startswith("https://")):
                    raise ValueError(f"Invalid URL format: {button_url}")
                
                buttons.append([InlineKeyboardButton(button_text, url=button_url)])

        user_data[user_id]["buttons"] = buttons
        user_data[user_id]["state"] = State.WAITING_FOR_CHANNEL
        
        # Show preview and channel selection button
        preview = await message.reply_photo(
            photo=user_data[user_id]["anime_cover_url"],
            caption=(
                f"✨ Anime Name: {user_data[user_id]['anime_title']} | {user_data[user_id]['anime_title']} ✨\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📺 Quality: 720p | 1080p\n"
                f"🍂 Season: {user_data[user_id]['season']}\n"
                f"📆 Episodes: 1 to {user_data[user_id]['episodes']}\n"
                f"━━━━━━━━━━━━━━━"
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        # Get channels where bot is admin and create selection buttons
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
            return

        # Create channel selection keyboard
        keyboard = []
        for channel in channels:
            keyboard.append([
                InlineKeyboardButton(
                    f"{channel['title']}",
                    callback_data=f"anime_post_{channel['id']}"
                )
            ])

        await message.reply(
            "Select a channel to post:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except ValueError as e:
        await message.reply(f"❌ Error: {str(e)}\nPlease follow the correct button format.")

@Bot.on_callback_query(filters.regex("^anime_post_") & filters.user(OWNER_ID))
async def post_to_channel(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        if user_id not in user_data or user_data[user_id].get("state") != State.WAITING_FOR_CHANNEL:
            await callback_query.answer("No active session found.", show_alert=True)
            return

        channel_id = int(callback_query.data.replace("anime_post_", ""))
        
        # Show channel ID in message box
        await callback_query.message.edit_text(f"{channel_id}")

        # Post to channel
        await client.send_photo(
            chat_id=channel_id,
            photo=user_data[user_id]["anime_cover_url"],
            caption=(
                f"✨ Anime Name: {user_data[user_id]['anime_title']} | {user_data[user_id]['anime_title']} ✨\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📺 Quality: 720p | 1080p\n"
                f"🍂 Season: {user_data[user_id]['season']}\n"
                f"📆 Episodes: 1 to {user_data[user_id]['episodes']}\n"
                f"━━━━━━━━━━━━━━━"
            ),
            reply_markup=InlineKeyboardMarkup(user_data[user_id]["buttons"])
        )

        # Clean up
        user_data.pop(user_id)
        await callback_query.message.reply("✅ Posted successfully!")

    except Exception as e:
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)