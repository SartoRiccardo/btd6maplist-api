import pytest


@pytest.mark.get
@pytest.mark.users
class TestGetUsers:
    async def test_get_user(self, btd6ml_test_client):
        """Test getting a user by ID"""
        pytest.skip("Not Implemented")

    async def test_invalid_user(self, btd6ml_test_client):
        """Test getting a nonexistent user by ID, or an invalid string as an ID"""
        pytest.skip("Not Implemented")


@pytest.mark.post
@pytest.mark.users
class TestAddUser:
    async def test_add_user(self, btd6ml_test_client, mock_discord_api):
        """Test adding a user with a valid payload"""
        pytest.skip("Not Implemented")

    async def test_add_invalid_user(self, btd6ml_test_client, mock_discord_api):
        """Test adding an invalid user, with duplicate or invalid properties"""
        pytest.skip("Not Implemented")

    async def test_add_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test adding a user, with missing properties"""
        pytest.skip("Not Implemented")

    async def test_fuzz(self, btd6ml_test_client, mock_discord_api):
        """Test setting every field to a different data type, one by one"""
        pytest.skip("Not Implemented")

    async def test_add_unauthorized(self, btd6ml_test_client, mock_discord_api):
        """Test adding a user without having the perms to do so"""
        pytest.skip("Not Implemented")

    async def test_edit_invalid(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile with missing or invalid fields"""
        pytest.skip("Not Implemented")


@pytest.mark.put
@pytest.mark.users
class TestEditSelf:
    async def test_edit(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile"""
        pytest.skip("Not Implemented")

    async def test_edit_other(self, btd6ml_test_client, mock_discord_api):
        """Test editing someone else's profile"""
        pytest.skip("Not Implemented")

    async def test_edit_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile with missing fields"""
        pytest.skip("Not Implemented")

    async def test_fuzz(self, btd6ml_test_client, mock_discord_api):
        """Test setting every field to a different data type, one by one"""
        pytest.skip("Not Implemented")

    async def test_edit_invalid(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own profile with missing or invalid fields"""
        pytest.skip("Not Implemented")
