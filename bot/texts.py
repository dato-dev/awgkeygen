"""Тексты сообщений бота (HTML)."""

from __future__ import annotations

import html

from bot.awg.stats import PeerStats
from bot.database import User, UserStatus

AMNEZIA_DOWNLOAD_URL = "https://amnezia.org/downloads"
AMNEZIAWG_ANDROID_URL = "https://github.com/amnezia-vpn/amneziawg-android/releases"

DOWNLOAD_LINK = f'<a href="{AMNEZIA_DOWNLOAD_URL}">Скачать AmneziaVPN</a>'
AWG_ANDROID_LINK = f'<a href="{AMNEZIAWG_ANDROID_URL}">AmneziaWG для Android</a>'

SEP = "━━━━━━━━━━━━━━━━━━━━"

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


def _cmd(text: str) -> str:
    """Команда в моноширинном блоке — удобно тапнуть и скопировать."""
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<code>{safe}</code>"


def _format_traffic(stats: PeerStats | None) -> str:
    if stats is None:
        return "📊 Трафик: <i>нет данных (ключ не на сервере)</i>"
    if stats.rx_bytes == 0 and stats.tx_bytes == 0:
        online = f"🟢 {stats.latest_handshake}" if stats.online else "⚪️ не подключался"
        return f"📊 Трафик: <i>пока нет</i>\n🕐 Handshake: {online}"
    online = f"🟢 {stats.latest_handshake}" if stats.online else "⚪️ давно"
    return (
        f"📊 <b>Трафик</b>\n"
        f"   ⬇️ {stats.rx_human} · ⬆️ {stats.tx_human}\n"
        f"   📦 Всего: {stats.total_human}\n"
        f"   🕐 {online}"
    )


def user_help(has_key: bool) -> str:
    key_block = (
        "🔑 <b>Ключ</b>\n"
        f"   {_cmd('/config')} — показать ключ\n"
        f"   {_cmd('/remint')} — перечеканить"
        if has_key
        else "🔑 <b>Ключ</b>\n"
        f"   {_cmd('/key')} — получить VPN-ключ"
    )
    return (
        f"📖 <b>Справка</b>\n{SEP}\n\n"
        "🧭 <b>Команды</b>\n"
        f"   {_cmd('/start')} — главное меню\n"
        f"   {_cmd('/status')} — мой статус\n"
        f"   {key_block}\n"
        f"   {_cmd('/help')} — эта справка\n\n"
        "📲 <b>Клиенты</b>\n"
        f"   • {DOWNLOAD_LINK}\n"
        f"   • {AWG_ANDROID_LINK}\n\n"
        "🚀 <b>Подключение</b>\n"
        "   1️⃣ Получите ключ → /key\n"
        f"   2️⃣ Установите {DOWNLOAD_LINK}\n"
        "   3️⃣ Нажмите на ключ ниже — он скопируется, вставьте в AmneziaVPN"
    )


def user_welcome_approved(has_key: bool) -> str:
    if has_key:
        hint = f"🔑 {_cmd('/config')} · 🔄 {_cmd('/remint')}"
    else:
        hint = f"▶️ Нажмите {_cmd('/key')} чтобы получить ключ"
    return (
        f"👋 <b>С возвращением!</b>\n{SEP}\n\n"
        f"Статус: {STATUS_LABELS[UserStatus.APPROVED]}\n\n"
        f"{hint}\n"
        f"📖 {_cmd('/help')}"
    )


def user_welcome_pending() -> str:
    return (
        f"👋 <b>Добро пожаловать!</b>\n{SEP}\n\n"
        "📝 Заявка отправлена администратору.\n"
        "Как только доступ одобрят — придёт уведомление.\n\n"
        f"ℹ️ Проверить статус: {_cmd('/status')}"
    )


def user_welcome_denied(status: UserStatus) -> str:
    return (
        f"👋 <b>Добро пожаловать!</b>\n{SEP}\n\n"
        f"Статус: {STATUS_LABELS[status]}\n\n"
        "Если считаете это ошибкой — напишите администратору."
    )


def user_approved_notification() -> str:
    return (
        f"🎉 <b>Доступ одобрен!</b>\n{SEP}\n\n"
        "Теперь можно получить VPN-ключ.\n\n"
        f"▶️ {_cmd('/key')}\n"
        f"📲 {DOWNLOAD_LINK}\n"
        f"📖 {_cmd('/help')}"
    )


def user_status(user: User) -> str:
    key_icon = "✅ выдан" if user.has_key else "❌ не выдан"
    extra = ""
    if user.status == UserStatus.APPROVED and not user.has_key:
        extra = f"\n\n▶️ {_cmd('/key')}"
    elif user.status == UserStatus.APPROVED and user.has_key:
        extra = f"\n\n{_cmd('/config')} · {_cmd('/remint')}"
    return (
        f"ℹ️ <b>Ваш статус</b>\n{SEP}\n\n"
        f"📌 {STATUS_LABELS[user.status]}\n"
        f"🔑 Ключ: <b>{key_icon}</b>"
        f"{extra}"
    )


def user_key_deleted() -> str:
    return (
        f"🗑 <b>Ключ удалён</b>\n{SEP}\n\n"
        "Ваш VPN-ключ отозван администратором.\n"
        f"Для нового ключа: {_cmd('/key')}"
    )


def vpn_import_hint() -> str:
    return (
        "💡 <b>Как подключить</b>\n"
        f"1. {DOWNLOAD_LINK}\n"
        "2. «Добавить VPN» → вставьте скопированный ключ или файл .vpn"
    )


def key_created(remint: bool, ip: str) -> str:
    if remint:
        title = "🔄 Ключ перечеканен"
        warning = "\n\n⚠️ <b>Старый ключ больше не работает!</b>"
    else:
        title = "🎉 Ключ готов"
        warning = ""
    ip_plain = ip.split("/")[0]
    return (
        f"{title}\n{SEP}\n\n"
        f"📍 IP: <code>{ip_plain}</code>"
        f"{warning}\n\n"
        "📋 Ниже ключ — <b>нажмите на него</b>, чтобы скопировать\n"
        "📄 Также придёт файл <code>.vpn</code> на случай, если удобнее так"
    )


def key_vpn_text(vpn_uri: str) -> str | None:
    """Текстовый ключ в <code> — в Telegram копируется по нажатию."""
    header = (
        "🔑 <b>VPN-ключ</b>\n"
        "👆 Нажмите на текст ниже — он попадёт в буфер обмена\n\n"
    )
    if len(header) + len(vpn_uri) + 17 > 4096:  # 17 ≈ длина <code></code>
        return None
    safe = html.escape(vpn_uri)
    return f"{header}<code>{safe}</code>"


def key_done_footer() -> str:
    return (
        f"✨ <b>Готово!</b>\n\n"
        f"📲 {DOWNLOAD_LINK}\n"
        f"📖 Подробнее: {_cmd('/help')}"
    )


def admin_help() -> str:
    return (
        f"🛠 <b>Панель администратора</b>\n{SEP}\n\n"
        "🚀 <b>Быстрый старт</b>\n"
        f"   {_cmd('/onboard <id>')} — одобрить + выдать ключ\n\n"
        "📋 <b>Заявки</b>\n"
        f"   {_cmd('/pending')}\n"
        f"   {_cmd('/approve <id>')} · {_cmd('/reject <id>')}\n\n"
        "👥 <b>Пользователи</b>\n"
        f"   {_cmd('/users')} · {_cmd('/user <id>')}\n"
        f"   {_cmd('/revoke <id>')}\n\n"
        "🔑 <b>Ключи</b>\n"
        f"   {_cmd('/genkey <id>')} — выдать\n"
        f"   {_cmd('/genkey <id> remint')} — перечеканить\n"
        f"   {_cmd('/delkey <id>')} — удалить с сервера\n"
        f"   {_cmd('/repair <id>')} — починить PSK\n\n"
        "🎁 <b>Автономные ключи</b> (без привязки к боту)\n"
        f"   {_cmd('/keygen <метка>')} — создать ключ для выдачи вручную\n"
        f"   {_cmd('/keys')} — список автономных ключей\n"
        f"   {_cmd('/keydel <метка>')} — удалить автономный ключ\n\n"
        "📊 <b>Трафик</b> (из awg show)\n"
        f"   {_cmd('/traffic')} — все peers\n"
        f"   {_cmd('/traffic <id>')} — по пользователю\n\n"
        "📢 <b>Рассылка</b>\n"
        f"   {_cmd('/notify_all текст')} — всем одобренным\n"
        f"   {_cmd('/notify_user <id> текст')} — одному пользователю\n"
        "   📎 можно прикрепить файл в подпись\n\n"
        f"📦 {_cmd('/version')} — версия и статус бота\n"
        f"ℹ️ {_cmd('/admin')}"
    )


def admin_new_request(user: User) -> str:
    username = f"@{user.username}" if user.username else "—"
    tid = user.telegram_id
    return (
        f"🆕 <b>Новая заявка</b>\n{SEP}\n\n"
        f"👤 <b>{user.display_name}</b>\n"
        f"📎 {username}\n"
        f"🆔 <code>{tid}</code>\n"
        f"📅 {user.created_at[:10]}\n\n"
        f"🚀 Быстро: {_cmd(f'/onboard {tid}')}\n"
        "👇 Или кнопки ниже"
    )


def admin_user_card(user: User, stats: PeerStats | None = None) -> str:
    username = f"@{user.username}" if user.username else "—"
    key = "✅ выдан" if user.has_key else "❌ нет"
    approved = f"\n📅 Одобрен: {user.approved_at[:10]}" if user.approved_at else ""
    tid = user.telegram_id
    traffic = _format_traffic(stats) if user.has_key else ""
    traffic_block = f"\n\n{traffic}" if traffic else ""

    return (
        f"👤 <b>Карточка пользователя</b>\n{SEP}\n\n"
        f"Имя: <b>{user.display_name}</b>\n"
        f"📎 {username}\n"
        f"🆔 <code>{tid}</code>\n"
        f"📌 {STATUS_LABELS[user.status]}\n"
        f"🔑 Ключ: <b>{key}</b>\n"
        f"📅 Регистрация: {user.created_at[:10]}"
        f"{approved}"
        f"{traffic_block}\n\n"
        f"🚀 {_cmd(f'/onboard {tid}')}\n"
        "👇 Кнопки копирования ниже"
    )


def admin_pending_list(users: list[User]) -> str:
    if not users:
        return f"📋 <b>Заявки</b>\n{SEP}\n\n✨ Нет ожидающих заявок."
    lines = [f"📋 <b>Ожидают одобрения</b> ({len(users)})\n{SEP}\n"]
    for u in users:
        uname = f" @{u.username}" if u.username else ""
        lines.append(
            f"⏳ <b>{u.display_name}</b>{uname}\n"
            f"   🆔 <code>{u.telegram_id}</code>\n"
            f"   🚀 {_cmd(f'/onboard {u.telegram_id}')}\n"
            f"   ❌ {_cmd(f'/reject {u.telegram_id}')}\n"
        )
    return "\n".join(lines)


def admin_users_list(users: list[User]) -> str:
    if not users:
        return f"👥 <b>Пользователи</b>\n{SEP}\n\nПусто."
    lines = [f"👥 <b>Все пользователи</b> ({len(users)})\n{SEP}\n"]
    for u in users:
        emoji = STATUS_EMOJI.get(u.status, "❓")
        key = "🔑" if u.has_key else "·"
        uname = ""
        if u.username and u.display_name != f"@{u.username}":
            uname = f" @{u.username}"
        lines.append(
            f"{emoji} {key} <b>{u.display_name}</b>{uname}\n"
            f"      <code>{u.telegram_id}</code>"
        )
    lines.append(f"\n👤 {_cmd('/user <id>')} · 📊 {_cmd('/traffic <id>')}")
    return "\n".join(lines)


def admin_traffic_user(user: User, stats: PeerStats | None) -> str:
    return (
        f"📊 <b>Трафик</b> — {user.display_name}\n{SEP}\n\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"{_format_traffic(stats)}"
    )


def admin_traffic_all(
    users: list[User],
    stats_by_pubkey: dict[str, PeerStats],
    peer_names: dict[str, str],
) -> str:
    lines = [f"📊 <b>Трафик AWG</b>\n{SEP}\n"]
    lines.append("<i>⬇️ с сервера к клиенту · ⬆️ от клиента</i>\n")

    # Сначала бот-пользователи
    shown_pubkeys: set[str] = set()
    for u in users:
        if not u.has_key:
            continue
        name = f"tg_{u.telegram_id}"
        # find stats by matching peer name in config - we pass peer_names pubkey->name
        for pubkey, peer_name in peer_names.items():
            if peer_name == name:
                shown_pubkeys.add(pubkey)
                st = stats_by_pubkey.get(pubkey)
                if st:
                    online = "🟢" if st.online else "⚪️"
                    lines.append(
                        f"\n{online} <b>{u.display_name}</b>\n"
                        f"   ⬇️ {st.rx_human} · ⬆️ {st.tx_human}"
                    )
                break

    # Остальные peers (не из бота)
    other = []
    for pubkey, st in stats_by_pubkey.items():
        if pubkey in shown_pubkeys:
            continue
        pname = peer_names.get(pubkey, pubkey[:12] + "…")
        online = "🟢" if st.online else "⚪️"
        other.append(
            f"{online} <b>{pname}</b>\n"
            f"   ⬇️ {st.rx_human} · ⬆️ {st.tx_human}"
        )
    if other:
        lines.append(f"\n<b>Другие peers</b>\n" + "\n".join(other))

    if len(lines) == 2:
        lines.append("\n<i>Нет данных</i>")

    return "\n".join(lines)


def admin_action_ok(title: str, user: User, *, extra: str = "") -> str:
    return (
        f"{title}\n{SEP}\n\n"
        f"👤 <b>{user.display_name}</b>\n"
        f"🆔 <code>{user.telegram_id}</code>"
        f"{extra}"
    )


def admin_version_info(
    *,
    version: str,
    python_version: str,
    in_docker: bool,
    docker_container: str,
    server_endpoint: str,
    awg_port: int | None,
    database_path: str,
    admins_count: int,
) -> str:
    port = str(awg_port) if awg_port else "из конфига"
    env_label = "🐳 Docker" if in_docker else "🖥 Хост"
    return (
        f"📦 <b>Версия бота</b>\n{SEP}\n\n"
        f"🏷 Версия: <code>{version}</code>\n"
        f"🐍 Python: <code>{python_version}</code>\n"
        f"📍 Среда: {env_label}\n\n"
        f"🐳 AWG-контейнер: <code>{docker_container}</code>\n"
        f"🌐 Endpoint: <code>{server_endpoint}</code> · порт <code>{port}</code>\n"
        f"💾 База: <code>{database_path}</code>\n"
        f"👮 Админов: <b>{admins_count}</b>"
    )


def admin_keygen_help() -> str:
    return (
        f"🎁 <b>Автономный ключ</b>\n{SEP}\n\n"
        "Создаёт VPN-ключ <b>без привязки</b> к Telegram-аккаунту — "
        "для тех, кто не может зайти в бота. Конфиг придёт сюда, "
        "вы передадите его получателю любым удобным способом.\n\n"
        f"   {_cmd('/keygen <метка>')} — например {_cmd('/keygen ivan')}\n"
        f"   {_cmd('/keygen')} — метка сгенерируется автоматически\n\n"
        f"📋 {_cmd('/keys')} — список · 🗑 {_cmd('/keydel <метка>')} — удалить"
    )


def admin_keygen_result(label: str, ip: str) -> str:
    return (
        f"🎁 <b>Автономный ключ создан</b>\n{SEP}\n\n"
        f"🏷 Метка: <code>{html.escape(label)}</code>\n"
        f"📍 IP: <code>{ip}</code>\n\n"
        "📨 Конфиг ниже — перешлите его получателю.\n"
        f"🗑 Удалить: {_cmd(f'/keydel {label}')}"
    )


def admin_keys_list(keys: list[tuple[str, str]]) -> str:
    if not keys:
        return (
            f"🎁 <b>Автономные ключи</b>\n{SEP}\n\n"
            "Пока нет.\n\n"
            f"▶️ Создать: {_cmd('/keygen <метка>')}"
        )
    lines = [f"🎁 <b>Автономные ключи</b> ({len(keys)})\n{SEP}\n"]
    for label, ip in keys:
        safe = html.escape(label)
        lines.append(
            f"🏷 <b>{safe}</b> · <code>{ip}</code>\n"
            f"   🗑 {_cmd(f'/keydel {label}')}\n"
        )
    return "\n".join(lines)


def admin_keydel_result(label: str, ip: str) -> str:
    return (
        f"🗑 <b>Автономный ключ удалён</b>\n{SEP}\n\n"
        f"🏷 Метка: <code>{html.escape(label)}</code>\n"
        f"📍 IP: <code>{ip}</code>"
    )


def admin_notify_user_help() -> str:
    return (
        f"📨 <b>Уведомление пользователю</b>\n{SEP}\n\n"
        f"   {_cmd('/notify_user <id> Текст сообщения')}\n\n"
        "📎 <b>С файлом</b> — прикрепите документ, текст в подписи:\n"
        f"   {_cmd('/notify_user 123456 Список во вложении')}\n\n"
        "↩️ Или ответьте на сообщение с файлом командой с id и текстом."
    )


def admin_notify_user_ok(user: User, *, with_attachment: bool) -> str:
    attach = " · 📎 с вложением" if with_attachment else ""
    return (
        f"📨 <b>Уведомление отправлено</b>{attach}\n{SEP}\n\n"
        f"👤 <b>{user.display_name}</b>\n"
        f"🆔 <code>{user.telegram_id}</code>"
    )


def admin_notify_all_help() -> str:
    return (
        f"📢 <b>Рассылка</b>\n{SEP}\n\n"
        "Отправляет сообщение всем <b>одобренным</b> пользователям.\n\n"
        "💬 <b>Только текст</b>\n"
        f"   {_cmd('/notify_all Наблюдаются проблемы с VPN')}\n\n"
        "📎 <b>С файлом</b>\n"
        "   Прикрепите документ и напишите текст в подписи:\n"
        f"   {_cmd('/notify_all Список адресов во вложении')}\n\n"
        "↩️ <b>Ответ на файл</b>\n"
        f"   Ответьте на сообщение с вложением командой {_cmd('/notify_all текст')}"
    )


def admin_notify_all_result(
    ok: int,
    fail: int,
    total: int,
    *,
    with_attachment: bool,
) -> str:
    attach = " · 📎 с вложением" if with_attachment else ""
    lines = [
        f"📢 <b>Рассылка завершена</b>{attach}\n{SEP}\n",
        f"👥 Всего: <b>{total}</b>",
        f"✅ Доставлено: <b>{ok}</b>",
    ]
    if fail:
        lines.append(f"❌ Не доставлено: <b>{fail}</b>")
        lines.append("\n<i>Часто это пользователи, заблокировавшие бота.</i>")
    return "\n".join(lines)
