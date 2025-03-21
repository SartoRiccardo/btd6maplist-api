import pytest
import src.utils.validators


format_schema = {
    "id": int,
    "name": str,
    "hidden": bool,
    "map_submission_status": str,
    "run_submission_status": str,
}


@pytest.mark.formats
@pytest.mark.get
async def test_formats(btd6ml_test_client):
    async with btd6ml_test_client.get("/formats") as resp:
        assert resp.ok, f"GET /formats returned {resp.status}"
        resp_data = await resp.json()
        assert len(resp_data) == 5, "Returned more formats than expected"
        for i, fmt in enumerate(resp_data):
            assert len(src.utils.validators.check_fields(fmt, format_schema)) == 0, \
                f"Error while validating Format[{i}]"
