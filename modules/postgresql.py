from psycopg_pool import AsyncConnectionPool
import psycopg
import atexit
import asyncio
from settings import DATABASE_PASSWORD, DATABASE_URL

pools = {}

async def get_pool(db_name):
    db_name = db_name.lower()
    if (db_name not in pools):
        pools[db_name] = AsyncConnectionPool(f"user='postgres' password='{DATABASE_PASSWORD}' host='{DATABASE_URL}' dbname='{db_name}'")
    return pools[db_name]

def init(app):
    pass
