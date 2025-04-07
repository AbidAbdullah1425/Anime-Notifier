from aiohttp import web
from plugins import web_server

from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
import pyrogram.utils
from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, PORT


# Import the handlers from source.py
from plugins.spurce import anime_new_handler, add_button_handler, button_input_handler, done_handler

# Import the original handlers from anilist.py
from plugins.anilist import anime_handler, add_button_handler as add_button_handler_old, button_input_handler as button_input_handler_old, done_handler as done_handler_old

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        try:
            self.set_parse_mode(ParseMode.HTML)
            self.LOGGER(__name__).info(f"Bot Running..!\n\nCreated by \nhttps://t.me/CodeXBotz")
            self.LOGGER(__name__).info(f""" 
░█████╗░░█████╗░██████╗░███████╗██╗░░██╗██████╗░░█████╗░████████╗
██╔══██╗██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗╚══██╔══╝
██║░░╚═╝██║░░██║██║░░██║█████╗░░░╚███╔╝░██████╦╝██║░░██║░░░██║░░░
██║░░██╗██║░░██║██║░░██║██╔══╝░░░██╔██╗░██╔══██╗██║░░██║░░░██║░░░
╚█████╔╝╚█████╔╝██████╔╝███████╗██╔╝╚██╗██████╦╝╚█████╔╝░░░██║░░░
░╚════╝░░╚════╝░╚═════╝░╚══════╝╚═╝░░╚═╝╚═════╝░░╚════╝░░░░╚═╝░░░
            """)
        except Exception as e:
            self.LOGGER(__name__).warning(f"Error during bot startup: {e}")
            sys.exit()

        self.username = usr_bot_me.username

        

        # web-response
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

# Add the new command handlers
Bot.add_handler(anime_new_handler)
Bot.add_handler(add_button_handler)
Bot.add_handler(button_input_handler)
Bot.add_handler(done_handler)

# Add the original command handlers
Bot.add_handler(anime_handler)
Bot.add_handler(add_button_handler_old)
Bot.add_handler(button_input_handler_old)
Bot.add_handler(done_handler_old)