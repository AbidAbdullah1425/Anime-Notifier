import requests
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import OWNER_ID

logger = logging.getLogger(__name__)

# Temporary storage for user input
user_data = {}

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

    # Prefer English title if available; fallback to romaji or native
    anime_title = titles.get("english") or titles.get("romaji") or titles.get("native")
    anime_cover_url = f"https://img.anili.st/media/{anime_id}"

    # Fetch additional metadata
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
async def anime_new_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Anime name is missing. Usage: /anime [anime name]")
        return

    anime_name = " ".join(message.command[1:])
    anime_details = fetch_anime_details(anime_name)

    if anime_details is None:
        await message.reply("Anime not found. Please check the name and try again.")
        return

    # Save anime details to user_data
    user_data[user_id] = anime_details
    user_data[user_id]["in_progress"] = True

    # First, ask for button details
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
async def process_buttons(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    try:
        buttons = []
        
        # Process button details line by line
        for line in message.text.strip().split('\n'):
            if not line.strip():
                continue
            
            # Check if line contains horizontal buttons (separated by |)
            if '|' in line:
                horizontal_buttons = []
                button_parts = line.split('|')
                
                for part in button_parts:
                    if ' - ' not in part:
                        raise ValueError(f"Invalid button format in: {part}")
                    
                    button_text, button_url = [x.strip() for x in part.split(' - ', 1)]
                    
                    if not (button_url.startswith("http://") or button_url.startswith("https://")):
                        raise ValueError(f"Invalid URL format: {button_url}")
                    
                    horizontal_buttons.append(InlineKeyboardButton(button_text, url=button_url))
                
                buttons.append(horizontal_buttons)
            
            # Single button per line
            else:
                if ' - ' not in line:
                    raise ValueError(f"Invalid button format in line: {line}")
                
                button_text, button_url = [x.strip() for x in line.split(' - ', 1)]
                
                if not (button_url.startswith("http://") or button_url.startswith("https://")):
                    raise ValueError(f"Invalid URL format: {button_url}")
                
                buttons.append([InlineKeyboardButton(button_text, url=button_url)])

        user_data[user_id]["buttons"] = buttons
        
        # Show preview and ask for channel selection
        preview_msg = await message.reply_photo(
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
        
        # Add channel selection button
        await message.reply(
            "Preview shown above. Now you can:\n\n"
            "1. Send new button format to update the buttons\n"
            "2. Click 'Select Channel' to post\n\n"
            "Button Format Examples:\n"
            "• Single row: Button - URL\n"
            "• Side by side: Button1 - URL1 | Button2 - URL2",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 Select Channel", callback_data="select_channel")
            ]])
        )

    except ValueError as e:
        await message.reply(
            f"❌ Error: {str(e)}\n\n"
            "Please use one of these formats:\n"
            "1. One button per line:\n"
            "Button1 - https://example1.com\n"
            "Button2 - https://example2.com\n\n"
            "2. Side by side buttons:\n"
            "Button1 - https://example1.com | Button2 - https://example2.com"
        )

@Bot.on_callback_query(filters.regex("select_channel") & filters.user(OWNER_ID))
async def channel_selector(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        if user_id not in user_data:
            await callback_query.answer("Session expired. Please start over.", show_alert=True)
            return

        # Forward message to channel
        await callback_query.message.edit_text(
            "Please forward a message from your target channel or share your post to channel."
        )

    except Exception as e:
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)

@Bot.on_message(filters.forwarded & filters.private & filters.user(OWNER_ID))
async def handle_forwarded(client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_data:
        return

    try:
        # Get the channel information
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            channel_id = message.forward_from_chat.id
            
            try:
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
                await message.reply("✅ Posted successfully!")
            except Exception as e:
                await message.reply(f"❌ Failed to post to channel. Error: {str(e)}")
        else:
            await message.reply("❌ Please forward a message from a channel, not from a user or group.")
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")