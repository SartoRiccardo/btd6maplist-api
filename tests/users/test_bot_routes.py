import pytest


@pytest.mark.bot
@pytest.mark.put
class TestBotReadRules:
    async def test_read_rules(self, btd6ml_test_client):
        """Test reding the rules"""
        pytest.skip("Not Implemented")

    async def test_invalid_signature(self, btd6ml_test_client):
        """Test sending an invalid or missing signature"""
        pytest.skip("Not Implemented")


@pytest.mark.bot
class TestBotReadRules:
    @pytest.mark.get
    async def test_get_profile(self, btd6ml_test_client):
        """Test getting a user's profile, with and without loading the OAK"""
        pytest.skip("Not Implemented")

    @pytest.mark.get
    async def test_invalid_signature_get(self, btd6ml_test_client):
        """Test sending an invalid or missing signature"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_edit_profile(self, btd6ml_test_client):
        """Test editing a user's profile"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_invalid_signature_put(self, btd6ml_test_client):
        """Test sending an invalid or missing signature"""
        pytest.skip("Not Implemented")
