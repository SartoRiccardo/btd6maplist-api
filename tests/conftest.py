import asyncio
import pathlib

import pytest
import pytest_asyncio
import importlib
import requests
import src.db.connection
import src.requests
from .mocks.DiscordRequestMock import DiscordRequestMock
from aiohttp.test_utils import TestServer, TestClient
from .testutils import clear_db_patch_data, override_config
btd6maplist_api = importlib.import_module("btd6maplist-api")


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if pytest_asyncio.is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


def pytest_configure():
    override_config()
    clear_db_patch_data()


@pytest_asyncio.fixture(autouse=True, scope="class")
async def reset_database():
    """Resets the database before every test module"""
    clear_db_patch_data()

    @src.db.connection.postgres
    async def restore(conn=None):
        drops = await conn.fetch(
            """
            SELECT 'DROP TABLE IF EXISTS "' || tablename || '" CASCADE;'
            FROM pg_tables
            WHERE schemaname = 'public';
            """
        )
        if len(drops):
            await conn.execute("\n".join(d[0] for d in drops))
        await src.db.connection.init_database(test=True, conn=conn)

    await restore()


@pytest.fixture(autouse=True)
def mock_discord_api():
    src.requests.set_discord_api(src.requests.DiscordRequests)

    def set_mock(**kwargs):
        src.requests.set_discord_api(DiscordRequestMock(**kwargs))
    return set_mock


@pytest.fixture(scope="session")
def btd6ml_app():
    """The main Application"""
    app = btd6maplist_api.get_application(
        with_swagger=False,
        init_database=False,
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
    yield await aiohttp_client(btd6ml_app)

    # https://github.com/pytest-dev/pytest-asyncio/issues/435
    event_loop = asyncio.get_running_loop()
    self = asyncio.current_task(event_loop)
    for task in asyncio.all_tasks(event_loop):
        if task.done() or task == self:
            continue
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass


@pytest.fixture
def save_image(tmp_path: pathlib.Path):
    images = [
        "https://dummyimage.com/300x200/000/fff",
        "https://dummyimage.com/400x300/00ff00/000",
        "https://dummyimage.com/600x400/0000ff/fff",
        "https://dummyimage.com/800x600/ff0000/fff",
        "https://dummyimage.com/200x200/ff00ff/fff",
        "https://dummyimage.com/500x300/ffff00/000",
        "https://dummyimage.com/700x500/ff6600/fff",
        "https://dummyimage.com/900x700/663399/fff",
        "https://dummyimage.com/250x150/9966cc/fff",
        "https://dummyimage.com/450x350/00cccc/000",
        "https://dummyimage.com/650x450/cc00cc/fff",
        "https://dummyimage.com/850x650/339966/fff",
        "https://dummyimage.com/150x100/ff9933/000",
        "https://dummyimage.com/350x250/33cc99/fff",
        "https://dummyimage.com/550x350/3399ff/000",
        "https://dummyimage.com/750x550/996633/fff",
        "https://dummyimage.com/950x750/cc9966/fff",
        "https://dummyimage.com/100x100/6699cc/000",
        "https://dummyimage.com/300x250/663366/fff",
        "https://dummyimage.com/500x400/ff6699/000",
    ]

    def save(index: int, filename: str = "image.png") -> pathlib.Path:
        path = tmp_path / filename
        path.write_bytes(requests.get(images[index % len(images)]).content)
        return path
    return save


@pytest.fixture(scope="session")
def assert_state_unchanged(btd6ml_test_client):
    class AssertStateEquals:
        def __init__(self, endpoint: str):
            self.endpoint = endpoint
            self.prev_value = None

        async def __aenter__(self):
            async with btd6ml_test_client.get(self.endpoint) as resp:
                self.prev_value = await resp.json()
                return self.prev_value

        async def __aexit__(self, exception_type, exception_value, exception_traceback):
            if exception_type != AssertionError:
                async with btd6ml_test_client.get(self.endpoint) as resp:
                    assert self.prev_value == await resp.json()

    return AssertStateEquals
