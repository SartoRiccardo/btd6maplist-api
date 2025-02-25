import pytest
import http
from ..mocks import DiscordPermRoles

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.users
class TestAuth:
    async def test_get_self(self, btd6ml_test_client, mock_auth, calc_user_profile_medals,
                            calc_usr_placements):
        """Test getting one's own profile"""
        USER_ID = 37
        await mock_auth(user_id=USER_ID, perms=DiscordPermRoles.MAPLIST_MOD)

        expected_created_map_ids = ["MLXXXAG", "MLXXXCJ"]
        expected_created_maps = []
        copy_keys = ["code", "created_on", "deleted_on", "difficulty", "map_data", "map_preview_url", "name",
                     "optimal_heros", "placement_all", "placement_cur", "r6_start"]
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
            "maplist": await calc_usr_placements(USER_ID),
            "completions": comps,
            "medals": expected_medals,
            "created_maps": expected_created_maps,
            "roles": [
                {
                    "id": 4,
                    "name": "Maplist Moderator",
                    "edit_maplist": True,
                    "edit_experts": False,
                    "requires_recording": False,
                    "cannot_submit": False,
                }
            ],
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
            ]
        }

        async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Trying to log in returns {resp.status}"
            resp_data = await resp.json()
            resp_data["completions"] = sorted(
                resp_data["completions"],
                key=lambda x: (x["map"], x["black_border"], x["no_geraldo"], x["current_lcc"], x["format"]),
            )

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
            "maplist": await calc_usr_placements(None),
            "medals": {"black_border": 0, "no_geraldo": 0, "lccs": 0, "wins": 0},
            "created_maps": [],
            "avatarURL": None,
            "bannerURL": None,
            "roles": [],
            "achievement_roles": [],
        }
        async with btd6ml_test_client.get(f"/users/{USER_ID}") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting unknown user returns {resp.status}"
            resp_data = await resp.json()
            assert resp_data == expected_maplist_profile, \
                "Initial empty profile differs from expected"

