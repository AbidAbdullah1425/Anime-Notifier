# plugins/runner.py
import time
import schedule
from plugins.anilist import fetch_anime_schedule
from plugins.notifier import send_notification, send_daily_schedule, send_startup_schedule
from database.database import is_blocked
from datetime import datetime

def check_anime_updates():
    anime_list = fetch_anime_schedule()
    for anime in anime_list:
        last_episode = max(anime['airingSchedule']['nodes'], key=lambda x: x['episode'])
        if last_episode['airingAt'] < time.time():
            if not is_blocked(anime['title']['romaji']):
                send_notification(anime, ended=True)
            else:
                print(f"Anime '{anime['title']['romaji']}' is blocked.")
        else:
            if not is_blocked(anime['title']['romaji']):
                send_notification(anime, ended=False)
            else:
                print(f"Anime '{anime['title']['romaji']}' is blocked.")

def send_daily_anime_list():
    anime_list = fetch_anime_schedule()
    send_daily_schedule(anime_list)

async def send_startup_anime_list():
    anime_list = fetch_anime_schedule()
    send_startup_schedule(anime_list)

if __name__ == '__main__':
    # Send the startup anime list
    send_startup_anime_list()

    # Schedule the daily anime list at 5 AM
    schedule.every().day.at("05:00").do(send_daily_anime_list)

    # Continuously check for anime updates (runs every hour)
    while True:
        check_anime_updates()
        schedule.run_pending()
        time.sleep(3600)