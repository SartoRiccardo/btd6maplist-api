import pytest
import http


@pytest.mark.users
class TestAuth:
    async def test_get_self(self, btd6ml_test_client, mock_discord_api, calc_user_profile_medals,
                            calc_usr_placements):
        """Test getting one's own profile"""
        USER_ID = 37
        mock_discord_api(user_id=USER_ID)

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
        }

        async with btd6ml_test_client.post("/auth?discord_token=test_token") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Trying to log in returns {resp.status}"
            resp_data = await resp.json()
            resp_data["maplist_profile"]["completions"] = sorted(
                resp_data["maplist_profile"]["completions"],
                key=lambda x: (x["map"], x["black_border"], x["no_geraldo"], x["current_lcc"], x["format"]),
            )

            assert resp_data["maplist_profile"] == expected_maplist_profile, \
                "Maplist profile differs from expected"

    async def test_invalid_token(self, btd6ml_test_client, mock_discord_api):
        """Test using an invalid Discord Token to log in"""
        mock_discord_api(unauthorized=True)
        async with btd6ml_test_client.post("/auth") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Omitting discord_token returns {resp.status}"

        async with btd6ml_test_client.post("/auth?discord_token=test_token") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Omitting discord_token returns {resp.status}"

    async def test_new_user(self, btd6ml_test_client, mock_discord_api):
        """Test logging in as a new user creates a new Maplist account"""
        USER_ID = 2000000
        USERNAME = "test_new_usr"
        mock_discord_api(user_id=USER_ID, username=USERNAME)

        async with btd6ml_test_client.get(f"/users/{USER_ID}") as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"Getting unknown user returns {resp.status}"

        async with btd6ml_test_client.post("/auth?discord_token=test_token") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Authenticating as a new user returns {resp.status}"

        expected_maplist_profile = {
            "id": str(USER_ID),
            "name": USERNAME,
            "maplist": {
                "all": {"lccs": 0.0, "lccs_placement": None, "points": 0.0, "pts_placement": None},
                "current": {"lccs": 0.0, "lccs_placement": None, "points": 0.0, "pts_placement": None},
            },
            "medals": {"black_border": 0, "no_geraldo": 0, "lccs": 0, "wins": 0},
            "created_maps": [],
            "avatarURL": None,
            "bannerURL": None,
        }
        async with btd6ml_test_client.get(f"/users/{USER_ID}") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting unknown user returns {resp.status}"
            resp_data = await resp.json()
            assert resp_data == expected_maplist_profile, \
                "Initial empty profile differs from expected"

