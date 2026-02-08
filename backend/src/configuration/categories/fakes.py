from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import UUID4
from starlette import status

from configuration.categories.repository import CategoryRepository
from configuration.categories.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    PaginatedCategoryResponse,
)
from configuration.categories.service import CategoryService
from configuration.models import Category
from schemas import Error, Message


class FakeCategoryRepository(CategoryRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.categories: dict[UUID, Category] = {}

    async def get_all_categories_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> list[tuple[Category, int]]:
        all_categories = list(self.categories.values())

        if search:
            search_lower = search.lower()
            all_categories = [
                s for s in all_categories if search_lower in s.title.lower()
            ]

        categories = sorted(all_categories, key=lambda x: x.title)[skip : skip + limit]
        return [(category, 0) for category in categories]

    async def count_categories(
        self,
        search: str | None = None,
    ) -> int:
        all_categories = list(self.categories.values())

        if search:
            search_lower = search.lower()
            all_categories = [
                s for s in all_categories if search_lower in s.title.lower()
            ]

        return len(all_categories)

    async def check_title_exists(self, title: str) -> bool:
        return any(s.title.lower() == title.lower() for s in self.categories.values())

    async def check_title_exists_excluding_id(
        self, title: str, category_id: UUID4
    ) -> bool:
        return any(
            s.title.lower() == title.lower() and s.id != category_id
            for s in self.categories.values()
        )

    async def get_category_by_id(self, category_id: UUID4) -> Category | None:
        category = self.categories.get(category_id)
        if category:
            category.subcategories = []  # type: ignore
            category.subcategory_count = 0  # type: ignore
        return category

    async def create_category(self, category_create: CategoryCreate) -> Category:
        category = Category(
            id=uuid4(),
            title=category_create.title,
            created_at=datetime.now(UTC),
        )
        category.subcategories = []  # type: ignore
        category.subcategory_count = 0  # type: ignore
        self.categories[category.id] = category
        return category

    async def update_category(
        self, category: Category, category_update: CategoryUpdate
    ) -> Category:
        category.title = category_update.title
        category.updated_at = datetime.now(UTC)
        category.subcategories = []  # type: ignore
        category.subcategory_count = 0  # type: ignore
        return category

    async def delete_category(self, category: Category) -> None:
        if category.id in self.categories:
            del self.categories[category.id]


class FakeCategoryService(CategoryService):
    def __init__(self) -> None:
        self.categories: dict[UUID, Category] = {}

    async def get_all_categories_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> PaginatedCategoryResponse | Error:
        if page < 1:
            return Error(
                detail="Page must be greater than or equal to 1",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if page_size < 1:
            return Error(
                detail="Page size must be greater than or equal to 1",
                code=status.HTTP_400_BAD_REQUEST,
            )

        skip = (page - 1) * page_size

        all_categories = list(self.categories.values())

        if search:
            search_lower = search.lower()
            all_categories = [
                s for s in all_categories if search_lower in s.title.lower()
            ]

        sorted_categories = sorted(all_categories, key=lambda x: x.title)
        paginated_categories = sorted_categories[skip : skip + page_size]

        total_rows = len(all_categories)
        total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0

        for category in paginated_categories:
            category.subcategory_count = 0  # type: ignore

        return PaginatedCategoryResponse(
            data=[
                CategoryResponse.model_validate(category)
                for category in paginated_categories
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
    ) -> Category | Error:
        title_exists = any(
            s.title.lower() == category_create.title.lower()
            for s in self.categories.values()
        )
        if title_exists:
            return Error(
                detail="Category title already exists", code=status.HTTP_400_BAD_REQUEST
            )

        category = Category(
            id=uuid4(),
            title=category_create.title,
            created_at=datetime.now(UTC),
        )
        category.subcategories = []  # type: ignore
        category.subcategory_count = 0  # type: ignore
        self.categories[category.id] = category
        return category

    async def update_category(
        self, category_id: UUID4, category_update: CategoryUpdate
    ) -> Category | Error:
        category = self.categories.get(category_id)
        if not category:
            return Error(detail="Category not found", code=status.HTTP_404_NOT_FOUND)

        if category.title != category_update.title:
            title_exists = any(
                s.title.lower() == category_update.title.lower() and s.id != category_id
                for s in self.categories.values()
            )
            if title_exists:
                return Error(
                    detail="Category title already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        category.title = category_update.title
        category.updated_at = datetime.now(UTC)
        category.subcategories = []  # type: ignore
        category.subcategory_count = 0  # type: ignore
        return category

    async def get_category_by_id(self, category_id: UUID4) -> Category | Error:
        category = self.categories.get(category_id)
        if not category:
            return Error(detail="Category not found", code=status.HTTP_404_NOT_FOUND)
        category.subcategories = []  # type: ignore
        category.subcategory_count = 0  # type: ignore
        return category

    async def delete_category(self, category_id: UUID4) -> Message | Error:
        category = self.categories.get(category_id)
        if not category:
            return Error(detail="Category not found", code=status.HTTP_404_NOT_FOUND)
        del self.categories[category_id]
        return Message(detail="Category deleted successfully")
