import json
import stat
import tempfile
import unittest
from pathlib import Path

from monitoring.store import load_servers, save_servers, validate_new_server


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "data" / "servers.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_file_is_empty(self):
        servers, error = load_servers(self.path)
        self.assertEqual(servers, [])
        self.assertIsNone(error)

    def test_round_trip_and_file_mode(self):
        save_servers(self.path, [{"id": "1", "name": "web"}])
        mode = stat.S_IMODE(self.path.stat().st_mode)
        self.assertEqual(mode, 0o600)
        servers, error = load_servers(self.path)
        self.assertIsNone(error)
        self.assertEqual(servers[0]["name"], "web")

    def test_invalid_json_is_empty_with_error(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{", encoding="utf-8")
        servers, error = load_servers(self.path)
        self.assertEqual(servers, [])
        self.assertEqual(error, "The server list could not be read.")

    def test_unreadable_file_is_empty_with_error(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("[]", encoding="utf-8")
        self.path.chmod(0)
        try:
            servers, error = load_servers(self.path)
        finally:
            self.path.chmod(0o600)
        self.assertEqual(servers, [])
        self.assertEqual(error, "The server list could not be read.")

    def test_saved_entry_is_present_after_reload(self):
        entry, error = validate_new_server(
            {
                "name": "web",
                "host": "10.0.0.8",
                "port": "",
                "username": "monitor",
                "password": "ssh-secret",
                "private_key": "",
            },
            [],
        )
        self.assertIsNone(error)
        save_servers(self.path, [entry])
        loaded, load_error = load_servers(self.path)
        self.assertIsNone(load_error)
        self.assertEqual(loaded[0]["name"], "web")
        self.assertEqual(loaded[0]["password"], "ssh-secret")
        self.assertEqual(loaded[0]["port"], 22)

    def test_rejects_duplicate_name_and_both_secrets(self):
        existing, _error = validate_new_server(
            {
                "name": "web",
                "host": "10.0.0.8",
                "username": "monitor",
                "password": "one",
            },
            [],
        )
        duplicate, error = validate_new_server(
            {
                "name": "web",
                "host": "10.0.0.9",
                "username": "monitor",
                "password": "two",
            },
            [existing],
        )
        self.assertIsNone(duplicate)
        self.assertIn("already", error)

        both, both_error = validate_new_server(
            {
                "name": "db",
                "host": "10.0.0.9",
                "username": "monitor",
                "password": "two",
                "private_key": "-----BEGIN KEY-----",
            },
            [],
        )
        self.assertIsNone(both)
        self.assertIn("only one", both_error)

        neither, neither_error = validate_new_server(
            {"name": "db", "host": "10.0.0.9", "username": "monitor"},
            [],
        )
        self.assertIsNone(neither)
        self.assertIn("only one", neither_error)

    def test_remove_is_gone_after_reload(self):
        save_servers(
            self.path,
            [
                {"id": "keep", "name": "keep"},
                {"id": "drop", "name": "drop"},
            ],
        )
        servers, _error = load_servers(self.path)
        kept = [server for server in servers if server["id"] != "drop"]
        save_servers(self.path, kept)
        reloaded = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual([server["id"] for server in reloaded], ["keep"])
