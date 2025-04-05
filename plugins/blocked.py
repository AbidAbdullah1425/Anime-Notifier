# plugins/blocked.py
from database import block_anime

def handle_blocked_command(anime_name):
    block_anime(anime_name)
    print(f"Anime '{anime_name}' has been blocked.")