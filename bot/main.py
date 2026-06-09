import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from bot.awg.manager import AWGManager
from bot.config import load_settings
from bot.database import Database
from bot.handlers import setup_routers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()

    db = Database(settings.database_path)
    await db.init()

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

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp["db"] = db
    dp["awg"] = awg
    dp["admin_ids"] = settings.admin_ids

    dp.include_router(setup_routers())

    await _setup_commands(bot, settings.admin_ids)

    logger.info("Бот запущен. Контейнер: %s", settings.docker_container)
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
        BotCommand(command="pending", description="Заявки на доступ"),
        BotCommand(command="users", description="Все пользователи"),
        BotCommand(command="approve", description="Одобрить: /approve <id>"),
        BotCommand(command="reject", description="Отклонить: /reject <id>"),
        BotCommand(command="revoke", description="Отозвать: /revoke <id>"),
        BotCommand(command="genkey", description="Выдать ключ: /genkey <id>"),
        BotCommand(command="repair", description="Починить peer: /repair <id>"),
        BotCommand(command="user", description="Карточка: /user <id>"),
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
