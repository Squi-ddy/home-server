import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")
UPDATE_PASSWORD = os.environ.get("UPDATE_PASSWORD")
SERVER_NAME = os.environ.get("SERVER_NAME")
DATABASE_URL = os.environ.get("DATABASE_URL")