import pytest_asyncio


@pytest_asyncio.fixture(autouse=True, scope="module")
async def init_nogerry_experts_config(btd6ml_test_client):
    config_init = {
        "exp_nogerry_points_casual": 1,
        "exp_nogerry_points_medium": 1,
        "exp_nogerry_points_high": 2,
        "exp_nogerry_points_true": 2,
        "exp_nogerry_points_extreme": 3,
    }
    async with btd6ml_test_client.put("/config", headers=HEADERS, json=config_init):
        pass
