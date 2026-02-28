import logging
from pathlib import Path
from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import UUID4

from auth.dependencies import CurrentUser, require_permission
from core.documents.schemas import (
    DocumentChatRequest,
    DocumentChatResponse,
    DocumentCommentCreate,
    DocumentCommentResponse,
    DocumentCreate,
    DocumentFilterParams,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUpdate,
    PaginatedDocumentResponse,
    ShareDocumentCreate,
    ShareDocumentResponse,
    ShareLinkAccessRequest,
    ShareLinkCreate,
    ShareLinkResponse,
    VersionHistoryResponse,
)
from core.documents.service import DocumentService
from core.reminders.schemas import ReminderCreate, ReminderResponse
from core.reminders.service import ReminderService
from schemas import Error, Message

router = APIRouter(tags=["documents"])

logger = logging.getLogger(__name__)


def _get_media_type(file_extension: str) -> str:
    """Determine media type based on file extension."""
    media_types = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt": "text/plain",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    return media_types.get(file_extension, "application/octet-stream")


@router.get(
    "/documents",
    response_model=PaginatedDocumentResponse,
    description="Required permission: documents.list | documents.list_my",
)
@inject
async def get_documents(
    current_user: CurrentUser,
    filters: Annotated[DocumentFilterParams, Depends()],
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> PaginatedDocumentResponse:
    response = await document_service.get_all_documents_paginated(
        filters=filters, current_user=current_user
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/documents",
    response_model=DocumentResponse,
    description="Required permission: documents.create",
)
@inject
async def create_document(
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    category_id: UUID4 = Form(...),
    subcategory_id: UUID4 = Form(...),
    stage_id: UUID4 = Form(...),
    assigned_to: UUID4 = Form(...),
    description: str | None = Form(None),
    tags: str | None = Form(None),  # Comma-separated tags
    document: UploadFile = File(...),
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentResponse:
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else None

    document_create = DocumentCreate(
        name=name,
        category_id=category_id,
        subcategory_id=subcategory_id,
        stage_id=stage_id,
        assigned_to=assigned_to,
        description=description,
        tag_ids=tags_list,
    )

    response = await document_service.create_document(
        document_create=document_create,
        document_file=document,
        current_user=current_user,
        background_tasks=background_tasks,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return DocumentResponse.model_validate(response)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    description="Required permission: documents.view | documents.view_my",
)
@inject
async def get_document(
    current_user: CurrentUser,
    document_id: UUID4,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentResponse:
    response = await document_service.get_document_by_id(
        document_id=document_id, current_user=current_user
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return DocumentResponse.model_validate(response)


@router.delete(
    "/documents/{document_id}",
    response_model=Message,
    description="Required permission: documents.delete | documents.delete_my",
)
@inject
async def delete_document(
    document_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> Message:
    response = await document_service.delete_document(
        document_id=document_id,
        current_user=current_user,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.put(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    description="Required permission: documents.update | documents.update_my",
)
@inject
async def update_document(
    document_id: UUID4,
    current_user: CurrentUser,
    document_update: DocumentUpdate,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentResponse:
    response = await document_service.update_document(
        document_id=document_id,
        document_update=document_update,
        current_user=current_user,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return DocumentResponse.model_validate(response)


@router.patch(
    "/documents/{document_id}/archive",
    response_model=DocumentResponse,
    description="Required permission: documents.archive | documents.archive_my",
)
@inject
async def archive_document(
    document_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentResponse:
    response = await document_service.archive_document(
        document_id=document_id,
        current_user=current_user,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return DocumentResponse.model_validate(response)


@router.get(
    "/documents/{document_id}/download",
    description="Required permission: documents.download | documents.download_my",
)
@inject
async def download_document(
    document_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> FileResponse:
    file_path_response = await document_service.get_document_file_path(
        document_id, current_user=current_user
    )

    if isinstance(file_path_response, Error):
        raise HTTPException(
            status_code=file_path_response.code, detail=file_path_response.detail
        )

    file_path = Path(file_path_response)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")
    return FileResponse(
        path=str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
    )


@router.get(
    "/documents/{document_id}/preview",
    description="Required permission: documents.preview | documents.preview_my",
)
@inject
async def preview_document(
    document_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> FileResponse:
    file_path_response = await document_service.get_document_file_path(
        document_id,
        current_user=current_user,
        full_permission="documents.preview",
        my_permission="documents.preview_my",
    )

    if isinstance(file_path_response, Error):
        raise HTTPException(
            status_code=file_path_response.code, detail=file_path_response.detail
        )

    file_path = Path(file_path_response)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Determine media type based on file extension
    media_type = _get_media_type(file_path.suffix.lower())

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        headers={"Content-Disposition": "inline"},
    )


@router.get(
    "/documents/{document_id}/versions",
    response_model=list[VersionHistoryResponse],
    description="Required permission: documents.view_version | documents.view_version_my",
)
@inject
async def get_version_history(
    document_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> list[VersionHistoryResponse]:
    response = await document_service.get_version_history(
        document_id=document_id, current_user=current_user
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return [VersionHistoryResponse.model_validate(version) for version in response]


@router.post(
    "/documents/{document_id}/versions/me",
    response_model=VersionHistoryResponse,
    dependencies=[Depends(require_permission("documents.create_version_my"))],
    description="Required permission: documents.create_version_my",
)
@inject
async def create_my_new_version(
    document_id: UUID4,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    document: UploadFile = File(...),
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> VersionHistoryResponse:
    response = await document_service.create_new_version(
        document_id=document_id,
        document_file=document,
        current_user_id=current_user.id,
        user_id=current_user.id,
        background_tasks=background_tasks,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return VersionHistoryResponse.model_validate(response)


@router.post(
    "/documents/{document_id}/versions",
    response_model=VersionHistoryResponse,
    dependencies=[Depends(require_permission("documents.create_version"))],
    description="Required permission: documents.create_version",
)
@inject
async def create_new_version(
    document_id: UUID4,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    document: UploadFile = File(...),
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> VersionHistoryResponse:
    response = await document_service.create_new_version(
        document_id=document_id,
        document_file=document,
        current_user_id=current_user.id,
        background_tasks=background_tasks,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return VersionHistoryResponse.model_validate(response)


@router.get(
    "/documents/{document_id}/versions/{version_id}/download/me",
    dependencies=[Depends(require_permission("documents.download_version_my"))],
    description="Required permission: documents.download_version_my",
)
@inject
async def download_my_document_version(
    document_id: UUID4,
    version_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> FileResponse:
    file_path_response = await document_service.get_version_file_path(
        document_id, version_id, user_id=current_user.id
    )

    if isinstance(file_path_response, Error):
        raise HTTPException(
            status_code=file_path_response.code, detail=file_path_response.detail
        )

    file_path = Path(file_path_response)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
    )


@router.get(
    "/documents/{document_id}/versions/{version_id}/download",
    dependencies=[Depends(require_permission("documents.download_version"))],
    description="Required permission: documents.download_version",
)
@inject
async def download_document_version(
    document_id: UUID4,
    version_id: UUID4,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> FileResponse:
    file_path_response = await document_service.get_version_file_path(
        document_id, version_id
    )

    if isinstance(file_path_response, Error):
        raise HTTPException(
            status_code=file_path_response.code, detail=file_path_response.detail
        )

    file_path = Path(file_path_response)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
    )


@router.get(
    "/documents/{document_id}/versions/{version_id}/preview/me",
    dependencies=[Depends(require_permission("documents.preview_version_my"))],
    description="Required permission: documents.preview_version_my",
)
@inject
async def preview_my_document_version(
    document_id: UUID4,
    version_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> FileResponse:
    file_path_response = await document_service.get_version_file_path(
        document_id, version_id, user_id=current_user.id
    )

    if isinstance(file_path_response, Error):
        raise HTTPException(
            status_code=file_path_response.code, detail=file_path_response.detail
        )

    file_path = Path(file_path_response)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Determine media type based on file extension
    media_type = _get_media_type(file_path.suffix.lower())

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        headers={"Content-Disposition": "inline"},
    )


@router.get(
    "/documents/{document_id}/versions/{version_id}/preview",
    dependencies=[Depends(require_permission("documents.preview_version"))],
    description="Required permission: documents.preview_version",
)
@inject
async def preview_document_version(
    document_id: UUID4,
    version_id: UUID4,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> FileResponse:
    file_path_response = await document_service.get_version_file_path(
        document_id, version_id
    )

    if isinstance(file_path_response, Error):
        raise HTTPException(
            status_code=file_path_response.code, detail=file_path_response.detail
        )

    file_path = Path(file_path_response)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Determine media type based on file extension
    media_type = _get_media_type(file_path.suffix.lower())

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        headers={"Content-Disposition": "inline"},
    )


@router.get(
    "/documents/{document_id}/comments/me",
    response_model=list[DocumentCommentResponse],
    dependencies=[Depends(require_permission("comments.list_my"))],
    description="Required permission: comments.list_my",
)
@inject
async def get_my_document_comments(
    document_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> list[DocumentCommentResponse]:
    response = await document_service.get_document_comments(
        document_id=document_id, user_id=current_user.id
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return [DocumentCommentResponse.model_validate(comment) for comment in response]


@router.get(
    "/documents/{document_id}/comments",
    response_model=list[DocumentCommentResponse],
    dependencies=[Depends(require_permission("comments.list"))],
    description="Required permission: comments.list",
)
@inject
async def get_document_comments(
    document_id: UUID4,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> list[DocumentCommentResponse]:
    response = await document_service.get_document_comments(document_id=document_id)

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return [DocumentCommentResponse.model_validate(comment) for comment in response]


@router.post(
    "/documents/{document_id}/comments/me",
    response_model=DocumentCommentResponse,
    dependencies=[Depends(require_permission("comments.create_my"))],
    description="Required permission: comments.create_my",
)
@inject
async def create_my_comment(
    document_id: UUID4,
    current_user: CurrentUser,
    comment_create: DocumentCommentCreate,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentCommentResponse:
    response = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment_create,
        current_user_id=current_user.id,
        user_id=current_user.id,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return DocumentCommentResponse.model_validate(response)


@router.post(
    "/documents/{document_id}/comments",
    response_model=DocumentCommentResponse,
    dependencies=[Depends(require_permission("comments.create"))],
    description="Required permission: comments.create",
)
@inject
async def create_comment(
    document_id: UUID4,
    current_user: CurrentUser,
    comment_create: DocumentCommentCreate,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentCommentResponse:
    response = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment_create,
        current_user_id=current_user.id,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return DocumentCommentResponse.model_validate(response)


@router.post(
    "/documents/{document_id}/share/me",
    response_model=list[ShareDocumentResponse],
    dependencies=[Depends(require_permission("documents.share_my"))],
    description="Required permission: documents.share_my",
)
@inject
async def share_my_document(
    document_id: UUID4,
    current_user: CurrentUser,
    share_data: ShareDocumentCreate,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> list[ShareDocumentResponse]:
    response = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=current_user.id,
        user_id=current_user.id,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return [ShareDocumentResponse.model_validate(share) for share in response]


@router.post(
    "/documents/{document_id}/share",
    response_model=list[ShareDocumentResponse],
    dependencies=[Depends(require_permission("documents.share"))],
    description="Required permission: documents.share",
)
@inject
async def share_document(
    document_id: UUID4,
    current_user: CurrentUser,
    share_data: ShareDocumentCreate,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> list[ShareDocumentResponse]:
    response = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=current_user.id,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return [ShareDocumentResponse.model_validate(share) for share in response]


@router.get(
    "/documents/{document_id}/shared-users/me",
    response_model=list[ShareDocumentResponse],
    dependencies=[Depends(require_permission("documents.share_my"))],
    description="Required permission: documents.share_my",
)
@inject
async def get_my_shared_users(
    document_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> list[ShareDocumentResponse]:
    response = await document_service.get_shared_users(
        document_id=document_id, user_id=current_user.id
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return [ShareDocumentResponse.model_validate(share) for share in response]


@router.get(
    "/documents/{document_id}/shared-users",
    response_model=list[ShareDocumentResponse],
    dependencies=[Depends(require_permission("documents.share"))],
    description="Required permission: documents.share",
)
@inject
async def get_shared_users(
    document_id: UUID4,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> list[ShareDocumentResponse]:
    response = await document_service.get_shared_users(document_id=document_id)

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return [ShareDocumentResponse.model_validate(share) for share in response]


@router.delete(
    "/documents/{document_id}/share/{share_id}/me",
    response_model=Message,
    dependencies=[Depends(require_permission("documents.share_my"))],
    description="Required permission: documents.share_my",
)
@inject
async def delete_my_share_document(
    document_id: UUID4,
    share_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> Message:
    response = await document_service.delete_share_document(
        document_id=document_id,
        share_id=share_id,
        current_user_id=current_user.id,
        user_id=current_user.id,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return response


@router.delete(
    "/documents/{document_id}/share/{share_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("documents.share"))],
    description="Required permission: documents.share",
)
@inject
async def delete_share_document(
    document_id: UUID4,
    share_id: UUID4,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> Message:
    response = await document_service.delete_share_document(
        document_id=document_id,
        share_id=share_id,
        current_user_id=current_user.id,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return response


@router.post(
    "/documents/{document_id}/share-link/me",
    response_model=ShareLinkResponse,
    dependencies=[Depends(require_permission("documents.share_my"))],
    description="Required permission: documents.share_my",
)
@inject
async def generate_my_share_link(
    document_id: UUID4,
    current_user: CurrentUser,
    share_link_create: ShareLinkCreate,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> ShareLinkResponse:
    response = await document_service.generate_share_link(
        document_id=document_id,
        share_link_create=share_link_create,
        current_user_id=current_user.id,
        user_id=current_user.id,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return ShareLinkResponse(token=response)


@router.post(
    "/documents/{document_id}/share-link",
    response_model=ShareLinkResponse,
    dependencies=[Depends(require_permission("documents.share"))],
    description="Required permission: documents.share",
)
@inject
async def generate_share_link(
    document_id: UUID4,
    current_user: CurrentUser,
    share_link_create: ShareLinkCreate,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> ShareLinkResponse:
    response = await document_service.generate_share_link(
        document_id=document_id,
        share_link_create=share_link_create,
        current_user_id=current_user.id,
    )

    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)

    return ShareLinkResponse(token=response)


@router.post(
    "/documents/shared/{token}",
    description="Access document via share link (no authentication required)",
)
@inject
async def preview_shared_document(
    token: str,
    access_request: ShareLinkAccessRequest,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> FileResponse:
    document_id = await document_service.validate_share_link(
        token=token,
        password=access_request.password,
    )

    if isinstance(document_id, Error):
        raise HTTPException(status_code=document_id.code, detail=document_id.detail)

    file_path_response = await document_service.get_document_file_path(document_id)

    if isinstance(file_path_response, Error):
        raise HTTPException(
            status_code=file_path_response.code, detail=file_path_response.detail
        )

    file_path = Path(file_path_response)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Determine media type based on file extension
    media_type = _get_media_type(file_path.suffix.lower())

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        headers={"Content-Disposition": "inline"},
    )


@router.post(
    "/documents/{document_id}/reminders/me",
    response_model=ReminderResponse,
    dependencies=[Depends(require_permission("reminders.create_my"))],
    status_code=201,
    description="Required permission: reminders.create_my",
)
@inject
async def create_my_reminder(
    document_id: UUID4,
    reminder_create: ReminderCreate,
    current_user: CurrentUser,
    reminder_service: ReminderService = Depends(Provide["reminder_service"]),
) -> ReminderResponse:
    result = await reminder_service.create_reminder(
        document_id=document_id,
        reminder_create=reminder_create,
        current_user_id=current_user.id,
        user_id=current_user.id,
    )

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)

    return ReminderResponse.model_validate(result)


@router.post(
    "/documents/{document_id}/reminders",
    response_model=ReminderResponse,
    dependencies=[Depends(require_permission("reminders.create"))],
    status_code=201,
    description="Required permission: reminders.create",
)
@inject
async def create_reminder(
    document_id: UUID4,
    reminder_create: ReminderCreate,
    current_user: CurrentUser,
    reminder_service: ReminderService = Depends(Provide["reminder_service"]),
) -> ReminderResponse:
    result = await reminder_service.create_reminder(
        document_id=document_id,
        reminder_create=reminder_create,
        current_user_id=current_user.id,
    )

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)

    return ReminderResponse.model_validate(result)


@router.get(
    "/documents/{document_id}/reminders/me",
    response_model=list[ReminderResponse],
    dependencies=[Depends(require_permission("reminders.list_my"))],
    description="Required permission: reminders.list_my",
)
@inject
async def get_my_document_reminders(
    document_id: UUID4,
    current_user: CurrentUser,
    reminder_service: ReminderService = Depends(Provide["reminder_service"]),
) -> list[ReminderResponse]:
    result = await reminder_service.get_reminders_by_document(
        document_id=document_id, user_id=current_user.id
    )

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)

    return [ReminderResponse.model_validate(reminder) for reminder in result]


@router.get(
    "/documents/{document_id}/reminders",
    response_model=list[ReminderResponse],
    dependencies=[Depends(require_permission("reminders.list"))],
    description="Required permission: reminders.list",
)
@inject
async def get_document_reminders(
    document_id: UUID4,
    reminder_service: ReminderService = Depends(Provide["reminder_service"]),
) -> list[ReminderResponse]:
    result = await reminder_service.get_reminders_by_document(document_id=document_id)

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)

    return [ReminderResponse.model_validate(reminder) for reminder in result]


@router.post(
    "/documents/search",
    response_model=DocumentSearchResponse,
    dependencies=[Depends(require_permission("documents.search"))],
    description="Required permission: documents.search",
)
@inject
async def search_documents(
    request: DocumentSearchRequest,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentSearchResponse:
    result = await document_service.search_documents(request)

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code or 500, detail=result.detail)

    return result


@router.post(
    "/documents/search/me",
    response_model=DocumentSearchResponse,
    dependencies=[Depends(require_permission("documents.search_my"))],
    description="Required permission: documents.search_my",
)
@inject
async def search_my_documents(
    request: DocumentSearchRequest,
    current_user: CurrentUser,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentSearchResponse:
    result = await document_service.search_documents(request, user_id=current_user.id)

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code or 500, detail=result.detail)

    return result


@router.post(
    "/documents/{document_id}/versions/{version_id}/chat/me",
    response_model=DocumentChatResponse,
    dependencies=[Depends(require_permission("documents.chat_my"))],
    description="Required permission: documents.chat_my",
)
@inject
async def chat_my_document_version(
    document_id: UUID4,
    version_id: UUID4,
    current_user: CurrentUser,
    request: DocumentChatRequest,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentChatResponse:
    result = await document_service.chat_with_document_version(
        document_id, version_id, request.message, user_id=current_user.id
    )
    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)
    return DocumentChatResponse(message=result)


@router.post(
    "/documents/{document_id}/versions/{version_id}/chat",
    response_model=DocumentChatResponse,
    dependencies=[Depends(require_permission("documents.chat"))],
    description="Required permission: documents.chat",
)
@inject
async def chat_document_version(
    document_id: UUID4,
    version_id: UUID4,
    request: DocumentChatRequest,
    document_service: DocumentService = Depends(Provide["document_service"]),
) -> DocumentChatResponse:
    result = await document_service.chat_with_document_version(
        document_id, version_id, request.message
    )
    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)
    return DocumentChatResponse(message=result)
