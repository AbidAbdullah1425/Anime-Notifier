# plugins/runner.py
import time
from anilist import fetch_recently_aired_anime
from notifier import send_notification
from database import is_blocked
from blocked import handle_blocked_command

def check_anime_updates():
    anime_list = fetch_recently_aired_anime()
    for anime in anime_list:
        if not is_blocked(anime['title']['romaji']):
            send_notification(anime)
        else:
            print(f"Anime '{anime['title']['romaji']}' is blocked.")

if __name__ == '__main__':
    # Example of handling the blocked command
    handle_blocked_command('Devil May Cry!')
    
    # Continuously check for anime updates (runs every hour)
    while True:
        check_anime_updates()
        time.sleep(600)