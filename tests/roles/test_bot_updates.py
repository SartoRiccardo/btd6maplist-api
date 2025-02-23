import http
import urllib.parse
import pytest
from ..mocks import DiscordPermRoles
import src.utils.validators

HEADERS = {"Authorization": "Bearer test_token"}
update_schema = {
    "guild_id": str,
    "role_id": str,
    "user_id": str,
    "action": str,
}


@pytest.mark.get
@pytest.mark.bot
@pytest.mark.roles
async def test_get_role_updates(btd6ml_test_client, mock_auth, sign_message):
    """Test getting and resetting the update endpoints"""
    qparams = {"signature": sign_message(b"")}
    async with btd6ml_test_client.get(f"/roles/achievement/updates/bot?{urllib.parse.urlencode(qparams)}") as resp:
        assert resp.status == http.HTTPStatus.OK, f"Getting achievement updates returned {resp.status}"
        assert len(await resp.json()) == 0, "Role updates present in a fresh database"

    await mock_auth(perms=DiscordPermRoles.ADMIN)
    req_data = {"config": {"points_top_map": 10000, "points_bottom_map": 300}}
    async with btd6ml_test_client.get("/roles/achievement") as resp_roles, \
            btd6ml_test_client.get("/maps/leaderboard") as resp_lb, \
            btd6ml_test_client.put("/config", headers=HEADERS, json=req_data) as resp:
        highest_threshold = max([
            rl["threshold"] for rl in await resp_roles.json()
            if rl["lb_type"] == "points" and rl["lb_format"] == 1 and not rl["for_first"]
        ])

        leaderboard = await resp_lb.json()
        updated_users = len([
            entry for entry in leaderboard["entries"]
            if entry["position"] != 1 and entry["score"] < highest_threshold
        ]) + leaderboard["total"] - len(leaderboard["entries"])
        updated_users *= 2
        assert resp.status == http.HTTPStatus.OK, f"Editing config returned {resp.status}"

    async with btd6ml_test_client.get(f"/roles/achievement/updates/bot?{urllib.parse.urlencode(qparams)}") as resp_upd:
        assert resp_upd.status == http.HTTPStatus.OK, f"Getting achievement updates returned {resp.status}"
        updates = await resp_upd.json()
        assert len(updates) == updated_users, \
            "Number of role updates differ from expected"
        for i, role in enumerate(updates):
            assert len(src.utils.validators.check_fields(role, update_schema)) == 0, \
                f"Error while validating RoleUpdate[{i}]"

    async with btd6ml_test_client.post(f"/roles/achievement/updates/bot?{urllib.parse.urlencode(qparams)}") as resp_post, \
            btd6ml_test_client.get(f"/roles/achievement/updates/bot?{urllib.parse.urlencode(qparams)}") as resp_get:
        assert resp_post.status == http.HTTPStatus.NO_CONTENT, f"Wiping achievement updates returned {resp.status}"
        assert resp_get.status == http.HTTPStatus.OK, f"Getting achievement updates returned {resp.status}"
        assert len(await resp_get.json()) == 0, "Role updates present after wipe"


@pytest.mark.get
@pytest.mark.bot
@pytest.mark.roles
async def test_update_delete_roles(btd6ml_test_client, mock_auth, sign_message):
    """Test deleting all roles and checking the update endpoint"""
    qparams = {"signature": sign_message(b"")}
    await mock_auth(perms=DiscordPermRoles.ADMIN)

    data = {
        "lb_format": 1,
        "lb_type": "points",
        "roles": [],
    }

    async with btd6ml_test_client.put(f"/roles/achievement", headers=HEADERS, json=data) as resp_ach, \
            btd6ml_test_client.get(f"/roles/achievement/updates/bot?{urllib.parse.urlencode(qparams)}") as resp_get, \
            btd6ml_test_client.get("/maps/leaderboard") as resp_lb:
        # #1 role has 2 linked roles & I'm hardcoding it
        assert len(await resp_get.json()) == (await resp_lb.json())["total"] + 1, \
                "Update count differs from expected"
