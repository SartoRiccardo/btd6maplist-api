import pytest


@pytest.mark.get
@pytest.mark.completions
async def test_get_lcc():
    """Test the LCC flag is correctly assigned"""
    pytest.skip("Not Implemented")


@pytest.mark.completions
class TestAddLCC:
    """Test adding an LCC correctly reevaluates the lcc flag."""

    @pytest.mark.post
    async def test_add(self, btd6ml_test_client, mock_discord_api):
        """
        Test adding an LCC with the correct payload, once with a suboptimal LCC and once with an optimal one
        """
        pytest.skip("Not Implemented")
    
    @pytest.mark.post
    @pytest.mark.put
    async def test_invalid_fields(self, btd6ml_test_client, mock_discord_api):
        """Test adding and editing an LCC with invalid fields in the payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_discord_api):
        """Test editing an LCC with a correct payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_unset(self, btd6ml_test_client, mock_discord_api):
        """
        Test setting a completion's LCC to null
        """
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_set(self, btd6ml_test_client, mock_discord_api):
        """
        Test setting a completion's LCC from null to an LCC, once with a suboptimal LCC and once with an optimal one
        """
        pytest.skip("Not Implemented")
