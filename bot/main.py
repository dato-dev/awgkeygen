import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from bot.awg.manager import AWGManager
from bot.config import Settings, load_settings
from bot.database import Database
from bot.handlers import setup_routers
from bot.middleware import UpdateLoggingMiddleware
from bot.version import runtime_info

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )
    # Меньше шума от aiogram — свои команды логирует bot.updates
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


def _log_startup(settings: Settings) -> None:
    info = runtime_info()
    port = settings.awg_port if settings.awg_port else "auto"
    env = "docker" if info["in_docker"] == "True" else "host"
    logger.info("=" * 56)
    logger.info("AWG Keygen Bot v%s", info["version"])
    logger.info("Python %s · %s", info["python"], env)
    logger.info("AWG container: %s", settings.docker_container)
    logger.info("Server endpoint: %s (port %s)", settings.server_endpoint, port)
    logger.info("Database: %s", settings.database_path)
    logger.info("Admins: %s", settings.admin_ids)
    logger.info("=" * 56)


async def main() -> None:
    setup_logging()
    settings = load_settings()
    _log_startup(settings)

    db = Database(settings.database_path)
    await db.init()
    logger.info("Database initialized")

    awg = AWGManager(
        container=settings.docker_container,
        config_path=settings.awg_config_path,
        server_endpoint=settings.server_endpoint,
        dns_primary=settings.dns_primary,
        dns_secondary=settings.dns_secondary,
        awg_port=settings.awg_port,
        awg_container_type=settings.awg_container_type,
        vpn_description=settings.vpn_description,
        awg_mtu=settings.awg_mtu,
    )

    if not awg.check_container():
        logger.error(
            "Контейнер '%s' не найден. Проверьте DOCKER_CONTAINER в .env",
            settings.docker_container,
        )
        sys.exit(1)
    logger.info("AWG container '%s' is reachable", settings.docker_container)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.middleware(UpdateLoggingMiddleware())

    dp["db"] = db
    dp["awg"] = awg
    dp["admin_ids"] = settings.admin_ids
    dp["settings"] = settings

    dp.include_router(setup_routers())

    await _setup_commands(bot, settings.admin_ids)

    me = await bot.get_me()
    logger.info("Polling started as @%s (id=%s)", me.username, me.id)
    await dp.start_polling(bot)


async def _setup_commands(bot: Bot, admin_ids: list[int]) -> None:
    user_commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Справка и ссылки на клиент"),
        BotCommand(command="status", description="Мой статус"),
        BotCommand(command="key", description="Получить VPN-ключ"),
        BotCommand(command="remint", description="Перечеканить ключ"),
        BotCommand(command="config", description="Показать конфиг"),
    ]
    admin_commands = user_commands + [
        BotCommand(command="admin", description="Панель администратора"),
        BotCommand(command="version", description="Версия бота"),
        BotCommand(command="onboard", description="Одобрить + выдать ключ"),
        BotCommand(command="pending", description="Заявки на доступ"),
        BotCommand(command="users", description="Все пользователи"),
        BotCommand(command="traffic", description="Статистика трафика"),
        BotCommand(command="genkey", description="Выдать ключ"),
        BotCommand(command="delkey", description="Удалить ключ"),
        BotCommand(command="keygen", description="Автономный ключ (вручную)"),
        BotCommand(command="keys", description="Список автономных ключей"),
        BotCommand(command="keydel", description="Удалить автономный ключ"),
        BotCommand(command="repair", description="Починить PSK"),
        BotCommand(command="notify_all", description="Рассылка всем"),
        BotCommand(command="notify_user", description="Уведомление одному"),
        BotCommand(command="user", description="Карточка пользователя"),
    ]

    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception:
            logger.warning("Не удалось установить команды для админа %s", admin_id)


if __name__ == "__main__":
    asyncio.run(main())
