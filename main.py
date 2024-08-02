import os
import asyncio

from dotenv import load_dotenv
from modules import load_db, start_bot

from modules.bot.bot import Bot


load_dotenv(".env")
load_db(os.getenv("DATABASE_URL"))


async def main():
    await start_bot(os.getenv("BOT_TOKEN"))

async def gay():
    bot = Bot(os.getenv("BOT_TOKEN"))
    await bot.start()

if __name__ == "__main__":
    asyncio.run(gay())
