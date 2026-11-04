"""Parse read-only Linux metric text. No SSH and no host changes."""

SECTION_MARKERS = ("LOADAVG", "STAT1", "STAT2", "MEM", "NET", "LISTEN", "CONN")


def split_sections(text):
    sections = {}
    current = None
    lines = []
    for line in text.splitlines():
        marker = line.strip()
        if marker.startswith("---") and marker.endswith("---"):
            name = marker.strip("-")
            if current is not None:
                sections[current] = "\n".join(lines)
            current = name if name in SECTION_MARKERS else None
            lines = []
            continue
        if current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines)
    return sections


def _cpu_counters(line):
    parts = line.split()
    if len(parts) < 5 or parts[0] != "cpu":
        raise ValueError("cpu line")
    numbers = [int(part) for part in parts[1:]]
    idle = numbers[3]
    if len(numbers) > 4:
        idle += numbers[4]
    return sum(numbers), idle


def cpu_percent(first_line, second_line):
    total_a, idle_a = _cpu_counters(first_line)
    total_b, idle_b = _cpu_counters(second_line)
    total = total_b - total_a
    idle = idle_b - idle_a
    if total <= 0 or idle < 0 or idle > total:
        raise ValueError("cpu delta")
    return 100 * (total - idle) / total


def parse_loadavg(text):
    parts = text.split()
    if len(parts) < 3:
        raise ValueError("loadavg")
    return [float(parts[0]), float(parts[1]), float(parts[2])]


def parse_meminfo(text):
    values = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        token = raw.strip().split()
        if not token:
            continue
        values[key] = int(token[0])
    total = values["MemTotal"]
    if total <= 0:
        raise ValueError("memory")
    free = values.get("MemAvailable", values.get("MemFree"))
    if free is None or free < 0:
        raise ValueError("memory")
    used = max(total - free, 0)
    return {
        "used_kib": used,
        "free_kib": free,
        "total_kib": total,
        "percent": 100 * used / total,
    }


def parse_net_dev(text):
    counters = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, raw = line.split(":", 1)
        columns = raw.split()
        if len(columns) < 9:
            continue
        counters[name.strip()] = (int(columns[0]), int(columns[8]))
    if not counters:
        raise ValueError("net")
    return counters


def network_rates(previous, current, elapsed):
    """Bytes/sec between two /proc/net/dev samples."""
    if elapsed <= 0:
        raise ValueError("elapsed")
    rows = []
    for name in sorted(current):
        if name not in previous:
            continue
        old_rx, old_tx = previous[name]
        new_rx, new_tx = current[name]
        if new_rx < old_rx or new_tx < old_tx:
            continue
        rows.append(
            {
                "name": name,
                "inbound": _format_rate((new_rx - old_rx) / elapsed),
                "outbound": _format_rate((new_tx - old_tx) / elapsed),
            }
        )
    return rows


def _local_port(address):
    if address.startswith("["):
        host, separator, port = address.rpartition("]:")
        if separator != "]:":
            raise ValueError("address")
        return port
    _host, separator, port = address.rpartition(":")
    if separator != ":":
        raise ValueError("address")
    return port


def _process_name(line):
    marker = '(("'
    start = line.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end = line.find('"', start)
    if end < 0:
        return ""
    return line[start:end]


def parse_listening(text):
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            port = _local_port(parts[4])
        except ValueError:
            continue
        rows.append(
            {
                "protocol": parts[0],
                "port": port,
                "process": _process_name(line),
            }
        )
    return rows


def parse_connections(text, limit=100):
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6 or parts[1] == "LISTEN":
            continue
        rows.append(
            {
                "local": parts[4],
                "remote": parts[5],
                "state": parts[1],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _format_rate(bytes_per_sec):
    return f"{bytes_per_sec / 1024:.1f} KiB/s"


def _format_mib(kib):
    return f"{kib / 1024:.1f} MiB"


def parse_report(text):
    """Build metric sections. A broken section is None and the rest stay."""
    sections = split_sections(text)
    report = {
        "cpu": None,
        "memory": None,
        "net_counters": None,
        "listening": None,
        "connections": None,
    }

    load = None
    percent = None
    try:
        load = parse_loadavg(sections["LOADAVG"])
    except (KeyError, ValueError, IndexError):
        load = None
    try:
        percent = cpu_percent(sections["STAT1"], sections["STAT2"])
    except (KeyError, ValueError, IndexError):
        percent = None
    if load is not None or percent is not None:
        report["cpu"] = {
            "percent": None if percent is None else f"{percent:.1f}%",
            "load1": None if load is None else f"{load[0]:.2f}",
            "load5": None if load is None else f"{load[1]:.2f}",
            "load15": None if load is None else f"{load[2]:.2f}",
        }

    try:
        memory = parse_meminfo(sections["MEM"])
        report["memory"] = {
            "used": _format_mib(memory["used_kib"]),
            "free": _format_mib(memory["free_kib"]),
            "total": _format_mib(memory["total_kib"]),
            "percent": f"{memory['percent']:.1f}%",
        }
    except (KeyError, ValueError, IndexError):
        report["memory"] = None

    try:
        report["net_counters"] = parse_net_dev(sections["NET"])
    except (KeyError, ValueError, IndexError):
        report["net_counters"] = None

    try:
        if "LISTEN" not in sections:
            raise KeyError("LISTEN")
        report["listening"] = parse_listening(sections["LISTEN"])
    except (KeyError, ValueError, IndexError):
        report["listening"] = None

    try:
        if "CONN" not in sections:
            raise KeyError("CONN")
        report["connections"] = parse_connections(sections["CONN"])
    except (KeyError, ValueError, IndexError):
        report["connections"] = None

    return report
