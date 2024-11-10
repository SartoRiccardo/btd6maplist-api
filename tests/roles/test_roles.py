import http
import pytest
import src.utils.validators
from ..mocks import DiscordPermRoles

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
