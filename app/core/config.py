from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "TerraPulse"
    app_version : str = "1.0.0"
    api_v1_str: str = "/api/v1"
    app_secret_key: str
    redis_url: str
    gee_project_id : str 

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()