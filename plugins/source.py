from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bot import Bot
import logging
from config import OWNER_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary storage for user input
user_data = {}

def fetch_anime_details(anime_name):
    query = """query ($search: String) {
        Media(search: $search, type: ANIME) {
            id
            title {
                romaji
                native
            }
            genres
            format
            averageScore
            status
            startDate {
                year
                month
                day
            }
            endDate {
                year
                month
                day
            }
            duration
            episodes
            description
            coverImage {
                extraLarge
            }
            season
        }
    }"""
    variables = {"search": anime_name}
    response = requests.post("https://graphql.anilist.co", json={"query": query, "variables": variables})
    response.raise_for_status()
    
    return response.json()['data']['Media']

def format_anime_post(anime_details):
    title_romaji = anime_details['title']['romaji']
    title_native = anime_details['title']['native']
    genres = ", ".join(anime_details['genres'])
    format = anime_details['format']
    average_score = anime_details['averageScore']
    status = anime_details['status']
    start_date = f"{anime_details['startDate']['year']}-{anime_details['startDate']['month']:02}-{anime_details['startDate']['day']:02}"
    end_date = f"{anime_details['endDate']['year']}-{anime_details['endDate']['month']:02}-{anime_details['endDate']['day']:02}" if anime_details['endDate']['year'] else "N/A"
    duration = anime_details['duration']
    episodes = anime_details['episodes']
    description = anime_details['description']
    anime_id = anime_details["id"]
    anime_cover_url = f"https://img.anili.st/media/{anime_id}"

    post_text = (
        f"✨ Anime Name: {title_romaji} | {title_native} ✨\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📺 Quality: 720p | 1080p\n"
        f"🍂 Season: {anime_details['season']}\n"
        f"📆 Episodes: 1 to {episodes}\n"
        f"━━━━━━━━━━━━━━━"
    )
    
    return post_text, anime_cover_url

@Bot.on_message(filters.command("source") & filters.private & filters.user(OWNER_ID))
async def source_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Anime name is missing. Usage: /source [anime name]")
        return

    anime_name = " ".join(message.command[1:])
    try:
        anime_details = fetch_anime_details(anime_name)
        post_text, anime_cover_url = format_anime_post(anime_details)
        
        user_data[user_id] = {
            "post_text": post_text,
            "anime_cover_url": anime_cover_url,
            "in_progress": True
        }

        # First, ask for button details
        await message.reply_photo(
            photo=anime_cover_url,
            caption=post_text
        )
        
        await message.reply(
            "Please send the button details in these formats:\n\n"
            "1. One button per line (vertical):\n"
            "Button1 - https://example1.com\n"
            "Button2 - https://example2.com\n\n"
            "2. Side by side buttons (horizontal):\n"
            "Button1 - https://example1.com | Button2 - https://example2.com\n\n"
            "You can mix both formats as needed."
        )

    except Exception as e:
        logger.exception("An error occurred while processing the /source command.")
        await message.reply("An error occurred while fetching the anime details. Please try again.")

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
            caption=user_data[user_id]["post_text"],
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
        # Get the list of channels where the bot is admin
        dialogs = []
        async for dialog in client.get_dialogs():
            if dialog.chat.type == "channel":
                # Check if bot has admin rights in the channel
                try:
                    member = await client.get_chat_member(dialog.chat.id, (await client.get_me()).id)
                    if member.status in ["administrator", "creator"]:
                        dialogs.append({
                            "title": dialog.chat.title,
                            "id": dialog.chat.id
                        })
                except Exception:
                    continue

        if not dialogs:
            await callback_query.answer("No channels found where bot is admin!", show_alert=True)
            return

        # Create keyboard with channel list
        keyboard = []
        for dialog in dialogs:
            keyboard.append([
                InlineKeyboardButton(
                    f"📢 {dialog['title']}", 
                    callback_data=f"post_to_{dialog['id']}"
                )
            ])

        await callback_query.message.edit_text(
            "Select a channel to post:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)

@Bot.on_callback_query(filters.regex("^post_to_") & filters.user(OWNER_ID))
async def post_to_channel(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("Session expired. Please start over.", show_alert=True)
        return

    try:
        channel_id = int(callback_query.data.replace("post_to_", ""))
        
        # Post to channel
        await client.send_photo(
            chat_id=channel_id,
            photo=user_data[user_id]["anime_cover_url"],
            caption=user_data[user_id]["post_text"],
            reply_markup=InlineKeyboardMarkup(user_data[user_id]["buttons"])
        )

        # Clean up
        user_data.pop(user_id)
        await callback_query.message.edit_text("✅ Posted successfully!")

    except Exception as e:
        await callback_query.answer(f"Error posting: {str(e)}", show_alert=True)