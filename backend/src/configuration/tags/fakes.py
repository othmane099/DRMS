from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import UUID4
from starlette import status

from configuration.models import Tag
from configuration.tags.repository import TagRepository
from configuration.tags.schemas import (
    PaginatedTagResponse,
    TagCreate,
    TagResponse,
    TagUpdate,
)
from configuration.tags.service import TagService
from schemas import Error, Message


class FakeTagRepository(TagRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.tags: dict[UUID, Tag] = {}

    async def get_all_tags_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> list[Tag]:
        all_tags = list(self.tags.values())

        if search:
            search_lower = search.lower()
            all_tags = [t for t in all_tags if search_lower in t.title.lower()]

        return sorted(all_tags, key=lambda x: x.title)[skip : skip + limit]

    async def count_tags(
        self,
        search: str | None = None,
    ) -> int:
        all_tags = list(self.tags.values())

        if search:
            search_lower = search.lower()
            all_tags = [t for t in all_tags if search_lower in t.title.lower()]

        return len(all_tags)

    async def check_title_exists(self, title: str) -> bool:
        return any(t.title.lower() == title.lower() for t in self.tags.values())

    async def get_tag_by_id(self, tag_id: UUID4) -> Tag | None:
        return self.tags.get(tag_id)

    async def create_tag(self, tag_create: TagCreate) -> Tag:
        tag = Tag(
            id=uuid4(),
            title=tag_create.title,
            created_at=datetime.now(UTC),
        )
        self.tags[tag.id] = tag
        return tag

    async def update_tag(self, tag: Tag, tag_update: TagUpdate) -> Tag:
        tag.title = tag_update.title
        tag.updated_at = datetime.now(UTC)
        return tag

    async def delete_tag(self, tag: Tag) -> None:
        if tag.id in self.tags:
            del self.tags[tag.id]


class FakeTagService(TagService):
    def __init__(self) -> None:
        self.tags: dict[UUID, Tag] = {}

    async def get_all_tags_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> PaginatedTagResponse | Error:
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

        all_tags = list(self.tags.values())

        if search:
            search_lower = search.lower()
            all_tags = [t for t in all_tags if search_lower in t.title.lower()]

        sorted_tags = sorted(all_tags, key=lambda x: x.title)
        paginated_tags = sorted_tags[skip : skip + page_size]

        total_rows = len(all_tags)
        total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0

        return PaginatedTagResponse(
            data=[TagResponse.model_validate(tag) for tag in paginated_tags],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def create_tag(self, tag_create: TagCreate) -> Tag | Error:
        title_exists = any(
            t.title.lower() == tag_create.title.lower() for t in self.tags.values()
        )
        if title_exists:
            return Error(
                detail="Tag title already exists", code=status.HTTP_400_BAD_REQUEST
            )

        tag = Tag(
            id=uuid4(),
            title=tag_create.title,
            created_at=datetime.now(UTC),
        )
        self.tags[tag.id] = tag
        return tag

    async def update_tag(self, tag_id: UUID4, tag_update: TagUpdate) -> Tag | Error:
        tag = self.tags.get(tag_id)
        if not tag:
            return Error(detail="Tag not found", code=status.HTTP_404_NOT_FOUND)

        if tag.title != tag_update.title:
            title_exists = any(
                t.title.lower() == tag_update.title.lower() and t.id != tag_id
                for t in self.tags.values()
            )
            if title_exists:
                return Error(
                    detail="Tag title already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        tag.title = tag_update.title
        tag.updated_at = datetime.now(UTC)
        return tag

    async def get_tag_by_id(self, tag_id: UUID4) -> Tag | Error:
        tag = self.tags.get(tag_id)
        if not tag:
            return Error(detail="Tag not found", code=status.HTTP_404_NOT_FOUND)
        return tag

    async def delete_tag(self, tag_id: UUID4) -> Message | Error:
        tag = self.tags.get(tag_id)
        if not tag:
            return Error(detail="Tag not found", code=status.HTTP_404_NOT_FOUND)
        del self.tags[tag_id]
        return Message(detail="Tag deleted successfully")
