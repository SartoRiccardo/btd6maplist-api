import pytest
import requests


@pytest.fixture
def map_submission_payload():
    def generate(code: str, notes: str = None, format: int = 1, proposed: int = 0) -> dict:
        return {
            "code": code,
            "notes": notes,
            "format": format,
            "proposed": proposed,
        }
    return generate


@pytest.fixture(scope="session")
def valid_codes():
    maps_url = "https://data.ninjakiwi.com/btd6/maps/filter/mostLiked"
    return [m["id"] for m in requests.get(maps_url).json()["body"]]
