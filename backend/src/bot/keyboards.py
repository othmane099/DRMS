from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def h(text: str) -> str:
    """HTML-escape dynamic content for safe use in HTML parse_mode messages."""
    return html.escape(str(text))


# ── Documents ──────────────────────────────────────────────────────────────


def doc_list_keyboard(docs, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(doc.name, callback_data=f"dd:{doc.id}:{page}")]
        for doc in docs
    ]
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"d:{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"d:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def doc_detail_keyboard(doc_id: str, from_page: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ Download", callback_data=f"dw:{doc_id}")],
        [InlineKeyboardButton("◀ Back to list", callback_data=f"d:{from_page}")],
    ])


# ── Reminders ──────────────────────────────────────────────────────────────


def rem_list_keyboard(rems, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(rem.subject, callback_data=f"rd:{rem.id}:{page}")]
        for rem in rems
    ]
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"r:{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"r:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def rem_back_keyboard(from_page: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀ Back to list", callback_data=f"r:{from_page}")]]
    )
