import os
import asyncio

from dotenv import load_dotenv
from modules import load_db, start_bot

from modules.bot.bot import Bot


load_dotenv(".env")
load_db(os.getenv("DATABASE_URL"))


async def main():
    bot = Bot(os.getenv("BOT_TOKEN"))
    await bot.start()

    stop_event = asyncio.Event()
    await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
