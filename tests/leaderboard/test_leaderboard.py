import pytest
import http
import src.utils.misc


@pytest.mark.completions
class TestLeaderboard:
    @staticmethod
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
            if i == 0 or user_comps[i-1]["map"]["code"] != compl["map"]["code"]:
                bonuses_applied = {"ger": False, "bb": False, "lcc": False}
                points += raw_pts * multiplier
                raw_pts = src.utils.misc.point_formula(
                    compl["map"]["placement_cur"],
                    config["points_bottom_map"],
                    config["points_top_map"],
                    config["map_count"],
                    config["formula_slope"],
                )
                multiplier = 1
                raw_pts = round(raw_pts, config["decimal_digits"])
            if compl["current_lcc"] and not bonuses_applied["lcc"]:
                points += config["points_extra_lcc"]
                bonuses_applied["lcc"] = True

            if compl["no_geraldo"] and compl["black_border"]:
                multiplier = 6
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

    @staticmethod
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
        points = 0
        for i, comp in enumerate(user_comps):
            if comp["map"]["difficulty"] == -1:
                continue
            if i == 0 or comp["map"]["code"] != user_comps[i-1]["map"]["code"]:
                points += config[config_keys[comp["map"]["difficulty"]]]
        return points

    @staticmethod
    async def calc_lcc_count(
            user_id: int,
            formats: list[int],
            btd6ml_test_client,
            req_field: str = "placement_cur",
    ) -> int:
        async with btd6ml_test_client.get(
                f"/users/{user_id}/completions?formats={','.join(str(x) for x in formats)}"
        ) as resp:
            user_comps = sorted(
                (await resp.json())["completions"],
                key=lambda x: (x["map"]["code"], x["current_lcc"]),
                reverse=True,
            )
        lcc_count = 0
        for i, comp in enumerate(user_comps):
            if req_field == "placement_cur" and comp["map"]["placement_cur"] not in range(1, 50):
                continue
            elif req_field == "difficulty" and comp["map"]["difficulty"] == -1:
                continue

            if comp["current_lcc"] and (i == 0 or user_comps[i-1]["map"]["code"] != comp["map"]["code"]):
                lcc_count += 1
        return lcc_count

    async def test_ml_point_leaderboard(self, btd6ml_test_client):
        """Test the leaderboard is correctly calculated"""
        USER_ID = 47
        points = await self.calc_ml_user_points(USER_ID, btd6ml_test_client)

        async with btd6ml_test_client.get("/maps/leaderboard") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting the leaderboard returns {resp.status}"
            usr_entry = next(
                entry for entry in (await resp.json())["entries"]
                if entry["user"]["id"] == str(USER_ID)
            )
            assert usr_entry["score"] == points, "User points differ from expected"

    async def test_exp_point_leaderboard(self, btd6ml_test_client):
        """Test the expert leaderboard is correctly calculated"""
        USER_ID = 1
        points = await self.calc_exp_user_points(USER_ID, btd6ml_test_client)

        async with btd6ml_test_client.get("/maps/leaderboard?format=51") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting the leaderboard returns {resp.status}"
            usr_entry = next(
                entry for entry in (await resp.json())["entries"]
                if entry["user"]["id"] == str(USER_ID)
            )
            assert usr_entry["score"] == points, "User points differ from expected"

    async def test_ml_lcc_leaderboard(self, btd6ml_test_client):
        """Test the maplist lcc leaderboard is correctly calculated"""
        USER_ID = 39
        lcc_count = await self.calc_lcc_count(USER_ID, [1], btd6ml_test_client)

        async with btd6ml_test_client.get("/maps/leaderboard?format=1&value=lccs") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting the leaderboard returns {resp.status}"
            usr_entry = next(
                entry for entry in (await resp.json())["entries"]
                if entry["user"]["id"] == str(USER_ID)
            )
            assert usr_entry["score"] == lcc_count, "User LCC count differs from expected"

    async def test_exp_lcc_leaderboard(self, btd6ml_test_client):
        """Test the expert lcc leaderboard is correctly calculated"""
        USER_ID = 46
        lcc_count = await self.calc_lcc_count(USER_ID, [1, 51], btd6ml_test_client, req_field="difficulty")

        async with btd6ml_test_client.get("/maps/leaderboard?format=51&value=lccs") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting the leaderboard returns {resp.status}"
            usr_entry = next(
                entry for entry in (await resp.json())["entries"]
                if entry["user"]["id"] == str(USER_ID)
            )
            assert usr_entry["score"] == lcc_count, "User LCC count differs from expected"


@pytest.mark.completions
class TestRecalc:
    async def test_config_recalc(self, btd6ml_test_client):
        """Test the point leaderboards are updated on config var changes"""
        pytest.skip("Not Implemented")

    async def test_submission_recalc(self, btd6ml_test_client):
        """Test the point leaderboards are NOT updated on unaccepted submissions"""
        pytest.skip("Not Implemented")

    async def test_placement_change_recalc(self, btd6ml_test_client):
        """Test the maplist point leaderboard is updated on placement changes"""
        pytest.skip("Not Implemented")

    async def test_diff_change_recalc(self, btd6ml_test_client):
        """Test the experts point leaderboard is updated on placement changes"""
        pytest.skip("Not Implemented")

    async def test_completion_change_recalc(self, btd6ml_test_client):
        """Test the point & lcc leaderboards are updated on placement changes"""
        pytest.skip("Not Implemented")
