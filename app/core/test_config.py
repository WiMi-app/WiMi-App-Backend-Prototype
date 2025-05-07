from app.core.config import Settings

class TestSettings(Settings):
    """
    Test-specific settings that extend the base settings.
    Used during test execution for a controlled environment.
    """
    # Set environment to test
    ENVIRONMENT: str = "test"
    DEBUG: bool = True
    
    # Increase token expiration time to 24 hours for tests
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 24 * 60  # 24 hours
    
    # Disable rate limits for tests
    DISABLE_RATE_LIMITS: bool = True
    
    # Use test-specific database settings
    SUPABASE_URL: str = "https://test-instance.supabase.co"
    SUPABASE_KEY: str = "test-key"
    
    # Enable mock auth for tests
    MOCK_AUTH: bool = True
    
    # Disable real moderation in tests
    OPENAI_API_KEY: str = "sk-test-key"
    
    # Static secret key for tests
    SECRET_KEY: str = "test-secret-key-not-for-production"

# Create a test settings instance
test_settings = TestSettings() 