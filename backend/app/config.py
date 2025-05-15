from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "LinkedIn Automation AI Agent"

    # MongoDB
    MONGO_CONNECTION_STRING: str
    MONGO_DATABASE_NAME: str

    # External APIs
    PERPLEXITY_API_KEY: str
    DEEPSEEK_API_KEY: str
    IDEOGRAM_API_KEY: str

    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str # e.g., whatsapp:+14155238886
    USER_WHATSAPP_NUMBER: str   # e.g., whatsapp:+11234567890 (your personal number for testing)

    # LinkedIn
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    LINKEDIN_REDIRECT_URI: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache # Cache the settings object for performance
def get_settings():
    return Settings()

settings = get_settings() 