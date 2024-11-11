import http
import pytest
import src.utils.validators
from ..mocks import DiscordPermRoles
from ..testutils import fuzz_data, remove_fields, invalidate_field

HEADERS = {"Authorization": "Bearer test_token"}

role_schema = {
    "id": int,
    "name": str,
    "edit_maplist": bool,
    "edit_experts": bool,
    "cannot_submit": bool,
    "requires_recording": bool,
    "can_grant": [int],
}


@pytest.mark.roles
@pytest.mark.get
async def test_roles(btd6ml_test_client):
    async with btd6ml_test_client.get("/roles") as resp:
        assert resp.status == http.HTTPStatus.OK, f"Getting roles returned {resp.status}"
        resp_data = await resp.json()
        for i, role_data in enumerate(resp_data):
            assert len(src.utils.validators.check_fields(role_data, role_schema)) == 0, \
                f"Error while validating Role[{i}]"


@pytest.mark.roles
@pytest.mark.put
class TestGrants:
    async def test_grant(self, btd6ml_test_client, mock_auth, set_roles, assert_state_unchanged):
        """Test correctly granting and removing roles"""
        await mock_auth(perms=DiscordPermRoles.EXPLIST_OWNER)

        user_id = 20
        await set_roles(user_id, [6])
        async with btd6ml_test_client.get(f"/users/{user_id}") as resp:
            resp_data = await resp.json()
            assert [rl["id"] for rl in resp_data["roles"]] == [6], \
                "Test user roles differ from expected"

        body = {
            "roles": [
                {"id": 5, "action": "POST"},
                {"id": 6, "action": "DELETE"},
            ],
        }
        async with btd6ml_test_client.patch(f"/users/{user_id}/roles", json=body, headers=HEADERS) as resp, \
                btd6ml_test_client.get(f"/users/{user_id}") as resp_get:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Patching a user's roles correctly returned {resp.status}"
            user_data = await resp_get.json()
            assert [rl["id"] for rl in user_data["roles"]] == [5], \
                "Test user roles differ from expected"

        async with assert_state_unchanged(f"/users/{user_id}"), \
                btd6ml_test_client.patch(f"/users/{user_id}/roles", json=body, headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Patching a user's roles again returned {resp.status}"

    async def test_grant_no_perms(self, btd6ml_test_client, mock_auth, set_roles, assert_state_unchanged):
        """Test correctly granting and removing roles"""
        await mock_auth(perms=DiscordPermRoles.EXPLIST_OWNER)

        user_id = 20
        await set_roles(user_id, [6, 1])
        body = {
            "roles": [
                {"id": 5, "action": "POST"},
                {"id": 6, "action": "DELETE"},
                # Wrong roles below
                {"id": 1, "action": "DELETE"},
                {"id": 4, "action": "POST"},
            ],
        }
        async with assert_state_unchanged(f"/users/{user_id}"), \
                btd6ml_test_client.patch(f"/users/{user_id}/roles", json=body, headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Patching a user's roles one doesn't have permissions to change correctly returned {resp.status}"
            data = await resp.json()
            assert "errors" in data, "Errors not present in response when granting roles without the necessary perms"
            assert "roles[2]" in data["errors"], \
                "Attempting to delete a role without perms doesn't appear in response.errors"
            assert "roles[3]" in data["errors"], \
                "Attempting to grant a role without perms doesn't appear in response.errors"

    async def test_fuzz(self, mock_auth, assert_state_unchanged, btd6ml_test_client):
        """Test sending invalid data types in the body"""
        await mock_auth(perms=DiscordPermRoles.EXPLIST_OWNER)

        user_id = 20
        body = {"roles": [{"id": 5, "action": "POST"}]}

        for req_data, path, sub_value in fuzz_data(body):
            async with assert_state_unchanged(f"/users/{user_id}"), \
                    btd6ml_test_client.patch(f"/users/{user_id}/roles", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Setting {path} to {sub_value} while editing a completion returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors"

    async def test_invalid_fields(self, mock_auth, assert_state_unchanged, btd6ml_test_client):
        """Test sending invalid data"""
        await mock_auth(perms=DiscordPermRoles.EXPLIST_OWNER)
        user_id = 20
        body = {"roles": [{"id": 5, "action": "POST"}]}

        async def call_endpoints(
                req_data: dict,
                edited_path: str,
                error_msg: str,
                expected_status: int = http.HTTPStatus.NO_CONTENT
        ) -> None:
            error_msg = error_msg.replace("[keypath]", edited_path)
            async with assert_state_unchanged(f"/users/{user_id}"), \
                    btd6ml_test_client.patch(f"/users/{user_id}/roles", headers=HEADERS, json=req_data) as resp:
                assert resp.status == expected_status, \
                    f"Editing {error_msg} returned {resp.status}"

        validations = [
            (99999, "a role that doesn't exist"),
            (-3, "a negative role"),
        ]
        invalid_schema = {"roles": ["id"]}
        for req_data, edited_path, error_msg in invalidate_field(body, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg, expected_status=http.HTTPStatus.FORBIDDEN)

        validations = [
            ("change it up", "an invalid action"),
        ]
        invalid_schema = {"roles": ["action"]}
        for req_data, edited_path, error_msg in invalidate_field(body, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

    async def test_missing_fields(self, mock_auth, assert_state_unchanged, btd6ml_test_client):
        """Test sending data with missing fields"""
        await mock_auth(perms=DiscordPermRoles.EXPLIST_OWNER)

        user_id = 20
        body = {"roles": [{"id": 5, "action": "POST"}]}

        for req_data, path in remove_fields(body):
            async with assert_state_unchanged(f"/users/{user_id}"), \
                    btd6ml_test_client.patch(f"/users/{user_id}/roles", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Removing {path} while adding a completion returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors"

    async def test_unauthorized(self, mock_auth, btd6ml_test_client):
        """Test patching a user's roles without the proper authentication"""
        await mock_auth(unauthorized=True)

        user_id = 20
        async with btd6ml_test_client.patch(f"/users/{user_id}/roles") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Patching a user's roles without providing authorization returned {resp.status}"

        async with btd6ml_test_client.patch(f"/users/{user_id}/roles", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Patching a user's roles while unauthorized returned {resp.status}"

    async def test_repeated_fields(self, mock_auth, btd6ml_test_client, assert_state_unchanged):
        """Test providing the same role twice"""
        await mock_auth(perms=DiscordPermRoles.EXPLIST_OWNER)

        user_id = 20
        body = {
            "roles": [
                {"id": 5, "action": "POST"},
                {"id": 5, "action": "POST"},
            ],
        }
        async with btd6ml_test_client.patch(f"/users/{user_id}/roles", json=body, headers=HEADERS) as resp, \
                btd6ml_test_client.get(f"/users/{user_id}") as resp_get:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Adding the same role twice returned {resp.status}"
            user_data = await resp_get.json()
            assert [rl["id"] for rl in user_data["roles"]] == [5], \
                "Modified roles differ from expected"

        body = {
            "roles": [
                {"id": 5, "action": "DELETE"},
                {"id": 5, "action": "DELETE"},
            ],
        }
        async with btd6ml_test_client.patch(f"/users/{user_id}/roles", json=body, headers=HEADERS) as resp, \
                btd6ml_test_client.get(f"/users/{user_id}") as resp_get:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Removing the same role twice returned {resp.status}"
            user_data = await resp_get.json()
            assert len(user_data["roles"]) == 0, \
                "Modified roles differ from expected"

        body = {
            "roles": [
                {"id": 5, "action": "POST"},
                {"id": 5, "action": "DELETE"},
                {"id": 7, "action": "DELETE"},
                {"id": 7, "action": "POST"},
            ],
        }
        async with btd6ml_test_client.patch(f"/users/{user_id}/roles", json=body, headers=HEADERS) as resp, \
                btd6ml_test_client.get(f"/users/{user_id}") as resp_get:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Removing and adding the same role twice returned {resp.status}"
            user_data = await resp_get.json()
            assert len(user_data["roles"]) == 0, \
                "Modified roles differ from expected"
