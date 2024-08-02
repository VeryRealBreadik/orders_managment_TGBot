import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database.crud import Database
from .bot.bot import Bot

database = None


def load_db(database_url):
    postgresql_database_url = database_url

    engine = create_engine(postgresql_database_url)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    global database
    database = Database(session())
    if not database:
        print("База данных не была загружена, попробуйте ещё раз")
        sys.exit()


async def start_bot(bot_token):
    global database

    bot = Bot(bot_token, database)
    await bot.start()
