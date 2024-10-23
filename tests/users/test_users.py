import pytest
import pytest_asyncio
import http
from ..mocks import DiscordPermRoles
from ..testutils import fuzz_data, remove_fields, invalidate_field

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.fixture
def profile_payload():
    def generate(name: str, oak: str = None):
        return {
            "name": name,
            "oak": oak,
        }
    return generate


@pytest.fixture
def new_user_payload():
    def generate(uid: int, name: str = None):
        return {
            "discord_id": str(uid),
            "name": name if name else f"usr{uid}",
        }
    return generate


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
        USERNAME = "Test_User_2M"
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

    async def test_add_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test adding a user, with missing properties"""
        pytest.skip("Not Implemented")

    async def test_fuzz(self, btd6ml_test_client, mock_discord_api):
        """Test setting every field to a different data type, one by one"""
        pytest.skip("Not Implemented")

    async def test_add_unauthorized(self, btd6ml_test_client, mock_discord_api):
        """Test adding a user without having the perms to do so"""
        pytest.skip("Not Implemented")

    async def test_edit_invalid(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile with missing or invalid fields"""
        pytest.skip("Not Implemented")


@pytest.mark.put
@pytest.mark.users
class TestEditSelf:
    async def test_edit(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile"""
        pytest.skip("Not Implemented")

    async def test_edit_other(self, btd6ml_test_client, mock_discord_api):
        """Test editing someone else's profile"""
        pytest.skip("Not Implemented")

    async def test_edit_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile with missing fields"""
        pytest.skip("Not Implemented")

    async def test_fuzz(self, btd6ml_test_client, mock_discord_api):
        """Test setting every field to a different data type, one by one"""
        pytest.skip("Not Implemented")

    async def test_edit_invalid(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile with missing or invalid fields"""
        pytest.skip("Not Implemented")
