import pytest
import pytest_asyncio
import http
from ..mocks import Permissions
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
            "list_stats": await calc_usr_placements(user_id),
            "medals": expected_medals,
            "created_maps": [],
            "avatarURL": None,
            "bannerURL": None,
            "roles": [{"id": 8, "name": "Can Submit"}],
            "achievement_roles": [],
            "is_banned": False,
            **profile_overrides,
        }
        async with btd6ml_test_client.get(f"/users/{user_id}") as resp:
            assert await resp.json() == expected_profile, \
                "User profile differs from expected"
    return assert_user


@pytest.mark.get
@pytest.mark.users
class TestGetUsers:
    async def test_get_user(self, validate_user, mock_auth):
        """Test getting a user by ID"""
        USER_ID = 33
        await mock_auth(user_id=USER_ID)
        roles = [
            {"id": 8, "name": "Can Submit"},
        ]
        await validate_user(USER_ID, profile_overrides={
            "roles": roles,
            "achievement_roles": [
                {
                    "clr_border": 6782619,
                    "clr_inner": 9004349,
                    "for_first": False,
                    "lb_format": 1,
                    "lb_type": "points",
                    "linked_roles": [
                        {
                            "guild_id": "3780309980101",
                            "role_id": "4004915198708",
                        },
                    ],
                    "name": "List lv2",
                    "threshold": 100,
                    "tooltip_description": "100+ points",
                },
                {
                    "clr_border": 13232760,
                    "clr_inner": 16749515,
                    "for_first": False,
                    "lb_format": 51,
                    "lb_type": "points",
                    "linked_roles": [],
                    "name": "Experts lv1",
                    "threshold": 1,
                    "tooltip_description": None,
                },
            ],
        })

    async def test_invalid_user(self, btd6ml_test_client):
        """Test getting a nonexistent user by ID, or an invalid string as an ID"""
        async with btd6ml_test_client.get("/users/doesntexist") as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"Nonexistent user returned {resp.status}"


@pytest.mark.post
@pytest.mark.users
class TestAddUser:
    async def test_add_user(self, btd6ml_test_client, mock_auth, new_user_payload, validate_user):
        """Test adding a user with a valid payload"""
        USER_ID = 2000000
        USERNAME = "Test User 2M"
        await mock_auth(perms={None: {"create:user"}})

        req_data = new_user_payload(USER_ID, USERNAME)
        async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_data) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Creating a user with a correct payload returns {resp.status}"
        await validate_user(USER_ID, USERNAME)

    async def test_add_invalid_user(self, btd6ml_test_client, mock_auth, new_user_payload):
        """Test adding an invalid user, with duplicate or invalid properties"""
        await mock_auth(perms={None: {"create:user"}})

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

    async def test_add_missing_fields(self, btd6ml_test_client, mock_auth, assert_state_unchanged,
                                      new_user_payload):
        """Test adding a user with missing properties"""
        USER_ID = 2000001
        USERNAME = "Test User 2M1"
        await mock_auth(perms={None: {"create:user"}})

        req_usr_data = new_user_payload(USER_ID, USERNAME)
        for req_data, path in remove_fields(req_usr_data):
            async with assert_state_unchanged(f"/users/{USER_ID}"):
                async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Creating a user with a missing {path} returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" is not in the returned errors"

    async def test_fuzz(self, btd6ml_test_client, mock_auth, new_user_payload):
        """Test setting every field to a different data type, one by one"""
        await mock_auth(perms={None: {"create:user"}})
        req_usr_data = new_user_payload(2000001, "Test User 2M1")

        for req_data, path, sub_value in fuzz_data(req_usr_data):
            async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Setting User.{path} to {sub_value} while adding a user returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors"

    async def test_add_unauthorized(self, btd6ml_test_client, mock_auth, new_user_payload):
        """Test adding a user without having the perms to do so"""
        await mock_auth(unauthorized=True)
        req_usr_data = new_user_payload(999888)

        async with btd6ml_test_client.post("/users", json=req_usr_data) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Creating a user without an Authorization header returns {resp.status}"

        async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_usr_data) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Creating a user with an invalid token returns {resp.status}"

        await mock_auth()
        async with btd6ml_test_client.post("/users", headers=HEADERS, json=req_usr_data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Creating a user without the necessary permissions returns {resp.status}"


@pytest.mark.put
@pytest.mark.users
class TestEditSelf:
    async def test_edit(self, btd6ml_test_client, mock_auth, profile_payload, validate_user,
                        mock_ninja_kiwi_api):
        """Test editing one's own profile"""
        USER_ID = 33
        USERNAME = "New Name 33"
        await mock_auth(user_id=USER_ID, perms={None: Permissions.basic()})
        mock_ninja_kiwi_api()
        req_usr_data = profile_payload(USERNAME, oak="oak_test123")

        async with btd6ml_test_client.put("/users/@me", headers=HEADERS, json=req_usr_data) as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Editing a profile with a correct payload returns {resp.status}"
            extra = {
                "roles": [{"id": 16, "name": "test-role"}],
                "avatarURL":
                    "https://static-api.nkstatic.com/appdocs/4/assets/opendata/a5d32db006cb5d8d535a14494320fc92_ProfileAvatar26.png",
                "bannerURL":
                    "https://static-api.nkstatic.com/appdocs/4/assets/opendata/aaeaf38ca1c20d6df888cae9c3c99abe_ProfileBanner43.png",
                "achievement_roles": [
                    {
                        "clr_border": 6782619,
                        "clr_inner": 9004349,
                        "for_first": False,
                        "lb_format": 1,
                        "lb_type": "points",
                        "linked_roles": [{"guild_id": "3780309980101", "role_id": "4004915198708"}],
                        "name": "List lv2",
                        "threshold": 100,
                        "tooltip_description": "100+ points",
                    },
                    {
                        "clr_border": 13232760,
                        "clr_inner": 16749515,
                        "for_first": False,
                        "lb_format": 51,
                        "lb_type": "points",
                        "linked_roles": [],
                        "name": "Experts lv1",
                        "threshold": 1,
                        "tooltip_description": None,
                    },
                ],
            }
            await validate_user(USER_ID, name=USERNAME, profile_overrides=extra)

    async def test_edit_leave_name(self, btd6ml_test_client, mock_auth, profile_payload, mock_ninja_kiwi_api):
        """Test editing one's own profile while leaving the name unchanged"""
        USER_ID = 29
        await mock_auth(user_id=USER_ID, perms={None: Permissions.basic()})
        mock_ninja_kiwi_api()
        req_usr_data = profile_payload(f"usr{USER_ID}", oak="oak_test123")

        async with btd6ml_test_client.put("/users/@me", headers=HEADERS, json=req_usr_data) as resp:
            assert resp.status == http.HTTPStatus.OK

    async def test_edit_forbidden(self, mock_auth, btd6ml_test_client, profile_payload, assert_state_unchanged):
        """Test calling the endpoint without the necessary permissions"""
        await mock_auth(user_id=33)
        async with assert_state_unchanged("/users/33"), \
                btd6ml_test_client.put("/users/@me", headers=HEADERS, json=profile_payload("Newer Name 33")) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Editing oneself without edit:self returns {resp.status}"

    async def test_edit_missing_fields(self, btd6ml_test_client, mock_auth, profile_payload,
                                       assert_state_unchanged):
        """Test editing one's own profile with missing fields"""
        await mock_auth(user_id=33, perms={None: Permissions.basic()})
        req_usr_data = profile_payload("Newer Name 33")

        for req_data, path in remove_fields(req_usr_data):
            async with assert_state_unchanged("/users/33"):
                async with btd6ml_test_client.put("/users/@me", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Editing oneself with a missing {path} returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" is not in the returned errors"

    async def test_fuzz(self, btd6ml_test_client, mock_auth, profile_payload, assert_state_unchanged):
        """Test setting every field to a different data type, one by one"""
        await mock_auth(user_id=33, perms={None: Permissions.basic()})
        req_usr_data = profile_payload("Newer Name 33")
        extra_expected = {"oak": [str]}

        for req_data, path, sub_value in fuzz_data(req_usr_data, extra_expected):
            async with assert_state_unchanged("/users/33"):
                async with btd6ml_test_client.put("/users/@me", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Setting User.{path} to {sub_value} while editing oneself returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

    async def test_edit_invalid(self, btd6ml_test_client, mock_auth, profile_payload, assert_state_unchanged,
                                mock_ninja_kiwi_api):
        """Test editing one's own profile with missing or invalid fields"""
        await mock_auth(perms={None: Permissions.basic()})

        req_usr_data = profile_payload("Cool Username")

        async def call_endpoints(req_data: dict, error_path: str, error_msg: str = ""):
            error_msg = error_msg.replace("[keypath]", error_path)
            async with btd6ml_test_client.put("/users/@me", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Setting {error_msg} returned %d" % resp.status
                resp_data = await resp.json()
                assert "errors" in resp_data and error_path in resp_data["errors"], \
                    f"\"{error_path}\" was not in response.errors"

        validations = [
            ("usr1", "the name as an already taken one"),
            ("a"*1000, "a name too long"),
            ("", "an empty name"),
            ("test&&&space", "a name with invalid characters"),
        ]
        invalid_schema = {None: ["name"]}
        for req_data, edited_path, error_msg in invalidate_field(req_usr_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        mock_ninja_kiwi_api(error_on_user=True)
        validations = [
            ("", "an empty OAK"),
            ("oak_...--??eaf", "a malformatted OAK"),
            ("oak_thiswillthrowanerror", "an invalid OAK"),
        ]
        invalid_schema = {None: ["oak"]}
        for req_data, edited_path, error_msg in invalidate_field(req_usr_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

    async def test_edit_unauthorized(self, mock_auth, btd6ml_test_client):
        """Test calling the endpoint without proper authorization"""
        await mock_auth(unauthorized=True)
        async with btd6ml_test_client.post("/users") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Editing oneself without an Authorization header returns {resp.status}"
        async with btd6ml_test_client.post("/users", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Editing oneself with an invalid token returns {resp.status}"
