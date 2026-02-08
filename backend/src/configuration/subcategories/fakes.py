from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import UUID4
from starlette import status

from configuration.models import Subcategory
from configuration.subcategories.repository import SubcategoryRepository
from configuration.subcategories.schemas import (
    PaginatedSubcategoryResponse,
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)
from configuration.subcategories.service import SubcategoryService
from schemas import Error, Message


class FakeSubcategoryRepository(SubcategoryRepository):
    def __init__(
        self,
        session: Any = None,
        subcategories: dict[UUID, Subcategory] | None = None,
    ):
        self.session = session
        self.subcategories = subcategories if subcategories is not None else {}

    async def get_all_subcategories_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        category_id: UUID4 | None = None,
    ) -> list[Subcategory]:
        all_subcategories = list(self.subcategories.values())

        if category_id:
            all_subcategories = [
                s for s in all_subcategories if s.category_id == category_id
            ]

        if search:
            search_lower = search.lower()
            all_subcategories = [
                s for s in all_subcategories if search_lower in s.title.lower()
            ]

        return sorted(all_subcategories, key=lambda x: x.title)[skip : skip + limit]

    async def count_subcategories(
        self,
        search: str | None = None,
        category_id: UUID4 | None = None,
    ) -> int:
        all_subcategories = list(self.subcategories.values())

        if category_id:
            all_subcategories = [
                s for s in all_subcategories if s.category_id == category_id
            ]

        if search:
            search_lower = search.lower()
            all_subcategories = [
                s for s in all_subcategories if search_lower in s.title.lower()
            ]

        return len(all_subcategories)

    async def check_title_exists(self, title: str) -> bool:
        return any(
            s.title.lower() == title.lower() for s in self.subcategories.values()
        )

    async def check_title_exists_excluding_id(
        self, title: str, subcategory_id: UUID4
    ) -> bool:
        return any(
            s.title.lower() == title.lower() and s.id != subcategory_id
            for s in self.subcategories.values()
        )

    async def get_subcategory_by_id(self, subcategory_id: UUID4) -> Subcategory | None:
        return self.subcategories.get(subcategory_id)

    async def create_subcategory(
        self, subcategory_create: SubcategoryCreate
    ) -> Subcategory:
        subcategory = Subcategory(
            id=uuid4(),
            title=subcategory_create.title,
            category_id=subcategory_create.category_id,
            created_at=datetime.now(UTC),
        )
        self.subcategories[subcategory.id] = subcategory
        return subcategory

    async def update_subcategory(
        self, subcategory: Subcategory, subcategory_update: SubcategoryUpdate
    ) -> Subcategory:
        subcategory.title = subcategory_update.title
        subcategory.category_id = subcategory_update.category_id
        subcategory.updated_at = datetime.now(UTC)
        return subcategory

    async def delete_subcategory(self, subcategory: Subcategory) -> None:
        if subcategory.id in self.subcategories:
            del self.subcategories[subcategory.id]


class FakeSubcategoryService(SubcategoryService):
    def __init__(self) -> None:
        self.subcategories: dict[UUID, Subcategory] = {}
        self.categories: dict[UUID, Any] = {}

    async def get_all_subcategories_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        category_id: UUID4 | None = None,
    ) -> PaginatedSubcategoryResponse | Error:
        if category_id and category_id not in self.categories:
            return Error(detail="Category not found", code=status.HTTP_404_NOT_FOUND)

        skip = (page - 1) * page_size

        all_subcategories = list(self.subcategories.values())

        if category_id:
            all_subcategories = [
                s for s in all_subcategories if s.category_id == category_id
            ]

        if search:
            search_lower = search.lower()
            all_subcategories = [
                s for s in all_subcategories if search_lower in s.title.lower()
            ]

        sorted_subcategories = sorted(all_subcategories, key=lambda x: x.title)
        paginated_subcategories = sorted_subcategories[skip : skip + page_size]

        total_rows = len(all_subcategories)
        total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0

        data = []
        for subcategory in paginated_subcategories:
            category = self.categories.get(subcategory.category_id)
            data.append(
                SubcategoryResponse(
                    id=subcategory.id,
                    title=subcategory.title,
                    category_id=subcategory.category_id,
                    category_title=category.title if category else "",
                    created_at=subcategory.created_at,
                )
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
        if category_id not in self.categories:
            return Error(detail="Category not found", code=status.HTTP_404_NOT_FOUND)

        all_subcategories = [
            s for s in self.subcategories.values() if s.category_id == category_id
        ]
        sorted_subcategories = sorted(all_subcategories, key=lambda x: x.title)

        category = self.categories.get(category_id)
        return [
            SubcategoryResponse(
                id=subcategory.id,
                title=subcategory.title,
                category_id=subcategory.category_id,
                category_title=category.title if category else "",
                created_at=subcategory.created_at,
            )
            for subcategory in sorted_subcategories
        ]

    async def create_subcategory(
        self, subcategory_create: SubcategoryCreate
    ) -> SubcategoryResponse | Error:
        if subcategory_create.category_id not in self.categories:
            return Error(detail="Category not found", code=status.HTTP_404_NOT_FOUND)

        title_exists = any(
            s.title.lower() == subcategory_create.title.lower()
            for s in self.subcategories.values()
        )
        if title_exists:
            return Error(
                detail="Subcategory title already exists",
                code=status.HTTP_400_BAD_REQUEST,
            )

        category = self.categories.get(subcategory_create.category_id)
        subcategory = Subcategory(
            id=uuid4(),
            title=subcategory_create.title,
            category_id=subcategory_create.category_id,
            created_at=datetime.now(UTC),
        )
        self.subcategories[subcategory.id] = subcategory

        return SubcategoryResponse(
            id=subcategory.id,
            title=subcategory.title,
            category_id=subcategory.category_id,
            category_title=category.title if category else "",
            created_at=subcategory.created_at,
        )

    async def update_subcategory(
        self, subcategory_id: UUID4, subcategory_update: SubcategoryUpdate
    ) -> SubcategoryResponse | Error:
        subcategory = self.subcategories.get(subcategory_id)
        if not subcategory:
            return Error(detail="Subcategory not found", code=status.HTTP_404_NOT_FOUND)

        if subcategory_update.category_id not in self.categories:
            return Error(detail="Category not found", code=status.HTTP_404_NOT_FOUND)

        if subcategory.title != subcategory_update.title:
            title_exists = any(
                s.title.lower() == subcategory_update.title.lower()
                and s.id != subcategory_id
                for s in self.subcategories.values()
            )
            if title_exists:
                return Error(
                    detail="Subcategory title already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        subcategory.title = subcategory_update.title
        subcategory.category_id = subcategory_update.category_id
        subcategory.updated_at = datetime.now(UTC)

        category = self.categories.get(subcategory.category_id)
        return SubcategoryResponse(
            id=subcategory.id,
            title=subcategory.title,
            category_id=subcategory.category_id,
            category_title=category.title if category else "",
            created_at=subcategory.created_at,
        )

    async def get_subcategory_by_id(
        self, subcategory_id: UUID4
    ) -> SubcategoryResponse | Error:
        subcategory = self.subcategories.get(subcategory_id)
        if not subcategory:
            return Error(detail="Subcategory not found", code=status.HTTP_404_NOT_FOUND)

        category = self.categories.get(subcategory.category_id)
        return SubcategoryResponse(
            id=subcategory.id,
            title=subcategory.title,
            category_id=subcategory.category_id,
            category_title=category.title if category else "",
            created_at=subcategory.created_at,
        )

    async def delete_subcategory(self, subcategory_id: UUID4) -> Message | Error:
        subcategory = self.subcategories.get(subcategory_id)
        if not subcategory:
            return Error(detail="Subcategory not found", code=status.HTTP_404_NOT_FOUND)
        del self.subcategories[subcategory_id]
        return Message(detail="Subcategory deleted successfully")
