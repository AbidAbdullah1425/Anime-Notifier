
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import logging
from config import OWNER_ID
from bot import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHANNELS = ["@AnimeWillow", "@AnimeBili"]

# Temporary storage for user input
user_data = {}

async def reset_user_data(user_id):
    """
    Function to reset user data after the process is complete
    """
    if user_id in user_data:
        user_data.pop(user_id)

@Bot.on_message(filters.command("anime") & filters.private & filters.user(OWNER_ID))
async def anime_handler(client, message: Message):
    user_id = message.from_user.id

    # Check if the command has the required anime name
    if len(message.command) < 2:
        logger.error("Anime name is missing. Usage: /anime [anime name]")
        return  # Exit without replying

    # Extract anime name from the command
    anime_name = " ".join(message.command[1:])

    try:
        # Fetch anime data from AniList
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
        data = response.json()

        if "errors" in data:
            logger.error("Anime not found. Name provided: %s", anime_name)
            return  # Exit without replying

        anime_details = data["data"]["Media"]
        anime_id = anime_details["id"]
        titles = anime_details["title"]
        cover_image = anime_details["coverImage"]["large"]
        episodes = anime_details["episodes"]
        season = anime_details["season"]
        year = anime_details["startDate"]["year"]

        # Prefer English title if available; fallback to romaji or native
        anime_title = titles.get("english") or titles.get("romaji") or titles.get("native")
        anime_romaji = titles.get("romaji")
        anime_native = titles.get("native")
        anime_cover_url = f"https://img.anili.st/media/{anime_id}"

        # Save anime details to user_data
        user_data[user_id] = {
            "anime_title": anime_title,
            "anime_romaji": anime_romaji,
            "anime_native": anime_native,
            "anime_cover_url": anime_cover_url,
            "episodes": episodes,
            "season": season,
            "year": year,
            "in_progress": True  # Set in-progress state
        }

        # Prompt for Episode Number
        await message.reply_photo(
            photo=anime_cover_url,
            caption=f"{anime_title}\n\nPlease send the episode start number (1 - {episodes}).",
        )

    except Exception as e:
        logger.exception("An error occurred while processing the /anime command.")

@Bot.on_message(filters.text & filters.private & filters.user(OWNER_ID))
async def episode_url_handler(client, message: Message):
    user_id = message.from_user.id
    user_input = message.text.strip()

    # Ignore messages that don't correspond to a valid /anime process
    if user_id not in user_data or "in_progress" not in user_data[user_id]:
        return  # Ignore irrelevant inputs

    try:
        # Check for episode start input
        if "episode_start" not in user_data[user_id]:
            if user_input.isdigit() and 1 <= int(user_input) <= user_data[user_id]["episodes"]:
                user_data[user_id]["episode_start"] = int(user_input)
                await message.reply(f"Episode {user_input} selected. Now, send the episode end number (1 - {user_data[user_id]['episodes']}).")
            else:
                await message.reply(f"Invalid episode number. Please provide a number between 1 and {user_data[user_id]['episodes']}.")
            return

        # Check for episode end input
        if "episode_end" not in user_data[user_id]:
            if user_input.isdigit() and user_data[user_id]["episode_start"] <= int(user_input) <= user_data[user_id]["episodes"]:
                user_data[user_id]["episode_end"] = int(user_input)
                await message.reply("Episode end number selected. Now, send the URL for the button.")
            else:
                await message.reply(f"Invalid episode number. Please provide a number between {user_data[user_id]['episode_start']} and {user_data[user_id]['episodes']}.")
            return

        # Check for URL input
        if "url" not in user_data[user_id]:
            if user_input.startswith("http://") or user_input.startswith("https://"):
                user_data[user_id]["url"] = user_input

                # Prepare and send the final post
                anime_title = user_data[user_id]["anime_title"]
                anime_romaji = user_data[user_id]["anime_romaji"]
                anime_native = user_data[user_id]["anime_native"]
                anime_cover_url = user_data[user_id]["anime_cover_url"]
                season = user_data[user_id]["season"]
                year = user_data[user_id]["year"]
                episode_start = user_data[user_id]["episode_start"]
                episode_end = user_data[user_id]["episode_end"]
                button_url = user_data[user_id]["url"]

                # Format the post text
                post_text = (
                    f"✨ Anime Name: {anime_title} | {anime_native}✨\n"
                    "━━━━━━━━━━━━━━━\n"
                    "🗣 Language: Japanese\n"
                    "📺 Quality: 720p | 1080p\n"
                    f"🍂 Season: {season} {year}\n"
                    f"📆 Episode: {episode_start} to {episode_end}\n"
                )

                button = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🏖️ Watch / Download", url=button_url)]]
                )

                # Send post to channels
                for channel in CHANNELS:
                    try:
                        await client.send_photo(
                            chat_id=channel,
                            photo=anime_cover_url,
                            caption=post_text,
                            reply_markup=button
                        )
                    except Exception as e:
                        logger.error("Failed to post to %s: %s", channel, e)

                logger.info("Post created and sent to channels!")
                await reset_user_data(user_id)  # Reset user data
            else:
                await message.reply("Invalid URL. Please provide a valid URL (starting with http:// or https://).")
            return
    except Exception as e:
        logger.exception("An error occurred while processing user input.")