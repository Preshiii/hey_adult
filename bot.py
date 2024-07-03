import logging
import logging.config

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)

from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from pymongo.errors import OperationFailure
from database.ia_filterdb import Media, Media2, choose_mediaDB, db as clientDB
from database.users_chats_db import db
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_STR, LOG_CHANNEL, PORT, SECONDDB_URI, DATABASE_URI
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script 
from datetime import date, datetime 
import pytz
from aiohttp import web
from plugins import web_server
from sample_info import tempDict


class Bot(Client):

    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=200,
            plugins={"root": "plugins"},
            sleep_threshold=10,
        )

    async def dbStats(self):
        try:
            stats = await clientDB.command('dbStats')
            return stats
        except OperationFailure as e:
            logging.error(f"Error fetching dbStats: {e}")
            return None

    async def start(self):
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        await super().start()
        await Media.ensure_indexes()
        await Media2.ensure_indexes()

        # Fetch dbStats for the primary DB
        stats = await self.dbStats()
        if not stats:
            logging.error("Failed to get dbStats from primary DB.")
            return
        
        # Calculate the free db space from bytes to MB
        free_dbSize = round(512 - ((stats['dataSize'] / (1024 * 1024)) + (stats['indexSize'] / (1024 * 1024))), 2)
        logging.info(f"Primary DB free space: {free_dbSize} MB")
        
        # Choose the right DB by checking the free space
        if SECONDDB_URI and free_dbSize < 100:  # If the primary DB has less than 100MB left, use the second DB.
            tempDict["indexDB"] = SECONDDB_URI
            logging.info(f"Since Primary DB has only {free_dbSize} MB left, Secondary DB will be used to store data.")
        elif SECONDDB_URI is None:
            logging.error("Missing second DB URI! Add SECONDDB_URI now! Exiting...")
            exit()
        else:
            tempDict["indexDB"] = DATABASE_URI
            logging.info(f"Since primary DB has enough space ({free_dbSize} MB) left, it will be used for storing data.")

        await choose_mediaDB()

        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        self.username = '@' + me.username
        
        logging.info(f"{me.first_name} with for Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
        logging.info(LOG_STR)
        logging.info(script.LOGO)
        
        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        time = now.strftime("%H:%M:%S %p")
        
        await self.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time))
        
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot stopped. Bye.")

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1


if __name__ == "__main__":
    app = Bot()
    app.run()
