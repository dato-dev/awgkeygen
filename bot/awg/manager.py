"""Управление ключами AmneziaWG через Docker-контейнер."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

from bot.awg.vpnuri import generate_vpn_uri
from bot.awg.config_parser import (
    ConfigParseError,
    add_peer,
    ensure_peer_psk,
    find_next_ip,
    get_listen_port,
    get_server_public_key,
    parse_config,
    serialize_config,
    update_peer_keys,
)

logger = logging.getLogger(__name__)

PSK_PATH = "/opt/amnezia/awg/wireguard_psk.key"
SERVER_PUBKEY_PATH = "/opt/amnezia/awg/wireguard_server_public_key.key"


class AWGError(Exception):
    pass


@dataclass
class ClientKey:
    name: str
    config_text: str
    ip: str
    vpn_uri: str


class AWGManager:
    def __init__(
        self,
        container: str,
        config_path: str,
        server_endpoint: str,
        dns_primary: str = "1.1.1.1",
        dns_secondary: str = "1.0.0.1",
        awg_port: int | None = None,
        awg_container_type: str = "amnezia-awg2",
        vpn_description: str = "AWG Server",
        awg_mtu: int = 1280,
    ):
        self.container = container
        self.config_path = config_path
        self.server_endpoint = server_endpoint
        self.dns_primary = dns_primary
        self.dns_secondary = dns_secondary
        self.awg_port = awg_port
        self.awg_container_type = awg_container_type
        self.vpn_description = vpn_description
        self.awg_mtu = awg_mtu

    def _exec(self, cmd: str, *, input_data: str | None = None) -> str:
        full_cmd = ["docker", "exec", "-i", self.container, "sh", "-c", cmd]
        try:
            result = subprocess.run(
                full_cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AWGError(f"Таймаут выполнения команды: {cmd}") from exc
        except FileNotFoundError as exc:
            raise AWGError("Docker не найден. Убедитесь, что Docker установлен.") from exc

        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            detail = stderr or stdout or f"exit code {result.returncode}"
            raise AWGError(f"Ошибка в контейнере: {detail}")

        return result.stdout.strip()

    def _read_file(self, path: str) -> str:
        return self._exec(f"cat '{path}'")

    def _write_file(self, path: str, content: str) -> None:
        full_cmd = ["docker", "exec", "-i", self.container, "sh", "-c", f"cat > '{path}'"]
        try:
            result = subprocess.run(
                full_cmd,
                input=content,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AWGError(f"Таймаут записи файла: {path}") from exc

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise AWGError(f"Не удалось записать {path}: {detail}")

    def _genkey(self) -> str:
        return self._exec("awg genkey")

    def _pubkey(self, private_key: str) -> str:
        return self._exec("awg pubkey", input_data=private_key + "\n")

    def _get_psk(self) -> str | None:
        try:
            return self._read_file(PSK_PATH)
        except AWGError:
            return None

    def _get_server_pubkey(self, config_text: str) -> str:
        try:
            config = parse_config(config_text)
            return get_server_public_key(config)
        except ConfigParseError:
            pass

        try:
            return self._read_file(SERVER_PUBKEY_PATH)
        except AWGError as exc:
            raise AWGError("Не удалось получить публичный ключ сервера") from exc

    def _apply_config(self) -> None:
        # Process substitution <(...) не работает в /bin/sh внутри docker exec
        sync_cmd = (
            f"awg-quick strip '{self.config_path}' | awg syncconf awg0 /dev/stdin"
        )
        try:
            self._exec(sync_cmd)
        except AWGError:
            logger.warning("syncconf не сработал, перезапускаю интерфейс")
            self._exec(
                f"awg-quick down '{self.config_path}' 2>/dev/null; "
                f"awg-quick up '{self.config_path}'"
            )

    def _has_psk_file(self) -> bool:
        try:
            self._read_file(PSK_PATH)
            return True
        except AWGError:
            return False

    def _apply_peer_live(self, public_key: str, allowed_ips: str, psk: str | None) -> None:
        """Добавить/обновить peer в работающем интерфейсе."""
        ip = allowed_ips.split("/")[0].split(",")[0].strip()
        cmd = f"awg set awg0 peer {public_key} allowed-ips {ip}/32 persistent-keepalive 25"
        if psk and self._has_psk_file():
            cmd += f" preshared-key '{PSK_PATH}'"
        try:
            self._exec(cmd)
        except AWGError as exc:
            logger.warning("awg set peer не сработал: %s", exc)

    def _render_client_config(
        self,
        private_key: str,
        client_ip: str,
        server_config: dict[str, str],
        server_pubkey: str,
        psk: str | None,
        port: str,
    ) -> str:
        iface_params = [
            "Jc", "Jmin", "Jmax",
            "S1", "S2", "S3", "S4",
            "H1", "H2", "H3", "H4",
            "I1", "I2", "I3", "I4", "I5",
        ]

        lines = [
            "[Interface]",
            f"Address = {client_ip}/32",
            f"DNS = {self.dns_primary}, {self.dns_secondary}",
            f"PrivateKey = {private_key}",
        ]

        for param in iface_params:
            value = server_config.get(param)
            if value:
                lines.append(f"{param} = {value}")

        lines.append("")
        lines.append("[Peer]")
        lines.append(f"PublicKey = {server_pubkey}")
        if psk:
            lines.append(f"PresharedKey = {psk}")
        lines.append("AllowedIPs = 0.0.0.0/0, ::/0")
        lines.append(f"Endpoint = {self.server_endpoint}:{port}")
        lines.append("PersistentKeepalive = 25")

        return "\n".join(lines) + "\n"

    def _build_client_key(
        self,
        name: str,
        private_key: str,
        public_key: str,
        client_ip: str,
        server_config: dict[str, str],
        server_pubkey: str,
        psk: str | None,
        port: str,
    ) -> ClientKey:
        client_config = self._render_client_config(
            private_key, client_ip, server_config, server_pubkey, psk, port
        )
        vpn_uri = generate_vpn_uri(
            private_key=private_key,
            public_key=public_key,
            client_ip=client_ip,
            server_pubkey=server_pubkey,
            psk=psk,
            endpoint=self.server_endpoint,
            port=port,
            awg_params=server_config,
            dns_primary=self.dns_primary,
            dns_secondary=self.dns_secondary,
            container=self.awg_container_type,
            description=self.vpn_description,
            mtu=self.awg_mtu,
        )
        return ClientKey(
            name=name,
            config_text=client_config,
            ip=client_ip,
            vpn_uri=vpn_uri,
        )

    def _client_name(self, telegram_id: int) -> str:
        return f"tg_{telegram_id}"

    def create_key(self, telegram_id: int) -> ClientKey:
        name = self._client_name(telegram_id)
        config_text = self._read_file(self.config_path)
        config = parse_config(config_text)

        if name in config.peers:
            raise AWGError("Ключ уже существует. Используйте перечеканку.")

        private_key = self._genkey()
        public_key = self._pubkey(private_key)
        client_ip = find_next_ip(config)

        psk = self._get_psk()
        add_peer(config, name, public_key, private_key, client_ip, psk=psk)
        self._write_file(self.config_path, serialize_config(config))
        self._apply_config()
        self._apply_peer_live(public_key, client_ip, psk)

        server_pubkey = self._get_server_pubkey(config_text)
        port = str(self.awg_port or get_listen_port(config))

        result = self._build_client_key(
            name, private_key, public_key, client_ip,
            config.interface, server_pubkey, psk, port,
        )
        logger.info("Создан ключ для %s (%s)", name, client_ip)
        return result

    def get_existing_key(self, telegram_id: int) -> ClientKey:
        name = self._client_name(telegram_id)
        config_text = self._read_file(self.config_path)
        config = parse_config(config_text)

        if name not in config.peers:
            raise AWGError("Ключ не найден. Сначала создайте ключ.")

        peer = config.peers[name]
        if not peer.private_key:
            raise AWGError("Приватный ключ клиента не найден в конфиге сервера.")

        server_pubkey = self._get_server_pubkey(config_text)
        psk = self._get_psk()
        port = str(self.awg_port or get_listen_port(config))

        return self._build_client_key(
            name, peer.private_key, peer.public_key, peer.allowed_ips,
            config.interface, server_pubkey, psk, port,
        )

    def remint_key(self, telegram_id: int) -> ClientKey:
        name = self._client_name(telegram_id)
        config_text = self._read_file(self.config_path)
        config = parse_config(config_text)

        if name not in config.peers:
            raise AWGError("Ключ не найден. Сначала создайте ключ.")

        peer = config.peers[name]
        private_key = self._genkey()
        public_key = self._pubkey(private_key)

        old_public_key = peer.public_key
        psk = peer.preshared_key or self._get_psk()
        update_peer_keys(config, name, public_key, private_key)
        if psk:
            ensure_peer_psk(config, name, psk)
        self._write_file(self.config_path, serialize_config(config))
        self._apply_config()
        if old_public_key != public_key:
            try:
                self._exec(f"awg set awg0 peer {old_public_key} remove")
            except AWGError:
                logger.warning("Не удалось удалить старый peer %s", old_public_key)
        self._apply_peer_live(public_key, peer.allowed_ips, psk)

        server_pubkey = self._get_server_pubkey(config_text)
        port = str(self.awg_port or get_listen_port(config))

        result = self._build_client_key(
            name, private_key, public_key, peer.allowed_ips,
            config.interface, server_pubkey, psk, port,
        )
        logger.info("Перечеканен ключ для %s", name)
        return result

    def repair_peer(self, telegram_id: int) -> ClientKey:
        """Починить peer на сервере (добавить PSK, применить конфиг) без смены ключей."""
        name = self._client_name(telegram_id)
        config_text = self._read_file(self.config_path)
        config = parse_config(config_text)

        if name not in config.peers:
            raise AWGError("Ключ не найден на сервере.")

        peer = config.peers[name]
        psk = self._get_psk()
        if psk:
            ensure_peer_psk(config, name, psk)

        self._write_file(self.config_path, serialize_config(config))
        self._apply_config()
        self._apply_peer_live(peer.public_key, peer.allowed_ips, psk)

        server_pubkey = self._get_server_pubkey(config_text)
        port = str(self.awg_port or get_listen_port(config))

        logger.info("Починен peer для %s", name)
        return self._build_client_key(
            name, peer.private_key or "", peer.public_key, peer.allowed_ips,
            config.interface, server_pubkey, psk, port,
        )

    def has_key(self, telegram_id: int) -> bool:
        name = self._client_name(telegram_id)
        try:
            config_text = self._read_file(self.config_path)
            config = parse_config(config_text)
            return name in config.peers
        except (AWGError, ConfigParseError):
            return False

    def check_container(self) -> bool:
        try:
            subprocess.run(
                ["docker", "inspect", self.container],
                capture_output=True,
                check=True,
                timeout=10,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
