#!/bin/sh

set -eu

alembic upgrade head
python scripts/create_superuser.py
python scripts/seed_permissions.py
exec gunicorn src.main:app -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:8000 --access-logfile - --error-logfile -
