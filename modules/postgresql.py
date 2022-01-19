from psycopg_pool import AsyncConnectionPool
import atexit
import asyncio
from settings import DATABASE_PASSWORD

pools = {}

async def get_pool(db_name):
    db_name = db_name.lower()
    if (db_name not in pools):
        pools[db_name] = AsyncConnectionPool(f"user='postgres' host='localhost' password='{DATABASE_PASSWORD}' dbname='{db_name}'")
    return pools[db_name]

def close_pools():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(coro_close_pools)

async def coro_close_pools():
    list_coro_close_pools = [pool.close() for pool in pools]
    await asyncio.wait(list_coro_close_pools, return_when=asyncio.ALL_COMPLETED)

atexit.register(close_pools)