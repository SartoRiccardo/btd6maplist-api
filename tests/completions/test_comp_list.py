import http
import math
import pytest
import src.utils.validators

schema_completion = {
    "id": int,
    "map": str,
    "users": [{"id": str, "name": str}],
    "black_border": bool,
    "no_geraldo": bool,
    "current_lcc": bool,
    "format": int,
    "subm_proof_img": [str],
    "subm_proof_vid": [str],
}
schema_completion_map = {
    **schema_completion,
    "users": [str],
    "map": {
        "name": str,
        "code": str,
        "placement_cur": int,
        "placement_all": int,
        "difficulty": int,
        "r6_start": str | None,
        "map_preview_url": str,
        "optimal_heros": [str],
        "created_on": int,
        "deleted_on": int | None,
    },
}
schema_lcc = {"leftover": int, "proof": str}


@pytest.mark.get
@pytest.mark.completions
class TestCompletionList:
    """
    Test all endpoints returning only accepted, not deleted, and
    not overridden completions.
    """
    @staticmethod
    def validate_comp_list(
            completions,
            schema_comp: dict = None,
            compl_ids: set = None,
            allowed_formats: list = None,
    ) -> set:
        if compl_ids is None:
            compl_ids = set()
        if allowed_formats is None:
            allowed_formats = [1, 51]

        for i, compl in enumerate(completions):
            assert compl["id"] not in compl_ids, "Completion with duplicate ID"
            compl_ids.add(compl["id"])
            assert compl["format"] in allowed_formats, \
                "Found a different format than expected"
            if schema_comp is not None:
                assert len(src.utils.validators.check_fields(compl, schema_comp)) == 0, \
                    f"Error while validating Completion[{i}]"
                if compl["lcc"]:
                    assert len(src.utils.validators.check_fields(compl["lcc"], schema_lcc)) == 0, \
                        f"Error while validating Completion[{i}].lcc"
        return compl_ids

    async def test_map_completions(self, btd6ml_test_client):
        """Test getting a map's completions"""
        async with btd6ml_test_client.get("/maps/MLXXXAJ/completions") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Get a map's completions returns {resp.status}"
            comp_data = await resp.json()
            # This code should have 9 completions, 1 deleted, 3 pending, 1 with format=2
            assert comp_data["total"] == 9-1-3-1, "Total completions differ from expected"
            assert comp_data["pages"] == 1, "Total pages differs from expected"
            self.validate_comp_list(comp_data["completions"], schema_completion)

        async with btd6ml_test_client.get("/maps/MLXXXAJ/completions?formats=2") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Get a map's completions returns {resp.status}"
            comp_data = await resp.json()
            assert comp_data["total"] == 1, "Total completions differ from expected"
            self.validate_comp_list(comp_data["completions"], schema_completion, allowed_formats=[2])

    async def test_unknown_map_completions(self, btd6ml_test_client):
        """Test getting a nonexistent map's completions"""
        async with btd6ml_test_client.get("/maps/XXXXXXX/completions") as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"Get an unknown map's completions returns {resp.status}"

    async def test_map_completions_paginate(self, btd6ml_test_client):
        """Test getting a map's completions, by page"""
        compl_ids = set()
        expected_compl = 98
        expected_pages = math.ceil(expected_compl/50)
        for pg in range(1, expected_pages+1):
            async with btd6ml_test_client.get(f"/maps/MLXXXAB/completions?formats=1,51,2&page={pg}") as resp:
                resp_data = await resp.json()
                assert resp_data["pages"] == expected_pages, "Total pages differs from expected"
                assert resp_data["total"] == expected_compl, "Total completions differ from expected"
                compl_ids = self.validate_comp_list(
                    resp_data["completions"],
                    allowed_formats=[1, 2, 51],
                    compl_ids=compl_ids,
                )

        async with btd6ml_test_client.get(f"/maps/MLXXXAB/completions?formats=1,51,2&page={expected_pages+1}") as resp:
            resp_data = await resp.json()
            assert resp_data["pages"] == 0, "Total pages on overflown page differs from expected"
            assert resp_data["total"] == 0, "Total completions on overflown page differ from expected"

    async def test_user_completions(self, btd6ml_test_client):
        """Test getting a user's completions"""
        # Non-overlapping invalid runs:
        # Player #21: p21_total=24 p21_not_accepted=6 p21_deleted_on=0 p21_format_2=7 p21_del_map=1
        runs_f2 = 7
        expected_runs = 24 - (6+0+runs_f2+1)

        async with btd6ml_test_client.get("/users/21/completions") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Get a map's completions returns {resp.status}"
            comp_data = await resp.json()
            assert comp_data["total"] == expected_runs, "Total completions differ from expected"
            assert comp_data["pages"] == 1, "Total pages differs from expected"
            self.validate_comp_list(comp_data["completions"], schema_completion_map)

        async with btd6ml_test_client.get("/users/21/completions?formats=2") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Get a map's completions returns {resp.status}"
            comp_data = await resp.json()
            assert comp_data["total"] == runs_f2, "Total completions differ from expected"
            self.validate_comp_list(comp_data["completions"], schema_completion_map, allowed_formats=[2])

    async def test_unknown_user_completions(self, btd6ml_test_client):
        """Test getting a nonexistent user's completions"""
        async with btd6ml_test_client.get("/users/999989999/completions") as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"Get an unknown users's completions returns {resp.status}"

    async def test_user_completions_paginate(self, btd6ml_test_client):
        """Test getting a user's completions, by page"""
        # Player #42: {'tot': 159, 'na': 3, 'del': 0, 'fmt2': 7, 'delmap': 20}
        expected_total = 159 - (3+20)
        expected_pages = math.ceil(expected_total/50)
        compl_ids = set()
        for pg in range(1, expected_pages+1):
            async with btd6ml_test_client.get(f"/users/42/completions?formats=1,51,2&page={pg}") as resp:
                resp_data = await resp.json()
                assert resp_data["pages"] == expected_pages, "Total pages differs from expected"
                assert resp_data["total"] == expected_total, "Total completions differ from expected"
                compl_ids = self.validate_comp_list(
                    resp_data["completions"],
                    allowed_formats=[1, 2, 51],
                    compl_ids=compl_ids,
                )

        async with btd6ml_test_client.get(f"/users/42/completions?formats=1,51,2&page={expected_pages+1}") as resp:
            resp_data = await resp.json()
            assert resp_data["pages"] == 0, "Total pages on overflown page differs from expected"
            assert resp_data["total"] == 0, "Total completions on overflown page differ from expected"

        pytest.skip("Not Implemented")

    async def test_own_completions_on(self, btd6ml_test_client, mock_discord_api):
        """Test getting a user's own completions on a map"""
        pytest.skip("Not Implemented")

    async def test_recent_completions(self, btd6ml_test_client):
        """Test recent completions"""
        pytest.skip("Not Implemented")
