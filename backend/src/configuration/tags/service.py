import logging
from typing import Protocol

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4
from starlette import status

from configuration.models import Tag
from configuration.tags.schemas import (
    PaginatedTagResponse,
    TagCreate,
    TagResponse,
    TagUpdate,
)
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class TagService(Protocol):
    async def get_all_tags_paginated(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
    ) -> PaginatedTagResponse | Error: ...

    async def create_tag(self, tag_create: TagCreate) -> Tag | Error: ...

    async def update_tag(self, tag_id: UUID4, tag_update: TagUpdate) -> Tag | Error: ...

    async def get_tag_by_id(self, tag_id: UUID4) -> Tag | Error: ...

    async def delete_tag(self, tag_id: UUID4) -> Message | Error: ...


class TagServiceImpl(TagService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_tags_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> PaginatedTagResponse | Error:
        logger.debug(
            "Fetching tags (page=%s, page_size=%s, search=%s",
            page,
            page_size,
            search,
        )

        skip = (page - 1) * page_size
        limit = page_size

        async with self._unit_of_work as uow:
            tags = await uow.tag_repository.get_all_tags_paginated(
                skip=skip,
                limit=limit,
                search=search,
            )
            total_rows = await uow.tag_repository.count_tags(
                search=search,
            )

        total_pages = (total_rows + page_size - 1) // page_size

        logger.info(
            "Tags fetched (page=%s, page_size=%s, total_rows=%s, total_pages=%s)",
            page,
            page_size,
            total_rows,
            total_pages,
        )
        return PaginatedTagResponse(
            data=[TagResponse.model_validate(tag) for tag in tags],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def create_tag(self, tag_create: TagCreate) -> Tag | Error:
        logger.info("Creating tag (title=%s)", tag_create.title)
        async with self._unit_of_work as uow:
            title_exists = await uow.tag_repository.check_title_exists(tag_create.title)
            if title_exists:
                logger.warning(
                    "Tag creation rejected: title already exists (title=%s)",
                    tag_create.title,
                )
                return Error(
                    detail="Tag title already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            tag = await uow.tag_repository.create_tag(tag_create)
            await uow.commit()

        logger.info(
            "Tag created successfully (id=%s, title=%s)",
            tag.id,
            tag.title,
        )
        return tag

    async def update_tag(self, tag_id: UUID4, tag_update: TagUpdate) -> Tag | Error:
        logger.info("Updating tag (id=%s)", tag_id)

        async with self._unit_of_work as uow:
            existing_tag = await uow.tag_repository.get_tag_by_id(tag_id)
            if not existing_tag:
                logger.warning("Tag update failed: not found (id=%s)", tag_id)
                return Error(detail="Tag not found", code=status.HTTP_404_NOT_FOUND)

            if existing_tag.title != tag_update.title:
                title_exists = await uow.tag_repository.check_title_exists(
                    tag_update.title
                )
                if title_exists:
                    logger.warning(
                        "Tag update rejected: title conflict (id=%s, title=%s)",
                        tag_id,
                        tag_update.title,
                    )
                    return Error(
                        detail="Tag title already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

            updated_tag = await uow.tag_repository.update_tag(existing_tag, tag_update)
            await uow.commit()

        logger.info("Tag updated successfully (id=%s)", tag_id)
        return updated_tag

    async def get_tag_by_id(self, tag_id: UUID4) -> Tag | Error:
        logger.debug("Fetching tag by id=%s", tag_id)

        async with self._unit_of_work as uow:
            tag = await uow.tag_repository.get_tag_by_id(tag_id)
            if not tag:
                logger.warning("Tag not found (id=%s)", tag_id)
                return Error(detail="Tag not found", code=status.HTTP_404_NOT_FOUND)

            logger.debug("Tag found (id=%s)", tag_id)
            return tag

    async def delete_tag(self, tag_id: UUID4) -> Message | Error:
        logger.info("Deleting tag (id=%s)", tag_id)

        async with self._unit_of_work as uow:
            tag_to_delete = await uow.tag_repository.get_tag_by_id(tag_id)
            if not tag_to_delete:
                logger.warning("Tag deletion failed: not found (id=%s)", tag_id)
                return Error(detail="Tag not found", code=status.HTTP_404_NOT_FOUND)

            await uow.tag_repository.delete_tag(tag_to_delete)
            await uow.commit()

        logger.info("Tag deleted successfully (id=%s)", tag_id)
        return Message(detail="Tag deleted successfully")
