import requests
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import OWNER_ID

logger = logging.getLogger(__name__)

# Storage for post data
post_data = {}

def get_genre_emoji(genre):
    """Get emoji for each genre"""
    emoji_map = {
        'Action': '⚔️',
        'Adventure': '🪂',
        'Comedy': '🤣',
        'Drama': '🎭',
        'Fantasy': '🌗',
        'Horror': '👻',
        'Mystery': '🔍',
        'Romance': '💖',
        'Sci-Fi': '🚀',
        'Slice of Life': '🌟',
        'Sports': '⚽',
        'Supernatural': '✨',
        'Thriller': '😱',
        'Mecha': '🤖',
        'Music': '🎵',
        'Psychological': '🧠',
        'Military': '🎖️',
        'School': '🏫',
        'Magic': '🔮',
        'Ecchi': '💝',
        'Demons': '😈',
        'Harem': '👥',
        'Historical': '📜',
        'Martial Arts': '🥋',
        'Super Power': '💪',
        'Game': '🎮',
        'Parody': '🃏',
        'Police': '👮',
        'Space': '🌌',
        'Vampire': '🧛',
        'Samurai': '⚔️',
        'Seinen': '👨',
        'Shoujo': '👧',
        'Shounen': '👦',
        'Josei': '👩'
    }
    return emoji_map.get(genre, '🎬')

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
            duration
            status
            averageScore
            genres
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
            description
            format
        }
    }
    """
    
    variables = {"search": anime_name}
    response = requests.post("https://graphql.anilist.co", json={"query": query, "variables": variables})
    data = response.json()

    if "errors" in data:
        logger.error("Anime not found. Name provided: %s", anime_name)
        return None

    return data["data"]["Media"]

# Channel ID helper
@Bot.on_message(filters.forwarded & filters.private & filters.user(OWNER_ID))
async def get_channel_id(client, message: Message):
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        channel_id = message.forward_from_chat.id
        await message.reply(f"Channel ID: `{channel_id}`")

# Main post command
@Bot.on_message(filters.command("post") & filters.private & filters.user(OWNER_ID))
async def post_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Name missing. Usage: /post [anime name]")
        return

    anime_name = " ".join(message.command[1:])
    anime_data = fetch_anime_details(anime_name)

    if anime_data is None:
        await message.reply("Anime not found. Please check the name and try again.")
        return

    # Format dates
    start_date = datetime(
        anime_data["startDate"]["year"],
        anime_data["startDate"]["month"],
        anime_data["startDate"]["day"]
    ).strftime("%B %d, %Y") if all(anime_data["startDate"].values()) else "TBA"

    end_date = datetime(
        anime_data["endDate"]["year"],
        anime_data["endDate"]["month"],
        anime_data["endDate"]["day"]
    ).strftime("%B %d, %Y") if all(anime_data["endDate"].values()) else "TBA"

    # Generate cover URL
    cover_url = f"https://img.anili.st/media/{anime_data['id']}"

    # Format genres with emojis
    genres_formatted = ', '.join([f'{get_genre_emoji(genre)} #{genre}' for genre in anime_data['genres']])

    # Save data
    post_data[user_id] = {
        "anime_data": anime_data,
        "cover_url": cover_url,
        "genres_formatted": genres_formatted,
        "step": "waiting_channel"
    }

    # Preview both posts
    info_post = (
        f"{anime_data['title']['romaji']} | {anime_data['title']['native']}\n\n"
        f"‣ Genres : {genres_formatted}\n"
        f"‣ Type : {anime_data['format']}\n"
        f"‣ Average Rating : {anime_data['averageScore']}%\n"
        f"‣ Status : {anime_data['status']}\n"
        f"‣ First aired : {start_date}\n"
        f"‣ Last aired : {end_date}\n"
        f"‣ Runtime : {anime_data['duration']} minutes\n"
        f"‣ No of episodes : {anime_data['episodes']}\n\n"
        f"‣ Synopsis : {anime_data['description']}\n\n"
        f"(Source: AniList)"
    )

    anime_post = (
        f"✨ Anime Name: {anime_data['title']['english'] or anime_data['title']['romaji']}"
        f" | {anime_data['title']['romaji']} ✨\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🗣 Language: Japanese\n"
        f"📺 Quality: 720p | 1080p\n"
        f"🍂 Season: {anime_data['season']}\n"
        f"📆 Episodes: 1 to {anime_data['episodes']}\n"
        f"━━━━━━━━━━━━━━━"
    )

    # Show previews with cover image
    await message.reply_photo(
        photo=cover_url,
        caption="Preview of first post (Info):\n\n" + info_post
    )
    await message.reply_photo(
        photo=cover_url,
        caption="Preview of second post (Anime):\n\n" + anime_post
    )

    # Ask for channel ID
    await message.reply(
        "Send the channel ID (-100xxxxxxxxxx)\n"
        "Or forward any message from the channel to get its ID."
    )

@Bot.on_message(filters.regex(r'^-100\d+$') & filters.private & filters.user(OWNER_ID))
async def handle_channel_id(client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in post_data:
        await message.reply("No active post. Start with /post command first.")
        return

    channel_id = message.text
    anime_data = post_data[user_id]["anime_data"]
    cover_url = post_data[user_id]["cover_url"]
    genres_formatted = post_data[user_id]["genres_formatted"]

    try:
        # First post (Info with cover)
        start_date = datetime(
            anime_data["startDate"]["year"],
            anime_data["startDate"]["month"],
            anime_data["startDate"]["day"]
        ).strftime("%B %d, %Y") if all(anime_data["startDate"].values()) else "TBA"

        end_date = datetime(
            anime_data["endDate"]["year"],
            anime_data["endDate"]["month"],
            anime_data["endDate"]["day"]
        ).strftime("%B %d, %Y") if all(anime_data["endDate"].values()) else "TBA"

        await client.send_photo(
            chat_id=channel_id,
            photo=cover_url,
            caption=(
                f"{anime_data['title']['romaji']} | {anime_data['title']['native']}\n\n"
                f"‣ Genres : {genres_formatted}\n"
                f"‣ Type : {anime_data['format']}\n"
                f"‣ Average Rating : {anime_data['averageScore']}%\n"
                f"‣ Status : {anime_data['status']}\n"
                f"‣ First aired : {start_date}\n"
                f"‣ Last aired : {end_date}\n"
                f"‣ Runtime : {anime_data['duration']} minutes\n"
                f"‣ No of episodes : {anime_data['episodes']}\n\n"
                f"‣ Synopsis : {anime_data['description']}\n\n"
                f"(Source: AniList)"
            )
        )

        # Save channel ID and update step
        post_data[user_id]["channel_id"] = channel_id
        post_data[user_id]["step"] = "waiting_buttons"
        
        # Ask for buttons
        await message.reply(
            "✅ First post completed!\n\n"
            "Now send button details for second post:\n"
            "Format:\n"
            "text - link\n"
            "text - link | text2 - link2\n\n"
            "Example:\n"
            "Watch - https://example.com\n"
            "480p - link1 | 720p - link2 | 1080p - link3"
        )

    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}\nMake sure bot is admin in channel.")
        post_data.pop(user_id, None)

@Bot.on_message(filters.text & filters.private & filters.user(OWNER_ID))
async def handle_button_input(client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in post_data or post_data[user_id]["step"] != "waiting_buttons":
        return

    try:
        buttons = []
        for line in message.text.strip().split('\n'):
            if not line.strip():
                continue
            
            row = []
            parts = line.split('|')
            
            for part in parts:
                part = part.strip()
                if ' - ' not in part:
                    raise ValueError(f"Invalid format: {part}")
                
                text, url = [x.strip() for x in part.split(' - ', 1)]
                if not (url.startswith('http://') or url.startswith('https://')):
                    raise ValueError(f"Invalid URL: {url}")
                
                row.append(InlineKeyboardButton(text, url=url))
            
            buttons.append(row)

        anime_data = post_data[user_id]["anime_data"]
        channel_id = post_data[user_id]["channel_id"]
        cover_url = post_data[user_id]["cover_url"]

        # Second post (Anime with buttons and cover)
        await client.send_photo(
            chat_id=channel_id,
            photo=cover_url,
            caption=(
                f"✨ Anime Name: {anime_data['title']['english'] or anime_data['title']['romaji']}"
                f" | {anime_data['title']['romaji']} ✨\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🗣 Language: Japanese\n"
                f"📺 Quality: 720p | 1080p\n"
                f"🍂 Season: {anime_data['season']}\n"
                f"📆 Episodes: 1 to {anime_data['episodes']}\n"
                f"━━━━━━━━━━━━━━━"
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        await message.reply("✅ Both posts completed successfully!")
        # Clean up
        post_data.pop(user_id)

    except ValueError as e:
        await message.reply(f"❌ Error: {str(e)}")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
        post_data.pop(user_id, None)