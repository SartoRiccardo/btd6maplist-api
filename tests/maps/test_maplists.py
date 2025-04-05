import pytest
import src.utils.validators

list_map_schema = {
    "name": str,
    "code": str,
    "map_preview_url": str,
    "verified": bool,
    "format_idx": int,
}


@pytest.mark.maps
@pytest.mark.get
class TestMaplists:
    async def test_maplist(self, btd6ml_test_client):
        async with btd6ml_test_client.get("/maps") as resp:
            assert resp.ok, f"GET /maps returned {resp.status}"
            resp_data = await resp.json()
            assert resp_data[0]["code"] == "MLXXXAA", "First map code differs from expected"
            assert resp_data[-1]["code"] == "MLXXXEJ", "Last map code differs from expected"
            assert len(resp_data) == 50, "Maplist length differs from expected"
            for i, map_data in enumerate(resp_data):
                assert map_data["format_idx"] == i+1, \
                    f"ListMap[{i}].format_idx is misplaced"
                assert len(src.utils.validators.check_fields(map_data, list_map_schema)) == 0, \
                    f"Error while validating ListMap[{i}]"

    async def test_maplist_allvers(self, btd6ml_test_client):
        async with btd6ml_test_client.get("/maps?format=2") as resp:
            assert resp.ok, f"GET /maps returned {resp.status}"
            resp_data = await resp.json()
            assert resp_data[0]["code"] == "MLAXXAA", "First map code differs from expected"
            assert resp_data[-1]["code"] == "MLXXXFE", "Last map code differs from expected"
            assert len(resp_data) == 50, "Maplist length differs from expected"
            for i, map_data in enumerate(resp_data):
                assert map_data["format_idx"] == i+1, \
                    f"ListMap[{i}].format_idx is misplaced"
                assert len(src.utils.validators.check_fields(map_data, list_map_schema)) == 0, \
                    f"Error while validating ListMap[{i}]"

    async def test_expert_list(self, btd6ml_test_client):

        async with btd6ml_test_client.get("/maps?format=51") as resp:
            assert resp.ok, f"GET /maps returned {resp.status}"
            resp_data = await resp.json()
            for i, map_data in enumerate(resp_data):
                assert len(src.utils.validators.check_fields(map_data, list_map_schema)) == 0, \
                    f"Error while validating ExpertMap[{i}]"

    async def test_legacy_list(self, btd6ml_test_client):
        """Test the legacy list and its pagination"""
        # Currently doesn't paginate will do so in the future
        legacy_map_schema = {
            **list_map_schema,
            "format_idx": int | None
        }

        async with btd6ml_test_client.get("/maps/legacy") as resp:
            assert resp.ok, f"GET /maps/legacy returned {resp.status}"
            resp_data = await resp.json()
            assert resp_data[0]["format_idx"] > 0, "First map's placement is negative"
            for i, map_data in enumerate(resp_data):
                if i > 0 and map_data["format_idx"] is not None:
                    assert resp_data[i-1]["format_idx"] < map_data["format_idx"], \
                        "Placement does not increase in legacy list"
                assert map_data["format_idx"] is None or map_data["format_idx"] > 50, \
                    f"LegacyMap[{i}].format_idx is misplaced"
                assert len(src.utils.validators.check_fields(map_data, legacy_map_schema)) == 0, \
                    f"Error while validating LegacyMap[{i}]"
