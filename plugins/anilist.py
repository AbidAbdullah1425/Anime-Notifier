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
          extraLarge
        }
        season
        episodes
        description
      }
    }
    """
    variables = {"search": anime_name}
    response = requests.post("https://graphql.anilist.co", json={"query": query, "variables": variables})
    data = response.json()

    if "errors" in data:
        logger.error("Anime not found. Name provided: %s", anime_name)
        return None  # Return None to indicate failure

    anime_data = data["data"]["Media"]
    titles = anime_data["title"]
    anime_id = anime_data["id"]

    # Prefer English title if available; fallback to romaji or native
    anime_title = titles.get("english") or titles.get("romaji") or titles.get("native")
    anime_cover_url = f"https://img.anili.st/media/{anime_id}"  # Use the AniList media cover URL

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
    user_data[user_id]["buttons"] = []
    user_data[user_id]["in_progress"] = True  # Set in-progress state

    await message.reply_photo(
        photo=anime_details["anime_cover_url"],
        caption=(
            f"✨ Anime Name: {anime_details['anime_title']} | {anime_details['anime_title']} ✨\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📺 Quality: 720p | 1080p\n"
            f"🍂 Season: {anime_details['season']}\n"
            f"📆 Episodes: 1 to {anime_details['episodes']}\n"
            f"━━━━━━━━━━━━━━━"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Add Button", callback_data="add_button")],
            [InlineKeyboardButton("Skip Button", callback_data="skip_button")]
        ])
    )

@Bot.on_callback_query(filters.regex("add_button") & filters.user(OWNER_ID))
async def add_button_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    await callback_query.message.reply("Please send the button text and URL in the format: `Button Text | URL`. Send 'done' when you are finished.", quote=True)

@Bot.on_callback_query(filters.regex("skip_button") & filters.user(OWNER_ID))
async def skip_button_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    await callback_query.message.reply(
        "Please select the channel where you want to post the content:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Select Channel", switch_inline_query="select_channel")]
        ])
    )
    user_data[user_id]["waiting_for_channel"] = True

@Bot.on_callback_query(filters.regex("cancel_process") & filters.user(OWNER_ID))
async def cancel_process_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_data:
        user_data.pop(user_id)
    await callback_query.message.reply("Process has been canceled.", quote=True)

@Bot.on_message(filters.text & filters.private & filters.user(OWNER_ID) & filters.reply)
async def button_input_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    if message.reply_to_message is None:
        await message.reply("Please reply to the bot's message.", quote=True)
        return

    user_input = message.text.strip()
    if user_input.lower() == "done":
        await message.reply(
            "Please select the channel where you want to post the content:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Select Channel", switch_inline_query="select_channel")]
            ])
        )
        user_data[user_id]["waiting_for_channel"] = True
        return

    if "waiting_for_channel" in user_data[user_id] and message.reply_to_message.text == "Please select the channel where you want to post the content:":
        channel_id = message.forward_from_chat.id
        try:
            post_text = (
                f"✨ Anime Name: {user_data[user_id]['anime_title']} | {user_data[user_id]['anime_title']} ✨\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📺 Quality: 720p | 1080p\n"
                f"🍂 Season: {user_data[user_id]['season']}\n"
                f"📆 Episodes: 1 to {user_data[user_id]['episodes']}\n"
                f"━━━━━━━━━━━━━━━"
            )
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
        return

    try:
        button_text, button_url = user_input.split("|")
        button_text = button_text.strip()
        button_url = button_url.strip()

        if not (button_url.startswith("http://") or button_url.startswith("https://")):
            await message.reply("Invalid URL. Please provide a valid URL (starting with http:// or https://).", quote=True)
            return

        user_data[user_id]["buttons"].append([InlineKeyboardButton(button_text, url=button_url)])
        await message.reply("Button added. Send 'done' if you have finished adding buttons or add another button in the format: `Button Text | URL`", quote=True)

    except ValueError:
        await message.reply("Invalid format. Please provide the button text and URL in the format: `Button Text | URL`", quote=True)

@Bot.on_callback_query(filters.regex("done") & filters.user(OWNER_ID))
async def done_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    await callback_query.message.reply("Please select the channel where you want to post the content:", quote=True)
    user_data[user_id]["waiting_for_channel"] = True