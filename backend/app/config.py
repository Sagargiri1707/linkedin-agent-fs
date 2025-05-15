# app/config.py
# This file loads application settings from environment variables (typically from a .env file).

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache # For caching the settings object

class Settings(BaseSettings):
    """
    Pydantic model for application settings.
    It automatically reads environment variables or from a .env file.
    Field names are case-insensitive when matching environment variables.
    """
    PROJECT_NAME: str = "LinkedIn Automation AI Agent"

    # --- MongoDB Configuration ---
    MONGO_CONNECTION_STRING: str
    MONGO_DATABASE_NAME: str

    # --- External API Keys ---
    PERPLEXITY_API_KEY: str
    DEEPSEEK_API_KEY: str
    IDEOGRAM_API_KEY: str # Assuming this is how Ideogram provides API access

    # --- Twilio Configuration ---
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str # e.g., "whatsapp:+14155238886"
    USER_WHATSAPP_NUMBER: str   # e.g., "whatsapp:+11234567890" (your personal number for testing)

    # --- LinkedIn API Configuration (OAuth 2.0) ---
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    LINKEDIN_REDIRECT_URI: str # e.g., "http://localhost:8000/auth/linkedin/callback"
    LINKEDIN_API_VERSION: str # e.g., "202405"

    # --- Application Settings (Optional) ---
    # DEFAULT_AGENT_USER_ID: str = "default_personal_user" # Example if needed

    # Pydantic settings configuration
    # env_file = ".env": Specifies that settings should be loaded from a .env file.
    # extra = "ignore": Ignores extra fields in the .env file that are not defined in this model.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

@lru_cache
def get_settings() -> Settings:
    """
    Returns the cached Settings instance.
    Using lru_cache ensures that the .env file is read and settings are parsed only once.
    """
    return Settings()

# Create a single instance of settings to be imported by other modules
settings = get_settings()

# You can add a simple check here to see if settings are loaded (optional, for debugging)
# if __name__ == "__main__":
#     print("Settings loaded:")
#     print(f"Project Name: {settings.PROJECT_NAME}")
#     print(f"MongoDB URI: {settings.MONGO_CONNECTION_STRING[:20]}...") # Print partial URI for security
#     print(f"Perplexity Key Loaded: {'Yes' if settings.PERPLEXITY_API_KEY else 'No'}")
#     print(f"LinkedIn Client ID: {settings.LINKEDIN_CLIENT_ID}")
