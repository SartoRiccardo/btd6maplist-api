import asyncpg
import config
from src.utils.colors import red, purple
from functools import wraps

pool: asyncpg.Pool | None


async def start():
    global pool
    try:
        pool = await asyncpg.create_pool(
            user=config.DB_USER, password=config.DB_PSWD,
            database=config.DB_NAME, host=config.DB_HOST
        )
        print(f"{purple('[PSQL]')} Connected")
        await init_database()
    except:
        print(f"{purple('[PSQL]')} {red('Error connecting to Postgres database')}")
        exit(1)


def postgres(wrapped):
    @wraps(wrapped)
    async def wrapper(*args, **kwargs):
        if "conn" in kwargs:
            return await wrapped(*args, **kwargs)

        if pool is None:
            return
        async with pool.acquire() as conn:
            return await wrapped(*args, **kwargs, conn=conn)
    return wrapper


@postgres
async def init_database(conn=None):
    with open("database/views.psql") as fviews:
        await conn.execute(fviews.read())
        print(f"{purple('[PSQL]')} Created views")
    with open("database/triggers.psql") as ftriggers:
        await conn.execute(ftriggers.read())
        print(f"{purple('[PSQL]')} Created triggers")
