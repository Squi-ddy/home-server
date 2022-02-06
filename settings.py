import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")
UPDATE_PASSWORD = os.environ.get("UPDATE_PASSWORD")
SERVER_NAME = os.environ.get("SERVER_NAME")
DATABASE_URL = os.environ.get("DATABASE_URL")
IS_HTTPS = bool(int(os.environ.get("IS_HTTPS", "0")))
STATIC_SITE_NAME = os.environ.get("STATIC_SITE_NAME")
STATIC_IS_HTTPS = bool(int(os.environ.get("STATIC_IS_HTTPS", "0")))
