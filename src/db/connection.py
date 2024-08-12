import asyncpg
import config
from src.utils.colors import red

connection = None


async def start():
    global connection
    try:
        connection = await asyncpg.create_pool(
            user=config.DB_USER, password=config.DB_PSWD,
            database=config.DB_NAME, host=config.DB_HOST
        )
    except:
        print(red("Error connecting to Postgres database"))
        exit(-1)


def postgres(func):
    async def inner(*args, **kwargs):
        if connection is None:
            return
        return await func(*args, **kwargs, conn=connection)
    return inner
