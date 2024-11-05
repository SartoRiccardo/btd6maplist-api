import asyncio
import os
import asyncpg.exceptions
from aiohttp import web
import src.db.connection
import config
from src.utils.colors import red


async def get(_r: web.Request) -> web.Response:
    """
    Wipes the database and resets it completely with the test data.
    There is no authorization needed or required for this route.
    It's a GET so it can be visited from the browser out of convenience.
    """
    await reset_database()
    return web.Response(
        body=f"""
        <html>
            <head></head>
            <body>
                <p>Reset <u>{config.DB_NAME}</u></p>
            </body>
        </html>
        """,
        content_type="text/html",
    )


@src.db.connection.postgres
async def reset_database(conn=None):
    """Copied from the test suite, didn't want to refactor it so it wasn't a fixture"""
    drops = await conn.fetch(
        """
        SELECT 'DROP TABLE IF EXISTS "' || tablename || '" CASCADE;'
        FROM pg_tables
        WHERE schemaname = 'public';
        """
    )
    if len(drops):
        tries = 3
        while tries:
            try:
                await conn.execute("\n".join(d[0] for d in drops))
                break
            except asyncpg.exceptions.DeadlockDetectedError:
                await asyncio.sleep(1)
                tries -= 1
                print(f"{red('[PSQL/Deadlock]')} Retrying {tries} more times...")
    dbinfo_path = os.path.join(config.PERSISTENT_DATA_PATH, "data", "dbinfo.txt")
    if os.path.exists(dbinfo_path):
        os.remove(dbinfo_path)
    await src.db.connection.init_database(test=True, conn=conn)
