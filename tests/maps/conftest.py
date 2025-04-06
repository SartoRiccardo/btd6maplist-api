import pytest
import http
import requests
from ..testutils import to_formdata

HEADERS = {"Authorization": "Bearer xxx"}


def to_subm_formdata(subm_data: dict, img_url: str, tmp_path: "pathlib.Path"):
    form_data = to_formdata(subm_data)
    path = tmp_path / "proof_completion.png"
    path.write_bytes(requests.get(img_url).content)
    form_data.add_field("proof_completion", path.open("rb"))
    return form_data


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


@pytest.fixture
def submit_test_map(mock_auth, btd6ml_test_client, tmp_path, map_submission_payload):
    async def function(map_code: str, format_id: int = 1) -> None:
        await mock_auth()

        req_data = map_submission_payload(map_code, format=format_id)
        form_data = to_subm_formdata(req_data, "https://dummyimage.com/400x300/00ff00/000", tmp_path)
        async with btd6ml_test_client.post("/maps/submit", headers=HEADERS, data=form_data) as resp, \
                btd6ml_test_client.get("/maps/submit") as resp_get:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Valid submission returned {resp.status}"

            resp_data = await resp_get.json()
            assert resp_data["submissions"][0]["code"] == map_code, \
                "Latest submission differs from expected"
    return function


@pytest.fixture
def assert_submission(btd6ml_test_client):
    async def function(map_code: str, exists: bool = False) -> None:
        async with btd6ml_test_client.get("/maps/submit") as resp_get, \
                btd6ml_test_client.get("/maps/submit?pending=all") as resp_get_all:
            resp_data = await resp_get.json()
            resp_data_all = await resp_get_all.json()

            if exists:
                assert resp_data["submissions"][0]["code"] == map_code, \
                    "Latest submission is not the recently added map"
                assert resp_data_all["submissions"][0]["code"] == map_code, \
                    "Latest submission is not the recently added map, when showing all submissions"
            else:
                assert resp_data["submissions"][0]["code"] != map_code, \
                    "Latest submission is still the recently added map"
                assert resp_data_all["submissions"][0]["code"] != map_code, \
                    "Latest submission is still the recently added map, when showing all submissions"
    return function
