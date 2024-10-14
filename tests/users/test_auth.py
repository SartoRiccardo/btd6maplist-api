import pytest


@pytest.mark.users
class TestAuth:
    async def test_login(self, btd6ml_test_client, mock_discord_api):
        """Test logging in"""
        pytest.skip("Unauthorized")

    async def test_invalid_token(self, btd6ml_test_client, mock_discord_api):
        """Test using an invalid Discord Token to log in"""
        pytest.skip("Unauthorized")

    async def test_new_user(self, btd6ml_test_client, mock_discord_api):
        """Test logging in as a new user creates a new Maplist account"""
        pytest.skip("Unauthorized")
