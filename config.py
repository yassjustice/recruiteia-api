from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    groq_api_key: str = ""
    secret_key: str = "changeme"
    database_url: str = "sqlite:///./data/recruiteia.db"
    upload_dir: str = "data/uploads"
    spacy_model_en: str = "en_core_web_sm"
    spacy_model_fr: str = "fr_core_news_sm"
    access_token_expire_hours: int = 24

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Ensure upload dir exists
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
