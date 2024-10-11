import os
import asyncpg
import config
from src.utils.colors import red, purple
from functools import wraps

pool: asyncpg.Pool | None


async def start():
    global pool
    try:
        os.makedirs(os.path.join(config.PERSISTENT_DATA_PATH, "data"), exist_ok=True)
        pool = await asyncpg.create_pool(
            user=config.DB_USER, password=config.DB_PSWD,
            database=config.DB_NAME, host=config.DB_HOST,
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
async def init_database(test: bool = False, conn=None):
    await update_schema(test=test, conn=conn)

    with open(os.path.join("database", "views.psql")) as fviews:
        await conn.execute(fviews.read())
        print(f"{purple('[PSQL/Init]')} Created views")
    with open(os.path.join("database", "triggers.psql")) as ftriggers:
        await conn.execute(ftriggers.read())
        print(f"{purple('[PSQL/Init]')} Created triggers")


@postgres
async def update_schema(test: bool = False, conn=None):
    dbinfo_path = os.path.join(config.PERSISTENT_DATA_PATH, "data", "dbinfo.txt")
    patches_path = os.path.join("database", "patches")
    if not os.path.exists(dbinfo_path):
        with open(dbinfo_path, "w") as fdb:
            fdb.write("0")

    with open(dbinfo_path) as fdb:
        last_update = int(fdb.read())

    print(f"{purple('[PSQL/Schema]')} Last update: {last_update}")
    updates = sorted(os.listdir(patches_path))
    for upd in updates:
        if upd.startswith("9999") and not test:
            continue

        upd_day, _ = upd.split("-", 1)
        upd_day = int(upd_day.replace("_", ""))
        if upd_day <= last_update:
            continue
        patch_path = os.path.join(patches_path, upd)
        print(f"{purple('[PSQL/Schema]')} Applying {patch_path}")
        with open(patch_path) as fpatch:
            await conn.execute(f"BEGIN; {fpatch.read()} COMMIT;")

        last_update = upd_day

    with open(dbinfo_path, "w") as fdb:
        fdb.write(str(last_update))

