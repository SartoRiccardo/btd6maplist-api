import http
import pytest
import src.utils.validators

user_schema = {
    "name": str,
    "id": str,
}

map_schema = {
    "code": str,
    "name": str,
    "placement_allver": int | None,
    "placement_curver": int | None,
    "difficulty": int | None,
    "botb_difficulty": int | None,
    "r6_start": str | None,
    "map_data": str | None,
    "optimal_heros": [str],
    "deleted_on": int | None,
    "map_preview_url": str
}


@pytest.mark.get
class TestSearch:
    @staticmethod
    def assert_results(results: list, allowed_types: list[str]) -> None:
        schemas = {
            "user": user_schema,
            "map": map_schema,
        }

        for i, result in enumerate(results):
            assert result["type"] in allowed_types, "Search returned a type that wasn't requested"
            assert len(src.utils.validators.check_fields(result["data"], schemas[result["type"]])) == 0, \
                f"Error while validating results[{i}]"

    async def test_search(self, btd6ml_test_client):
        """Tests the search function working correctly"""
        async with btd6ml_test_client.get("/search?q=r32") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Searching returned {resp.status}"
            self.assert_results(await resp.json(), ["user"])

    async def test_params(self, btd6ml_test_client):
        """Tests the search params working correctly"""
        async with btd6ml_test_client.get("/search?q=p%2021&limit=20&type=user,map") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Searching returned {resp.status}"
            self.assert_results(await resp.json(), ["user", "map"])

        limit = 3
        async with btd6ml_test_client.get(f"/search?q=usr&limit={limit}&type=user") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Searching returned {resp.status}"
            results = await resp.json()
            self.assert_results(results, ["user"])
            assert len(results) == limit, "Length of results differs from expected"

        limit = 1000
        async with btd6ml_test_client.get(f"/search?q=usr&limit={limit}&type=user") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Searching returned {resp.status}"
            results = await resp.json()
            self.assert_results(results, ["user"])
            assert len(results) == 50, "Length of results differs from expected"

    async def test_invalid_query(self, btd6ml_test_client):
        """Tests the search not working for missing or invalid queries"""
        async with btd6ml_test_client.get("/search?limit=10") as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"Searching returned {resp.status} when not providing a query"
            resp_data = await resp.json()
            assert "errors" in resp_data and "q" in resp_data["errors"], \
                "query not in response.errors when not providing a query"

        async with btd6ml_test_client.get("/search?q=&limit=10") as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"Searching returned {resp.status} when providing a query too short"
            resp_data = await resp.json()
            assert "errors" in resp_data and "q" in resp_data["errors"], \
                "query not in response.errors when providing a query too short"
