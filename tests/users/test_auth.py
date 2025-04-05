import pytest
import http
from ..mocks import DiscordPermRoles

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.users
class TestAuth:
    async def test_get_self(self, btd6ml_test_client, mock_auth, calc_user_profile_medals, add_role):
        """Test getting one's own profile"""
        USER_ID = 37
        await mock_auth(user_id=USER_ID)
        await add_role(USER_ID, DiscordPermRoles.MAPLIST_MOD)

        expected_created_map_ids = ["MLXXXAG", "MLXXXCJ"]
        expected_created_maps = []
        copy_keys = ["code", "botb_difficulty", "deleted_on", "difficulty", "map_data", "map_preview_url", "name",
                     "optimal_heros", "placement_allver", "placement_curver", "r6_start"]
        for map_id in expected_created_map_ids:
            async with btd6ml_test_client.get(f"/maps/{map_id}") as resp:
                map_data = await resp.json()
                map_min = {}
                for key in copy_keys:
                    map_min[key] = map_data[key]
                expected_created_maps.append(map_min)

        expected_medals, comps = await calc_user_profile_medals(USER_ID)
        expected_maplist_profile = {
            "id": "37",
            "name": "usr37",
            "oak": None,
            "has_seen_popup": True,
            "completions": comps,
            "permissions": [
                {
                    "format": 1,
                    "permissions": {
                        "create:completion",
                        "edit:config",
                        "edit:completion",
                        "create:map",
                        "delete:map",
                        "edit:map",
                        "delete:completion",
                        "delete:map_submission",
                        "edit:achievement_roles",
                    },
                },
                {
                    "format": 2,
                    "permissions": {
                        "create:completion",
                        "create:map",
                        "edit:config",
                        "edit:completion",
                        "delete:map",
                        "edit:map",
                        "delete:completion",
                        "delete:map_submission",
                        "edit:achievement_roles",
                    },
                },
                {
                    "format": None,
                    "permissions": {
                        "ban:user",
                        "create:map_submission",
                        "create:completion_submission",
                        "create:user",
                    },
                },
            ],
            "roles": [
                {
                    "id": 4,
                    "name": "Maplist Moderator",
                },
                {
                    "id": 8,
                    "name": "Can Submit",
                },
            ],
        }

        async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Trying to log in returns {resp.status}"
            resp_data = await resp.json()
            resp_data["completions"] = sorted(
                resp_data["completions"],
                key=lambda x: (x["map"], x["black_border"], x["no_geraldo"], x["current_lcc"], x["format"]),
            )
            for i in range(len(resp_data["permissions"])):
                resp_data["permissions"][i]["permissions"] = set(resp_data["permissions"][i]["permissions"])

            assert resp_data == expected_maplist_profile, "Maplist profile differs from expected"

    async def test_invalid_token(self, btd6ml_test_client, mock_auth):
        """Test using an invalid Discord Token to log in"""
        await mock_auth(unauthorized=True)
        async with btd6ml_test_client.post("/auth") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Omitting discord_token returns {resp.status}"

        async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Omitting discord_token returns {resp.status}"

    async def test_new_user(self, btd6ml_test_client, mock_auth, calc_usr_placements):
        """Test logging in as a new user creates a new Maplist account"""
        USER_ID = 2000000
        USERNAME = "test_new_usr"
        await mock_auth(user_id=USER_ID, username=USERNAME)

        async with btd6ml_test_client.get(f"/users/{USER_ID}") as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"Getting unknown user returns {resp.status}"

        async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Authenticating as a new user returns {resp.status}"

        expected_maplist_profile = {
            "id": str(USER_ID),
            "name": USERNAME,
            "list_stats": await calc_usr_placements(None),
            "medals": {"black_border": 0, "no_geraldo": 0, "lccs": 0, "wins": 0},
            "created_maps": [],
            "avatarURL": None,
            "bannerURL": None,
            "roles": [{"id": 8, "name": "Can Submit"}],
            "achievement_roles": [],
            "is_banned": False,
        }
        async with btd6ml_test_client.get(f"/users/{USER_ID}") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting unknown user returns {resp.status}"
            resp_data = await resp.json()
            assert resp_data == expected_maplist_profile, \
                "Initial empty profile differs from expected"

