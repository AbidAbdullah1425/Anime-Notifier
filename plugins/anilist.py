import requests
import logging

logger = logging.getLogger(__name__)

# Assuming user_data dictionary and other necessary imports are already defined

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
          medium
        }
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

    # Prefer English title if available; fallback to romaji or native
    anime_title = titles.get("english") or titles.get("romaji") or titles.get("native")
    anime_cover_url = anime_data["coverImage"]["large"]  # Use the large cover image URL

    return {
        "anime_title": anime_title,
        "anime_cover_url": anime_cover_url
    }

@Bot.on_message(filters.command("source") & filters.private & filters.user(OWNER_ID))
async def anime_new_handler(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Anime name is missing. Usage: /source [anime name]")
        return

    anime_name = " ".join(message.command[1:])
    anime_details = fetch_anime_details(anime_name)

    if anime_details is None:
        await message.reply("Anime not found. Please check the name and try again.")
        return

    # Save anime details to user_data
    user_data[user_id] = {
        "anime_title": anime_details["anime_title"],
        "anime_cover_url": anime_details["anime_cover_url"],
        "in_progress": True  # Set in-progress state
    }

    await message.reply_photo(
        photo=anime_details["anime_cover_url"],
        caption=f"✨ Anime Name: {anime_details['anime_title']} ✨\n\nClick 'Add Button' to add more buttons.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Add Button", callback_data="add_button")]])
    )

# The rest of the handlers remain unchanged