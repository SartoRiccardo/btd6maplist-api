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
    async def test_retro_maps(self, btd6ml_test_client):
        """Test the retro maps endpoint"""
        retro_map_schema = {"id": int, "name": str}

        async with btd6ml_test_client.get("/maps/retro") as resp:
            assert resp.ok, f"GET /maps returned {resp.status}"
            resp_data = await resp.json()
            for game_name in resp_data:
                for diff_name in resp_data[game_name]:
                    seen_ids = set()
                    for i, retro_map in enumerate(resp_data[game_name][diff_name]):
                        assert retro_map["id"] not in seen_ids, f"Encountered id {retro_map['id']} twice"
                        assert len(src.utils.validators.check_fields(retro_map, retro_map_schema)) == 0, \
                            f"Error while validating RetroMap[{i}]"
                        seen_ids.add(retro_map["id"])

    async def test_maplist(self, btd6ml_test_client):
        """Test the Current Version maplist"""
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
        """Test the All Versions maplist"""
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

    async def test_expert_lists(self, btd6ml_test_client):
        """Test the Expert List and Best of the Best packs"""
        for format_id in [51, 52]:
            async with btd6ml_test_client.get(f"/maps?format={format_id}&filter=1") as resp:
                assert resp.ok, f"GET /maps returned {resp.status}"
                resp_data = await resp.json()
                for i, map_data in enumerate(resp_data):
                    assert len(src.utils.validators.check_fields(map_data, list_map_schema)) == 0, \
                        f"Error while validating Map[{i}] ({format_id=})"

    async def test_nostalgia_pack(self, btd6ml_test_client):
        """Test the nostalgia pack"""
        np_schema = {
            **list_map_schema,
            "code": str | None,
            "format_idx": {
                "id": int,
                "name": str,
                "sort_order": int,
                "preview_url": str,
                "game": {"id": int, "name": str},
                "category": {"id": int, "name": str},
                "subcategory": {"id": int, "name": str | None},
            },
        }

        async with btd6ml_test_client.get(f"/maps?format=11&filter=4") as resp:
            assert resp.ok, f"GET /maps returned {resp.status}"
            resp_data = await resp.json()
            for i, map_data in enumerate(resp_data):
                assert len(src.utils.validators.check_fields(map_data, np_schema)) == 0, \
                    f"Error while validating NostalgiaPackMap[{i}]"

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
