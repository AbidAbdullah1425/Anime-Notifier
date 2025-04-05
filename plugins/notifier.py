# plugins/notifier.py
import requests
from config import TG_BOT_TOKEN, OWNER_ID

TELEGRAM_API_URL = f'https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage'

def send_notification(anime):
    message = f"""
    ✨ Anime Name: {anime['title']['romaji']} | {anime['title']['english'] or anime['title']['romaji']} ✨
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