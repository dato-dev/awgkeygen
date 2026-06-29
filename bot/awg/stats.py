"""Парсинг статистики из awg show."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PeerStats:
    public_key: str
    allowed_ips: str = ""
    endpoint: str = ""
    latest_handshake: str = ""
    rx_bytes: int = 0
    tx_bytes: int = 0
    online: bool = False

    @property
    def rx_human(self) -> str:
        return _format_bytes(self.rx_bytes)

    @property
    def tx_human(self) -> str:
        return _format_bytes(self.tx_bytes)

    @property
    def total_human(self) -> str:
        return _format_bytes(self.rx_bytes + self.tx_bytes)


def _parse_size(text: str) -> int:
    text = text.strip().lower()
    m = re.match(r"([\d.]+)\s*([kmgt]?i?b)", text)
    if not m:
        return 0
    value = float(m.group(1))
    unit = m.group(2)
    multipliers = {
        "b": 1,
        "kb": 1000,
        "kib": 1024,
        "mb": 1000**2,
        "mib": 1024**2,
        "gb": 1000**3,
        "gib": 1024**3,
        "tb": 1000**4,
        "tib": 1024**4,
    }
    return int(value * multipliers.get(unit, 1))


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KiB"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} MiB"
    return f"{n / 1024**3:.2f} GiB"


def parse_awg_show(output: str) -> dict[str, PeerStats]:
    """Разобрать вывод `awg show awg0`. Ключ словаря — public key peer."""
    peers: dict[str, PeerStats] = {}
    current: PeerStats | None = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith("peer:"):
            pubkey = line.split(":", 1)[1].strip()
            current = PeerStats(public_key=pubkey)
            peers[pubkey] = current
            continue
        if current is None:
            continue

        low = line.lower()
        if low.startswith("allowed ips:"):
            current.allowed_ips = line.split(":", 1)[1].strip()
        elif low.startswith("endpoint:"):
            current.endpoint = line.split(":", 1)[1].strip()
        elif low.startswith("latest handshake:"):
            current.latest_handshake = line.split(":", 1)[1].strip()
            current.online = True
        elif low.startswith("transfer:"):
            rest = line.split(":", 1)[1]
            rx_m = re.search(r"([\d.]+\s*\w+)\s+received", rest, re.I)
            tx_m = re.search(r"([\d.]+\s*\w+)\s+sent", rest, re.I)
            if rx_m:
                current.rx_bytes = _parse_size(rx_m.group(1))
            if tx_m:
                current.tx_bytes = _parse_size(tx_m.group(1))

    return peers
