import logging
from typing import Protocol

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4
from starlette import status

from configuration.categories.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CategoryWithSubcategoriesResponse,
    PaginatedCategoryResponse,
)
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class CategoryService(Protocol):
    async def get_all_categories_paginated(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
    ) -> PaginatedCategoryResponse | Error: ...

    async def create_category(
        self, category_create: CategoryCreate
    ) -> CategoryResponse | Error: ...

    async def update_category(
        self, category_id: UUID4, category_update: CategoryUpdate
    ) -> CategoryResponse | Error: ...

    async def get_category_by_id(
        self, category_id: UUID4
    ) -> CategoryWithSubcategoriesResponse | Error: ...

    async def delete_category(self, category_id: UUID4) -> Message | Error: ...


class CategoryServiceImpl(CategoryService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_categories_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> PaginatedCategoryResponse | Error:
        logger.debug(
            "Fetching categories (page=%s, page_size=%s, search=%s)",
            page,
            page_size,
            search,
        )

        skip = (page - 1) * page_size
        limit = page_size

        async with self._unit_of_work as uow:
            result = await uow.category_repository.get_all_categories_paginated(
                skip=skip,
                limit=limit,
                search=search,
            )
            total_rows = await uow.category_repository.count_categories(
                search=search,
            )

        total_pages = (total_rows + page_size - 1) // page_size

        logger.info(
            "Categories fetched (page=%s, page_size=%s, total_rows=%s, total_pages=%s)",
            page,
            page_size,
            total_rows,
            total_pages,
        )
        return PaginatedCategoryResponse(
            data=[
                CategoryResponse(
                    id=category.id,
                    title=category.title,
                    subcategory_count=subcategory_count,
                    created_at=category.created_at,
                )
                for category, subcategory_count in result
            ],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def create_category(
        self, category_create: CategoryCreate
    ) -> CategoryResponse | Error:
        logger.info("Creating category (title=%s)", category_create.title)
        async with self._unit_of_work as uow:
            title_exists = await uow.category_repository.check_title_exists(
                category_create.title
            )
            if title_exists:
                logger.warning(
                    "Category creation rejected: title already exists (title=%s)",
                    category_create.title,
                )
                return Error(
                    detail="Category title already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            category = await uow.category_repository.create_category(category_create)
            await uow.commit()

        logger.info(
            "Category created successfully (id=%s, title=%s)",
            category.id,
            category.title,
        )
        return CategoryResponse(
            id=category.id,
            title=category.title,
            subcategory_count=len(category.subcategories),
            created_at=category.created_at,
        )

    async def update_category(
        self, category_id: UUID4, category_update: CategoryUpdate
    ) -> CategoryResponse | Error:
        logger.info("Updating category (id=%s)", category_id)

        async with self._unit_of_work as uow:
            existing_category = await uow.category_repository.get_category_by_id(
                category_id
            )
            if not existing_category:
                logger.warning("Category update failed: not found (id=%s)", category_id)
                return Error(
                    detail="Category not found", code=status.HTTP_404_NOT_FOUND
                )

            if existing_category.title != category_update.title:
                title_exists = await uow.category_repository.check_title_exists(
                    category_update.title
                )
                if title_exists:
                    logger.warning(
                        "Category update rejected: title conflict (id=%s, title=%s)",
                        category_id,
                        category_update.title,
                    )
                    return Error(
                        detail="Category title already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

            updated_category = await uow.category_repository.update_category(
                existing_category, category_update
            )
            await uow.commit()

        logger.info("Category updated successfully (id=%s)", category_id)
        return CategoryResponse(
            id=category_id,
            title=updated_category.title,
            subcategory_count=len(updated_category.subcategories),
            created_at=updated_category.created_at,
        )

    async def get_category_by_id(
        self, category_id: UUID4
    ) -> CategoryWithSubcategoriesResponse | Error:
        logger.debug("Fetching category by id=%s", category_id)

        async with self._unit_of_work as uow:
            category = await uow.category_repository.get_category_by_id(category_id)
            if not category:
                logger.warning("Category not found (id=%s)", category_id)
                return Error(
                    detail="Category not found", code=status.HTTP_404_NOT_FOUND
                )

            logger.debug("Category found (id=%s)", category_id)
            return CategoryWithSubcategoriesResponse(
                id=category.id,
                title=category.title,
                subcategory_count=len(category.subcategories),
                subcategories=category.subcategories,
                created_at=category.created_at,
            )

    async def delete_category(self, category_id: UUID4) -> Message | Error:
        logger.info("Deleting category (id=%s)", category_id)

        async with self._unit_of_work as uow:
            category_to_delete = await uow.category_repository.get_category_by_id(
                category_id
            )
            if not category_to_delete:
                logger.warning(
                    "Category deletion failed: not found (id=%s)", category_id
                )
                return Error(
                    detail="Category not found", code=status.HTTP_404_NOT_FOUND
                )

            await uow.category_repository.delete_category(category_to_delete)
            await uow.commit()

        logger.info("Category deleted successfully (id=%s)", category_id)
        return Message(detail="Category deleted successfully")
