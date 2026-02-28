from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from telegram import Update
from telegram.ext import ContextTypes

from auth.users.service import UserService
from bot.keyboards import (
    doc_detail_keyboard,
    doc_list_keyboard,
    h,
    mydoc_detail_keyboard,
    mydoc_list_keyboard,
)
from core.documents.schemas import DocumentFilterParams, DocumentSearchRequest
from core.documents.service import DocumentService
from schemas import Error

logger = logging.getLogger(__name__)

_PAGE_SIZE = 5


def _doc_list_text(result, page: int) -> str:
    lines = [
        f"📄 <b>Documents</b> — page {page}/{result.total_pages} ({result.total_rows} total)\n"
    ]
    for doc in result.data:
        lines.append(
            f"• <b>{h(doc.name)}</b>\n"
            f"  {h(doc.category.title)} › {h(doc.subcategory.title)} | {h(doc.stage.title)}\n"
        )
    lines.append("<i>Tap a document name for details.</i>")
    return "\n".join(lines)


def _doc_detail_text(doc) -> str:
    updated = doc.updated_at.strftime("%Y-%m-%d %H:%M") if doc.updated_at else "—"
    tags = ", ".join(h(t.title) for t in doc.tags) if doc.tags else "—"
    desc = h(doc.description) if doc.description else "—"
    return (
        f"📄 <b>{h(doc.name)}</b>\n\n"
        f"<b>Category:</b> {h(doc.category.title)} › {h(doc.subcategory.title)}\n"
        f"<b>Stage:</b> {h(doc.stage.title)}\n"
        f"<b>Assigned to:</b> {h(doc.assigned_user.username)}\n"
        f"<b>Created by:</b> {h(doc.creator.username)}\n"
        f"<b>Tags:</b> {tags}\n"
        f"<b>Description:</b> {desc}\n"
        f"<b>Created:</b> {doc.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"<b>Updated:</b> {updated}\n"
    )


@inject
async def documents(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
    document_svc: DocumentService = Provide["document_service"],
) -> None:
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id

    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if isinstance(user, Error):
        await update.message.reply_text(
            "Please /login first to link your DRMS account."
        )
        return

    result = await document_svc.get_all_documents_paginated(
        filters=DocumentFilterParams(page=1, page_size=_PAGE_SIZE, archive=False),
        current_user=user,
    )

    if isinstance(result, Error):
        await update.message.reply_text(f"Could not fetch documents: {result.detail}")
        return

    if not result.data:
        await update.message.reply_text("You have no active documents.")
        return

    await update.message.reply_text(
        _doc_list_text(result, 1),
        parse_mode="HTML",
        reply_markup=doc_list_keyboard(result.data, 1, result.total_pages),
    )


@inject
async def documents_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
    document_svc: DocumentService = Provide["document_service"],
) -> None:
    query = update.callback_query
    if not query or not update.effective_chat:
        return
    await query.answer()

    chat_id = update.effective_chat.id
    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if isinstance(user, Error):
        await query.edit_message_text("Session expired. Please /login again.")
        return

    data: str = query.data  # type: ignore

    if data.startswith("dd:"):
        _, doc_id, from_page = data.split(":", 2)
        doc = await document_svc.get_document_by_id(UUID(doc_id), user_id=user.id)
        if isinstance(doc, Error):
            await query.edit_message_text(f"Could not load document: {doc.detail}")
            return
        await query.edit_message_text(
            _doc_detail_text(doc),
            parse_mode="HTML",
            reply_markup=doc_detail_keyboard(doc_id, from_page),
        )

    elif data.startswith("dw:"):
        doc_id = data.split(":", 1)[1]
        file_path_result = await document_svc.get_document_file_path(
            UUID(doc_id), user_id=user.id
        )
        if isinstance(file_path_result, Error):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Download failed: {file_path_result.detail}",
            )
            return
        path = Path(file_path_result)
        if not path.exists():
            await context.bot.send_message(
                chat_id=chat_id, text="File not found on disk."
            )
            return
        with path.open("rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=path.name,
            )

    else:
        page = int(data.split(":")[1])
        result = await document_svc.get_all_documents_paginated(
            filters=DocumentFilterParams(
                page=page, page_size=_PAGE_SIZE, archive=False
            ),
            current_user=user,
        )
        if isinstance(result, Error):
            await query.edit_message_text(f"Could not fetch documents: {result.detail}")
            return
        await query.edit_message_text(
            _doc_list_text(result, page),
            parse_mode="HTML",
            reply_markup=doc_list_keyboard(result.data, page, result.total_pages),
        )


@inject
async def search_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
    document_svc: DocumentService = Provide["document_service"],
) -> None:
    if not update.effective_chat or not update.message:
        return
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            "Usage: /search <your message>\n"
            "Example: /search contracts signed last month"
        )
        return

    chat_id = update.effective_chat.id
    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if isinstance(user, Error):
        await update.message.reply_text(
            "Please /login first to link your DRMS account."
        )
        return

    user_id = user.id
    if "documents.search" in [p.code for p in user.role.permissions]:
        user_id = None
    await update.message.reply_text("🔍 Searching…")

    result = await document_svc.search_documents(
        DocumentSearchRequest(message=query),
        user_id=user_id,
    )

    if isinstance(result, Error):
        await update.message.reply_text(f"Search failed: {h(result.detail)}")
        return

    await update.message.reply_text(
        f"🔍 <b>Search results</b>\n\n{h(result.message)}",
        parse_mode="HTML",
    )


def _mydoc_list_text(result, page: int) -> str:
    lines = [
        f"📄 <b>My Documents</b> — page {page}/{result.total_pages} ({result.total_rows} total)\n"
    ]
    for doc in result.data:
        lines.append(
            f"• <b>{h(doc.name)}</b>\n"
            f"  {h(doc.category.title)} › {h(doc.subcategory.title)} | {h(doc.stage.title)}\n"
        )
    lines.append("<i>Tap a document name for details.</i>")
    return "\n".join(lines)


@inject
async def my_documents(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
    document_svc: DocumentService = Provide["document_service"],
) -> None:
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id

    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if isinstance(user, Error):
        await update.message.reply_text(
            "Please /login first to link your DRMS account."
        )
        return

    result = await document_svc.get_all_documents_paginated(
        filters=DocumentFilterParams(
            page=1, page_size=_PAGE_SIZE, archive=False, only_my=True
        ),
        current_user=user,
    )

    if isinstance(result, Error):
        await update.message.reply_text(f"Could not fetch documents: {result.detail}")
        return

    if not result.data:
        await update.message.reply_text("You have no active documents.")
        return

    await update.message.reply_text(
        _mydoc_list_text(result, 1),
        parse_mode="HTML",
        reply_markup=mydoc_list_keyboard(result.data, 1, result.total_pages),
    )


@inject
async def my_documents_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_svc: UserService = Provide["user_service"],
    document_svc: DocumentService = Provide["document_service"],
) -> None:
    query = update.callback_query
    if not query or not update.effective_chat:
        return
    await query.answer()

    chat_id = update.effective_chat.id
    user = await user_svc.get_user_by_telegram_chat_id(chat_id)
    if isinstance(user, Error):
        await query.edit_message_text("Session expired. Please /login again.")
        return

    data: str = query.data  # type: ignore

    if data.startswith("mdd:"):
        _, doc_id, from_page = data.split(":", 2)
        doc = await document_svc.get_document_by_id(UUID(doc_id), user_id=user.id)
        if isinstance(doc, Error):
            await query.edit_message_text(f"Could not load document: {doc.detail}")
            return
        await query.edit_message_text(
            _doc_detail_text(doc),
            parse_mode="HTML",
            reply_markup=mydoc_detail_keyboard(doc_id, from_page),
        )

    elif data.startswith("mdw:"):
        doc_id = data.split(":", 1)[1]
        file_path_result = await document_svc.get_document_file_path(
            UUID(doc_id), user_id=user.id
        )
        if isinstance(file_path_result, Error):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Download failed: {file_path_result.detail}",
            )
            return
        path = Path(file_path_result)
        if not path.exists():
            await context.bot.send_message(
                chat_id=chat_id, text="File not found on disk."
            )
            return
        with path.open("rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=path.name,
            )

    else:
        page = int(data.split(":")[1])
        result = await document_svc.get_all_documents_paginated(
            filters=DocumentFilterParams(
                page=page, page_size=_PAGE_SIZE, archive=False, only_my=True
            ),
            current_user=user,
        )
        if isinstance(result, Error):
            await query.edit_message_text(f"Could not fetch documents: {result.detail}")
            return
        await query.edit_message_text(
            _mydoc_list_text(result, page),
            parse_mode="HTML",
            reply_markup=mydoc_list_keyboard(result.data, page, result.total_pages),
        )
