from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    egress_app_url: str    
    fe_url: str
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )

settings = Settings()
print(settings.model_config)        # shows config including env_file path
print(settings.model_dump())        # shows all loaded values