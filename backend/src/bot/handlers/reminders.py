from __future__ import annotations

import logging
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from telegram import Update
from telegram.ext import ContextTypes

from auth.users.service import UserService
from bot.keyboards import h, rem_back_keyboard, rem_list_keyboard
from core.reminders.service import ReminderService
from schemas import Error

logger = logging.getLogger(__name__)

_PAGE_SIZE = 5


def _rem_list_text(result, page: int) -> str:
    lines = [
        f"🔔 <b>Reminders</b> — page {page}/{result.total_pages} ({result.total_rows} total)\n"
    ]
    for rem in result.data:
        lines.append(
            f"• <b>{h(rem.subject)}</b>\n"
            f"  {h(rem.document.name)} | {rem.date} {rem.time.strftime('%H:%M')}\n"
        )
    lines.append("<i>Tap a reminder for details.</i>")
    return "\n".join(lines)


def _rem_detail_text(rem) -> str:
    updated = rem.updated_at.strftime("%Y-%m-%d %H:%M") if rem.updated_at else "—"
    users = (
        ", ".join(h(u.username) for u in rem.assigned_users)
        if rem.assigned_users
        else "—"
    )
    return (
        f"🔔 <b>{h(rem.subject)}</b>\n\n"
        f"<b>Document:</b> {h(rem.document.name)}\n"
        f"<b>Date:</b> {rem.date} at {rem.time.strftime('%H:%M')}\n"
        f"<b>Message:</b> {h(rem.message)}\n"
        f"<b>Assigned to:</b> {users}\n"
        f"<b>Created by:</b> {h(rem.creator.username)}\n"
        f"<b>Created:</b> {rem.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"<b>Updated:</b> {updated}\n"
    )


@inject
async def reminders(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
    reminder_svc: ReminderService = Provide["reminder_service"],
) -> None:
    assert update.effective_chat and update.message
    chat_id = update.effective_chat.id

    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if isinstance(user, Error):
        await update.message.reply_text(
            "Please /login first to link your DRMS account."
        )
        return

    result = await reminder_svc.get_all_reminders_paginated(
        page=1,
        page_size=_PAGE_SIZE,
        user_id=user.id,
    )

    if isinstance(result, Error):
        await update.message.reply_text(f"Could not fetch reminders: {result.detail}")
        return

    if not result.data:
        await update.message.reply_text("You have no reminders.")
        return

    await update.message.reply_text(
        _rem_list_text(result, 1),
        parse_mode="HTML",
        reply_markup=rem_list_keyboard(result.data, 1, result.total_pages),
    )


@inject
async def reminders_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
    reminder_svc: ReminderService = Provide["reminder_service"],
) -> None:
    query = update.callback_query
    assert query and update.effective_chat
    await query.answer()

    chat_id = update.effective_chat.id
    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if isinstance(user, Error):
        await query.edit_message_text("Session expired. Please /login again.")
        return

    data: str = query.data  # type: ignore

    if data.startswith("rd:"):
        _, rem_id, from_page = data.split(":", 2)
        rem = await reminder_svc.get_reminder_by_id(UUID(rem_id), user_id=user.id)
        if isinstance(rem, Error):
            await query.edit_message_text(f"Could not load reminder: {rem.detail}")
            return
        await query.edit_message_text(
            _rem_detail_text(rem),
            parse_mode="HTML",
            reply_markup=rem_back_keyboard(from_page),
        )
    else:
        page = int(data.split(":")[1])
        result = await reminder_svc.get_all_reminders_paginated(
            page=page,
            page_size=_PAGE_SIZE,
            user_id=user.id,
        )
        if isinstance(result, Error):
            await query.edit_message_text(f"Could not fetch reminders: {result.detail}")
            return
        await query.edit_message_text(
            _rem_list_text(result, page),
            parse_mode="HTML",
            reply_markup=rem_list_keyboard(result.data, page, result.total_pages),
        )
