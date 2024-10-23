import pytest_asyncio


@pytest_asyncio.fixture
async def calc_user_profile_medals(btd6ml_test_client):
    async def calculate(user_id: int) -> tuple[dict, dict]:
        expected_medals = {
            "black_border": 0,
            "no_geraldo": 0,
            "lccs": 0,
            "wins": 0,
        }
        async with btd6ml_test_client.get(f"/users/{user_id}/completions?formats=1,2,51") as resp:
            comps = (await resp.json())["completions"]
            comps = [
                {
                    "map": cmp["map"]["code"],
                    "black_border": cmp["black_border"],
                    "no_geraldo": cmp["no_geraldo"],
                    "current_lcc": cmp["current_lcc"],
                    "format": cmp["format"]
                }
                for cmp in comps
            ]
            comps = sorted(
                comps, key=lambda x: (x["map"], x["black_border"], x["no_geraldo"], x["current_lcc"], x["format"])
            )

            added_medals = 0b0000  # In order of the keys declared in expected_medals
            for i, comp in enumerate(comps):
                if i == 0 or comp["map"] != comps[i - 1]["map"]:
                    added_medals = 0

                if not added_medals & 0b0001:
                    added_medals |= 0b0001
                    expected_medals["wins"] += 1
                if comp["black_border"] and not added_medals & 0b1000:
                    added_medals |= 0b1000
                    expected_medals["black_border"] += 1
                if comp["no_geraldo"] and not added_medals & 0b0100:
                    added_medals |= 0b0100
                    expected_medals["no_geraldo"] += 1
                if comp["current_lcc"] and not added_medals & 0b0010:
                    added_medals |= 0b0010
                    expected_medals["lccs"] += 1
        return expected_medals, comps

    return calculate


@pytest_asyncio.fixture
async def calc_usr_placements(btd6ml_test_client):
    async def calculate(user_id: int) -> dict:
        async def get_usr_data(lb_format, lb_value) -> tuple[float, int | None]:
            async with btd6ml_test_client.get(f"/maps/leaderboard?format={lb_format}&value={lb_value}") as resp:
                data = await resp.json()
                try:
                    entry = next(
                        entry for entry in data["entries"]
                        if entry["user"]["id"] == str(user_id)
                    )
                    return entry["score"], entry["position"]
                except StopIteration:
                    return 0.0, None

        cpts_sc, cpts_plc = await get_usr_data(1, "points")
        apts_sc, apts_plc = await get_usr_data(2, "points")
        clcc_sc, clcc_plc = await get_usr_data(1, "lccs")
        alcc_sc, alcc_plc = await get_usr_data(2, "lccs")
        placements = {
            "all": {"lccs": alcc_sc, "lccs_placement": alcc_plc, "points": apts_sc, "pts_placement": apts_plc},
            "current": {"lccs": clcc_sc, "lccs_placement": clcc_plc, "points": cpts_sc, "pts_placement": cpts_plc},
        }
        return placements
    return calculate
