from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    docker_container: str
    awg_config_path: str
    server_endpoint: str
    dns_primary: str
    dns_secondary: str
    database_path: Path
    awg_port: int | None = None
    awg_container_type: str = "amnezia-awg2"
    vpn_description: str = "AWG Server"
    awg_mtu: int = 1280


def _parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.append(int(part))
    return ids


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN не задан в .env")

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    if not admin_ids:
        raise ValueError("ADMIN_IDS не задан в .env")

    server_endpoint = os.getenv("SERVER_ENDPOINT", "").strip()
    if not server_endpoint:
        raise ValueError("SERVER_ENDPOINT не задан в .env")

    port_raw = os.getenv("AWG_PORT", "").strip()
    awg_port = int(port_raw) if port_raw else None

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        docker_container=os.getenv("DOCKER_CONTAINER", "amnezia-awg2").strip(),
        awg_config_path=os.getenv("AWG_CONFIG_PATH", "/opt/amnezia/awg/awg0.conf").strip(),
        server_endpoint=server_endpoint,
        dns_primary=os.getenv("DNS_PRIMARY", "1.1.1.1").strip(),
        dns_secondary=os.getenv("DNS_SECONDARY", "1.0.0.1").strip(),
        database_path=Path(os.getenv("DATABASE_PATH", "./data/bot.db")),
        awg_port=awg_port,
        awg_container_type=os.getenv("AWG_CONTAINER_TYPE", "amnezia-awg2").strip(),
        vpn_description=os.getenv("VPN_DESCRIPTION", "AWG Server").strip(),
        awg_mtu=int(os.getenv("AWG_MTU", "1280").strip()),
    )
