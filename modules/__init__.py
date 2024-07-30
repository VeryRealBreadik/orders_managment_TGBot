from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .database.crud import Database

database = None


def load_db(database_url):
    postgresql_database_url = database_url

    engine = create_engine(postgresql_database_url, connect_args={"check_same_thread": False})
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    global database
    database = Database(session())