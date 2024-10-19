import http
import json
import pytest
from ..mocks import DiscordPermRoles

HEADERS = {
    "Authorization": "Bearer discord_token",
    "Content-Type": "application/json",
}


@pytest.mark.completions
@pytest.mark.put
class TestTransfer:
    async def test_transfer_completions(self, btd6ml_test_client, mock_discord_api):
        """Test transferring a map's completions to another"""
        TEST_CODE_FROM = "DELXXAC"
        TEST_CODE_TO = "MLXXXDF"

        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        old_comp_ids = []
        async with btd6ml_test_client.get(f"/maps/{TEST_CODE_FROM}/completions") as resp:
            assert resp.status == http.HTTPStatus.OK, f"Getting a deleted map's completions returns {resp.status}"
            for comp in (await resp.json())["completions"]:
                old_comp_ids.append(comp["id"])

        async with btd6ml_test_client.put(
                f"/maps/{TEST_CODE_FROM}/completions/transfer",
                headers=HEADERS,
                data=json.dumps({"code": TEST_CODE_TO}),
        ) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Transferring completions properly returns {resp.status}"
            async with btd6ml_test_client.get(f"/maps/{TEST_CODE_FROM}/completions") as resp_get:
                assert (await resp_get.json())["total"] == 0, "Old map still has completions after transferring them"
            async with btd6ml_test_client.get(f"/maps/{TEST_CODE_TO}/completions") as resp_get:
                new_comp_ids = [comp["id"] for comp in (await resp_get.json())["completions"]]
                for old_id in old_comp_ids:
                    assert old_id in new_comp_ids, "Old completion wasn't transferred"

    async def test_transfer_perms(self, btd6ml_test_client, mock_discord_api):
        """Test transferring a map's completions as a Maplist/Expert mod"""
        TEST_CODES_1 = ("DELXXAG", "MLXXXFC")
        TEST_CODES_2 = ("DELXXAJ", "MLXXXEG")

        async def transfer(code_from: str, code_to: str, maplist_first: bool = False):
            mock_discord_api(perms=DiscordPermRoles.MAPLIST_MOD if maplist_first else DiscordPermRoles.EXPLIST_MOD)
            async with btd6ml_test_client.put(
                    f"/maps/{code_from}/completions/transfer",
                    headers=HEADERS,
                    data=json.dumps({"code": code_to}),
            ) as resp:
                assert resp.status == http.HTTPStatus.NO_CONTENT, \
                    f"Transferring completions as a {'Maplist' if maplist_first else 'Experts'} " \
                    f"Moderator returns {resp.status}"
                async with btd6ml_test_client.get(f"/maps/{code_from}/completions") as resp_get:
                    completions = (await resp_get.json())["completions"]
                    format_range = range(51, 101) if maplist_first else range(1, 51)
                    for cmp in completions:
                        assert cmp["format"] in format_range, "Invalid format completion remaining after transfer"

            mock_discord_api(perms=DiscordPermRoles.EXPLIST_MOD if maplist_first else DiscordPermRoles.MAPLIST_MOD)
            async with btd6ml_test_client.put(
                    f"/maps/{code_from}/completions/transfer",
                    headers=HEADERS,
                    data=json.dumps({"code": code_to}),
            ) as resp:
                assert resp.status == http.HTTPStatus.NO_CONTENT, \
                    f"Transferring completions as a {'Experts' if maplist_first else 'Maplist'} " \
                    f"Moderator returns {resp.status}"
                async with btd6ml_test_client.get(f"/maps/{code_from}/completions") as resp_get:
                    assert (await resp_get.json())["total"] == 0, "Old map still has completions after transferring them"

        await transfer(*TEST_CODES_1, maplist_first=True)
        await transfer(*TEST_CODES_2, maplist_first=False)

    async def test_transfer_deleted(self, btd6ml_test_client, mock_discord_api):
        """Test transferring a map's completions to a deleted one or from a non-deleted one"""
        pytest.skip("Not Implemented")

    async def test_transfer_not_exists(self, btd6ml_test_client, mock_discord_api):
        """
        Test transferring a map's completions to
        or from one that doesn't exist
        """
        pytest.skip("Not Implemented")

    async def test_unauthorized(self, btd6ml_test_client, mock_discord_api):
        """Test transferring without the correct perms"""
        pytest.skip("Not Implemented")
