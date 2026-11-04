import io
import os
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from app import create_app, main


class AuthTests(unittest.TestCase):
    def test_missing_password_exits(self):
        env = os.environ.copy()
        env.pop("ADMIN_PASSWORD", None)
        with patch.dict(os.environ, env, clear=True):
            with redirect_stderr(io.StringIO()) as stderr:
                with self.assertRaises(SystemExit) as caught:
                    main()
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("ADMIN_PASSWORD is required.", stderr.getvalue())

    def test_empty_password_exits(self):
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "   "}):
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    main()
        self.assertEqual(caught.exception.code, 1)

    def test_main_binds_localhost_only(self):
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "secret", "SECRET_KEY": ""}):
            with patch("app.create_app") as create:
                app = create.return_value
                main()
        create.assert_called_once_with("secret", secret_key=None)
        app.run.assert_called_once_with(host="127.0.0.1", port=5000)

    def test_password_is_stored_as_a_hash(self):
        app = create_app("secret-value", secret_key="test-secret")
        stored = app.config["ADMIN_PASSWORD_HASH"]
        self.assertNotIn("secret-value", stored)
        self.assertTrue(stored.startswith("pbkdf2:sha256:"))
        self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])

    def test_correct_password_signs_in(self):
        app = create_app("secret-value", secret_key="test-secret")
        client = app.test_client()
        response = client.post(
            "/login",
            data={"username": "admin", "password": "secret-value"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        page = client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("No servers yet.", page.get_data(as_text=True))

    def test_wrong_password_stays_on_sign_in(self):
        app = create_app("secret-value", secret_key="test-secret")
        client = app.test_client()
        response = client.post(
            "/login",
            data={"username": "admin", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Sign-in failed.", body)
        self.assertNotIn("wrong-password", body)
        follow = client.get("/")
        self.assertEqual(follow.status_code, 302)
        self.assertIn("/login", follow.headers["Location"])
