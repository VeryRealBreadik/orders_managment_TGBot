import os

from dotenv import load_dotenv
from modules import load_db


load_dotenv(".env")
load_db(os.getenv("database_url"))
