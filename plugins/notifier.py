# plugins/notifier.py
import requests

TELEGRAM_API_URL = 'https://api.telegram.org/bot{}/sendMessage'
TELEGRAM_BOT_TOKEN = 'your_telegram_bot_token'  # Replace with your bot token
OWNER_ID = 'your_owner_id'  # Replace with the owner's Telegram ID

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
    
    url = TELEGRAM_API_URL.format(TELEGRAM_BOT_TOKEN)
    payload = {
        'chat_id': OWNER_ID,
        'text': message
    }
    
    response = requests.post(url, data=payload)
    response.raise_for_status()