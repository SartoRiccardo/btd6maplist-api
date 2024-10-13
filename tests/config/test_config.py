import pytest


@pytest.mark.get
async def test_get_config(btd6ml_app):
    """Test getting config vars"""
    pytest.skip("Not Implemented")


@pytest.mark.put
async def test_edit_config(btd6ml_app):
    """
    Test editing config variables, and that some variables are correctly
    gated by their required perms (ML Mod, Expert Mod, both or Admin-only)
    """
    pytest.skip("Not Implemented")
    # No admin-only variables as of now
