from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    egress_app_url: str
    fe_url: str
    secret_key: str
    egress_username: str
    egress_password: str
    num_approvals: int
    disable_auth: bool
    keycloak_url: str
    keycloak_client_id: str
    keycloak_realm: str
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )


settings = Settings()
