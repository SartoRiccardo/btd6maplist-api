import pytest
import requests


@pytest.fixture
def map_payload():
    def generate(code: str, creators: dict = None):
        return {
            "code": code,
            "name": "Test Map Data",
            "placement_allver": -1,
            "placement_curver": -1,
            "difficulty": -1,
            "r6_start": None,
            "map_data": None,
            "map_preview_url": None,
            "additional_codes": [],
            "creators": creators if creators is not None else [{"id": "1", "role": None}],
            "verifiers": [],
            "aliases": [],
            "version_compatibilities": [],
            "optimal_heros": [],
        }
    return generate


@pytest.fixture
def map_submission_payload():
    def generate(code: str, notes: str = None, for_list: int = 0, proposed: int = 0) -> dict:
        return {
            "code": code,
            "notes": notes,
            "type": "list" if for_list == 0 else "experts",
            "proposed": proposed,
        }
    return generate


@pytest.fixture(scope="session")
def valid_codes():
    maps_url = "https://data.ninjakiwi.com/btd6/maps/filter/mostLiked"
    return [m["id"] for m in requests.get(maps_url).json()["body"]]
