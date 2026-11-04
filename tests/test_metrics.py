import unittest

from monitoring.metrics import (
    cpu_percent,
    network_rates,
    parse_connections,
    parse_listening,
    parse_report,
)
from monitoring.ssh import HostKeyMismatch, Monitor, failure_reason
from tests.fakes import FakeConnection, ScriptedConnector

SAMPLE = """
---LOADAVG---
0.10 0.20 0.30 1/2 3
---STAT1---
cpu  100 0 100 700 100 0 0 0
---STAT2---
cpu  200 0 200 1400 200 0 0 0
---MEM---
MemTotal:       2048 kB
MemFree:         512 kB
MemAvailable:   1024 kB
---NET---
  eth0: 1000 0 0 0 0 0 0 0 5000 0 0 0 0 0 0 0
---LISTEN---
tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=1,fd=3))
tcp LISTEN 0 128 [::1]:631 [::]:* users:(("cupsd",pid=2,fd=4))
---CONN---
tcp ESTAB 0 0 10.0.0.8:22 10.0.0.9:50000
"""

SAMPLE_LATER = SAMPLE.replace(
    "eth0: 1000 0 0 0 0 0 0 0 5000",
    "eth0: 2024 0 0 0 0 0 0 0 7056",
)


class MetricParseTests(unittest.TestCase):
    def test_cpu_percent(self):
        percent = cpu_percent(
            "cpu  100 0 100 700 100 0 0 0",
            "cpu  200 0 200 1400 200 0 0 0",
        )
        self.assertEqual(percent, 20)

    def test_report_sections_and_bad_memory(self):
        report = parse_report(SAMPLE)
        self.assertEqual(report["cpu"]["percent"], "20.0%")
        self.assertEqual(report["cpu"]["load1"], "0.10")
        self.assertEqual(report["cpu"]["load5"], "0.20")
        self.assertEqual(report["cpu"]["load15"], "0.30")
        self.assertEqual(report["memory"]["percent"], "50.0%")
        self.assertEqual(report["listening"][0]["port"], "22")
        self.assertEqual(report["listening"][0]["process"], "sshd")
        self.assertEqual(report["listening"][1]["port"], "631")
        self.assertEqual(report["connections"][0]["state"], "ESTAB")

        broken = SAMPLE.replace("MemTotal:       2048 kB", "not-memory")
        partial = parse_report(broken)
        self.assertIsNone(partial["memory"])
        self.assertEqual(partial["cpu"]["percent"], "20.0%")
        self.assertIsNotNone(partial["listening"])

    def test_network_rates_over_ten_seconds(self):
        first = parse_report(SAMPLE)["net_counters"]
        second = parse_report(SAMPLE_LATER)["net_counters"]
        rows = network_rates(first, second, 10)
        self.assertEqual(rows[0]["name"], "eth0")
        self.assertEqual(rows[0]["inbound"], "0.1 KiB/s")
        self.assertEqual(rows[0]["outbound"], "0.2 KiB/s")

    def test_connection_cap(self):
        lines = [
            f"tcp ESTAB 0 0 10.0.0.8:{port} 10.0.0.9:1" for port in range(150)
        ]
        rows = parse_connections("\n".join(lines))
        self.assertEqual(len(rows), 100)

    def test_listening_parser_skips_short_lines(self):
        self.assertEqual(parse_listening("tcp LISTEN"), [])


class MonitorTests(unittest.TestCase):
    def test_rates_appear_on_the_second_sample(self):
        connector = ScriptedConnector(
            {
                "10.0.0.8": [
                    FakeConnection(output=SAMPLE),
                    FakeConnection(output=SAMPLE_LATER),
                ]
            }
        )
        monitor = Monitor(connector)
        server = {"id": "web", "host": "10.0.0.8"}
        first = monitor.metrics(server, now=0)
        self.assertTrue(first["reachable"])
        self.assertIsNone(first["network"])
        second = monitor.metrics(server, now=10)
        self.assertEqual(second["network"][0]["inbound"], "0.1 KiB/s")

    def test_host_key_change_and_timeout_hide_exception_text(self):
        connector = ScriptedConnector(
            {
                "changed": HostKeyMismatch(),
                "slow": TimeoutError("password super-secret"),
            }
        )
        monitor = Monitor(connector)
        status, reason, key = monitor.probe({"host": "changed"})
        self.assertEqual(status, "unreachable")
        self.assertEqual(reason, "The host key changed.")
        self.assertEqual(key, "")
        _status, timeout_reason, _key = monitor.probe({"host": "slow"})
        self.assertEqual(timeout_reason, "The connection timed out.")
        self.assertNotIn("super-secret", timeout_reason)
        self.assertEqual(failure_reason(TimeoutError("password super-secret")), timeout_reason)

    def test_failed_read_marks_sections_unavailable(self):
        monitor = Monitor(ScriptedConnector({"down": TimeoutError("timed out")}))
        report = monitor.metrics({"id": "down", "host": "down"}, now=5)
        self.assertFalse(report["reachable"])
        self.assertIsNone(report["cpu"])
        self.assertIsNone(report["memory"])
        self.assertIsNone(report["network"])
        self.assertIsNone(report["listening"])
