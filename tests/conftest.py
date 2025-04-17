import pytest
from unittest.mock import patch
from app.core.test_config import test_settings

# This will apply to all tests
@pytest.fixture(scope="session", autouse=True)
def use_test_settings():
    """Replace the application settings with test settings during tests."""
    with patch('app.core.security.settings', test_settings), \
         patch('app.api.v1.auth.settings', test_settings):
        yield 