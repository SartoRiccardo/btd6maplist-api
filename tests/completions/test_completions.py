import pytest


async def get_completion(btd6ml_test_client):
    """Test getting a completion"""
    pytest.skip("Not Implemented")


@pytest.mark.maps
@pytest.mark.post
async def test_add(btd6ml_test_client, mock_discord_api):
    """
    Test that adding a correct completion payload works, and can only be set with the correct perms
    """
    pytest.skip("Not Implemented")


@pytest.mark.completions
class TestValidateCompletions:
    @pytest.mark.post
    @pytest.mark.put
    async def test_invalid_fields(self, btd6ml_test_client, mock_discord_api):
        """Test adding and editing a completion with invalid fields in the payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    @pytest.mark.delete
    async def test_forbidden(self, btd6ml_test_client, mock_discord_api):
        """Test a user adding, editing or deleting a completion if they don't have perms"""
        pytest.skip("Not Implemented")


@pytest.mark.maps
class TestEditCompletion:
    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_discord_api):
        """Test editing a completion with a correct payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_admin_edit_perms(self, btd6ml_test_client, mock_discord_api):
        """Test Maplist Mods editing Expert List completions, and vice versa"""
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test editing a completion with some missing fields"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_edit_own_completion(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own completion, or adding themselves to a completion"""
        pytest.skip("Not Implemented")

    @pytest.mark.delete
    async def test_delete(self, btd6ml_test_client, mock_discord_api):
        """Test editing a completion, more than once"""
        pytest.skip("Not Implemented")
