from __future__ import annotations

import logging
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from telegram import Update
from telegram.ext import ContextTypes

from auth.schemas import LoginRequest
from auth.service import AuthService
from auth.users.service import UserService
from schemas import Error

logger = logging.getLogger(__name__)

_WELCOME = (
    "👋 Welcome to *DRMS Bot*!\n\n"
    "Use /login to link your DRMS account. You only need to do this once.\n\n"
    "*Available commands after linking:*\n"
    "/documents — list your recent documents\n"
    "/reminders — list your upcoming reminders\n"
    "/unlink — disconnect your Telegram account"
)


@inject
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
) -> None:
    assert update.effective_chat and update.message
    chat_id = update.effective_chat.id

    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if not isinstance(user, Error):
        await update.message.reply_text(
            f"You are linked as *{user.username}*.\n"
            "Use /unlink to disconnect your Telegram account.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(_WELCOME, parse_mode="Markdown")


@inject
async def login(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    auth_svc: AuthService = Provide["auth_service"],
    user_svc: UserService = Provide["user_service"],
) -> None:
    assert update.effective_chat and update.message
    chat_id = update.effective_chat.id

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/login <username> <password>`", parse_mode="Markdown"
        )
        return

    username, password = context.args[0], context.args[1]

    # Delete the message immediately so the password is not left in chat history.
    try:
        await update.message.delete()
    except Exception:
        pass

    result = await auth_svc.authenticate(
        LoginRequest(username=username, password=password)
    )

    if isinstance(result, Error):
        await context.bot.send_message(
            chat_id=chat_id, text=f"Login failed: {result.detail}"
        )
        return

    link_result = await user_svc.link_telegram(UUID(str(result.user.id)), chat_id)
    if isinstance(link_result, Error):
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Authentication succeeded but linking failed: {link_result.detail}",
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Linked successfully! Welcome, *{result.user.username}*.\nYou won't need to login again.",
        parse_mode="Markdown",
    )


@inject
async def unlink(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
) -> None:
    assert update.effective_chat and update.message
    chat_id = update.effective_chat.id

    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if isinstance(user, Error):
        await update.message.reply_text(
            "Your Telegram account is not linked. Use /login first."
        )
        return

    await user_svc.unlink_telegram(chat_id)
    await update.message.reply_text(
        "Your Telegram account has been unlinked. Use /login to reconnect."
    )
