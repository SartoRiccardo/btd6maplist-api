import pytest
import http
import src.utils.misc
from ..mocks import DiscordPermRoles
from ..testutils import to_formdata

HEADERS = {"Authorization": "Bearer test_client"}


async def calc_ml_user_points(user_id: int, btd6ml_test_client) -> int:
    async with btd6ml_test_client.get("/config") as resp:
        config = await resp.json()

    async with btd6ml_test_client.get(f"/users/{user_id}/completions?formats=1") as resp:
        user_comps = sorted(
            (await resp.json())["completions"],
            key=lambda x: (x["map"]["code"], x["no_geraldo"], x["black_border"], x["current_lcc"]),
            reverse=True,
        )

    points = 0
    bonuses_applied = {"ger": False, "bb": False, "lcc": False}
    multiplier = 1
    raw_pts = 0
    for i, compl in enumerate(user_comps):
        if i == 0 or user_comps[i - 1]["map"]["code"] != compl["map"]["code"]:
            bonuses_applied = {"ger": False, "bb": False, "lcc": False}
            points += raw_pts * multiplier
            multiplier = 1
            if compl["map"]["placement_cur"] in range(1, config["map_count"]+1):
                raw_pts = src.utils.misc.point_formula(
                    compl["map"]["placement_cur"],
                    config["points_bottom_map"],
                    config["points_top_map"],
                    config["map_count"],
                    config["formula_slope"],
                )
                raw_pts = round(raw_pts, config["decimal_digits"])
            else:
                raw_pts = 0
        if compl["current_lcc"] and not bonuses_applied["lcc"]:
            points += config["points_extra_lcc"]
            bonuses_applied["lcc"] = True

        if compl["no_geraldo"] and compl["black_border"]:
            multiplier = config["points_multi_bb"] * config["points_multi_gerry"]
            bonuses_applied["ger"] = True
            bonuses_applied["bb"] = True
        elif compl["black_border"] and not bonuses_applied["bb"]:
            if bonuses_applied["ger"]:
                multiplier += config["points_multi_bb"]
            multiplier = config["points_multi_bb"]
            bonuses_applied["bb"] = True
        elif compl["no_geraldo"] and not bonuses_applied["ger"]:
            if bonuses_applied["bb"]:
                multiplier += config["points_multi_gerry"]
            multiplier = config["points_multi_gerry"]
            bonuses_applied["ger"] = True
    points += raw_pts * multiplier

    return points


async def calc_exp_user_points(user_id: int, btd6ml_test_client) -> int:
    async with btd6ml_test_client.get("/config") as resp:
        config = await resp.json()

    async with btd6ml_test_client.get(f"/users/{user_id}/completions?formats=1,51") as resp:
        user_comps = sorted(
            (await resp.json())["completions"],
            key=lambda x: x["map"]["code"],
            reverse=True,
        )

    config_keys = ["exp_points_casual", "exp_points_medium", "exp_points_high", "exp_points_true", "exp_points_extreme"]
    config_keys_nogerry = ["exp_nogerry_points_casual", "exp_nogerry_points_medium", "exp_nogerry_points_high",
           "exp_nogerry_points_true", "exp_nogerry_points_extreme"]
    points = 0
    used_multis = {"no_gerry": False, "lcc": False, "bb": False}
    for i, comp in enumerate(user_comps):
        if comp["map"]["difficulty"] is None:
            continue
        if i == 0 or comp["map"]["code"] != user_comps[i - 1]["map"]["code"]:
            used_multis = {"no_gerry": False, "lcc": False, "bb": False}
            points += config[config_keys[comp["map"]["difficulty"]]]
            if comp["no_geraldo"] and not used_multis["no_gerry"]:
                used_multis["no_gerry"] = True
                points += config[config_keys_nogerry[comp["map"]["difficulty"]]]
            if comp["black_border"] and not used_multis["bb"]:
                used_multis["bb"] = True
                points += config[config_keys[comp["map"]["difficulty"]]] * (config["exp_bb_multi"]-1)
            if comp["current_lcc"] and not used_multis["lcc"]:
                used_multis["lcc"] = True
                points += config["exp_lcc_extra"]
    return points


async def calc_completion_count(
        user_id: int,
        formats: list[int],
        btd6ml_test_client,
        req_field: str = "placement_cur",
        count_key: str = "current_lcc",
) -> int:
    async with btd6ml_test_client.get(
            f"/users/{user_id}/completions?formats={','.join(str(x) for x in formats)}"
    ) as resp:
        user_comps = sorted(
            (await resp.json())["completions"],
            key=lambda x: (x["map"]["code"], x[count_key]),
            reverse=True,
        )
    comp_count = 0
    for i, comp in enumerate(user_comps):
        if req_field == "placement_cur" and comp["map"]["placement_cur"] not in range(1, 50):
            continue
        elif req_field == "difficulty" and comp["map"]["difficulty"] is None:
            continue

        if comp[count_key] and (i == 0 or user_comps[i - 1]["map"]["code"] != comp["map"]["code"]):
            comp_count += 1
    return comp_count


async def get_lb_score(user_id: int, lb_format: int, value: str, btd6ml_test_client) -> int:
    async with btd6ml_test_client.get(f"/maps/leaderboard?format={lb_format}&value={value}") as resp:
        assert resp.status == http.HTTPStatus.OK, \
            f"Getting the leaderboard returns {resp.status}"
        return next(
            entry for entry in (await resp.json())["entries"]
            if entry["user"]["id"] == str(user_id)
        )["score"]


@pytest.mark.completions
class TestLeaderboard:
    async def test_ml_point_leaderboard(self, btd6ml_test_client):
        """Test the leaderboard is correctly calculated"""
        USER_ID = 47
        points = await calc_ml_user_points(USER_ID, btd6ml_test_client)
        assert await get_lb_score(USER_ID, 1, "points", btd6ml_test_client) == points, \
            "User points differ from expected"

    async def test_exp_point_leaderboard(self, btd6ml_test_client):
        """Test the expert leaderboard is correctly calculated"""
        USER_ID = 1
        points = await calc_exp_user_points(USER_ID, btd6ml_test_client)
        assert await get_lb_score(USER_ID, 51, "points", btd6ml_test_client) == points, \
            "User points differ from expected"

    async def test_ml_lcc_leaderboard(self, btd6ml_test_client):
        """Test the maplist lcc leaderboard is correctly calculated"""
        USER_ID = 39
        lcc_count = await calc_completion_count(USER_ID, [1], btd6ml_test_client)
        assert await get_lb_score(USER_ID, 1, "lccs", btd6ml_test_client) == lcc_count, \
            "User LCC count differs from expected"

    async def test_exp_lcc_leaderboard(self, btd6ml_test_client):
        """Test the expert lcc leaderboard is correctly calculated"""
        USER_ID = 46
        lcc_count = await calc_completion_count(USER_ID, [1, 51], btd6ml_test_client, req_field="difficulty")
        assert await get_lb_score(USER_ID, 51, "lccs", btd6ml_test_client) == lcc_count, \
            "User LCC count differs from expected"

    async def test_ml_no_geraldo_leaderboard(self, btd6ml_test_client):
        """Test the maplist No Geraldo leaderboard is correctly calculated"""
        USER_ID = 13
        lcc_count = await calc_completion_count(USER_ID, [1], btd6ml_test_client, count_key="no_geraldo")
        assert await get_lb_score(USER_ID, 1, "no_geraldo", btd6ml_test_client) == lcc_count, \
            "User No Geraldo count differs from expected"

    async def test_exp_no_geraldo_leaderboard(self, btd6ml_test_client):
        """Test the expert No Geraldo leaderboard is correctly calculated"""
        USER_ID = 41
        lcc_count = await calc_completion_count(
            USER_ID,
            [1, 51],
            btd6ml_test_client,
            count_key="no_geraldo",
            req_field="difficulty",
        )

        assert await get_lb_score(USER_ID, 51, "no_geraldo", btd6ml_test_client) == lcc_count, \
            "User No Geraldo count differs from expected"

    async def test_ml_black_border_leaderboard(self, btd6ml_test_client):
        """Test the maplist Black Border leaderboard is correctly calculated"""
        USER_ID = 11
        lcc_count = await calc_completion_count(USER_ID, [1], btd6ml_test_client, count_key="black_border")
        assert await get_lb_score(USER_ID, 1, "black_border", btd6ml_test_client) == lcc_count, \
            "User Black Border count differs from expected"

    async def test_exp_black_border_leaderboard(self, btd6ml_test_client):
        """Test the expert Black Border leaderboard is correctly calculated"""
        USER_ID = 39
        lcc_count = await calc_completion_count(
            USER_ID,
            [1, 51],
            btd6ml_test_client,
            count_key="black_border",
            req_field="difficulty",
        )

        assert await get_lb_score(USER_ID, 51, "black_border", btd6ml_test_client) == lcc_count, \
            "User Black Border count differs from expected"


@pytest.mark.completions
class TestRecalc:
    async def test_config_recalc(self, btd6ml_test_client, mock_auth):
        """Test the point leaderboards are updated on config var changes"""
        await mock_auth(perms=DiscordPermRoles.ADMIN)

        req_config = {
            "exp_points_casual": 10,
            "exp_points_medium": 21,
            "exp_points_high": 32,
            "exp_points_true": 43,
            "exp_points_extreme": 54,
            "exp_nogerry_points_casual": 2,
            "exp_nogerry_points_medium": 3,
            "exp_nogerry_points_high": 4,
            "exp_nogerry_points_true": 5,
            "exp_nogerry_points_extreme": 6,
            "exp_bb_multi": 3,
            "exp_lcc_extra": 6,

            "points_top_map": 200,
            "points_bottom_map": 1,
            "formula_slope": 0.80,
            "points_extra_lcc": 10,
            "points_multi_gerry": 5,
            "points_multi_bb": 10,
            "decimal_digits": 5,
        }
        async with btd6ml_test_client.put("/config", headers=HEADERS, json={"config": req_config}) as resp:
            assert resp.status == http.HTTPStatus.OK, f"Editing config returned {resp.status}"

        user_id = 47
        points = await calc_ml_user_points(user_id, btd6ml_test_client)
        assert await get_lb_score(user_id, 1, "points", btd6ml_test_client) == points, \
            "Maplist user points differ from expected"

        user_id = 39
        points = await calc_exp_user_points(user_id, btd6ml_test_client)
        assert await get_lb_score(user_id, 51, "points", btd6ml_test_client) == points, \
            "Experts user points differ from expected"

    async def test_submission_recalc(self, btd6ml_test_client, mock_auth, comp_subm_payload, save_image,
                                     assert_state_unchanged):
        """Test the point leaderboards are NOT updated on unaccepted submissions"""
        await mock_auth()

        subm_image = save_image(1)
        req_subm = {
            **comp_subm_payload(),
            "black_border": True,
            "no_geraldo": True,
            "current_lcc": True,
            "leftover": 999999999,
            "video_proof_url": ["https://proof.com"],
        }

        req_form = to_formdata(req_subm)
        req_form.add_field("proof_completion", subm_image.open("rb"))
        async with assert_state_unchanged("/maps/leaderboard"):
            async with btd6ml_test_client.post("/maps/MLXXXEB/completions/submit", headers=HEADERS, data=req_form) as resp:
                assert resp.status == http.HTTPStatus.CREATED, f"Submitting a completion returned {resp.status}"

        req_subm["format"] = 51
        req_form = to_formdata(req_subm)
        req_form.add_field("proof_completion", subm_image.open("rb"))
        async with assert_state_unchanged("/maps/leaderboard?format=51"):
            async with btd6ml_test_client.post("/maps/MLXXXEB/completions/submit", headers=HEADERS, data=req_form) as resp:
                assert resp.status == http.HTTPStatus.CREATED, f"Submitting a completion returned {resp.status}"

    async def test_placement_change_recalc(self, btd6ml_test_client, mock_auth, map_payload):
        """Test the maplist point leaderboard is updated on placement changes"""
        USER_ID = 47
        await mock_auth(perms=DiscordPermRoles.ADMIN)

        async with btd6ml_test_client.get("/maps/1") as resp:
            assert resp.status == http.HTTPStatus.OK, f"Getting a map returned {resp.status}"
            map_code = (await resp.json())["code"]

        req_data = map_payload(map_code)
        req_data["placement_curver"] = 50
        async with btd6ml_test_client.put(f"/maps/{map_code}", headers=HEADERS, json=req_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, f"Editing a map returned {resp.status}"

        points = await calc_ml_user_points(USER_ID, btd6ml_test_client)
        assert await get_lb_score(USER_ID, 1, "points", btd6ml_test_client) == points, \
            "User points differ from expected"

    async def test_diff_change_recalc(self, btd6ml_test_client, mock_auth, map_payload):
        """Test the experts point leaderboard is updated on placement changes"""
        USER_ID = 1
        await mock_auth(perms=DiscordPermRoles.ADMIN)

        async with btd6ml_test_client.get(f"/users/{USER_ID}/completions") as resp:
            assert resp.status == http.HTTPStatus.OK, f"Get a user's completions returned {resp.status}"
            for compl in (await resp.json())["completions"]:
                if compl["map"]["difficulty"] is not None:
                    map_code = compl["map"]["code"]

        req_data = map_payload(map_code)
        req_data["difficulty"] = 3
        async with btd6ml_test_client.put(f"/maps/{map_code}", headers=HEADERS, json=req_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, f"Editing a map returned {resp.status}"

        points = await calc_exp_user_points(USER_ID, btd6ml_test_client)
        assert await get_lb_score(USER_ID, 51, "points", btd6ml_test_client) == points, \
            "User points differ from expected"
