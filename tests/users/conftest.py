import pytest_asyncio
import pytest


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
            comps = sorted(
                [
                    {
                        "map": cmp["map"]["code"],
                        "black_border": cmp["black_border"],
                        "no_geraldo": cmp["no_geraldo"],
                        "current_lcc": cmp["current_lcc"],
                        "format": cmp["format"]
                    }
                    for cmp in comps
                ],
                key=lambda x: (x["map"], x["format"], x["black_border"], x["no_geraldo"], x["current_lcc"]),
            )

            comps_compressed = []
            current_comp = None

            for i, comp in enumerate(comps):
                if i == 0 or comp["map"] != comps[i-1]["map"] or comp["format"] != comps[i-1]["format"]:
                    if current_comp is not None:
                        comps_compressed.append(current_comp)
                    current_comp = {
                        "map": comp["map"],
                        "black_border": comp["black_border"],
                        "no_geraldo": comp["no_geraldo"],
                        "current_lcc": comp["current_lcc"],
                        "format": comp["format"]
                    }
                current_comp["black_border"] = current_comp["black_border"] or comp["black_border"]
                current_comp["no_geraldo"] = current_comp["no_geraldo"] or comp["no_geraldo"]
                current_comp["current_lcc"] = current_comp["current_lcc"] or comp["current_lcc"]
            if current_comp is not None:
                comps_compressed.append(current_comp)

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

        return expected_medals, comps_compressed

    return calculate


@pytest_asyncio.fixture
async def calc_usr_placements(btd6ml_test_client):
    async def calculate(user_id: int | None) -> dict:
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

        placements = {}
        for key, format in [("current", 1), ("all", 2), ("experts", 51)]:
            if user_id is None:
                placements[key] = {
                    "points": 0.0, "pts_placement": None,
                    "lccs": 0.0, "lccs_placement": None,
                    "no_geraldo": 0.0, "no_geraldo_placement": None,
                    "black_border": 0.0, "black_border_placement": None,
                }
            else:
                pts_score, pts_plc = await get_usr_data(format, "points")
                lcc_score, lcc_plc = await get_usr_data(format, "lccs")
                nogerry_score, nogerry_plc = await get_usr_data(format, "no_geraldo")
                bb_score, bb_plc = await get_usr_data(format, "black_border")
                placements[key] = {
                    "points": pts_score, "pts_placement": pts_plc,
                    "lccs": lcc_score, "lccs_placement": lcc_plc,
                    "no_geraldo": nogerry_score, "no_geraldo_placement": nogerry_plc,
                    "black_border": bb_score, "black_border_placement": bb_plc,
                }

        return placements
    return calculate


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
