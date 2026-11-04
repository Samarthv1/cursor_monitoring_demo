import json
import os
import uuid
from pathlib import Path

DEFAULT_SERVERS_PATH = Path("data") / "servers.json"


def load_servers(path):
    """Return (servers, error). A missing file is an empty list."""
    file_path = Path(path)
    if not file_path.exists():
        return [], None
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return [], "The server list could not be read."
    if not isinstance(data, list):
        return [], "The server list could not be read."
    return data, None


def save_servers(path, servers):
    """Write the server list so only the current user can read it."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    with os.fdopen(os.open(file_path, flags, 0o600), "w", encoding="utf-8") as handle:
        json.dump(servers, handle)
        handle.write("\n")
    os.chmod(file_path, 0o600)


def public_view(server):
    """Fields safe to render. SSH secrets stay out of the page."""
    return {
        "id": server.get("id", ""),
        "name": server.get("name", ""),
        "host": server.get("host", ""),
        "port": server.get("port", 22),
        "status": server.get("status", "unknown"),
        "status_reason": server.get("status_reason", ""),
    }


def validate_new_server(form, existing):
    """Return (entry, error). Entry is None when the form is rejected."""
    name = (form.get("name") or "").strip()
    host = (form.get("host") or "").strip()
    username = (form.get("username") or "").strip()
    password = (form.get("password") or "").strip()
    private_key = (form.get("private_key") or "").strip()
    raw_port = (form.get("port") or "").strip()

    if not name:
        return None, "Display name is required."
    if any(server.get("name") == name for server in existing):
        return None, "That display name is already in the list."
    if not host or any(char.isspace() for char in host):
        return None, "Host is required."
    if not username or any(char.isspace() for char in username):
        return None, "SSH username is required."
    if raw_port == "":
        port = 22
    else:
        try:
            port = int(raw_port)
        except ValueError:
            return None, "SSH port must be a number from 1 to 65535."
        if port < 1 or port > 65535:
            return None, "SSH port must be a number from 1 to 65535."
    if bool(password) == bool(private_key):
        return None, "Enter a password or a private key, and only one of them."

    entry = {
        "id": uuid.uuid4().hex,
        "name": name,
        "host": host,
        "port": port,
        "username": username,
        "status": "unknown",
        "status_reason": "",
        "host_key": "",
    }
    if password:
        entry["password"] = password
    else:
        entry["private_key"] = private_key
    return entry, None
