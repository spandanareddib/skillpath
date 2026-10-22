from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./skillpath.db"
    secret_key: str = "change-me"
    access_token_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
