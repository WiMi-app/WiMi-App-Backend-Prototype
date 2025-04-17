from app.core.config import settings as base_settings

class TestSettings(type(base_settings)):
    # Extend with test-specific settings
    # Increase token expiration time to 24 hours for tests
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 24 * 60  # 24 hours

test_settings = TestSettings() 