import pytest


@pytest.mark.maps
@pytest.mark.get
class TestMaplists:
    async def test_maplist(self, btd6ml_test_client):
        async with btd6ml_test_client.get("/maps") as resp:
            assert resp.ok, f"GET /maps returned {resp.status}"
        pytest.skip("Not Implemented")

    async def test_maplist_allvers(self, btd6ml_test_client):
        async with btd6ml_test_client.get("/maps") as resp:
            assert resp.ok, f"GET /maps returned {resp.status}"
        pytest.skip("Not Implemented")

    async def test_expert_list(self, btd6ml_test_client):
        async with btd6ml_test_client.get("/exmaps") as resp:
            assert resp.ok, f"GET /maps returned {resp.status}"
        pytest.skip("Not Implemented")

    async def test_legacy_list(self, btd6ml_test_client):
        """Test the legacy list and its pagination"""
        pytest.skip("Not Implemented")
