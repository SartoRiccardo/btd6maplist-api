import pytest


@pytest.mark.users
@pytest.mark.get
async def test_valid_roles(btd6ml_test_client):
    """Test validating a user's achievement roles"""
    async with btd6ml_test_client.get("/roles/achievement") as resp:
        assert resp.ok, f"Getting achievement roles returned {resp.status}"
        ach_roles = sorted(
            await resp.json(),
            key=lambda x: (x["lb_type"], x["lb_format"], not x["for_first"], -x["threshold"])
        )

    lb_info = (0, "")
    lb_saved = []
    has_first = False
    for role in ach_roles:
        if lb_info != (role["lb_format"], role["lb_type"]):
            lb_info = (role["lb_format"], role["lb_type"])
            has_first = False
            async with btd6ml_test_client.get(f"/maps/leaderboard?format={lb_info[0]}&value={lb_info[1]}") as resp:
                assert resp.ok, f"Getting leaderboard returned {resp.status}"
                lb_saved = await resp.json()

        if role["for_first"]:
            player_id = lb_saved["entries"][0]["user"]["id"]
            has_first = True
        else:
            player_id = None
            for entry in reversed(lb_saved["entries"]):
                if entry["score"] >= role["threshold"] and (
                        entry["position"] > 1 or not has_first and entry["position"] == 1):
                    player_id = entry["user"]["id"]
                    break
            if player_id is None:
                continue

        async with btd6ml_test_client.get(f"/users/{player_id}") as resp:
            player_info = await resp.json()
            assert any(
                (role["lb_format"], role["lb_type"], role["threshold"]) == (ach["lb_format"], ach["lb_type"], ach["threshold"])
                for ach in player_info["achievement_roles"]
            ), "Role is not in the player's achievement roles, even if it should be"
