import os
import pytest
import pytest_asyncio
import importlib.util
import src.db.connection
from aiohttp.test_utils import TestServer, TestClient
import config
btd6maplist_api = importlib.import_module("btd6maplist-api")


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if pytest_asyncio.is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


def pytest_configure():
    def override_config():
        spec = importlib.util.spec_from_file_location(
            name="config_test",
            location=os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "config.test.py"),
        )
        config_test = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_test)

        forced_override = [
            "PERSISTENT_DATA_PATH",
            "DB_NAME",
        ]

        for vname in vars(config_test):
            if not vname.isupper():
                continue
            if vname in forced_override:
                if getattr(config, vname) == getattr(config_test, vname):
                    raise ValueError(f"Must override config.{forced_override[0]} in config.test.py "
                                     "with a different value than config.py")
                forced_override.remove(vname)
            setattr(config, vname, getattr(config_test, vname))

        if len(forced_override):
            raise ValueError(f"Must override config.{forced_override[0]} in config.test.py")

    def clear_previous_data():
        dbinfo_path = os.path.join(config.PERSISTENT_DATA_PATH, "data", "dbinfo.txt")
        os.remove(dbinfo_path)

    override_config()
    clear_previous_data()


@pytest_asyncio.fixture(autouse=True, scope="module")
async def reset_database():
    """Resets the database before every test module"""
    dbinfo_path = os.path.join(config.PERSISTENT_DATA_PATH, "data", "dbinfo.txt")
    os.remove(dbinfo_path)

    @src.db.connection.postgres
    async def restore(conn=None):
        drops = await conn.fetch(
            """
            SELECT 'DROP TABLE IF EXISTS "' || tablename || '" CASCADE;'
            FROM pg_tables
            WHERE schemaname = 'public';
            """
        )
        await conn.execute("\n".join(d[0] for d in drops))
        await src.db.connection.init_database(test=True, conn=conn)

    await restore()


@pytest.fixture(scope="session")
def btd6ml_app():
    """The main Application"""
    app = btd6maplist_api.get_application(
        with_swagger=False,
    )
    return app


# https://github.com/aio-libs/pytest-aiohttp/blob/master/pytest_aiohttp/plugin.py#L138C1-L172C36
@pytest_asyncio.fixture(scope="session")
async def aiohttp_client():
    """An aiohttp TestClient factory"""
    clients = []

    async def go(__param, *, server_kwargs=None, **kwargs):
        server_kwargs = server_kwargs or {}
        server = TestServer(__param, **server_kwargs)
        client = TestClient(server, **kwargs)

        await client.start_server()
        clients.append(client)
        return client

    yield go

    while clients:
        await clients.pop().close()


@pytest_asyncio.fixture(scope="session")
async def btd6ml_test_client(btd6ml_app, aiohttp_client):
    """A TestClient for the BTD6 Maplist API"""
    return await aiohttp_client(btd6ml_app)
