"""Inline-клавиатуры с кнопками копирования и быстрых действий."""

from __future__ import annotations

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup


def _copy_btn(label: str, text: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, copy_text=CopyTextButton(text=text[:256]))


def admin_new_user_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    tid = str(telegram_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Одобрить + выдать ключ",
                    callback_data=f"onboard:{tid}",
                ),
            ],
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{tid}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{tid}"),
            ],
            [
                _copy_btn("📋 /onboard", f"/onboard {tid}"),
                _copy_btn("❌ /reject", f"/reject {tid}"),
            ],
            [
                _copy_btn("🆔 ID", tid),
            ],
        ],
    )


def admin_user_keyboard(telegram_id: int, *, has_key: bool) -> InlineKeyboardMarkup:
    tid = str(telegram_id)
    rows: list[list[InlineKeyboardButton]] = [
        [
            _copy_btn("📋 /onboard", f"/onboard {tid}"),
            _copy_btn("🔑 /genkey", f"/genkey {tid}"),
        ],
        [
            _copy_btn("👤 /user", f"/user {tid}"),
            _copy_btn("📊 /traffic", f"/traffic {tid}"),
        ],
        [
            _copy_btn("📨 /notify_user", f"/notify_user {tid} "),
        ],
    ]
    if has_key:
        rows.append([
            _copy_btn("🔄 /remint", f"/genkey {tid} remint"),
            _copy_btn("🗑 /delkey", f"/delkey {tid}"),
        ])
        rows.append([
            InlineKeyboardButton(text="🔧 Починить PSK", callback_data=f"repair:{tid}"),
            InlineKeyboardButton(text="🗑 Удалить ключ", callback_data=f"delkey:{tid}"),
        ])
    else:
        rows.append([
            InlineKeyboardButton(text="🔑 Выдать ключ", callback_data=f"genkey:{tid}"),
        ])
    rows.append([
        InlineKeyboardButton(text="🚫 Отозвать доступ", callback_data=f"revoke:{tid}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vpn_copy_keyboard(vpn_uri: str) -> InlineKeyboardMarkup | None:
    """Кнопка копирования vpn:// (если URI ≤ 256 символов)."""
    if len(vpn_uri) > 256:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[_copy_btn("📋 Скопировать vpn://", vpn_uri)]],
    )


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _copy_btn("🎁 /keygen", "/keygen "),
                _copy_btn("📋 /keys", "/keys"),
            ],
            [InlineKeyboardButton(text="📦 Версия", callback_data="admin:version")],
        ],
    )
