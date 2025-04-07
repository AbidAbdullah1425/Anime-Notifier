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

    post_text = (
        f"{title_romaji} | {title_native}\n\n"
        f"‣ Genres : {genres}\n"
        f"‣ Type : {format}\n"
        f"‣ Average Rating : {average_score}\n"
        f"‣ Status : {status}\n"
        f"‣ First aired : {start_date}\n"
        f"‣ Last aired : {end_date}\n"
        f"‣ Runtime : {duration} minutes\n"
        f"‣ No of episodes : {episodes}\n\n"
        f"‣ Synopsis : {description}\n\n"
        f"(Source: AniList)"
    )
    
    return post_text

@Client.on_message(filters.command("source") & filters.private & filters.user(OWNER_ID))
async def anime_new_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Anime name is missing. Usage: /anime_new [anime name]")
        return

    anime_name = " ".join(message.command[1:])
    try:
        anime_details = fetch_anime_details(anime_name)
        post_text = format_anime_post(anime_details)
        
        user_data[user_id] = {
            "anime_details": anime_details,
            "post_text": post_text,
            "buttons": [],
            "in_progress": True
        }

        await message.reply(
            text=post_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Add Button", callback_data="add_button")]])
        )

    except Exception as e:
        logger.exception("An error occurred while processing the /anime_new command.")
        await message.reply("An error occurred while fetching the anime details. Please try again.")

@Client.on_callback_query(filters.regex("add_button") & filters.user(OWNER_ID))
async def add_button_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id].get("in_progress"):
        return

    await callback_query.message.reply("Please send the button text and URL in the format: `Button Text | URL`\nYou can add multiple buttons by sending each in a new line. Send 'done' when you are finished adding buttons.")

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
            buttons = user_data[user_id]["buttons"]
            reply_markup = InlineKeyboardMarkup(buttons)

            await client.send_message(
                chat_id=channel_id,
                text=post_text,
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