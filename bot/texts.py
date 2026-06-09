"""Тексты сообщений бота (HTML)."""

from bot.database import User, UserStatus

AMNEZIA_DOWNLOAD_URL = "https://amnezia.org/downloads"
AMNEZIAWG_ANDROID_URL = "https://github.com/amnezia-vpn/amneziawg-android/releases"

DOWNLOAD_LINK = f'<a href="{AMNEZIA_DOWNLOAD_URL}">Скачать AmneziaVPN</a>'
AWG_ANDROID_LINK = f'<a href="{AMNEZIAWG_ANDROID_URL}">AmneziaWG для Android</a>'

STATUS_LABELS = {
    UserStatus.PENDING: "⏳ Ожидает одобрения",
    UserStatus.APPROVED: "✅ Доступ одобрен",
    UserStatus.REJECTED: "❌ Доступ отклонён",
    UserStatus.REVOKED: "🚫 Доступ отозван",
}

STATUS_EMOJI = {
    UserStatus.PENDING: "⏳",
    UserStatus.APPROVED: "✅",
    UserStatus.REJECTED: "❌",
    UserStatus.REVOKED: "🚫",
}


def user_help(has_key: bool) -> str:
    key_cmds = (
        "/config — показать текущий конфиг\n"
        "/remint — перечеканить ключ"
        if has_key
        else "/key — получить VPN-ключ"
    )
    return (
        "<b>📖 Справка</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — главное меню\n"
        "/status — статус доступа\n"
        f"{key_cmds}\n"
        "/help — эта справка\n\n"
        "<b>📲 Клиенты:</b>\n"
        f"• {DOWNLOAD_LINK} — iOS, Windows, macOS, Linux\n"
        f"• {AWG_ANDROID_LINK} — лёгкий клиент для Android\n\n"
        "<b>Как подключиться:</b>\n"
        "1. Получите ключ командой /key\n"
        f"2. Установите {DOWNLOAD_LINK}\n"
        "3. «Добавить VPN» → вставьте <code>vpn://...</code> или отсканируйте QR"
    )


def user_welcome_approved(has_key: bool) -> str:
    if has_key:
        next_step = "Используйте /config или /remint."
    else:
        next_step = "Получите ключ командой /key."
    return (
        "<b>👋 С возвращением!</b>\n\n"
        f"Статус: {STATUS_LABELS[UserStatus.APPROVED]}\n\n"
        f"{next_step}\n"
        "Справка: /help"
    )


def user_welcome_pending() -> str:
    return (
        "<b>👋 Добро пожаловать!</b>\n\n"
        "Ваша заявка отправлена администратору.\n"
        "Как только доступ будет одобрен — придёт уведомление.\n\n"
        "Проверить статус: /status"
    )


def user_welcome_denied(status: UserStatus) -> str:
    return (
        "<b>👋 Добро пожаловать!</b>\n\n"
        f"Статус: {STATUS_LABELS[status]}\n\n"
        "Если считаете это ошибкой — обратитесь к администратору."
    )


def user_approved_notification() -> str:
    return (
        "<b>🎉 Доступ одобрен!</b>\n\n"
        "Получите ключ в формате <code>vpn://...</code> для AmneziaVPN.\n\n"
        "▶️ /key — получить ключ\n"
        f"📲 {DOWNLOAD_LINK}\n"
        "📖 /help — инструкция"
    )


def user_status(user: User) -> str:
    key_line = "🔑 Ключ: <b>выдан</b>" if user.has_key else "🔑 Ключ: <b>не выдан</b>"
    extra = ""
    if user.status == UserStatus.APPROVED and not user.has_key:
        extra = "\n\nПолучите ключ: /key"
    elif user.status == UserStatus.APPROVED and user.has_key:
        extra = "\n\n/config — конфиг · /remint — перечеканить"
    return (
        "<b>ℹ️ Ваш статус</b>\n\n"
        f"Статус: {STATUS_LABELS[user.status]}\n"
        f"{key_line}"
        f"{extra}"
    )


def vpn_import_hint() -> str:
    return (
        "<b>Как подключить:</b>\n"
        f"1. Установите {DOWNLOAD_LINK}\n"
        "2. «Добавить VPN» → «Вставить из буфера» или сканируйте QR"
    )


def key_created(remint: bool, ip: str) -> str:
    if remint:
        title = "🔄 Ключ перечеканен"
        warning = "\n\n⚠️ <b>Старый ключ больше не работает.</b>"
    else:
        title = "✅ Ключ создан"
        warning = ""
    return (
        f"<b>{title}</b>\n\n"
        f"📍 IP: <code>{ip}</code>"
        f"{warning}\n\n"
        "Формат: <code>vpn://...</code> для AmneziaVPN.\n"
        "Ниже — QR-код и файл ключа."
    )


def key_done_footer() -> str:
    return (
        "<b>Готово!</b>\n\n"
        f"📲 {DOWNLOAD_LINK}\n"
        "📖 Инструкция: /help"
    )


def admin_help() -> str:
    return (
        "<b>🛠 Панель администратора</b>\n\n"
        "<b>Заявки:</b>\n"
        "/pending — ожидают одобрения\n"
        "/approve &lt;id&gt; — одобрить\n"
        "/reject &lt;id&gt; — отклонить\n\n"
        "<b>Пользователи:</b>\n"
        "/users — все пользователи\n"
        "/user &lt;id&gt; — карточка пользователя\n"
        "/revoke &lt;id&gt; — отозвать доступ\n\n"
        "<b>Ключи:</b>\n"
        "/genkey &lt;id&gt; — создать и отправить ключ\n"
        "/genkey &lt;id&gt; remint — перечеканить и отправить\n"
        "/genkey &lt;id&gt; resend — повторно отправить текущий\n"
        "/repair &lt;id&gt; — починить peer на сервере (PSK)\n\n"
        "/admin — эта справка"
    )


def admin_new_request(user: User) -> str:
    username = f"@{user.username}" if user.username else "—"
    return (
        "<b>🆕 Новая заявка</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{user.display_name}</b>\n"
        f"📎 {username}\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"📅 {user.created_at[:10]}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"/approve {user.telegram_id}\n"
        f"/reject {user.telegram_id}"
    )


def admin_user_card(user: User) -> str:
    username = f"@{user.username}" if user.username else "—"
    key = "выдан" if user.has_key else "не выдан"
    approved = f"\n📅 Одобрен: {user.approved_at[:10]}" if user.approved_at else ""
    return (
        "<b>👤 Пользователь</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Имя: <b>{user.display_name}</b>\n"
        f"Username: {username}\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Статус: {STATUS_LABELS[user.status]}\n"
        f"Ключ: <b>{key}</b>\n"
        f"Зарегистрирован: {user.created_at[:10]}"
        f"{approved}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"/approve {user.telegram_id} · /reject {user.telegram_id}\n"
        f"/revoke {user.telegram_id} · /genkey {user.telegram_id}"
    )


def admin_pending_list(users: list[User]) -> str:
    if not users:
        return "<b>📋 Заявки</b>\n\nНет ожидающих заявок."
    lines = ["<b>📋 Ожидают одобрения</b>\n"]
    for u in users:
        uname = f" @{u.username}" if u.username else ""
        lines.append(
            f"⏳ <b>{u.display_name}</b>{uname}\n"
            f"   <code>{u.telegram_id}</code> · {u.created_at[:10]}"
        )
    lines.append("\n/approve &lt;id&gt; · /reject &lt;id&gt; · /user &lt;id&gt;")
    return "\n".join(lines)


def admin_users_list(users: list[User]) -> str:
    if not users:
        return "<b>👥 Пользователи</b>\n\nСписок пуст."
    lines = ["<b>👥 Все пользователи</b>\n"]
    for u in users:
        emoji = STATUS_EMOJI.get(u.status, "❓")
        key = "🔑" if u.has_key else "·"
        lines.append(f"{emoji} {key} <b>{u.display_name}</b> — <code>{u.telegram_id}</code>")
    lines.append("\n/user &lt;id&gt; — подробности")
    return "\n".join(lines)
