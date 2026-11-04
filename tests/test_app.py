import tempfile
import unittest
from pathlib import Path

from app import create_app
from tests.fakes import FakeConnection, ScriptedConnector
from tests.test_metrics import SAMPLE


class AppFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "servers.json"
        self.connector = ScriptedConnector({})
        self.app = create_app(
            "secret-value",
            secret_key="test-secret",
            servers_path=self.path,
            connector=self.connector,
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def sign_in(self):
        response = self.client.post(
            "/login",
            data={"username": "admin", "password": "secret-value"},
        )
        self.assertEqual(response.status_code, 302)

    def test_unsigned_pages_redirect_and_sign_out_keeps_the_file(self):
        for path in ("/", "/servers/add", "/servers/abc"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertIn("/login", response.headers["Location"])

        self.sign_in()
        self.client.post(
            "/servers/add",
            data={
                "name": "web",
                "host": "10.0.0.8",
                "port": "22",
                "username": "monitor",
                "password": "ssh-secret",
            },
        )
        self.assertTrue(self.path.exists())
        signed_out = self.client.post("/logout")
        self.assertEqual(signed_out.status_code, 302)
        self.assertIn("/login", signed_out.headers["Location"])
        again = self.client.get("/")
        self.assertEqual(again.status_code, 302)
        self.assertIn('"name": "web"', self.path.read_text(encoding="utf-8"))

    def test_add_remove_and_secret_not_rendered(self):
        self.sign_in()
        rejected = self.client.post(
            "/servers/add",
            data={
                "name": "web",
                "host": "10.0.0.8",
                "username": "monitor",
                "password": "ssh-secret",
                "private_key": "key-material",
            },
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertIn("only one", rejected.get_data(as_text=True))
        self.assertNotIn("ssh-secret", rejected.get_data(as_text=True))
        self.assertNotIn("key-material", rejected.get_data(as_text=True))

        saved = self.client.post(
            "/servers/add",
            data={
                "name": "web",
                "host": "10.0.0.8",
                "username": "monitor",
                "password": "ssh-secret",
            },
            follow_redirects=True,
        )
        body = saved.get_data(as_text=True)
        self.assertIn("web", body)
        self.assertIn("Up", body)
        self.assertNotIn("ssh-secret", body)
        self.assertIn("ssh-ed25519 TESTKEY", self.path.read_text(encoding="utf-8"))

        server_id = self._server_id()
        calls_before = len(self.connector.calls)
        removed = self.client.post(f"/servers/{server_id}/remove", follow_redirects=True)
        self.assertIn("No servers yet.", removed.get_data(as_text=True))
        self.assertEqual(len(self.connector.calls), calls_before)
        reloaded = self.path.read_text(encoding="utf-8")
        self.assertNotIn("web", reloaded)

    def test_unreachable_host_leaves_the_other_server(self):
        self.connector.outcomes["10.0.0.8"] = FakeConnection(output=SAMPLE)
        self.connector.outcomes["10.0.0.9"] = TimeoutError("down")
        self.sign_in()
        self.client.post(
            "/servers/add",
            data={"name": "good", "host": "10.0.0.8", "username": "monitor", "password": "a"},
        )
        self.client.post(
            "/servers/add",
            data={"name": "bad", "host": "10.0.0.9", "username": "monitor", "password": "b"},
        )
        listing = self.client.get("/")
        text = listing.get_data(as_text=True)
        self.assertIn("good", text)
        self.assertIn("bad", text)
        self.assertIn("Unreachable", text)
        self.assertIn("The connection timed out.", text)

        bad_id = self._id_for("bad")
        detail = self.client.get(f"/servers/{bad_id}")
        page = detail.get_data(as_text=True)
        self.assertIn("Unavailable", page)
        self.assertIn('http-equiv="refresh" content="10"', page)
        self.assertNotIn("<textarea", page)
        self.assertNotIn("Kill", page)
        self.assertNotIn('name="command"', page)

        still = self.client.get("/")
        self.assertIn("good", still.get_data(as_text=True))
        self.assertIn("bad", still.get_data(as_text=True))

    def test_detail_shows_metrics_and_has_no_host_controls(self):
        self.connector.outcomes["10.0.0.8"] = [
            FakeConnection(output=SAMPLE),
            FakeConnection(output=SAMPLE),
        ]
        self.sign_in()
        self.client.post(
            "/servers/add",
            data={"name": "web", "host": "10.0.0.8", "username": "monitor", "password": "a"},
        )
        server_id = self._server_id()
        page = self.client.get(f"/servers/{server_id}").get_data(as_text=True)
        self.assertIn("20.0%", page)
        self.assertIn("50.0%", page)
        self.assertIn("sshd", page)
        self.assertIn("10.0.0.9:50000", page)
        self.assertIn("Unavailable", page)
        self.assertNotIn('name="command"', page)

    def test_corrupt_file_shows_error(self):
        self.path.write_text("{", encoding="utf-8")
        self.sign_in()
        page = self.client.get("/")
        self.assertIn("could not be read", page.get_data(as_text=True))
        self.assertIn("No servers yet.", page.get_data(as_text=True))

    def _server_id(self):
        import json

        return json.loads(self.path.read_text(encoding="utf-8"))[0]["id"]

    def _id_for(self, name):
        import json

        servers = json.loads(self.path.read_text(encoding="utf-8"))
        return next(server["id"] for server in servers if server["name"] == name)
