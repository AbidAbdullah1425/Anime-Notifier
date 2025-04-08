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
    query = """
    query ($search: String) {
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
    }
    """
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
    anime_cover_url = f"https://img.anili.st/media/{anime_id}"  # Use the AniList media cover URL

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
async def anime_new_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Anime name is missing. Usage: /source [anime name]")
        return

    anime_name = " ".join(message.command[1:])
    try:
        anime_details = fetch_anime_details(anime_name)
        post_text, anime_cover_url = format_anime_post(anime_details)
        
        user_data[user_id] = {
            "anime_details": anime_details,
            "post_text": post_text,
            "anime_cover_url": anime_cover_url,
            "buttons": [],
            "in_progress": True
        }

        await message.reply_photo(
            photo=anime_cover_url,
            caption=post_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Add Button", callback_data="add_button")],
                [InlineKeyboardButton("Skip Button", callback_data="skip_button")],
                [InlineKeyboardButton("Cancel", callback_data="cancel_process")]
            ])
        )

    except Exception as e:
        logger.exception("An error occurred while processing the /source command.")
        await message.reply("An error occurred while fetching the anime details. Please try again.")

@Bot.on_callback_query(filters.regex("add_button") & filters.user(OWNER_ID))
async def add_button_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    await callback_query.message.reply(
        "Please send the button text and URL in the format: `Button Name - URL` or `Button Name - URL\nButton Name - URL` for multiple buttons. Use `|` to separate buttons on the same line.",
        quote=True
    )

@Bot.on_message(filters.text & filters.private & filters.user(OWNER_ID) & filters.reply)
async def button_input_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    if message.reply_to_message is None:
        await message.reply("Please reply to the bot's message.", quote=True)
        return

    user_input = message.text.strip()
    buttons = []
    try:
        for line in user_input.split("\n"):
            horizontal_buttons = []
            for part in line.split("|"):
                btn_text_url = part.split("-")
                if len(btn_text_url) != 2:
                    await message.reply("Invalid format. Please provide the button text and URL in the format: `Button Name - URL`", quote=True)
                    return

                button_text = btn_text_url[0].strip()
                button_url = btn_text_url[1].strip()

                if not (button_url.startswith("http://") or button_url.startswith("https://")):
                    await message.reply("Invalid URL. Please provide a valid URL (starting with http:// or https://).", quote=True)
                    return

                horizontal_buttons.append(InlineKeyboardButton(button_text, url=button_url))
            buttons.append(horizontal_buttons)

        user_data[user_id]["buttons"] = buttons

        await message.reply(
            "Buttons added. Please select the channel where you want to post the content:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Select Channel", switch_inline_query_current_chat="select_channel")]
            ])
        )
        user_data[user_id]["waiting_for_channel"] = True

    except ValueError:
        await message.reply("Invalid format. Please provide the button text and URL in the format: `Button Name - URL`", quote=True)

@Bot.on_callback_query(filters.regex("skip_button") & filters.user(OWNER_ID))
async def skip_button_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    await callback_query.message.reply(
        "Please select the channel where you want to post the content:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Select Channel", switch_inline_query_current_chat="select_channel")]
        ])
    )
    user_data[user_id]["waiting_for_channel"] = True

@Bot.on_callback_query(filters.regex("cancel_process") & filters.user(OWNER_ID))
async def cancel_process_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_data:
        user_data.pop(user_id)
    await callback_query.message.reply("Process has been canceled.", quote=True)

@Bot.on_inline_query(filters.user(OWNER_ID))
async def inline_query_handler(client, inline_query):
    user_id = inline_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("waiting_for_channel"):
        return

    results = [
        {
            "type": "article",
            "id": "select_channel",
            "title": "Select this channel",
            "input_message_content": {
                "message_text": "Selected channel"
            }
        }
    ]
    await inline_query.answer(results, cache_time=1)

@Bot.on_message(filters.text & filters.private & filters.user(OWNER_ID))
async def channel_selection_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id].get("waiting_for_channel"):
        return

    channel_id = message.forward_from_chat.id
    try:
        post_text = user_data[user_id]["post_text"]
        buttons = user_data[user_id]["buttons"]
        cover_image = user_data[user_id]["anime_cover_url"]
        reply_markup = InlineKeyboardMarkup(buttons)

        await client.send_photo(
            chat_id=channel_id,
            photo=cover_image,
            caption=post_text,
            reply_markup=reply_markup
        )
        await message.reply("Post successfully sent!", quote=True)
        user_data.pop(user_id)

    except Exception as e:
        logger.exception("An error occurred while posting to the channel.")
        await message.reply("An error occurred while posting to the channel. Please ensure the bot has permission to post in the channel.", quote=True)