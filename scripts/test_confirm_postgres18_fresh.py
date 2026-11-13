"""Validate the confirmation helper without contacting Docker."""

import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).with_name("confirm_postgres18_fresh.py")
spec = importlib.util.spec_from_file_location("dove_fresh_helper", path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ConfirmationTests(unittest.TestCase):
    @staticmethod
    def config(mode):
        password = "synthetic-password-0123456789"
        db_env = {"POSTGRES_USER": "dove", "POSTGRES_DB": "dove", "POSTGRES_PASSWORD": password}
        app_env = {"DATABASE_URL": f"postgresql+psycopg://dove:{password}@db/dove", "ENVIRONMENT": "local", "PUBLIC_URL": "http://127.0.0.1:8000", "MODEL_ADAPTER": "fixture", "EMAIL_ADAPTER": "local"}
        if mode == "production":
            app_env.update(ENVIRONMENT="production", PUBLIC_URL="https://fixture.invalid", MODEL_ADAPTER="openai", EMAIL_ADAPTER="resend", SECRET_KEY="s" * 40, OPENAI_API_KEY="synthetic", RESEND_API_KEY="synthetic", RESEND_WEBHOOK_SECRET="synthetic", EMAIL_FROM="fixture@example.invalid", REPLY_DOMAIN="reply.fixture.invalid")
        def volume(source, target, readonly=False):
            return {"type": "volume", "source": source, "target": target, "read_only": readonly}
        return {"volumes": {name: {"name": "dove_" + name} for name in ("postgres", "postgres18", "objects")}, "services": {
            "db": {"image": "postgres:18.4-alpine", "environment": db_env, "volumes": [volume("postgres", "/dove/legacy", True), volume("postgres18", "/var/lib/postgresql"), volume("objects", "/dove/objects")], "ports": [{"host_ip": "127.0.0.1", "published": "54329"}] if mode == "local" else []},
            "api": {"environment": app_env, "volumes": [volume("objects", "/data/objects")], "ports": [{"host_ip": "127.0.0.1", "published": "8000"}] if mode == "local" else []},
            "worker": {"environment": dict(app_env), "volumes": [volume("objects", "/data/objects")]},
            "caddy": {"environment": {"DOVE_DOMAIN": "fixture.invalid"}},
        }}

    def run_helper(self, mode, answer, *, existing="[]", host='"unix:///fixture"', extra=None, resolved=None):
        calls = []

        def docker(args, *, env=None, capture=False):
            calls.append((args, env))
            if args[:2] == ["context", "inspect"]:
                return host
            if "config" in args:
                return json.dumps(resolved or self.config(mode))
            if "ps" in args:
                return existing
            return None

        clean = {"PATH": os.environ.get("PATH", ""), **(extra or {})}
        with patch.dict(os.environ, clean, clear=True), patch.object(helper.sys, "argv", [str(path), mode]), patch.object(helper, "docker", docker), patch.object(helper.Path, "exists", return_value=False), patch("builtins.input", return_value=answer):
            helper.main()
        return calls

    def test_confirmation_and_selectors_fail_closed(self):
        for mode in ("local", "production"):
            with self.assertRaises(SystemExit):
                self.run_helper(mode, "no")
            with self.assertRaises(SystemExit):
                self.run_helper(mode, "NO EXISTING DOVE DATA", existing='{"ID":"existing"}')
        with self.assertRaises(SystemExit):
            self.run_helper("local", "NO EXISTING DOVE DATA", host='"tcp://fixture.invalid:2375"')
        with self.assertRaises(SystemExit):
            self.run_helper("local", "NO EXISTING DOVE DATA", extra={"COMPOSE_FILE": "unexpected"})
        for key in ("POSTGRES_PASSWORD", "DATABASE_URL", "PGHOST", "DOVE_PORT", "ENVIRONMENT", "OPENAI_API_KEY"):
            with self.subTest(key=key), self.assertRaises(SystemExit):
                self.run_helper("local", "NO EXISTING DOVE DATA", extra={key: "synthetic-only"})
        for key in ("DATABASE_URL", "PGPASSWORD", "DOVE_PG18_FRESH_INSTALL"):
            with self.subTest(key=key), self.assertRaises(SystemExit):
                self.run_helper("production", "NO EXISTING DOVE DATA", extra={key: "synthetic-only"})

    def test_dotenv_selector_names_without_reading_values(self):
        for entry in ("COMPOSE_FILE=x", "export DOCKER_HOST=x", "  PGDATA=x", "DATABASE_URL=x", "DOVE_PG18_FRESH_INSTALL=x"):
            self.assertIsNotNone(helper.unsafe_dotenv_selector(entry))
        self.assertIsNone(helper.unsafe_dotenv_selector("# PGDATA=x\nPOSTGRES_PASSWORD=synthetic\nDOVE_DOMAIN=fixture.invalid"))

    def test_production_can_use_intentional_secret_manager_values(self):
        calls = self.run_helper("production", "NO EXISTING DOVE DATA", extra={"POSTGRES_PASSWORD": "synthetic", "DOVE_DOMAIN": "fixture.invalid"})
        self.assertEqual(len([args for args, _ in calls if "up" in args]), 2)

    def test_mismatched_credentials_and_storage_fail_without_disclosure(self):
        cases = []
        mismatch = self.config("local")
        mismatch["services"]["api"]["environment"]["DATABASE_URL"] = "synthetic-sensitive-value"
        cases.append(mismatch)
        wrong_volume = self.config("local")
        wrong_volume["services"]["db"]["volumes"][0]["source"] = "unexpected"
        cases.append(wrong_volume)
        wrong_origin = self.config("local")
        wrong_origin["services"]["api"]["environment"]["PUBLIC_URL"] = "http://fixture.invalid:8000"
        wrong_origin["services"]["worker"]["environment"]["PUBLIC_URL"] = "http://fixture.invalid:8000"
        cases.append(wrong_origin)
        short_password = self.config("local")
        short_password["services"]["db"]["environment"]["POSTGRES_PASSWORD"] = "short"
        for service in ("api", "worker"):
            short_password["services"][service]["environment"]["DATABASE_URL"] = "postgresql+psycopg://dove:short@db/dove"
        cases.append(short_password)
        for config in cases:
            with self.assertRaises(SystemExit) as error:
                self.run_helper("local", "NO EXISTING DOVE DATA", resolved=config)
            self.assertNotIn("synthetic-sensitive-value", str(error.exception))
        production = self.config("production")
        production["services"]["caddy"]["environment"]["DOVE_DOMAIN"] = "other.invalid"
        with self.assertRaises(SystemExit):
            self.run_helper("production", "NO EXISTING DOVE DATA", resolved=production)
        production = self.config("production")
        for service in ("api", "worker"):
            production["services"][service]["environment"]["OPENAI_API_KEY"] = ""
        with self.assertRaises(SystemExit):
            self.run_helper("production", "NO EXISTING DOVE DATA", resolved=production)

    def test_dotenv_selector_stops_before_docker(self):
        with patch.dict(os.environ, {"PATH": os.environ.get("PATH", "")}, clear=True), patch.object(helper.sys, "argv", [str(path), "local"]), patch.object(helper.Path, "exists", return_value=True), patch.object(helper.Path, "read_text", return_value="COMPOSE_FILE=unexpected\nPOSTGRES_PASSWORD=synthetic"), patch.object(helper, "docker") as docker:
            with self.assertRaises(SystemExit):
                helper.main()
            docker.assert_not_called()

    def test_confirmed_commands_select_correct_files_and_modes(self):
        for mode in ("local", "production"):
            calls = self.run_helper(mode, "NO EXISTING DOVE DATA")
            starts = [(args, env) for args, env in calls if "up" in args]
            self.assertEqual(len(starts), 2)
            self.assertIn("compose.postgres18-init.yaml", starts[0][0])
            self.assertNotIn("compose.postgres18-init.yaml", starts[1][0])
            self.assertIn("--force-recreate", starts[1][0])
            self.assertEqual(starts[0][1]["DOVE_PG18_FRESH_INSTALL"], "confirmed-no-existing-dove-data")
            self.assertEqual("compose.production.yaml" in starts[0][0], mode == "production")


if __name__ == "__main__":
    unittest.main()
