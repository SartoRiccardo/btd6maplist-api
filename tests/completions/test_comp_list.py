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
schema_lcc = {"leftover": int, "proof": str}


@pytest.mark.get
@pytest.mark.completions
class TestCompletionList:
    """
    Test all endpoints returning only accepted, not deleted, and
    not overridden completions.
    """

    async def test_map_completions(self, btd6ml_test_client):
        """Test getting a map's completions"""
        async with btd6ml_test_client.get("/maps/MLXXXAJ/completions") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Get a map's completions returns {resp.status}"
            comp_data = await resp.json()
            # This code should have 9 completions, 1 deleted, 3 pending, 1 with format=2
            assert comp_data["total"] == 9-1-3-1, "Total completions differ from expected"
            assert comp_data["pages"] == 1, "Total pages differs from expected"
            compl_ids = set()
            for i, compl in enumerate(comp_data["completions"]):
                assert compl["id"] not in compl_ids, "Completion with duplicate ID"
                compl_ids.add(compl["id"])
                assert len(src.utils.validators.check_fields(compl, schema_completion)) == 0, \
                    f"Error while validating ListMap[{i}]"
                assert compl["format"] in [1, 51], "Found a different format when not providing the formats parameter"
                if compl["lcc"]:
                    assert len(src.utils.validators.check_fields(compl["lcc"], schema_lcc)) == 0, \
                        f"Error while validating ListMap[{i}].lcc"

        async with btd6ml_test_client.get("/maps/MLXXXAJ/completions?formats=2") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Get a map's completions returns {resp.status}"
            comp_data = await resp.json()
            assert comp_data["total"] == 1, "Total completions differ from expected"
            assert comp_data["completions"][0]["format"] == 2

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
                for compl in resp_data["completions"]:
                    assert compl["id"] not in compl_ids, "Completion with duplicate ID"
                    compl_ids.add(compl["id"])

        async with btd6ml_test_client.get(f"/maps/MLXXXAB/completions?formats=1,51,2&page={expected_pages+1}") as resp:
            resp_data = await resp.json()
            assert resp_data["pages"] == 0, "Total pages on overflown page differs from expected"
            assert resp_data["total"] == 0, "Total completions on overflown page differ from expected"

    async def test_user_completions(self, btd6ml_test_client):
        """Test getting a user's completions"""
        pytest.skip("Not Implemented")

    async def test_unknown_user_completions(self, btd6ml_test_client):
        """Test getting a nonexistent user's completions"""
        pytest.skip("Not Implemented")

    async def test_user_completions_paginate(self, btd6ml_test_client):
        """Test getting a user's completions, by page"""
        pytest.skip("Not Implemented")

    async def test_own_completions_on(self, btd6ml_test_client, mock_discord_api):
        """Test getting a user's own completions on a map"""
        pytest.skip("Not Implemented")

    async def test_recent_completions(self, btd6ml_test_client):
        """Test recent completions"""
        pytest.skip("Not Implemented")
