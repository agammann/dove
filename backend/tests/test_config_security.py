import os

import pytest
from dove.config import Settings


@pytest.mark.skipif(os.name != "posix", reason="Production validation requires Linux")
def test_production_requires_strong_database_password():
    shared = {
        "environment": "production",
        "secret_key": "s" * 48,
        "public_url": "https://dove.example.test",
        "model_adapter": "openai",
        "email_adapter": "resend",
        "openai_api_key": "test-only",
        "resend_api_key": "test-only",
        "resend_webhook_secret": "test-only",
        "_env_file": None,
    }
    weak = Settings(database_url="postgresql+psycopg://dove:short@db/dove", **shared)
    with pytest.raises(RuntimeError, match="database password"):
        weak.validate_deployment()

    strong = Settings(database_url=f"postgresql+psycopg://dove:{'s' * 32}@db/dove", **shared)
    strong.validate_deployment()
