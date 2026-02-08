import logging
from typing import Protocol

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4
from starlette import status

from configuration.subcategories.schemas import (
    PaginatedSubcategoryResponse,
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class SubcategoryService(Protocol):
    async def get_all_subcategories_paginated(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
        category_id: UUID4 | None = None,
    ) -> PaginatedSubcategoryResponse | Error: ...

    async def get_all_subcategories_by_category(
        self, category_id: UUID4
    ) -> list[SubcategoryResponse] | Error: ...

    async def create_subcategory(
        self, subcategory_create: SubcategoryCreate
    ) -> SubcategoryResponse | Error: ...

    async def update_subcategory(
        self, subcategory_id: UUID4, subcategory_update: SubcategoryUpdate
    ) -> SubcategoryResponse | Error: ...

    async def get_subcategory_by_id(
        self, subcategory_id: UUID4
    ) -> SubcategoryResponse | Error: ...

    async def delete_subcategory(self, subcategory_id: UUID4) -> Message | Error: ...


class SubcategoryServiceImpl(SubcategoryService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_subcategories_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        category_id: UUID4 | None = None,
    ) -> PaginatedSubcategoryResponse | Error:
        logger.debug(
            "Fetching subcategories (page=%s, page_size=%s, search=%s, category_id=%s)",
            page,
            page_size,
            search,
            category_id,
        )

        skip = (page - 1) * page_size
        limit = page_size

        async with self._unit_of_work as uow:
            if category_id:
                category = await uow.category_repository.get_category_by_id(category_id)
                if not category:
                    logger.warning("Category not found (id=%s)", category_id)
                    return Error(
                        detail="Category not found", code=status.HTTP_404_NOT_FOUND
                    )

            subcategories = (
                await uow.subcategory_repository.get_all_subcategories_paginated(
                    skip=skip,
                    limit=limit,
                    search=search,
                    category_id=category_id,
                )
            )
            total_rows = await uow.subcategory_repository.count_subcategories(
                search=search,
                category_id=category_id,
            )
            data = []
            for subcategory in subcategories:
                category = await uow.category_repository.get_category_by_id(
                    subcategory.category_id
                )
                data.append(
                    SubcategoryResponse(
                        id=subcategory.id,
                        title=subcategory.title,
                        category_id=subcategory.category_id,
                        category_title=category.title,
                        created_at=subcategory.created_at,
                    )
                )

        total_pages = (total_rows + page_size - 1) // page_size

        logger.info(
            "Subcategories fetched (page=%s, page_size=%s, total_rows=%s, total_pages=%s)",
            page,
            page_size,
            total_rows,
            total_pages,
        )

        return PaginatedSubcategoryResponse(
            data=data,
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def get_all_subcategories_by_category(
        self, category_id: UUID4
    ) -> list[SubcategoryResponse] | Error:
        logger.debug("Fetching all subcategories for category (id=%s)", category_id)

        async with self._unit_of_work as uow:
            category = await uow.category_repository.get_category_by_id(category_id)
            if not category:
                logger.warning("Category not found (id=%s)", category_id)
                return Error(
                    detail="Category not found", code=status.HTTP_404_NOT_FOUND
                )

            subcategories = (
                await uow.subcategory_repository.get_all_subcategories_paginated(
                    skip=0,
                    limit=10000,
                    category_id=category_id,
                )
            )

            data = []
            for subcategory in subcategories:
                data.append(
                    SubcategoryResponse(
                        id=subcategory.id,
                        title=subcategory.title,
                        category_id=subcategory.category_id,
                        category_title=category.title,
                        created_at=subcategory.created_at,
                    )
                )

        logger.info(
            "Subcategories fetched for category (id=%s, count=%s)",
            category_id,
            len(data),
        )
        return data

    async def create_subcategory(
        self, subcategory_create: SubcategoryCreate
    ) -> SubcategoryResponse | Error:
        logger.info(
            "Creating subcategory (title=%s, category_id=%s)",
            subcategory_create.title,
            subcategory_create.category_id,
        )
        async with self._unit_of_work as uow:
            category = await uow.category_repository.get_category_by_id(
                subcategory_create.category_id
            )
            if not category:
                logger.warning(
                    "Subcategory creation rejected: category not found (category_id=%s)",
                    subcategory_create.category_id,
                )
                return Error(
                    detail="Category not found", code=status.HTTP_404_NOT_FOUND
                )

            title_exists = await uow.subcategory_repository.check_title_exists(
                subcategory_create.title
            )
            if title_exists:
                logger.warning(
                    "Subcategory creation rejected: title already exists (title=%s)",
                    subcategory_create.title,
                )
                return Error(
                    detail="Subcategory title already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            subcategory = await uow.subcategory_repository.create_subcategory(
                subcategory_create
            )
            await uow.commit()

        logger.info(
            "Subcategory created successfully (id=%s, title=%s)",
            subcategory.id,
            subcategory.title,
        )
        return SubcategoryResponse(
            id=subcategory.id,
            title=subcategory.title,
            category_id=subcategory.category_id,
            category_title=category.title,
            created_at=subcategory.created_at,
        )

    async def update_subcategory(
        self, subcategory_id: UUID4, subcategory_update: SubcategoryUpdate
    ) -> SubcategoryResponse | Error:
        logger.info("Updating subcategory (id=%s)", subcategory_id)

        async with self._unit_of_work as uow:
            existing_subcategory = (
                await uow.subcategory_repository.get_subcategory_by_id(subcategory_id)
            )
            if not existing_subcategory:
                logger.warning(
                    "Subcategory update failed: not found (id=%s)", subcategory_id
                )
                return Error(
                    detail="Subcategory not found", code=status.HTTP_404_NOT_FOUND
                )

            category = await uow.category_repository.get_category_by_id(
                subcategory_update.category_id
            )
            if not category:
                logger.warning(
                    "Subcategory update rejected: category not found (category_id=%s)",
                    subcategory_update.category_id,
                )
                return Error(
                    detail="Category not found", code=status.HTTP_404_NOT_FOUND
                )

            if existing_subcategory.title != subcategory_update.title:
                title_exists = await uow.subcategory_repository.check_title_exists(
                    subcategory_update.title
                )
                if title_exists:
                    logger.warning(
                        "Subcategory update rejected: title conflict (id=%s, title=%s)",
                        subcategory_id,
                        subcategory_update.title,
                    )
                    return Error(
                        detail="Subcategory title already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

            updated_subcategory = await uow.subcategory_repository.update_subcategory(
                existing_subcategory, subcategory_update
            )
            await uow.commit()

        logger.info("Subcategory updated successfully (id=%s)", subcategory_id)
        return SubcategoryResponse(
            id=updated_subcategory.id,
            title=updated_subcategory.title,
            category_id=updated_subcategory.category_id,
            category_title=category.title,
            created_at=updated_subcategory.created_at,
        )

    async def get_subcategory_by_id(
        self, subcategory_id: UUID4
    ) -> SubcategoryResponse | Error:
        logger.debug("Fetching subcategory by id=%s", subcategory_id)

        async with self._unit_of_work as uow:
            subcategory = await uow.subcategory_repository.get_subcategory_by_id(
                subcategory_id
            )
            if not subcategory:
                logger.warning("Subcategory not found (id=%s)", subcategory_id)
                return Error(
                    detail="Subcategory not found", code=status.HTTP_404_NOT_FOUND
                )

            # Fetch category to get title
            category = await uow.category_repository.get_category_by_id(
                subcategory.category_id
            )
            category_title = category.title if category else ""

            logger.debug("Subcategory found (id=%s)", subcategory_id)
            return SubcategoryResponse(
                id=subcategory.id,
                title=subcategory.title,
                category_id=subcategory.category_id,
                category_title=category_title,
                created_at=subcategory.created_at,
            )

    async def delete_subcategory(self, subcategory_id: UUID4) -> Message | Error:
        logger.info("Deleting subcategory (id=%s)", subcategory_id)

        async with self._unit_of_work as uow:
            subcategory_to_delete = (
                await uow.subcategory_repository.get_subcategory_by_id(subcategory_id)
            )
            if not subcategory_to_delete:
                logger.warning(
                    "Subcategory deletion failed: not found (id=%s)", subcategory_id
                )
                return Error(
                    detail="Subcategory not found", code=status.HTTP_404_NOT_FOUND
                )

            await uow.subcategory_repository.delete_subcategory(subcategory_to_delete)
            await uow.commit()

        logger.info("Subcategory deleted successfully (id=%s)", subcategory_id)
        return Message(detail="Subcategory deleted successfully")
