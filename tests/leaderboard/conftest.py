import pytest_asyncio
from ..mocks import Permissions


@pytest_asyncio.fixture(autouse=True, scope="function")
async def init_nogerry_experts_config(btd6ml_test_client, mock_auth):
    config_init = {
        "exp_nogerry_points_casual": 1,
        "exp_nogerry_points_medium": 1,
        "exp_nogerry_points_high": 2,
        "exp_nogerry_points_true": 2,
        "exp_nogerry_points_extreme": 3,
    }
    await mock_auth(perms={51: Permissions.mod()})
    async with btd6ml_test_client.put(
            "/config",
            headers={"Authorization": "Bearer test_client"},
            json={"config": config_init}
    ):
        pass
