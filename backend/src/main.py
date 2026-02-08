import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(f"{os.getcwd()}/src")
from auth.api import router as auth_router
from auth.logged_histories.api import router as logged_histories_router
from auth.permissions.api import router as permissions_router
from auth.roles.api import router as roles_router
from auth.users.api import router as users_router
from config import settings
from configuration.categories.api import router as categories_router
from configuration.stages.api import router as stages_router
from configuration.subcategories.api import router as subcategories_router
from configuration.tags.api import router as tags_router
from containers import Container
from core.dashboard.api import router as dashboard_router
from core.documents.api import router as documents_router
from core.histories.api import router as histories_router
from core.reminders.api import router as reminders_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.is_debug,
)

container = Container()
container.wire(modules=[__name__])

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth_router)
app.include_router(permissions_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(logged_histories_router, prefix="/api/v1")
app.include_router(stages_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(subcategories_router, prefix="/api/v1")
app.include_router(tags_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(reminders_router, prefix="/api/v1")
app.include_router(histories_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
