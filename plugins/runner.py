# plugins/runner.py
import time
import schedule
from anilist import fetch_anime_schedule
from notifier import send_notification, send_daily_schedule
from database import is_blocked

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

if __name__ == '__main__':
    # Schedule the daily anime list at 5 AM
    schedule.every().day.at("05:00").do(send_daily_anime_list)

    # Continuously check for anime updates (runs every hour)
    while True:
        check_anime_updates()
        schedule.run_pending()
        time.sleep(3600)