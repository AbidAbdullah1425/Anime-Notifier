# plugins/blocked.py
from database import block_anime, unblock_anime

def handle_blocked_command(anime_name):
    block_anime(anime_name)

def handle_unblocked_command(anime_name):
    unblock_anime(anime_name)