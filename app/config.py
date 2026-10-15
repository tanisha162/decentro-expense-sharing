import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Decentro Expense Sharing Service"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./expense_sharing.db")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
