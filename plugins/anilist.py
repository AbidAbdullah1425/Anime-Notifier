from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import requests
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
          english
          native
        }
        coverImage {
          large
        }
        episodes
        season
        startDate {
          year
        }
      }
    }
    """
    variables = {"search": anime_name}
    response = requests.post("https://graphql.anilist.co", json={"query": query, "variables": variables})
    response.raise_for_status()
    
    return response.json()['data']['Media']

def format_anime_post(anime_details):
    title_english = anime_details['title'].get('english', anime_details['title']['romaji'])
    title_romaji = anime_details['title']['romaji']
    title_native = anime_details['title']['native']
    cover_image = anime_details['coverImage']['large']
    episodes = anime_details['episodes']
    season = anime_details['season']
    year = anime_details['startDate']['year']
    
    post_text = (
        f"✨ Anime Name: {title_english} | {title_native}✨\n"
        "━━━━━━━━━━━━━━━\n"
        "🗣 Language: Japanese\n"
        "📺 Quality: 720p | 1080p\n"
        f"🍂 Season: {season} {year}\n"
        f"📆 Episode: 1 to {episodes}\n"
    )
    
    return post_text, cover_image

@Client.on_message(filters.command("anime") & filters.private & filters.user(OWNER_ID))
async def anime_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Anime name is missing. Usage: /anime [anime name]")
        return

    anime_name = " ".join(message.command[1:])
    try:
        anime_details = fetch_anime_details(anime_name)
        post_text, cover_image = format_anime_post(anime_details)
        
        user_data[user_id] = {
            "anime_details": anime_details,
            "post_text": post_text,
            "cover_image": cover_image,
            "buttons": [],
            "in_progress": True
        }

        await message.reply_photo(
            photo=cover_image,
            caption=post_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Add Button", callback_data="add_button")]])
        )

    except Exception as e:
        logger.exception("An error occurred while processing the /anime command.")
        await message.reply("An error occurred while fetching the anime details. Please try again.")

@Client.on_callback_query(filters.regex("add_button") & filters.user(OWNER_ID))
async def add_button_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    await callback_query.message.reply("Please send the button text and URL in the format: `Button Text | URL`\nYou can add multiple buttons by sending each in a new line.")

@Client.on_message(filters.text & filters.private & filters.user(OWNER_ID))
async def button_input_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    user_input = message.text.strip()
    if user_input.lower() == "done":
        await message.reply("Please provide the channel ID where you want to post the content.")
        user_data[user_id]["waiting_for_channel"] = True
        return

    if "waiting_for_channel" in user_data[user_id]:
        channel_id = user_input
        try:
            post_text = user_data[user_id]["post_text"]
            cover_image = user_data[user_id]["cover_image"]
            buttons = user_data[user_id]["buttons"]
            reply_markup = InlineKeyboardMarkup(buttons)

            await client.send_photo(
                chat_id=channel_id,
                photo=cover_image,
                caption=post_text,
                reply_markup=reply_markup
            )
            await message.reply("Post successfully sent!")
            user_data.pop(user_id)

        except Exception as e:
            logger.exception("An error occurred while posting to the channel.")
            await message.reply("An error occurred while posting to the channel. Please ensure the bot has permission to post in the channel.")
        return

    try:
        button_text, button_url = user_input.split("|")
        button_text = button_text.strip()
        button_url = button_url.strip()

        if not (button_url.startswith("http://") or button_url.startswith("https://")):
            await message.reply("Invalid URL. Please provide a valid URL (starting with http:// or https://).")
            return

        user_data[user_id]["buttons"].append([InlineKeyboardButton(button_text, url=button_url)])
        await message.reply("Button added. Send 'done' if you have finished adding buttons or add another button in the format: `Button Text | URL`")

    except ValueError:
        await message.reply("Invalid format. Please provide the button text and URL in the format: `Button Text | URL`")

@Client.on_callback_query(filters.regex("done") & filters.user(OWNER_ID))
async def done_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    await callback_query.message.reply("Please provide the channel ID where you want to post the content.")
    user_data[user_id]["waiting_for_channel"] = True




