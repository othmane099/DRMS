import asyncio
import logging
from datetime import datetime

import pytz
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from celery_app import celery_app
from config import settings
from unit_of_work.uow import UnitOfWorkImpl

logger = logging.getLogger(__name__)

_local_tz = pytz.timezone(settings.LOCAL_TIMEZONE)


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.DATABASE_URL)
    return async_sessionmaker(engine, expire_on_commit=False)


def _local_now() -> datetime:
    """Return current naive datetime in the configured local timezone."""
    return datetime.now(tz=_local_tz).replace(tzinfo=None)


def _reminder_message(reminder) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"🔔 <b>Reminder: {reminder.subject}</b>\n\n"
        f"<b>Document:</b> {reminder.document.name}\n"
        f"<b>Message:</b> {reminder.message}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 View Document", callback_data=f"rdd:{reminder.document_id}")]
    ])
    return text, keyboard


async def _log_pending_reminders(reminder_repository) -> None:
    """Log all unsent reminders and their scheduled times for debugging."""
    pending = await reminder_repository.get_all_reminders()
    unsent = [r for r in pending if r.sent_at is None]

    if not unsent:
        logger.info("[DEBUG] No unsent reminders exist in the database")
        return

    for r in unsent:
        scheduled = datetime.combine(r.date, r.time)
        logger.info(
            "[DEBUG] Unsent reminder: id=%s subject=%r scheduled=%s",
            r.id,
            r.subject,
            scheduled.isoformat(),
        )


@celery_app.task
def dispatch_due_reminders() -> None:
    asyncio.run(_dispatch_due_reminders())


async def _dispatch_due_reminders() -> None:
    now = _local_now()
    logger.info(
        "Reminder dispatch started — local_tz=%s now=%s",
        settings.LOCAL_TIMEZONE,
        now.isoformat(),
    )

    uow = UnitOfWorkImpl(session_factory=_make_session_factory())
    async with uow:
        reminders = await uow.reminder_repository.get_due_reminders(now)

        if not reminders:
            logger.info("No due reminders found for now=%s", now.isoformat())
            await _log_pending_reminders(uow.reminder_repository)
            return

        logger.info("Found %d due reminder(s)", len(reminders))
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        message_cache: dict[str, tuple[str, InlineKeyboardMarkup]] = {}

        for reminder in reminders:
            reminder_id = str(reminder.id)
            scheduled = datetime.combine(reminder.date, reminder.time)
            logger.info(
                "Processing reminder id=%s subject=%r scheduled=%s",
                reminder_id,
                reminder.subject,
                scheduled.isoformat(),
            )
            text, keyboard = message_cache.setdefault(reminder_id, _reminder_message(reminder))

            for user in reminder.assigned_users:
                if not user.telegram_chat_id:
                    logger.info(
                        "Skipping user %s — no telegram_chat_id linked", user.username
                    )
                    continue
                try:
                    await bot.send_message(
                        chat_id=user.telegram_chat_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                    logger.info(
                        "Sent reminder %s to user %s (chat_id=%s)",
                        reminder_id,
                        user.username,
                        user.telegram_chat_id,
                    )
                except TelegramError:
                    logger.exception(
                        "Failed to send reminder %s to user %s",
                        reminder_id,
                        user.username,
                    )

            await uow.reminder_repository.mark_reminder_sent(reminder.id, now)

        await uow.commit()

    logger.info("Reminder dispatch completed")