import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")