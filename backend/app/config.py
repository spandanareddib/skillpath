from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./skillpath.db"
    secret_key: str = "change-me"
    access_token_minutes: int = 60
    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
