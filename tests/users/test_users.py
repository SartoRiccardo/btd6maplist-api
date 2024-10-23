import pytest
import pytest_asyncio
import http
from ..mocks import DiscordPermRoles
from ..testutils import fuzz_data, remove_fields, invalidate_field

HEADERS = {"Authorization": "Bearer test_token"}


@pytest_asyncio.fixture
async def validate_user(btd6ml_test_client, calc_user_profile_medals, calc_usr_placements):
    async def assert_user(user_id, name: str = None, profile_overrides: dict = None):
        if name is None:
            name = f"usr{user_id}"
        if profile_overrides is None:
            profile_overrides = {}

        expected_medals, _comps = await calc_user_profile_medals(user_id)
        expected_profile = {
            "id": str(user_id),
            "name": name,
            "maplist": await calc_usr_placements(user_id),
            "medals": expected_medals,
            "created_maps": [],
            "avatarURL": None,
            "bannerURL": None,
            **profile_overrides,
        }
        async with btd6ml_test_client.get(f"/users/{user_id}") as resp:
            assert await resp.json() == expected_profile, \
                "User profile differs from expected"
    return assert_user


@pytest.mark.get
@pytest.mark.users
class TestGetUsers:
    async def test_get_user(self, validate_user):
        """Test getting a user by ID"""
        USER_ID = 33
        await validate_user(USER_ID)

    async def test_invalid_user(self, btd6ml_test_client):
        """Test getting a nonexistent user by ID, or an invalid string as an ID"""
        async with btd6ml_test_client.get("/users/doesntexist") as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"Nonexistent user returned {resp.status}"


@pytest.mark.post
@pytest.mark.users
class TestAddUser:
    async def test_add_user(self, btd6ml_test_client, mock_discord_api, new_user_payload, validate_user):
        """Test adding a user with a valid payload"""
        USER_ID = 2000000
        USERNAME = "Test User 2M"
        mock_discord_api(perms=DiscordPermRoles.MAPLIST_MOD)

        req_data = new_user_payload(USER_ID, USERNAME)
        async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_data) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Creating a user with a correct payload returns {resp.status}"
        await validate_user(USER_ID, USERNAME)

    async def test_add_invalid_user(self, btd6ml_test_client, mock_discord_api, new_user_payload):
        """Test adding an invalid user, with duplicate or invalid properties"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        req_user_data = new_user_payload(8888)

        async def call_endpoints(req_data: dict, error_path: str, error_msg: str = ""):
            error_msg = error_msg.replace("[keypath]", error_path)
            async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Adding {error_msg} returned %d" % resp.status
                resp_data = await resp.json()
                assert "errors" in resp_data and error_path in resp_data["errors"], \
                    f"\"{error_path}\" was not in response.errors"

        validations = [
            ("usr1", "a user with a duplicate name"),
            ("a"*1000, "a user with a name too long"),
            ("", "a user with an empty name"),
            ("test&&&space", "a user with invalid characters"),
        ]
        invalid_schema = {None: ["name"]}
        for req_data, edited_path, error_msg in invalidate_field(req_user_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        validations = [
            ("1", "a user with a duplicate Discord ID"),
            ("", "a user with an empty Discord ID"),
        ]
        invalid_schema = {None: ["discord_id"]}
        for req_data, edited_path, error_msg in invalidate_field(req_user_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

    async def test_add_missing_fields(self, btd6ml_test_client, mock_discord_api, assert_state_unchanged,
                                      new_user_payload):
        """Test adding a user with missing properties"""
        USER_ID = 2000001
        USERNAME = "Test User 2M1"
        mock_discord_api(perms=DiscordPermRoles.MAPLIST_MOD)

        req_usr_data = new_user_payload(USER_ID, USERNAME)
        for req_data, path in remove_fields(req_usr_data):
            async with assert_state_unchanged(f"/users/{USER_ID}"):
                async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Creating a user with a missing {path} returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" is not in the returned errors"

    async def test_fuzz(self, btd6ml_test_client, mock_discord_api, new_user_payload, assert_state_unchanged):
        """Test setting every field to a different data type, one by one"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)
        req_usr_data = new_user_payload(2000001, "Test User 2M1")

        for req_data, path, sub_value in fuzz_data(req_usr_data):
            async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Setting User.{path} to {sub_value} while adding a user returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors"

    async def test_add_unauthorized(self, btd6ml_test_client, mock_discord_api):
        """Test adding a user without having the perms to do so"""
        mock_discord_api(unauthorized=True)
        async with btd6ml_test_client.post("/users") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Creating a user without an Authorization header returns {resp.status}"

        async with btd6ml_test_client.post("/users", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Creating a user with an invalid token returns {resp.status}"

        mock_discord_api()
        async with btd6ml_test_client.post("/users", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Creating a user without the necessary permissions returns {resp.status}"


@pytest.mark.put
@pytest.mark.users
class TestEditSelf:
    async def test_edit(self, btd6ml_test_client, mock_discord_api, profile_payload, validate_user):
        """Test editing one's own profile"""
        USER_ID = 33
        USERNAME = "New Name 33"
        mock_discord_api(user_id=USER_ID)
        req_usr_data = profile_payload(USERNAME)

        async with btd6ml_test_client.put("/users/@me", headers=HEADERS, json=req_usr_data) as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Editing a profile with a correct payload returns {resp.status}"
            await validate_user(USER_ID, name=USERNAME)

    async def test_edit_missing_fields(self, btd6ml_test_client, mock_discord_api, profile_payload,
                                       assert_state_unchanged):
        """Test editing one's own profile with missing fields"""
        mock_discord_api(user_id=33)
        req_usr_data = profile_payload("Newer Name 33")

        for req_data, path in remove_fields(req_usr_data):
            async with assert_state_unchanged(f"/users/33"):
                async with btd6ml_test_client.put("/users/@me", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Editing oneself with a missing {path} returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" is not in the returned errors"

    async def test_fuzz(self, btd6ml_test_client, mock_discord_api, profile_payload, assert_state_unchanged):
        """Test setting every field to a different data type, one by one"""
        mock_discord_api(user_id=33)
        req_usr_data = profile_payload("Newer Name 33")
        extra_expected = {"oak": [str]}

        for req_data, path, sub_value in fuzz_data(req_usr_data, extra_expected):
            async with assert_state_unchanged(f"/users/33"):
                async with btd6ml_test_client.put("/users/@me", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Setting User.{path} to {sub_value} while editing oneself returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

    async def test_edit_invalid(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile with missing or invalid fields"""
        pytest.skip("Not Implemented")

    async def test_edit_unauthorized(self, mock_discord_api, btd6ml_test_client):
        """Test calling the endpoint without proper authorization"""
        mock_discord_api(unauthorized=True)
        async with btd6ml_test_client.post("/users") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Editing oneself without an Authorization header returns {resp.status}"
        async with btd6ml_test_client.post("/users", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Editing oneself with an invalid token returns {resp.status}"
