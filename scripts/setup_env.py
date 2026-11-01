"""Create an ignored local Compose environment with a unique database password."""

import os
import re
import secrets
from pathlib import Path


def create_env(root: Path) -> bool:
    target = root / ".env"
    if target.exists():
        return False

    template = (root / ".env.example").read_text(encoding="utf-8")
    placeholder = r"(?m)^POSTGRES_PASSWORD=$"
    if len(re.findall(placeholder, template)) != 1:
        raise ValueError("Expected one blank POSTGRES_PASSWORD in .env.example")
    content = re.sub(placeholder, f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}", template)

    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(content)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return True


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[1]
    created = create_env(repository)
    print("Created .env with a unique local database password" if created else "Keeping existing .env")
