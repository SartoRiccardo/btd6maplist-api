import pytest


@pytest.fixture
def payload_format():
    def function() -> dict:
        return {
            "hidden": False,
            "run_submission_status": "closed",
            "map_submission_status": "closed",
            "run_submission_wh": "https://discord.com/wh/999",
            "map_submission_wh": "https://discord.com/wh/999",
        }
    return function
