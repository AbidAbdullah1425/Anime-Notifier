# plugins/runner.py
import time
from anilist import fetch_recently_aired_anime
from notifier import send_notification
from database import is_blocked
from blocked import handle_blocked_command, handle_unblocked_command

def check_anime_updates():
    anime_list = fetch_recently_aired_anime()
    for anime in anime_list:
        last_episode = max(anime['airingSchedule']['nodes'], key=lambda x: x['episode'])
        if last_episode['airingAt'] < time.time():
            if not is_blocked(anime['title']['romaji']):
                send_notification(anime)
            else:
                print(f"Anime '{anime['title']['romaji']}' is blocked.")
        else:
            print(f"Anime '{anime['title']['romaji']}' has not finished airing.")

if __name__ == '__main__':
    # Example of handling commands dynamically
    user_input = input("Enter command (block/unblock) and anime name: ").strip().split()
    command = user_input[0].lower()
    anime_name = ' '.join(user_input[1:])
    
    if command == 'block':
        handle_blocked_command(anime_name)
    elif command == 'unblock':
        handle_unblocked_command(anime_name)
    else:
        print("Invalid command. Use 'block' or 'unblock' followed by the anime name.")
    
    # Continuously check for anime updates (runs every hour)
    while True:
        check_anime_updates()
        time.sleep(3540)