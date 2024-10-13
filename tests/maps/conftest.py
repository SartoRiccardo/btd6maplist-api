import pytest
import requests
import copy


@pytest.fixture
def map_payload():
    sample_data = {
        "name": "Test Map Data",
        "placement_allver": -1,
        "placement_curver": -1,
        "difficulty": -1,
        "r6_start": None,
        "map_data": None,
        "map_preview_url": None,
        "additional_codes": [],
        "creators": [],
        "verifiers": [],
        "aliases":  [],
        "version_compatibilities": [],
        "optimal_heros": [],
    }

    def generate(code: str):
        return {
            "code": code,
            **copy.deepcopy(sample_data),
        }
    return generate


@pytest.fixture(scope="session")
def valid_codes():
    maps_url = "https://data.ninjakiwi.com/btd6/maps/filter/mostLiked"
    return [m["id"] for m in requests.get(maps_url).json()["body"]]
