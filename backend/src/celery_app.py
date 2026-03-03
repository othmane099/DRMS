import os
import sys

from celery import Celery

sys.path.append(f"{os.getcwd()}/src")

from config import settings

celery_app = Celery(
    "drms",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["core.documents.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)