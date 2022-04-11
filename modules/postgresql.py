import psycopg
from psycopg_pool import AsyncConnectionPool

from settings import DATABASE_PASSWORD, DATABASE_URL

pools = {}


async def get_pool(db_name):
    db_name = db_name.lower()
    if db_name not in pools:
        pools[db_name] = AsyncConnectionPool(
            f"""
                user=postgres
                password={DATABASE_PASSWORD}
                host={DATABASE_URL}
                dbname={db_name}
            """
        )
    return pools[db_name]


def retry(db_name):
    def decorator(fn):
        def wrapper(*args, **kw):
            cls = args[0]
            for x in range(cls._reconnectTries):
                print(x, cls._reconnectTries)
                try:
                    return fn(*args, **kw)
                except (psycopg.InterfaceError, psycopg.OperationalError) as e:
                    print("Database Connection Error")
                    print("Reinitialising...")
                    pools[db_name] = AsyncConnectionPool(
                        f"""
                            user=postgres
                            password={DATABASE_PASSWORD}
                            host={DATABASE_URL}
                            dbname={db_name}
                        """
                    )
                    return fn(*args, **kw)

        return wrapper

    return decorator
