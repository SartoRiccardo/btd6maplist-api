import pytest
import asyncio
import http
from ..mocks import DiscordPermRoles
from ..testutils import to_formdata

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.get
@pytest.mark.completions
async def test_get_lcc(btd6ml_test_client):
    """
    Test if the LCC flag is correctly assigned and if the
    correct run shows up in the map overview
    """
    MAP_CODE = "MLXXXAA"
    LCC_RUNS = [654 + i for i in range(12)] + [1]
    runs_data = [None for _ in range(len(LCC_RUNS))]

    async def get_run_data(i: int):
        async with btd6ml_test_client.get(f"/completions/{LCC_RUNS[i]}") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting a completion returned {resp.status}"
            runs_data[i] = await resp.json()

    await asyncio.gather(*[get_run_data(i) for i in range(len(LCC_RUNS))])
    runs_data = sorted(
        [run for run in runs_data if run["deleted_on"] is None],
        key=lambda x: x["lcc"]["leftover"],
        reverse=True,
    )
    for i, run in enumerate(runs_data):
        if i == 0:
            assert run["current_lcc"], "Run with most LCC leftover is not current LCC"
        else:
            assert not run["current_lcc"], "Run that isn't the current LCC is marked as it"

    async with btd6ml_test_client.get(f"/maps/{MAP_CODE}") as resp:
        resp_data = await resp.json()
        assert resp_data["lccs"][0]["id"] == runs_data[0]["id"], \
            "Map LCC differs from expected"


@pytest.mark.completions
class TestAddLCC:
    """Test adding an LCC correctly reevaluates the lcc flag."""

    @pytest.mark.post
    async def test_add(self, btd6ml_test_client, mock_discord_api, completion_payload, save_image):
        """
        Test adding an LCC with the correct payload, once with a suboptimal LCC and once with an optimal one
        """
        proof_completion = save_image(1)
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        req_comp_data = completion_payload()
        req_form = to_formdata(req_comp_data)
        req_form.add_field("submission_proof", proof_completion.open("rb"))
        async with btd6ml_test_client.post("/maps/MLXXXBB/completions", headers=HEADERS, json=req_comp_data) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Adding a completion with a correct payload returns {resp.status}"
            async with btd6ml_test_client.get(resp.headers["Location"]) as resp_get:
                comp_data = await resp_get.json()
                assert not comp_data["current_lcc"], \
                    "Current LCC is true even if the leftover is lower than others'"

        req_comp_data["lcc"]["leftover"] = 1_000_000_000
        req_form = to_formdata(req_comp_data)
        req_form.add_field("submission_proof", proof_completion.open("rb"))
        async with btd6ml_test_client.post("/maps/MLXXXBB/completions", headers=HEADERS, json=req_comp_data) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Adding a completion with a correct payload returns {resp.status}"
            async with btd6ml_test_client.get(resp.headers["Location"]) as resp_get:
                comp_data = await resp_get.json()
                assert comp_data["current_lcc"], \
                    "Current LCC is false even if the leftover is the highest"

    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_discord_api, completion_payload):
        """Test editing an LCC with a correct payload and seeing the flag update"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        req_comp_data = completion_payload()
        async with btd6ml_test_client.put("/completions/1", headers=HEADERS, json=req_comp_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing completion with a correct payload returns {resp.status}"
            async with btd6ml_test_client.get("/completions/1") as resp_get:
                comp_data = await resp_get.json()
                assert not comp_data["current_lcc"], \
                    "Current LCC is true even if the leftover is lower than others'"

        req_comp_data["lcc"]["leftover"] = 1_000_000_000
        async with btd6ml_test_client.put("/completions/1", headers=HEADERS, json=req_comp_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing completion with a correct payload returns {resp.status}"
            async with btd6ml_test_client.get("/completions/1") as resp_get:
                comp_data = await resp_get.json()
                assert comp_data["current_lcc"], \
                    "Current LCC is false even if the leftover is the highest"

    @pytest.mark.put
    async def test_unset(self, btd6ml_test_client, mock_discord_api, completion_payload):
        """
        Test setting a completion's LCC to null
        """
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        async with btd6ml_test_client.get("/maps/MLXXXCD") as resp:
            lcc_id = (await resp.json())["lccs"][0]["id"]

        req_comp_data = completion_payload()
        req_comp_data["lcc"] = None
        async with btd6ml_test_client.put(f"/completions/{lcc_id}", headers=HEADERS, json=req_comp_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing a completion with null LCC returned {resp.status}"
            async with btd6ml_test_client.get("/maps/MLXXXCD") as resp_map:
                lcc_ids = [lcc["id"] for lcc in (await resp_map.json())["lccs"]]
                assert lcc_id not in lcc_ids, "Old LCC is still in the map's LCCs"

    @pytest.mark.put
    async def test_set(self, btd6ml_test_client, mock_discord_api, completion_payload, assert_state_unchanged):
        """
        Test setting a completion's LCC from null to an LCC, once with a suboptimal LCC and once with an optimal one
        """
        # Both in the map MLXXXEE
        LCC_SUBOPT = 374
        LCC_OPT = 372

        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        async with assert_state_unchanged("/maps/MLXXXEE"):
            req_comp_data = completion_payload()
            req_comp_data["lcc"] = {"leftover": 1}
            async with btd6ml_test_client.put(f"/completions/{LCC_SUBOPT}", headers=HEADERS, json=req_comp_data) as resp:
                assert resp.status == http.HTTPStatus.NO_CONTENT, \
                    f"Editing a completion with a suboptimal LCC returned {resp.status}"

        req_comp_data = completion_payload()
        req_comp_data["lcc"] = {"leftover": 1_000_000_000}
        async with btd6ml_test_client.put(f"/completions/{LCC_OPT}", headers=HEADERS, json=req_comp_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing a completion with an optimal LCC returned {resp.status}"
            async with btd6ml_test_client.get("/maps/MLXXXEE") as resp_map:
                lcc_ids = [lcc["id"] for lcc in (await resp_map.json())["lccs"]]
                assert LCC_OPT in lcc_ids, "Optimal LCC is not in the map's LCCs"



