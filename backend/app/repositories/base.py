"""Generic async repository base.

Concrete repositories (UserRepository, InterviewRepository, ...) subclass this
and add domain-specific query methods. Repositories operate on a session that
is *passed in* — they never open or commit transactions themselves; that is the
caller's / Unit of Work's responsibility.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: uuid.UUID) -> ModelType | None:
        return await self.session.get(self.model, id_)

    async def list(self, limit: int = 100, offset: int = 0) -> list[ModelType]:
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def add(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelType) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def exists(self, **filters: Any) -> bool:
        conditions = [getattr(self.model, k) == v for k, v in filters.items()]
        result = await self.session.execute(
            select(self.model.id).where(*conditions).limit(1)
        )
        return result.scalar_one_or_none() is not None
