"""Validate the confirmation helper without contacting Docker."""

import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).with_name("confirm_postgres18_fresh.py")
spec = importlib.util.spec_from_file_location("dove_fresh_helper", path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ConfirmationTests(unittest.TestCase):
    def run_helper(self, mode, answer, *, existing="[]", host='"unix:///fixture"', extra=None):
        calls = []

        def docker(args, *, env=None, capture=False):
            calls.append((args, env))
            if args[:2] == ["context", "inspect"]:
                return host
            if "ps" in args:
                return existing
            return None

        clean = {"PATH": os.environ.get("PATH", ""), **(extra or {})}
        with patch.dict(os.environ, clean, clear=True), patch.object(helper.sys, "argv", [str(path), mode]), patch.object(helper, "docker", docker), patch("builtins.input", return_value=answer):
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
