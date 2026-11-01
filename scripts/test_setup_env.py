import tempfile
import unittest
from pathlib import Path

from scripts.setup_env import create_env


class SetupEnvTests(unittest.TestCase):
    def test_creates_unique_url_safe_password_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory(prefix="dove-setup-") as directory:
            root = Path(directory)
            (root / ".env.example").write_text("ENVIRONMENT=local\nPOSTGRES_PASSWORD=\n", encoding="utf-8")
            self.assertTrue(create_env(root))
            first = (root / ".env").read_text(encoding="utf-8")
            self.assertRegex(first, r"(?m)^POSTGRES_PASSWORD=[A-Za-z0-9_-]{43}$")
            self.assertFalse(create_env(root))
            self.assertEqual(first, (root / ".env").read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory(prefix="dove-setup-") as directory:
            root = Path(directory)
            (root / ".env.example").write_text("POSTGRES_PASSWORD=\n", encoding="utf-8")
            self.assertTrue(create_env(root))
            second = (root / ".env").read_text(encoding="utf-8")
            self.assertNotEqual(first.split("POSTGRES_PASSWORD=")[1].strip(), second.split("POSTGRES_PASSWORD=")[1].strip())

    def test_refuses_template_without_blank_password(self):
        with tempfile.TemporaryDirectory(prefix="dove-setup-") as directory:
            root = Path(directory)
            (root / ".env.example").write_text("ENVIRONMENT=local\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                create_env(root)
            self.assertFalse((root / ".env").exists())


if __name__ == "__main__":
    unittest.main()
