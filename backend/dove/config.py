from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "local"
    database_url: str = "sqlite:///.data/dove.db"
    storage_dir: Path = Path(".data/objects")
    secret_key: str = "local-only-do-not-deploy-change-this-value"
    public_url: str = "http://127.0.0.1:8000"
    model_adapter: str = "fixture"
    email_adapter: str = "local"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    resend_api_key: str = ""
    resend_webhook_secret: str = ""
    email_from: str = "Dove <dove@example.test>"
    reply_domain: str = "reply.example.test"
    max_upload_bytes: int = 8 * 1024 * 1024
    max_document_pages: int = 50
    max_text_chars: int = 100000
    max_model_calls_per_item: int = 20
    max_model_input_chars: int = 60000
    max_model_output_tokens: int = 4000
    max_messages_per_item: int = 15
    session_hours: int = 12
    pdf_timeout_seconds: float = 15
    max_org_storage_bytes: int = 512 * 1024 * 1024
    max_retained_objects_per_org: int = 1000
    max_document_versions_per_work: int = 100
    max_package_versions_per_work: int = 20
    max_package_bytes: int = 20 * 1024 * 1024

    def validate_deployment(self):
        if self.environment != "local":
            import os

            if os.name != "posix":
                raise RuntimeError(
                    "Production requires Linux container PDF resource limits"
                )
            if len(self.secret_key) < 40 or self.secret_key.startswith("local-"):
                raise RuntimeError(
                    "A random SECRET_KEY of at least 40 characters is required"
                )
            if not self.database_url.startswith(
                "postgresql"
            ) or not self.public_url.startswith("https://"):
                raise RuntimeError("Production requires PostgreSQL and HTTPS")
            if self.model_adapter != "openai" or self.email_adapter != "resend":
                raise RuntimeError("Production cannot use simulated adapters")
            if not all(
                (self.openai_api_key, self.resend_api_key, self.resend_webhook_secret)
            ):
                raise RuntimeError("Production integration configuration is incomplete")


settings = Settings()
