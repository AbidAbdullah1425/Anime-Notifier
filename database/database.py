# plugins/database.py
from pymongo import MongoClient
from config import DB_URI, DB_NAME

client = MongoClient(DB_URI)
db = client[DB_NAME]
blocked_collection = db['blocked']

def is_blocked(anime_name):
    """Check if the given anime is blocked."""
    return blocked_collection.find_one({'name': anime_name}) is not None

def block_anime(anime_name):
    """Block the given anime by adding its name to the blocked collection."""
    if not is_blocked(anime_name):
        blocked_collection.insert_one({'name': anime_name})
        print(f"Anime '{anime_name}' has been blocked.")
    else:
        print(f"Anime '{anime_name}' is already blocked.")