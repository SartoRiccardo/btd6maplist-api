import os
import asyncpg
import config
from src.utils.colors import red, purple
from functools import wraps

pool: asyncpg.Pool | None


async def start(should_init_database: bool = True):
    global pool
    try:
        os.makedirs(os.path.join(config.PERSISTENT_DATA_PATH, "data"), exist_ok=True)
        pool = await asyncpg.create_pool(
            user=config.DB_USER, password=config.DB_PSWD,
            database=config.DB_NAME, host=config.DB_HOST,
        )
        print(f"{purple('[PSQL]')} Connected")
        if should_init_database:
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
    await update_schema(conn=conn)
    if test:
        await dump_test_data(conn=conn)

    with open(os.path.join("database", "views.psql")) as fviews:
        await conn.execute(fviews.read())
        print(f"{purple('[PSQL/Init]')} Created views")
    with open(os.path.join("database", "triggers.psql")) as ftriggers:
        await conn.execute(ftriggers.read())
        print(f"{purple('[PSQL/Init]')} Created triggers")


@postgres
async def update_schema(conn=None):
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


@postgres
async def dump_test_data(conn=None):
    test_data_path = os.path.join("database", "data")
    tables = sorted(os.listdir(test_data_path))
    for fname in tables:
        if not fname.endswith(".csv"):
            continue

        table = fname.split("_")[-1][:-4]
        await conn.copy_to_table(
            table_name=table,
            source=os.path.join(test_data_path, fname),
            delimiter="\t",
            header=True,
            format="csv",
            null="\\N",
        )
