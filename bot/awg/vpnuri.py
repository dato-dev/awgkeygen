"""Генерация vpn:// URI для импорта в AmneziaVPN."""

from __future__ import annotations

import base64
import json
import struct
import zlib


def _subnet_from_ip(ip_with_mask: str) -> str:
    ip = ip_with_mask.split("/")[0].split(",")[0].strip()
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
    return ip


def _client_ip_plain(ip_with_mask: str) -> str:
    return ip_with_mask.split("/")[0].split(",")[0].strip()


def _awg_param(params: dict[str, str], key: str, default: str = "") -> str:
    return params.get(key, default) or default


def _render_amnezia_config(
    *,
    client_ip: str,
    private_key: str,
    server_pubkey: str,
    psk: str | None,
    endpoint: str,
    port: str,
    awg_params: dict[str, str],
) -> str:
    """Шаблон config для поля last_config (с плейсхолдерами DNS)."""
    lines = [
        "[Interface]",
        f"Address = {_client_ip_plain(client_ip)}/32",
        "DNS = $PRIMARY_DNS, $SECONDARY_DNS",
        f"PrivateKey = {private_key}",
    ]

    for key in ("Jc", "Jmin", "Jmax", "S1", "S2", "S3", "S4", "H1", "H2", "H3", "H4"):
        value = _awg_param(awg_params, key)
        if value:
            lines.append(f"{key} = {value}")

    for key in ("I1", "I2", "I3", "I4", "I5"):
        value = _awg_param(awg_params, key)
        lines.append(f"{key} = {value}")

    lines.append("")
    lines.append("[Peer]")
    lines.append(f"PublicKey = {server_pubkey}")
    if psk:
        lines.append(f"PresharedKey = {psk}")
    lines.append("AllowedIPs = 0.0.0.0/0, ::/0")
    lines.append(f"Endpoint = {endpoint}:{port}")
    lines.append("PersistentKeepalive = 25")

    return "\n".join(lines) + "\n"


def generate_vpn_uri(
    *,
    private_key: str,
    public_key: str,
    client_ip: str,
    server_pubkey: str,
    psk: str | None,
    endpoint: str,
    port: int | str,
    awg_params: dict[str, str],
    dns_primary: str = "1.1.1.1",
    dns_secondary: str = "1.0.0.1",
    container: str = "amnezia-awg2",
    description: str = "AWG Server",
    mtu: int = 1280,
    persistent_keepalive: int = 25,
) -> str:
    port_int = int(port)
    port_str = str(port_int)
    ip_plain = _client_ip_plain(client_ip)
    subnet = _subnet_from_ip(client_ip)

    config_text = _render_amnezia_config(
        client_ip=client_ip,
        private_key=private_key,
        server_pubkey=server_pubkey,
        psk=psk,
        endpoint=endpoint,
        port=port_str,
        awg_params=awg_params,
    )

    awg_fields = {
        "H1": _awg_param(awg_params, "H1"),
        "H2": _awg_param(awg_params, "H2"),
        "H3": _awg_param(awg_params, "H3"),
        "H4": _awg_param(awg_params, "H4"),
        "I1": _awg_param(awg_params, "I1"),
        "I2": _awg_param(awg_params, "I2"),
        "I3": _awg_param(awg_params, "I3"),
        "I4": _awg_param(awg_params, "I4"),
        "I5": _awg_param(awg_params, "I5"),
        "Jc": _awg_param(awg_params, "Jc"),
        "Jmin": _awg_param(awg_params, "Jmin"),
        "Jmax": _awg_param(awg_params, "Jmax"),
        "S1": _awg_param(awg_params, "S1"),
        "S2": _awg_param(awg_params, "S2"),
        "S3": _awg_param(awg_params, "S3"),
        "S4": _awg_param(awg_params, "S4"),
    }

    last_config = {
        **awg_fields,
        "allowed_ips": ["0.0.0.0/0", "::/0"],
        "clientId": public_key,
        "client_ip": ip_plain,
        "client_priv_key": private_key,
        "client_pub_key": public_key,
        "config": config_text,
        "hostName": endpoint,
        "mtu": str(mtu),
        "persistent_keep_alive": str(persistent_keepalive),
        "port": port_int,
        "psk_key": psk or "",
        "server_pub_key": server_pubkey,
    }

    last_config_str = json.dumps(last_config, indent=4, ensure_ascii=False) + "\n"

    awg_container = {
        **awg_fields,
        "last_config": last_config_str,
        "port": port_str,
        "protocol_version": "2",
        "subnet_address": subnet,
        "transport_proto": "udp",
    }

    outer = {
        "containers": [
            {
                "awg": awg_container,
                "container": container,
            }
        ],
        "defaultContainer": container,
        "description": description,
        "dns1": dns_primary,
        "dns2": dns_secondary,
        "hostName": endpoint,
    }

    outer_bytes = json.dumps(outer, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = struct.pack(">I", len(outer_bytes)) + zlib.compress(outer_bytes)
    b64 = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    return f"vpn://{b64}"
