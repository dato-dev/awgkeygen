"""Парсер конфигурации AmneziaWG / WireGuard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


AWG_PARAM_KEYS = frozenset({
    "Jc", "Jmin", "Jmax",
    "S1", "S2", "S3", "S4",
    "H1", "H2", "H3", "H4",
    "I1", "I2", "I3", "I4", "I5",
})


class ConfigParseError(Exception):
    pass


@dataclass
class Peer:
    name: str
    public_key: str
    allowed_ips: str
    private_key: str | None = None
    gen_key_time: str | None = None
    preshared_key: str | None = None
    start_line: int = 0
    end_line: int = 0


@dataclass
class ServerConfig:
    lines: list[str] = field(default_factory=list)
    interface: dict[str, str] = field(default_factory=dict)
    peers: dict[str, Peer] = field(default_factory=dict)


def _parse_ip(ip_str: str) -> tuple[list[int], int | None]:
    ip_str = ip_str.split(",")[0].strip()
    mask = None
    if "/" in ip_str:
        ip_part, mask_part = ip_str.split("/", 1)
        mask = int(mask_part)
    else:
        ip_part = ip_str
    parts = [int(x) for x in ip_part.split(".")]
    if len(parts) != 4:
        raise ConfigParseError(f"Некорректный IP: {ip_str}")
    return parts, mask


def _ip_to_str(parts: list[int], mask: int | None = None) -> str:
    base = ".".join(str(x) for x in parts)
    return f"{base}/{mask}" if mask is not None else base


def parse_config(text: str) -> ServerConfig:
    lines = text.splitlines()
    config = ServerConfig(lines=lines)

    current_section: str | None = None
    peer_data: dict[str, str] = {}
    peer_start = 0

    def finalize_peer(end_line: int) -> None:
        if current_section != "peer" or not peer_data:
            return

        name = peer_data.get("Name", peer_data.get("PublicKey", ""))
        if not name:
            raise ConfigParseError("Peer без имени или PublicKey")

        if "PublicKey" not in peer_data:
            raise ConfigParseError(f"Peer '{name}' без PublicKey")
        if "AllowedIPs" not in peer_data:
            raise ConfigParseError(f"Peer '{name}' без AllowedIPs")

        config.peers[name] = Peer(
            name=name,
            public_key=peer_data["PublicKey"],
            allowed_ips=peer_data["AllowedIPs"],
            private_key=peer_data.get("PrivateKey"),
            gen_key_time=peer_data.get("GenKeyTime"),
            preshared_key=peer_data.get("PresharedKey"),
            start_line=peer_start,
            end_line=end_line,
        )

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            finalize_peer(i - 1)
            section = stripped[1:-1].lower()
            if section not in ("interface", "peer"):
                raise ConfigParseError(f"Неизвестная секция: {section}")
            current_section = section
            peer_data = {}
            peer_start = i
            continue

        if not stripped:
            continue

        raw_line = stripped
        if raw_line.startswith("#") and not raw_line.startswith("#_"):
            # Amnezia хранит I1–I5 как комментарии: # I1 = <value>
            comment_body = raw_line[1:].strip()
            if current_section == "interface" and " = " in comment_body:
                ckey, cval = comment_body.split(" = ", 1)
                ckey = ckey.strip()
                if ckey in AWG_PARAM_KEYS and ckey not in config.interface:
                    config.interface[ckey] = cval.strip()
            continue

        if raw_line.startswith("#_"):
            raw_line = raw_line[2:]

        if " = " not in raw_line:
            continue

        key, value = raw_line.split(" = ", 1)
        key = key.strip()
        value = value.strip()

        if current_section == "interface":
            config.interface[key] = value
        elif current_section == "peer":
            peer_data[key] = value

    finalize_peer(len(lines) - 1)

    if not config.interface:
        raise ConfigParseError("Секция [Interface] не найдена")

    return config


def serialize_config(config: ServerConfig) -> str:
    return "\n".join(config.lines) + "\n"


def find_next_ip(config: ServerConfig) -> str:
    used: set[int] = set()

    iface_addr = config.interface.get("Address", "")
    if iface_addr:
        parts, _ = _parse_ip(iface_addr)
        used.add(parts[3])

    for peer in config.peers.values():
        parts, _ = _parse_ip(peer.allowed_ips)
        used.add(parts[3])

    if not iface_addr:
        raise ConfigParseError("Address не задан в [Interface]")

    base_parts, _ = _parse_ip(iface_addr)

    for host_id in range(2, 254):
        if host_id not in used:
            return _ip_to_str([base_parts[0], base_parts[1], base_parts[2], host_id], 32)

    raise ConfigParseError("Свободные IP-адреса закончились")


def add_peer(
    config: ServerConfig,
    name: str,
    public_key: str,
    private_key: str,
    ip: str,
    psk: str | None = None,
) -> None:
    if name in config.peers:
        raise ConfigParseError(f"Клиент '{name}' уже существует")

    now = datetime.now(timezone.utc).isoformat()
    block = [
        "",
        "[Peer]",
        f"#_Name = {name}",
        f"#_GenKeyTime = {now}",
        f"#_PrivateKey = {private_key}",
        f"PublicKey = {public_key}",
    ]
    if psk:
        block.append(f"PresharedKey = {psk}")
    block.append(f"AllowedIPs = {ip}")
    config.lines.extend(block)

    peer = Peer(
        name=name,
        public_key=public_key,
        allowed_ips=ip,
        private_key=private_key,
        preshared_key=psk,
        gen_key_time=now,
        start_line=len(config.lines) - len(block),
        end_line=len(config.lines) - 1,
    )
    config.peers[name] = peer


def update_peer_keys(config: ServerConfig, name: str, public_key: str, private_key: str) -> None:
    if name not in config.peers:
        raise ConfigParseError(f"Клиент '{name}' не найден")

    peer = config.peers[name]
    now = datetime.now(timezone.utc).isoformat()

    for i in range(peer.start_line, peer.end_line + 1):
        line = config.lines[i]
        if line.startswith("#_PrivateKey ="):
            config.lines[i] = f"#_PrivateKey = {private_key}"
        elif line.startswith("PublicKey ="):
            config.lines[i] = f"PublicKey = {public_key}"
        elif line.startswith("#_GenKeyTime ="):
            config.lines[i] = f"#_GenKeyTime = {now}"

    peer.public_key = public_key
    peer.private_key = private_key
    peer.gen_key_time = now


def ensure_peer_psk(config: ServerConfig, name: str, psk: str) -> None:
    """Добавить PresharedKey в peer на сервере, если отсутствует."""
    if name not in config.peers:
        return

    peer = config.peers[name]
    if peer.preshared_key:
        return

    insert_at = peer.end_line
    for i in range(peer.start_line, peer.end_line + 1):
        if config.lines[i].startswith("PublicKey ="):
            insert_at = i + 1
            break

    config.lines.insert(insert_at, f"PresharedKey = {psk}")
    peer.end_line += 1
    peer.preshared_key = psk

    for other in config.peers.values():
        if other.start_line > insert_at:
            other.start_line += 1
            other.end_line += 1


def get_server_public_key(config: ServerConfig) -> str:
    if "PublicKey" in config.interface:
        return config.interface["PublicKey"]
    raise ConfigParseError("PublicKey сервера не найден в конфиге")


def get_listen_port(config: ServerConfig) -> str:
    return config.interface.get("ListenPort", "51820")


def remove_peer(config: ServerConfig, name: str) -> Peer:
    """Удалить peer из конфига. Возвращает удалённый peer."""
    if name not in config.peers:
        raise ConfigParseError(f"Клиент '{name}' не найден")

    peer = config.peers[name]
    min_line, max_line = peer.start_line, peer.end_line
    del config.lines[min_line : max_line + 1]
    del config.peers[name]

    removed = max_line - min_line + 1
    for other in config.peers.values():
        if other.start_line > max_line:
            other.start_line -= removed
            other.end_line -= removed

    return peer
