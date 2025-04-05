# plugins/notifier.py
import requests
from config import TG_BOT_TOKEN, OWNER_ID

TELEGRAM_API_URL = f'https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage'

def send_notification(anime, ended=False):
    if ended:
        priority = "🔔"
    else:
        priority = "🔕"
    
    message = f"""
    {priority} Anime Name: {anime['title']['romaji']} | {anime['title']['english'] or anime['title']['romaji']} {priority}
    ━━━━━━━━━━━━━━━
    🗣 Language: Eng
    📺 Quality: 720p | 1080p
    🍂 Season: SPRING
    📆 Episode: 01-{len(anime['airingSchedule']['nodes'])}
    ━━━━━━━━━━━━━━━
    """
    
    payload = {
        'chat_id': OWNER_ID,
        'text': message
    }
    
    response = requests.post(TELEGRAM_API_URL, data=payload)
    response.raise_for_status()

def send_daily_schedule(anime_list):
    message = "📅 Today's Anime Schedule:\n"
    for anime in anime_list:
        message += f"✨ {anime['title']['romaji']} | {anime['title']['english'] or anime['title']['romaji']} - Episode {anime['airingSchedule']['nodes'][0]['episode']}\n"
    
    payload = {
        'chat_id': OWNER_ID,
        'text': message
    }
    
    response = requests.post(TELEGRAM_API_URL, data=payload)
    response.raise_for_status()