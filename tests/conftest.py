import asyncio
import json
import aiohttp
import os.path
import pathlib
import pytest
import pytest_asyncio
import importlib
import requests
import src.db.connection
import src.requests
from .mocks.DiscordRequestMock import DiscordRequestMock, DiscordPermRoles
from .mocks.NinjaKiwiMock import NinjaKiwiMock
from aiohttp.test_utils import TestServer, TestClient
from .testutils import clear_db_patch_data, override_config
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, utils
import base64
import hashlib
btd6maplist_api = importlib.import_module("btd6maplist-api")

private_key = None
privkey_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "btd6maplist-bot.test.pem")
with open(privkey_path, "rb") as fin:
    private_key = serialization.load_pem_private_key(
        fin.read(), password=None,
    )


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

    def set_mock(**kwargs) -> DiscordRequestMock:
        mocker = DiscordRequestMock(**kwargs)
        src.requests.set_discord_api(mocker)
        return mocker
    return set_mock


@pytest_asyncio.fixture(scope="function")
async def set_roles():
    @src.db.connection.postgres
    async def fixture(uid: int | str, roles: list[int], conn=None) -> None:
        if isinstance(uid, str):
            uid = int(uid)

        async with conn.transaction():
            await conn.execute("DELETE FROM user_roles WHERE user_id = $1", uid)
            await conn.execute(
                """
                INSERT INTO user_roles
                    (user_id, role_id)
                SELECT
                    $1, r.id
                FROM users u
                CROSS JOIN (SELECT UNNEST($2::int[])) r(id)
                WHERE u.discord_id = $1
                """,
                uid, roles,
            )

    return fixture


@pytest_asyncio.fixture(scope="function")
async def set_custom_role():
    inserted_roles = []

    @src.db.connection.postgres
    async def fixture(
            uid: int | str,
            permissions: dict[int | None, set[str]],
            conn: "asyncpg.pool.PoolConnectionProxy" = None,
    ) -> None:
        if isinstance(uid, str):
            uid = int(uid)

        for format_id in permissions:
            if isinstance(permissions[format_id], str):
                raise TypeError("permissions must not be str")

        async with conn.transaction():
            await conn.execute(
                "DELETE FROM user_roles WHERE user_id = $1",
                uid,
            )

            role_id = await conn.fetchval(
                """
                INSERT INTO roles (name) VALUES ($1) RETURNING id
                """,
                "test-role"
            )
            await conn.executemany(
                """
                INSERT INTO role_format_permissions
                    (role_id, format_id, permission)
                VALUES
                    ($1, $2, $3)
                """,
                [
                    (role_id, format_id, permission)
                    for format_id in permissions
                    for permission in permissions[format_id]
                ]
            )
            await conn.execute(
                """
                INSERT INTO user_roles
                    (user_id, role_id)
                VALUES
                    ($1, $2)
                """,
                uid, role_id
            )
            inserted_roles.append(role_id)

    @src.db.connection.postgres
    async def cleanup(
            roles: list[int],
            conn: "asyncpg.pool.PoolConnectionProxy" = None,
    ) -> None:
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM roles
                WHERE id = ANY($1::int[])
                """,
                roles,
            )

    yield fixture
    await cleanup(inserted_roles)


@pytest_asyncio.fixture(scope="function")
async def add_role():
    inserted_roles = []

    @src.db.connection.postgres
    async def fixture(
            uid: int | str,
            role_id: int,
            conn: "asyncpg.pool.PoolConnectionProxy" = None,
    ) -> None:
        if isinstance(uid, str):
            uid = int(uid)

        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO user_roles
                    (user_id, role_id)
                VALUES
                    ($1, $2)
                """,
                uid, role_id,
            )
            inserted_roles.append((uid, role_id))

    @src.db.connection.postgres
    async def cleanup(
            roles: list[tuple[int | int]],
            conn: "asyncpg.pool.PoolConnectionProxy" = None,
    ) -> None:
        async with conn.transaction():
            await conn.executemany(
                """
                DELETE FROM user_roles
                WHERE (user_id, role_id) IN (
                    VALUES
                        ($1::bigint, $2::int)
                )
                """,
                roles,
            )

    yield fixture
    await cleanup(inserted_roles)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def mock_auth(mock_discord_api, set_roles, set_custom_role):
    CAN_SUBMIT_ROLE_ID = 8

    @src.db.connection.postgres
    async def reset_roles(conn=None) -> None:
        await conn.execute(
            f"""
            DELETE FROM user_roles
            ;
            INSERT INTO user_roles
                (user_id, role_id)
            SELECT
                discord_id, {CAN_SUBMIT_ROLE_ID}
            FROM users
            ;
            """
        )

    async def set_mock(**kwargs) -> None:
        mocker = mock_discord_api(**kwargs)
        if kwargs.get("perms", None) is None:
            await set_roles(mocker.user_id, [CAN_SUBMIT_ROLE_ID])
        else:
            await set_custom_role(mocker.user_id, kwargs["perms"])
        return mocker.user_id

    await reset_roles()
    return set_mock


@pytest.fixture(autouse=True)
def mock_ninja_kiwi_api():
    src.requests.set_ninja_kiwi_api(src.requests.NinjaKiwiRequests)

    def set_mock(**kwargs):
        src.requests.set_ninja_kiwi_api(NinjaKiwiMock(**kwargs))
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

    def save(
            index: int,
            filename: str = "image.png",
            with_hash: bool = False
    ) -> tuple[pathlib.Path, str] | pathlib.Path:
        path = tmp_path / filename
        media = requests.get(images[index % len(images)]).content
        path.write_bytes(media)
        if not with_hash:
            return path

        fhash = hashlib.sha256(media).hexdigest()
        return path, fhash
    return save


@pytest.fixture(scope="session")
def assert_state_unchanged(btd6ml_test_client):
    class AssertStateEquals:
        def __init__(self, endpoint: str):
            self.endpoint = endpoint
            self.prev_code = 0
            self.prev_length = 0
            self.prev_value = None

        async def __aenter__(self):
            async with btd6ml_test_client.get(self.endpoint) as resp:
                self.prev_code = resp.status
                self.prev_length = int(resp.headers.get("Content-Length", "0"))
                if self.prev_length:
                    self.prev_value = await resp.json()
                return self.prev_value

        async def __aexit__(self, exception_type, exception_value, exception_traceback):
            if exception_type != AssertionError:
                async with btd6ml_test_client.get(self.endpoint) as resp:
                    assert self.prev_code == resp.status, f"{self.endpoint} response code changed"
                    content_length = int(resp.headers.get("Content-Length", "0"))
                    assert self.prev_length == content_length, f"{self.endpoint} Content-Length code changed"
                    if content_length > 0:
                        assert self.prev_value == await resp.json(), f"{self.endpoint} state changed"

    return AssertStateEquals


@pytest.fixture
def completion_payload():
    def make():
        return {
            "user_ids": ["1"],
            "black_border": False,
            "no_geraldo": False,
            "lcc": {"leftover": 1},
            "format": 1,
        }
    return make


@pytest.fixture
def comp_subm_payload():
    def make():
        return {
            "notes": None,
            "format": 1,
            "black_border": False,
            "no_geraldo": False,
            "current_lcc": False,
            "leftover": None,
            "video_proof_url": [],
        }
    return make


@pytest.fixture
def map_payload():
    def generate(code: str, creators: dict = None):
        return {
            "code": code,
            "name": "Test Map Data",
            "placement_allver": None,
            "placement_curver": None,
            "difficulty": None,
            "botb_difficulty": None,
            "remake_of": None,
            "r6_start": None,
            "map_data": None,
            "map_preview_url": None,
            "additional_codes": [],
            "creators": creators if creators is not None else [{"id": "1", "role": None}],
            "verifiers": [],
            "aliases": [],
            "version_compatibilities": [],
            "optimal_heros": [],
        }
    return generate


@pytest.fixture
def bot_user_payload():
    def generate(uid: int):
        return {
            "user": {
                "id": str(uid),
                "username": f"user{uid}",
                "name": f"User {uid}",
            },
        }
    return generate


@pytest.fixture
def sign_message():
    def sign(message: bytes | dict | str) -> str:
        if isinstance(message, dict):
            message = json.dumps(message)
        if isinstance(message, str):
            message = message.encode()

        # https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/#signing
        signature = private_key.sign(
            message,
            padding=padding.PSS(
                padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            algorithm=hashes.SHA256(),
        )
        return base64.b64encode(signature).decode()
    return sign


@pytest.fixture
def partial_sign():
    def sign(message: bytes, current: hashes.Hash | None = None) -> hashes.Hash:
        if current is None:
            current = hashes.Hash(hashes.SHA256())
        current.update(message)
        return current
    return sign


@pytest.fixture
def finish_sign():
    def sign(current: hashes.Hash) -> str:
        sha256 = hashes.SHA256()

        digest = current.finalize()
        signature = private_key.sign(
            digest,
            padding.PSS(
                padding.MGF1(sha256),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            utils.Prehashed(sha256),
        )
        return base64.b64encode(signature).decode()
    return sign


@pytest.fixture
def submission_formdata(save_image, partial_sign, finish_sign):
    def generate(data_str: str, files: list[tuple[str, pathlib.Path]], pre_sign: str = ""):
        form_data = aiohttp.FormData()
        contents_hash = partial_sign((pre_sign + data_str).encode())
        for name, path in files:
            with path.open("rb") as fin:
                contents_hash = partial_sign(fin.read(), current=contents_hash)
            form_data.add_field(name, path.open("rb"))
        form_data.add_field("data", json.dumps({"data": data_str, "signature": finish_sign(contents_hash)}))
        return form_data

    return generate


@pytest.fixture
def payload_format():
    def function() -> dict:
        return {
            "hidden": False,
            "run_submission_status": "closed",
            "map_submission_status": "closed",
            "run_submission_wh": "https://discord.com/wh/999",
            "map_submission_wh": "https://discord.com/wh/999",
        }
    return function
