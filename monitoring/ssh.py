"""SSH reads for metrics. The session is closed after each read."""

import io
import time

import paramiko

from monitoring.metrics import network_rates, parse_report

CONNECT_TIMEOUT = 5
READ_SCRIPT = """
echo '---LOADAVG---'
cat /proc/loadavg || true
echo '---STAT1---'
head -n 1 /proc/stat || true
sleep 1
echo '---STAT2---'
head -n 1 /proc/stat || true
echo '---MEM---'
cat /proc/meminfo || true
echo '---NET---'
cat /proc/net/dev || true
echo '---LISTEN---'
ss -H -lntup || true
echo '---CONN---'
ss -H -ntu || true
"""


class HostKeyMismatch(Exception):
    """The server presented a different host key than the one we stored."""


class InvalidAuth(Exception):
    """The saved SSH secret cannot be used."""


class RecordingPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(self, expected):
        self.expected = expected or ""
        self.fingerprint = ""

    def missing_host_key(self, client, hostname, key):
        seen = f"{key.get_name()} {key.get_base64()}"
        self.fingerprint = seen
        if self.expected and seen != self.expected:
            raise HostKeyMismatch()


def failure_reason(exc):
    """Short status text. Never include the exception text or secrets."""
    if isinstance(exc, HostKeyMismatch):
        return "The host key changed."
    if isinstance(exc, InvalidAuth):
        return "The saved sign-in is invalid."
    if isinstance(exc, TimeoutError):
        return "The connection timed out."
    if "auth" in exc.__class__.__name__.lower():
        return "Authentication failed."
    return "The host could not be reached."


def _load_private_key(text):
    errors = (paramiko.SSHException, ValueError)
    for loader in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return loader.from_private_key(io.StringIO(text))
        except errors:
            continue
    raise InvalidAuth()


class ParamikoConnection:
    def __init__(self, server):
        self.server = server
        self.client = None
        self.host_key = ""

    def __enter__(self):
        password = self.server.get("password") or ""
        private_key = self.server.get("private_key") or ""
        if bool(password) == bool(private_key):
            raise InvalidAuth()
        policy = RecordingPolicy(self.server.get("host_key") or "")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(policy)
        kwargs = {
            "hostname": self.server["host"],
            "port": int(self.server.get("port") or 22),
            "username": self.server["username"],
            "timeout": CONNECT_TIMEOUT,
            "banner_timeout": CONNECT_TIMEOUT,
            "auth_timeout": CONNECT_TIMEOUT,
            "look_for_keys": False,
            "allow_agent": False,
        }
        if private_key:
            kwargs["pkey"] = _load_private_key(private_key)
        else:
            kwargs["password"] = password
        try:
            client.connect(**kwargs)
        except HostKeyMismatch:
            client.close()
            raise
        except Exception:
            client.close()
            raise
        self.client = client
        self.host_key = policy.fingerprint
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.client is not None:
            self.client.close()
            self.client = None
        return False

    def read_output(self):
        _stdin, stdout, _stderr = self.client.exec_command(READ_SCRIPT, timeout=20)
        return stdout.read().decode("utf-8", errors="replace")


def paramiko_connector(server):
    return ParamikoConnection(server)


def empty_report(reason):
    return {
        "reachable": False,
        "reason": reason,
        "host_key": "",
        "cpu": None,
        "memory": None,
        "network": None,
        "listening": None,
        "connections": None,
    }


class Monitor:
    def __init__(self, connector=None):
        self.connector = connector or paramiko_connector
        self._samples = {}

    def probe(self, server):
        try:
            with self.connector(server) as conn:
                return "up", "", conn.host_key
        except Exception as exc:
            return "unreachable", failure_reason(exc), ""

    def metrics(self, server, now=None):
        moment = time.monotonic() if now is None else now
        try:
            with self.connector(server) as conn:
                parsed = parse_report(conn.read_output())
                host_key = conn.host_key
        except Exception as exc:
            return empty_report(failure_reason(exc))

        network = None
        counters = parsed["net_counters"]
        if counters is not None:
            previous = self._samples.get(server.get("id"))
            self._samples[server.get("id")] = (moment, counters)
            if previous is not None:
                elapsed = moment - previous[0]
                try:
                    network = network_rates(previous[1], counters, elapsed)
                except (ValueError, KeyError, ZeroDivisionError):
                    network = None

        return {
            "reachable": True,
            "reason": "",
            "host_key": host_key,
            "cpu": parsed["cpu"],
            "memory": parsed["memory"],
            "network": network,
            "listening": parsed["listening"],
            "connections": parsed["connections"],
        }
